from typing import Union, Optional, List
from requests_oauthlib import OAuth2Session
from ..state_machine import BaseState
from ..oauth2 import OAuthWebServer
from ..app import Application
from ..server import (
    Server, SecureInternetServer, InstituteAccessServer, CustomServer, Profile)
from .utils import SecureInternetLocation
from . import event


class InterfaceState(BaseState):
    """
    Base class for all interface states.
    """

    def server_db_finished_loading(self, app: Application) -> 'InterfaceState':
        # Loading the server db doesn't normally change the interface state.
        return self

    def toggle_settings(self, app: Application) -> 'InterfaceState':
        # Toggling the settings page normally shows the settings page.
        return ConfigureSettings(self)


class InitialInterfaceState(InterfaceState):
    """
    The state of the interface when the app starts.

    This is a transient state until
    the actual first state has been determined.
    """

    def found_active_connection(self,
                                app: Application,
                                server: Union[InstituteAccessServer, SecureInternetLocation],
                                ) -> InterfaceState:
        """
        An connection is already active, show its details.
        """
        return ConnectionStatus(server)

    def no_active_connection_found(self, app: Application) -> InterfaceState:
        """
        No connection is currently active, go to the main state.

        The concrete main state depends on
        whether any servers have been configured previously.
        """
        return event.go_to_main_state(app)


class MainState(InterfaceState):
    """
    The home state of the app,
    if any servers have been configured.

    Present the list of configured servers to start a connection.
    """

    def __init__(self, servers: List[Server]):
        self.servers = servers

    def configure_new_server(self, app: Application) -> InterfaceState:
        "Configure a new server."
        return ConfigurePredefinedServer()

    def connect_to_server(self,
                          app: Application,
                          server: Server) -> InterfaceState:
        "Connect to an already configured server."
        return event.connect_to_server(app, server)


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
        return event.enter_custom_address(app, address)

    def connect_to_server(self,
                          app: Application,
                          server: Server) -> InterfaceState:
        return event.connect_to_server(app, server)

    def server_db_finished_loading(self, app: Application) -> InterfaceState:
        """
        The list of predefined servers has been loaded,
        and the can how be shown to the user.
        """
        return event.enter_search_query(app, self.search_query)


class ConfigurePredefinedServer(InterfaceState):
    """
    Select a server from a list of known servers to configure.
    """

    def __init__(self,
                 search_query: str = '',
                 results: Optional[List[Server]] = None):
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
        return event.enter_search_query(app, search_query)

    def enter_custom_address(self, app: Application,
                             address: str,
                             ) -> InterfaceState:
        return event.enter_custom_address(app, address)

    def connect_to_server(self,
                          app: Application,
                          server: Server) -> InterfaceState:
        return event.connect_to_server(app, server)


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
        return event.enter_search_query(app, search_query)

    def enter_custom_address(self, app: Application,
                             address: str,
                             ) -> InterfaceState:
        return event.enter_custom_address(app, address)

    def connect_to_server(self,
                          app: Application,
                          server: Server) -> InterfaceState:
        return event.connect_to_server(app, server)


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

    def __init__(self, server: Server, oauth_web_server: OAuthWebServer):
        self.server = server
        self.oauth_web_server = oauth_web_server

    def oauth_setup_cancel(self, app: Application) -> InterfaceState:
        """
        Cancel the OAuth setup process
        and take the user back to the main page.
        """
        self.oauth_web_server.stop()
        return event.go_to_main_state(app)

    def oauth_setup_success(self,
                            app: Application,
                            oauth_session: OAuth2Session) -> InterfaceState:
        """
        The user has successfully completed the oauth setup by logging in.
        """
        return event.refresh_oauth_token(app, self.server, oauth_session)


class OAuthRefreshToken(InterfaceState):
    """
    The OAuth token is being refreshed.
    """

    def __init__(self,
                 app: Application,
                 server: Server,
                 oauth_session: OAuth2Session):
        self.app = app
        self.server = server
        self.oauth_session = oauth_session

    def oauth_refresh_success(self, app: Application) -> InterfaceState:
        return event.start_connection(app, self.server, self.oauth_session)

    def oauth_refresh_failed(self, app: Application) -> InterfaceState:
        """
        Refreshing the OAuth token failed,
        so the OAuth setup needs to be redone.
        """
        return event.setup_oauth(app, self.server)


class ChooseSecureInternetLocation(InterfaceState):
    """
    Allow the user to choose a secure internet location.
    """

    def __init__(self,
                 server: Server,
                 oauth_session: OAuth2Session,
                 locations: List[SecureInternetServer]):
        self.server = server
        self.oauth_session = oauth_session
        self.locations = locations

    def select_secure_internet_location(self, app, location) -> InterfaceState:
        return event.start_connection(app, self.server, self.oauth_session, location)


class ChooseProfile(InterfaceState):
    """
    Allow the user to choose a profile.
    """

    def __init__(self,
                 server: Union[InstituteAccessServer, SecureInternetLocation],
                 oauth_session: OAuth2Session,
                 profiles: List[Profile]):
        self.server = server
        self.oauth_session = oauth_session
        self.profiles = profiles

    def select_profile(self,
                       app: Application,
                       profile: Profile) -> InterfaceState:
        return event.chosen_profile(app, self.server, self.oauth_session, profile)


class ConfiguringConnection(InterfaceState):
    """
    Waiting to get the connection data and
    save the configuration to the network manager.
    """

    def __init__(self, server: Union[InstituteAccessServer, SecureInternetLocation]):
        self.server = server

    def finished_configuring_connection(self, app: Application) -> InterfaceState:
        return ConnectionStatus(self.server)


class ConnectionStatus(InterfaceState):
    """
    Show info on the active connection status.
    """

    def __init__(self, server: Union[InstituteAccessServer, SecureInternetLocation, CustomServer]):
        self.server = server


class ConfigureSettings(InterfaceState):
    """
    Allow the user to configure the application settings.
    """

    def __init__(self, previous_state):
        self.previous_state = previous_state

    def toggle_settings(self, app: Application) -> InterfaceState:
        return self.previous_state
