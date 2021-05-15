from typing import Optional, List
from requests_oauthlib import OAuth2Session
from eduvpn.settings import CLIENT_ID as OAUTH_CLIENT_ID
from .. import storage
from ..app import Application
from ..server import AnyServer, PredefinedServer
from . import event
from . import state


def enter_custom_address(app: Application, address: str) -> state.InterfaceState:
    """
    Enter an address for a custom server.
    """
    return state.ConfigureCustomServer(address)


def go_to_main_state(app: Application) -> state.InterfaceState:
    """
    If any servers have been configured, show the main state to select one.
    Otherwise, allow the user to configure a new server.
    """
    if not app.variant.use_configured_servers:
        return state.ConfigurePredefinedServer()
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


def create_new_oauth_session(token: str, token_endpoint: str) -> OAuth2Session:
    return OAuth2Session(
        client_id=OAUTH_CLIENT_ID,
        token=token,
        auto_refresh_url=token_endpoint,
    )


def connect_to_server(app: Application,
                      server: AnyServer,
                      renew: bool = False) -> state.InterfaceState:
    oauth_login_url = server.oauth_login_url  # type: ignore
    if renew:
        metadata = None
    else:
        metadata = storage.get_current_metadata(oauth_login_url)
    if metadata:
        # We've already configured this server.
        token, token_endpoint, *_ = metadata
        oauth_session = create_new_oauth_session(token, token_endpoint)
        event.on_refresh_oauth_token(app, server, oauth_session)
        return state.OAuthRefreshToken(app, server, oauth_session)
    else:
        # This is a new server that we need to configure first.
        event.on_setup_oauth(app, server)
        return state.OAuthSetupPending(server)
