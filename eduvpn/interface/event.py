from typing import Optional
import logging
import webbrowser
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2.rfc6749.errors import (
    InvalidGrantError as InvalidOauthGrantError)
from .. import storage
from .. import nm
from .. import actions
from .. import remote
from .. import crypto
from .. import oauth2
from ..app import Application
from ..server import (
    AnyServer, ConfiguredServer, InstituteAccessServer,
    SecureInternetServer, OrganisationServer, CustomServer,
    SecureInternetLocation, Profile)
from .error import get_error_message
from ..ovpn import Ovpn, InvalidOVPN
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
        server_info.token_endpoint, server_info.auth_endpoint, app.variant, oauth_token_callback)
    if isinstance(server, OrganisationServer):
        secure_internet = app.server_db.get_secure_internet_server(server.secure_internet_home)
        if secure_internet:
            browser_url = secure_internet.authentication_url(server, browser_url)
        else:
            logger.warning(f"missing 'secure internet server' for {server!r}")
    logger.info(f"opening browser with {browser_url}")
    webbrowser.open(browser_url)
    app.interface_transition_threadsafe('ready_for_oauth_setup', webserver)


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
    api_url = server_info.api_base_uri
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
            api_url = location_info.api_base_uri
            profile_server = SecureInternetLocation(server, location)
    else:
        profile_server = server

    profiles = [Profile(**data) for data in remote.list_profiles(oauth_session, api_url)]
    app.interface_transition_threadsafe(
        'choose_profile', profile_server, oauth_session, profiles)


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
        api_url = location_info.api_base_uri
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
        api_url = server_info.api_base_uri
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
        ovpn_content, private_key, certificate = actions.get_config_and_keycert(
            oauth_session, api_url, profile.id)
    except Exception as e:
        logger.error("error getting config and keycert", exc_info=True)
        enter_error_state_threadsafe(app, e)
        return
    ovpn = Ovpn.parse(ovpn_content)
    validity = crypto.get_certificate_validity(certificate)
    if validity is None:
        validity_start = validity_end = None
    else:
        validity_start, validity_end = validity.start, validity.end
    storage.set_metadata(
        auth_url, oauth_session.token, server_info.token_endpoint,
        server_info.auth_endpoint, api_url, display_name,
        support_contact, profile.id, con_type, country_code,
        validity_start, validity_end)
    storage.set_auth_url(auth_url)

    # Apply the users settings to the ovpn file.
    if app.config.force_tcp:
        try:
            ovpn.force_tcp()
        except InvalidOVPN as e:
            enter_error_state_threadsafe(app, e)
            return

    def finished_saving_config_callback(result):
        logger.info(f"Finished saving network manager config: {result}")
        app.session_transition('new_session', server, validity)
        app.interface_transition('finished_configuring_connection')
        app.current_network_uuid = storage.get_uuid()
        assert app.current_network_uuid is not None
        nm.set_default_gateway(profile.use_as_default_gateway)
        app.network_transition('start_new_connection', server)

    @app.make_func_threadsafe
    def save_connection():
        nm.save_connection(nm.get_client(), ovpn, private_key, certificate,
                           callback=finished_saving_config_callback)

    save_connection()


def enter_error_state(app: Application, error: Exception):
    message = get_error_message(error)
    from .transition import go_to_main_state
    app.interface_transition('encountered_exception', message, go_to_main_state)


def enter_error_state_threadsafe(app: Application, error: Exception):
    app.make_func_threadsafe(enter_error_state)(app, error)
