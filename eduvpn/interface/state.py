from typing import Optional, List, Callable
from requests_oauthlib import OAuth2Session
from ..state_machine import BaseState
from ..oauth2 import OAuthWebServer
from ..app import Application
from ..server import (
    AnyServer, PredefinedServer, ConfiguredServer,
    SecureInternetServer, OrganisationServer, CustomServer, Profile)
from . import event
from . import transition


Transition = Callable[[Application], 'InterfaceState']


class InterfaceState(BaseState):
    """
    Base class for all interface states.
    """

    def server_db_finished_loading(self, app: Application) -> 'InterfaceState':
        # Loading the server db doesn't normally change the interface state.
        return self

    def encountered_exception(self,
                              app: Application,
                              message: str,
                              next_transition: Optional[Transition] = None,
                              ) -> 'InterfaceState':
        return ErrorState(message, next_transition)

    def restart(self, app: Application):
        from .. import network as network_state
        if isinstance(app.network_state, network_state.InitialNetworkState):
            return InitialInterfaceState()
        elif isinstance(app.network_state, network_state.UnconnectedState):
            return transition.go_to_main_state(app)
        else:
            return ConnectionStatus()

    def renew_session(self, app: Application, server: ConfiguredServer) -> 'InterfaceState':
        return transition.connect_to_server(app, server, renew=True)


class InitialInterfaceState(InterfaceState):
    """
    The state of the interface when the app starts.

    This is a transient state until
    the actual first state has been determined.
    """

    def found_active_connection(self, app: Application) -> InterfaceState:
        """
        An connection is already active, show its details.
        """
        return ConnectionStatus()

    def no_active_connection_found(self, app: Application) -> InterfaceState:
        """
        No connection is currently active, go to the main state.

        The concrete main state depends on
        whether any servers have been configured previously.
        """
        return transition.go_to_main_state(app)


class MainState(InterfaceState):
    """
    The home state of the app,
    if any servers have been configured.

    Present the list of configured servers to start a connection.
    """

    def __init__(self, servers: List[ConfiguredServer]):
        self.servers = servers

    def configure_new_server(self, app: Application) -> InterfaceState:
        "Configure a new server."
        return ConfigurePredefinedServer()

    def connect_to_server(self,
                          app: Application,
                          server: ConfiguredServer) -> InterfaceState:
        "Connect to an already configured server."
        return transition.connect_to_server(app, server)


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
        return transition.enter_custom_address(app, address)

    def connect_to_server(self,
                          app: Application,
                          server: ConfiguredServer) -> InterfaceState:
        return transition.connect_to_server(app, server)

    def server_db_finished_loading(self, app: Application) -> InterfaceState:
        """
        The list of predefined servers has been loaded,
        and the can how be shown to the user.
        """
        return transition.enter_search_query(app, self.search_query)


class ConfigurePredefinedServer(InterfaceState):
    """
    Select a server from a list of known servers to configure.
    """

    def __init__(self,
                 search_query: str = '',
                 results: Optional[List[PredefinedServer]] = None):
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
        return transition.enter_search_query(app, search_query)

    def enter_custom_address(self, app: Application,
                             address: str,
                             ) -> InterfaceState:
        return transition.enter_custom_address(app, address)

    def connect_to_server(self,
                          app: Application,
                          server: PredefinedServer) -> InterfaceState:
        return transition.connect_to_server(app, server)


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
        return transition.enter_search_query(app, search_query)

    def enter_custom_address(self, app: Application,
                             address: str,
                             ) -> InterfaceState:
        return transition.enter_custom_address(app, address)

    def connect_to_server(self,
                          app: Application,
                          server: CustomServer) -> InterfaceState:
        return transition.connect_to_server(app, server)


configure_server_states = (
    # This is a tuple so it can be used with `isinstance()`.
    PendingConfigurePredefinedServer,
    ConfigurePredefinedServer,
    ConfigureCustomServer,
)


class OAuthSetupPending(InterfaceState):
    """
    Wait for the local OAuth webserver to start.
    """

    def __init__(self, server: AnyServer):
        self.server = server

    def ready_for_oauth_setup(self,
                              app: Application,
                              oauth_web_server: OAuthWebServer) -> InterfaceState:
        """
        Cancel the OAuth setup process
        and take the user back to the main page.
        """
        return OAuthSetup(self.server, oauth_web_server)


class OAuthSetup(InterfaceState):
    """
    Allow the user to log into the VPN server using their browser.
    """

    def __init__(self, server: AnyServer, oauth_web_server: OAuthWebServer):
        self.server = server
        self.oauth_web_server = oauth_web_server

    def oauth_setup_cancel(self, app: Application) -> InterfaceState:
        """
        Cancel the OAuth setup process
        and take the user back to the main page.
        """
        self.oauth_web_server.stop()
        return transition.go_to_main_state(app)

    def oauth_setup_success(self,
                            app: Application,
                            oauth_session: OAuth2Session) -> InterfaceState:
        """
        The user has successfully completed the oauth setup by logging in.
        """
        event.on_refresh_oauth_token(app, self.server, oauth_session)
        return OAuthRefreshToken(app, self.server, oauth_session)


class OAuthRefreshToken(InterfaceState):
    """
    The OAuth token is being refreshed.
    """

    def __init__(self,
                 app: Application,
                 server: AnyServer,
                 oauth_session: OAuth2Session):
        self.app = app
        self.server = server
        self.oauth_session = oauth_session

    def oauth_refresh_success(self, app: Application) -> InterfaceState:
        event.on_start_connection(app, self.server, self.oauth_session)
        return LoadingServerInformation()

    def oauth_refresh_failed(self, app: Application) -> InterfaceState:
        """
        Refreshing the OAuth token failed,
        so the OAuth setup needs to be redone.
        """
        event.on_setup_oauth(app, self.server)
        return OAuthSetupPending(self.server)


class LoadingServerInformation(InterfaceState):
    """
    Wait for server information to be requested.
    """

    def choose_secure_internet_location(self,
                                        app: Application,
                                        server: OrganisationServer,
                                        oauth_session: OAuth2Session,
                                        locations: List[SecureInternetServer]):
        if len(locations) == 1:
            # Skip location choice if there's only a single option.
            event.on_start_connection(app, server, oauth_session, locations[0])
            return LoadingServerInformation()
        else:
            return ChooseSecureInternetLocation(server, oauth_session, locations)

    def choose_profile(self,
                       app: Application,
                       server: AnyServer,
                       oauth_session: OAuth2Session,
                       profiles: List[Profile]) -> InterfaceState:
        if len(profiles) == 1:
            # Skip profile choice if there's only a single option.
            event.on_chosen_profile(app, server, oauth_session, profiles[0])
            return ConfiguringConnection(server)
        else:
            return ChooseProfile(server, oauth_session, profiles)


class ChooseSecureInternetLocation(InterfaceState):
    """
    Allow the user to choose a secure internet location.
    """

    def __init__(self,
                 server: OrganisationServer,
                 oauth_session: OAuth2Session,
                 locations: List[SecureInternetServer]):
        self.server = server
        self.oauth_session = oauth_session
        self.locations = locations

    def select_secure_internet_location(self, app, location) -> InterfaceState:
        event.on_start_connection(app, self.server, self.oauth_session, location)
        return LoadingServerInformation()


class ChooseProfile(InterfaceState):
    """
    Allow the user to choose a profile.
    """

    def __init__(self,
                 server: AnyServer,
                 oauth_session: OAuth2Session,
                 profiles: List[Profile]):
        self.server = server
        self.oauth_session = oauth_session
        self.profiles = profiles

    def select_profile(self,
                       app: Application,
                       profile: Profile) -> InterfaceState:
        event.on_chosen_profile(app, self.server, self.oauth_session, profile)
        return ConfiguringConnection(self.server)


class ConfiguringConnection(InterfaceState):
    """
    Waiting to get the connection data and
    save the configuration to the network manager.
    """

    def __init__(self, server: AnyServer):
        self.server = server

    def finished_configuring_connection(self, app: Application) -> InterfaceState:
        return ConnectionStatus()


class ConnectionStatus(InterfaceState):
    """
    Show info on the active connection status.
    """

    def go_back(self, app: Application) -> InterfaceState:
        return transition.go_to_main_state(app)

    def activate_connection(self, app: Application) -> InterfaceState:
        app.network_transition('reconnect')
        return self

    def deactivate_connection(self, app: Application) -> InterfaceState:
        app.network_transition('disconnect')
        return self


class ErrorState(InterfaceState):
    """
    An error has occured.
    """

    def __init__(self,
                 message: str,
                 next_transition: Optional[Transition] = None,
                 ):
        self.message = message
        self.next_transition = next_transition

    def acknowledge_error(self, app: Application) -> InterfaceState:
        assert self.next_transition is not None
        return self.next_transition(app)
