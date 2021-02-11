from typing import Optional, List
import logging
from .storage import get_current_metadata
from .state_machine import BaseState
from .app import Application
from .server import Server


logger = logging.getLogger(__name__)


class InterfaceState(BaseState):
    """
    Base class for all interface states.
    """

    def server_db_finished_loading(self, app: Application) -> 'InterfaceState':
        # By default, loading the server db doesn't change the interface state.
        return self

    def toggle_settings(self, app: Application) -> 'InterfaceState':
        return ConfigureSettings(self)


class InitialInterfaceState(InterfaceState):
    """
    The state of the interface when the app starts.

    This is a transient state until
    the actual first state has been determined.
    """

    def found_active_connection(self,
                                app: Application,
                                server: Server) -> InterfaceState:
        """
        An connection is already active, show its details.
        """
        return ConnectionStatus(server)

    def no_active_connection_found(self, app: Application) -> InterfaceState:
        """
        No connection is currently active, go to the main state.
        """
        return go_to_main_state(app)


def go_to_main_state(app: Application) -> InterfaceState:
    """
    If any servers have been configured, show the main state to select one.
    Otherwise, allow the user to configure a new server.
    """
    configured_servers = []  # TODO
    if configured_servers:
        return MainState(servers=configured_servers)
    else:
        return ConfigurePredefinedServer()


def connect_to_server(app: Application, server: Server) -> InterfaceState:
    if not hasattr(server, 'oauth_login_url'):
        # This server doesn't require OAuth setup
        # TODO make connection
        return ConnectionStatus(server)
    metadata = get_current_metadata(server.oauth_login_url)
    if metadata:
        # We've already configured this server.
        # TODO make connection
        return ConnectionStatus(server)
    else:
        # This is a new server.
        # TODO make connection
        return OAuthSetup(server)


class MainState(InterfaceState):
    """
    The home state of the app.

    Present a list of configured servers to start a connection.
    """

    def __init__(self, servers: List[Server]):
        self.servers = servers

    def configure_new_server(self, app: Application) -> InterfaceState:
        return ConfigurePredefinedServer()

    def connect_to_server(self,
                          app: Application,
                          server: Server) -> InterfaceState:
        return connect_to_server(app, server)


def enter_search_query(app: Application, search_query: str) -> InterfaceState:
    """
    Enter a search query for a predefined server.
    """
    if search_query:
        if app.server_db.is_loaded:
            results = list(app.server_db.search(search_query))
        else:
            return PendingConfigurePredefinedServer(search_query)
    else:
        results = None
    return ConfigurePredefinedServer(search_query, results)


def enter_custom_address(app: Application, address: str) -> InterfaceState:
    """
    Enter an address for a custom server.
    """
    return ConfigureCustomServer(address)


class PendingConfigurePredefinedServer(InterfaceState):
    """
    When the user searches for a server, but the list
    hasn't been downloaded yet, this state is temporarily
    set until the download is finished.
    """

    def __init__(self, search_query: str = ''):
        self.search_query = search_query

    def enter_search_query(self,
                           app: Application,
                           search_query: str,
                           ) -> InterfaceState:
        return PendingConfigurePredefinedServer(search_query)

    def enter_custom_address(self,
                             app: Application,
                             address: str,
                             ) -> InterfaceState:
        return enter_custom_address(app, address)

    def connect_to_server(self,
                          app: Application,
                          server: Server) -> InterfaceState:
        return connect_to_server(app, server)

    def server_db_finished_loading(self, app: Application) -> InterfaceState:
        return enter_search_query(app, self.search_query)


class ConfigurePredefinedServer(InterfaceState):
    """
    Select a server to configure
    from a list of known servers.
    """

    def __init__(self,
                 search_query: str = '',
                 results: Optional[Server] = None):
        self.search_query = search_query
        self.results = results

    def __repr__(self):
        if self.results is None:
            results = None
        else:
            # Don't include the long list of results.
            results = len(self.results)
        return (
            f"<ConfigurePredefinedServer"
            f" search_query={self.search_query!r}"
            f" results={results}>"
        )

    def enter_search_query(self, app: Application,
                           search_query: str,
                           ) -> InterfaceState:
        return enter_search_query(app, search_query)

    def enter_custom_address(self, app: Application,
                             address: str,
                             ) -> InterfaceState:
        return enter_custom_address(app, address)

    def connect_to_server(self,
                          app: Application,
                          server: Server) -> InterfaceState:
        return connect_to_server(app, server)


class ConfigureCustomServer(InterfaceState):
    """
    Select a custom server to configure
    by providing its address.
    """

    def __init__(self, address: str):
        self.address = address

    def enter_search_query(self, app: Application,
                           search_query: str,
                           ) -> InterfaceState:
        return enter_search_query(app, search_query)

    def enter_custom_address(self, app: Application,
                             address: str,
                             ) -> InterfaceState:
        return enter_custom_address(app, address)

    def connect_to_server(self,
                          app: Application,
                          server: Server) -> InterfaceState:
        return connect_to_server(app, server)


configure_server_states = (
    # This is a tuple so it can be used with `isinstance()`.
    PendingConfigurePredefinedServer,
    ConfigurePredefinedServer,
    ConfigureCustomServer,
)


class OAuthSetup(InterfaceState):
    """
    Allow the user to log into the VPN server using their browser.
    """

    def __init__(self, server: Server):
        self.server = server

    def oauth_setup_cancel(self, app: Application) -> InterfaceState:
        return go_to_main_state(app)

    def oauth_setup_success(self, app: Application) -> InterfaceState:
        return ConnectionStatus(self.server)

    def oauth_setup_failure(self,
                            app: Application,
                            error: str,
                            ) -> InterfaceState:
        return OAuthFailed(self.server, error)


class OAuthFailed(InterfaceState):
    """
    Inform the user that the OAuth process failed,
    and allow them to retry or cancel the process.
    """

    def __init__(self, server: Server, error: str):
        self.server = server
        self.error = error

    def oauth_setup_cancel(self, app: Application) -> InterfaceState:
        return go_to_main_state(app)

    def oauth_setup_retry(self, app: Application) -> InterfaceState:
        return OAuthSetup(self.server)


class ConfigureSettings(InterfaceState):
    """
    Allow the user to configure the application settings.
    """

    def __init__(self, previous_state):
        self.previous_state = previous_state

    def toggle_settings(self, app: Application) -> InterfaceState:
        return self.previous_state


class ConnectionStatus(InterfaceState):
    """
    Show info on the active connection status.
    """

    def __init__(self, server: Server):
        self.server = server
