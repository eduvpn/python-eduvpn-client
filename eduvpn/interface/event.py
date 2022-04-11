from typing import Optional
import logging
import webbrowser
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2.rfc6749.errors import (
    InvalidGrantError as InvalidOauthGrantError)
from .. import storage
from .. import nm
from .. import oauth2
from ..app import Application
from ..server import (
    AnyServer, ConfiguredServer, InstituteAccessServer,
    SecureInternetServer, OrganisationServer, CustomServer,
    SecureInternetLocation, Profile)
from .error import get_error_message
from ..session import active_session_states
from ..utils import run_in_background_thread


logger = logging.getLogger(__name__)


@run_in_background_thread('start-oauth-web-server')
def on_setup_oauth(app: Application, server: AnyServer):
    try:
        server_info = app.server_db.get_server_info(server)
    except Exception as e:
        logger.error("error getting server info", exc_info=True)
        enter_error_state_threadsafe(app, e)
        return

    def oauth_token_callback(oauth_session: Optional[OAuth2Session]):
        if oauth_session:
            app.interface_transition_threadsafe('oauth_setup_success', oauth_session)
        else:
            # The process has been canceled by the user through the app,
            # which already schedules the state transition so we don't need
            # to do that here.
            pass

    webserver, browser_url = oauth2.run_challenge_in_background(
        server_info.token_endpoint, server_info.authorization_endpoint, app.variant, oauth_token_callback)
    if isinstance(server, OrganisationServer):
        secure_internet = app.server_db.get_secure_internet_server(server.secure_internet_home)
        if secure_internet:
            browser_url = secure_internet.authentication_url(server, browser_url)
        else:
            logger.warning(f"missing 'secure internet server' for {server!r}")
    logger.info(f"opening browser with {browser_url}")
    app.interface_transition_threadsafe('ready_for_oauth_setup', webserver)
    webbrowser.open(browser_url)


@run_in_background_thread('oauth-refresh')
def on_refresh_oauth_token(app: Application,
                           server: AnyServer,
                           oauth_session: OAuth2Session):
    try:
        server_info = app.server_db.get_server_info(server)
    except Exception as e:
        logger.error("error getting server info", exc_info=True)
        enter_error_state_threadsafe(app, e)
        return
    try:
        oauth_session.refresh_token(token_url=server_info.token_endpoint)
    except InvalidOauthGrantError as e:
        logger.warning(f'Error refreshing OAuth token: {e}')
        app.interface_transition_threadsafe('oauth_refresh_failed')
    else:
        app.interface_transition_threadsafe('oauth_refresh_success')


@run_in_background_thread('load-server-info')
def on_start_connection(app: Application,
                        server: AnyServer,
                        oauth_session: OAuth2Session,
                        location: Optional[SecureInternetServer] = None):
    try:
        server_info = app.server_db.get_server_info(server)
    except Exception as e:
        logger.error("error getting server info", exc_info=True)
        enter_error_state_threadsafe(app, e)
        return
    profile_server_info = server_info
    profile_server: ConfiguredServer

    if isinstance(server, OrganisationServer):
        if not location:
            locations = [server for server in app.server_db.all()
                         if isinstance(server, SecureInternetServer)]
            app.interface_transition_threadsafe(
                'choose_secure_internet_location', server, oauth_session, locations)
            return
        else:
            try:
                location_info = app.server_db.get_server_info(location)
            except Exception as e:
                logger.error("error getting server info", exc_info=True)
                enter_error_state_threadsafe(app, e)
                return
            profile_server_info = location_info
            profile_server = SecureInternetLocation(server, location)
    else:
        profile_server = server

    all_profiles = profile_server_info.list_profiles(oauth_session)
    # Only show profiles with a supported protocol
    supported_profiles = [
        profile for profile in all_profiles
        if profile.has_supported_protocol and profile.supports_config(app.config)
    ]
    if not supported_profiles:
        message = "no profile with suppored protocol"
        logger.error(message, exc_info=False)
        enter_error_state_threadsafe(app, Exception(message))
        return

    app.interface_transition_threadsafe(
        'choose_profile', profile_server, oauth_session, supported_profiles)


@run_in_background_thread('configure-connection')
def on_chosen_profile(app: Application,
                      server: AnyServer,
                      oauth_session: OAuth2Session,
                      profile: Profile):
    country_code: Optional[str]
    if isinstance(server, SecureInternetLocation):
        try:
            server_info = app.server_db.get_server_info(server.server)
            location_info = app.server_db.get_server_info(server.location)
        except Exception as e:
            logger.error("error getting server info", exc_info=True)
            enter_error_state_threadsafe(app, e)
            return
        auth_url = server.server.oauth_login_url
        api_url = location_info.api_endpoint
        connect_server_info = location_info
        country_code = server.location.country_code
        con_type = storage.ConnectionType.SECURE
        display_name = str(server.server)
        support_contact = server.location.support_contact
    else:
        try:
            server_info = app.server_db.get_server_info(server)
        except Exception as e:
            logger.error("error getting server info", exc_info=True)
            enter_error_state_threadsafe(app, e)
            return
        api_url = server_info.api_endpoint
        connect_server_info = server_info
        auth_url = server.oauth_login_url
        country_code = None
        display_name = str(server)
        if isinstance(server, InstituteAccessServer):
            con_type = storage.ConnectionType.INSTITUTE
            support_contact = server.support_contact
        elif isinstance(server, CustomServer):
            con_type = storage.ConnectionType.OTHER
            support_contact = []
        else:
            raise TypeError(server)

    try:
        connection = connect_server_info.connect(app, profile, oauth_session)
    except Exception as e:
        logger.error("error connecting", exc_info=True)
        enter_error_state_threadsafe(app, e)
        return
    validity = connection.validity
    storage.set_metadata(
        auth_url, oauth_session.token, server_info.token_endpoint,
        server_info.authorization_endpoint, api_url, display_name,
        support_contact, profile.id, con_type, country_code,
        validity.start, validity.end, connection.protocol)
    storage.set_auth_url(auth_url)

    logger.debug(f"starting connection: {connection!r}")

    # Apply the users settings to the ovpn file.
    if app.config.force_tcp:
        try:
            connection.force_tcp()
        except Exception as e:
            enter_error_state_threadsafe(app, e)
            return

    def connected_callback(result):
        logger.info(f"Finished saving network manager config: {result}")
        app.session_transition('new_session', server, validity)
        app.interface_transition('finished_configuring_connection')
        app.current_network_uuid = storage.get_uuid()
        assert app.current_network_uuid is not None
        nm.set_default_gateway(profile.use_as_default_gateway)
        app.network_transition('start_new_connection', server)

    @app.make_func_threadsafe
    def connect():
        connection.connect(connected_callback)

    connect()


def on_disconnect(app: Application):
    if isinstance(app.session_state, active_session_states):
        server = app.session_state.server
    else:
        return
    oauth_session = storage.get_oauth_session()
    if not oauth_session:
        return

    @run_in_background_thread('stop-connection')
    def inner():
        server_info = app.server_db.get_server_info(server)
        server_info.disconnect(oauth_session)

    inner()


def enter_error_state(app: Application, error: Exception):
    message = get_error_message(error)
    from .transition import go_to_main_state
    app.interface_transition('encountered_exception', message, go_to_main_state)


def enter_error_state_threadsafe(app: Application, error: Exception):
    app.make_func_threadsafe(enter_error_state)(app, error)
