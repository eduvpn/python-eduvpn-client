from typing import Optional, List
import logging
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2.rfc6749.errors import (
    InvalidGrantError as InvalidOauthGrantError)
from eduvpn.settings import CLIENT_ID as OAUTH_CLIENT_ID
from .. import storage
from .. import nm
from .. import actions
from .. import remote
from ..oauth2 import OAuthWebServer
from ..app import Application
from ..server import (
    AnyServer, PredefinedServer, ConfiguredServer, InstituteAccessServer,
    SecureInternetServer, OrganisationServer, CustomServer,
    SecureInternetLocation, Profile)
from ..utils import run_in_background_thread
from . import state


logger = logging.getLogger(__name__)


def go_to_main_state(app: Application) -> state.InterfaceState:
    """
    If any servers have been configured, show the main state to select one.
    Otherwise, allow the user to configure a new server.
    """
    configured_servers = list(app.server_db.all_configured())
    if configured_servers:
        return state.MainState(servers=configured_servers)
    else:
        return state.ConfigurePredefinedServer()


def enter_search_query(app: Application, search_query: str) -> state.InterfaceState:
    """
    Enter a search query for a predefined server.
    """
    results: Optional[List[PredefinedServer]]
    if search_query:
        if app.server_db.is_loaded:
            results = list(app.server_db.search(search_query))
        else:
            return state.PendingConfigurePredefinedServer(search_query)
    else:
        results = None
    return state.ConfigurePredefinedServer(search_query, results)


def enter_custom_address(app: Application, address: str) -> state.InterfaceState:
    """
    Enter an address for a custom server.
    """
    return state.ConfigureCustomServer(address)


def create_new_oauth_session(token: str, token_endpoint: str) -> OAuth2Session:
    return OAuth2Session(
        client_id=OAUTH_CLIENT_ID,
        token=token,
        auto_refresh_url=token_endpoint,
    )


def connect_to_server(app: Application, server: AnyServer) -> state.InterfaceState:
    oauth_login_url = server.oauth_login_url  # type: ignore
    metadata = storage.get_current_metadata(oauth_login_url)
    if metadata:
        # We've already configured this server.
        token, token_endpoint, *_ = metadata
        oauth_session = create_new_oauth_session(token, token_endpoint)
        return refresh_oauth_token(app, server, oauth_session)
    else:
        # This is a new server that we need to configure first.
        return setup_oauth(app, server)


def setup_oauth(app: Application, server: AnyServer) -> state.InterfaceState:
    try:
        server_info = app.server_db.get_server_info(server)
    except Exception as e:
        logger.error("error getting server info", exc_info=True)
        return state.ErrorState(e)

    def oauth_token_callback(oauth_session: Optional[OAuth2Session]):
        if oauth_session:
            app.interface_transition_threadsafe('oauth_setup_success', oauth_session)
        else:
            # The process has been canceled by the user through the app,
            # which already schedules the state transition so we don't need
            # to do that here.
            pass

    web_server = OAuthWebServer.start(
        server_info.token_endpoint,
        server_info.auth_endpoint,
        oauth_token_callback,
    )
    return state.OAuthSetup(server, web_server)


def refresh_oauth_token(app: Application,
                        server: AnyServer,
                        oauth_session: OAuth2Session) -> state.InterfaceState:

    @run_in_background_thread('oauth-refresh')
    def oauth_refresh_thread():
        try:
            server_info = app.server_db.get_server_info(server)
        except Exception as e:
            logger.error("error getting server info", exc_info=True)
            return state.ErrorState(e)
        try:
            oauth_session.refresh_token(token_url=server_info.token_endpoint)
        except InvalidOauthGrantError as e:
            logger.warning(f'Error refreshing OAuth token: {e}')
            app.interface_transition_threadsafe('oauth_refresh_failed')
        else:
            app.interface_transition_threadsafe('oauth_refresh_success')

    oauth_refresh_thread()
    return state.OAuthRefreshToken(app, server, oauth_session)


def start_connection(app: Application,
                     server: AnyServer,
                     oauth_session: OAuth2Session,
                     location: Optional[SecureInternetServer] = None,
                     ) -> state.InterfaceState:
    try:
        server_info = app.server_db.get_server_info(server)
    except Exception as e:
        logger.error("error getting server info", exc_info=True)
        return state.ErrorState(e)
    api_url = server_info.api_base_uri
    profile_server: ConfiguredServer

    if isinstance(server, OrganisationServer):
        if not location:
            locations = [server for server in app.server_db.all()
                         if isinstance(server, SecureInternetServer)]
            if len(locations) == 1:
                # Skip location choice if there's only a single option.
                return start_connection(app, server, oauth_session, locations[0])
            else:
                return state.ChooseSecureInternetLocation(server, oauth_session, locations)
        else:
            try:
                location_info = app.server_db.get_server_info(location)
            except Exception as e:
                logger.error("error getting server info", exc_info=True)
                return state.ErrorState(e)
            api_url = location_info.api_base_uri
            profile_server = SecureInternetLocation(server, location)
    else:
        profile_server = server

    profiles = [Profile(**data) for data in remote.list_profiles(oauth_session, api_url)]
    if len(profiles) == 1:
        # Skip profile choice if there's only a single option.
        return chosen_profile(app, profile_server, oauth_session, profiles[0])
    else:
        return state.ChooseProfile(profile_server, oauth_session, profiles)


def chosen_profile(app: Application,
                   server: AnyServer,
                   oauth_session: OAuth2Session,
                   profile: Profile) -> state.InterfaceState:
    country_code: Optional[str]
    if isinstance(server, SecureInternetLocation):
        try:
            server_info = app.server_db.get_server_info(server.server)
            location_info = app.server_db.get_server_info(server.server)
        except Exception as e:
            logger.error("error getting server info", exc_info=True)
            return state.ErrorState(e)
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
            return state.ErrorState(e)
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

    @run_in_background_thread('configure-connection')
    def configure_connection_thread():
        try:
            config, private_key, certificate = actions.get_config_and_keycert(
                oauth_session, api_url, profile.id)
        except Exception as e:
            logger.error("error getting config and keycert", exc_info=True)
            app.make_func_threadsafe(enter_error_state)(app, e)
            return
        storage.set_metadata(
            auth_url, oauth_session.token, server_info.token_endpoint,
            server_info.auth_endpoint, api_url, display_name,
            support_contact, profile.id, con_type, country_code)
        storage.set_auth_url(auth_url)

        def finished_saving_config_callback(result):
            logger.info(f"Finished saving network manager config: {result}")
            app.interface_transition('finished_configuring_connection')
            app.current_network_uuid = storage.get_uuid()
            assert app.current_network_uuid is not None
            app.network_transition('start_new_connection', server)

        @app.make_func_threadsafe
        def save_connection():
            nm.save_connection(nm.get_client(), config, private_key, certificate,
                               callback=finished_saving_config_callback)

        save_connection()

    configure_connection_thread()
    return state.ConfiguringConnection(server)


def enter_error_state(app: Application, error: Exception):
    app.interface_transition('encountered_exception', error)
