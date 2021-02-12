import logging
from .nm import get_client, activate_connection, deactivate_connection
from .state_machine import BaseState
from .app import Application
from .server import Server


logger = logging.getLogger(__name__)


class NetworkState(BaseState):
    """
    Base class for all interface states.
    """


class InitialNetworkState(NetworkState):
    """
    The state of the network when the app starts.

    This is a transient state until
    the actual network state is obtained.
    """

    def found_active_connection(self,
                                app: Application,
                                server: Server,
                                ) -> NetworkState:
        """
        An already active connection was found.
        """
        app.interface_transition('found_active_connection', server)
        return ConnectedState(server)

    def found_previous_connection(self,
                                  app: Application,
                                  server: Server,
                                  ) -> NetworkState:
        """
        A previously established connection was found.

        This will be the default connection to start.
        """
        app.interface_transition('no_active_connection_found')
        return DisconnectedState(server)

    def no_previous_connection_found(self, app: Application) -> NetworkState:
        """
        No previously established connection was found.

        This is probably the first time the app runs.
        """
        app.interface_transition('no_active_connection_found')
        return UnconnectedState()


class UnconnectedState(NetworkState):
    """
    There is no current connection active,
    nor is there a configured connection available.

    As soon as a server is chosen,
    that becomes the default
    and this state is no longer reached.
    """

    def connecting_to_server(self,
                             app: Application,
                             server: Server,
                             ) -> NetworkState:
        # TODO store this as the default server
        return ConnectingState(server)


def connect(app: Application, server: Server) -> NetworkState:
    """
    Estabilish a connection to the server.
    """
    client = get_client()
    activate_connection(client, app.current_network_uuid)
    return ConnectingState(server)


def disconnect(app: Application, server: Server) -> NetworkState:
    """
    Break the connection to the server.
    """
    client = get_client()
    deactivate_connection(client, app.current_network_uuid)
    return DisconnectedState(server)


class ConnectingState(NetworkState):
    """
    The network is currently trying to connect to a server.
    """

    def __init__(self, server: Server):
        self.server = server

    def disconnect(self, app: Application) -> NetworkState:
        """
        Abort connecting.
        """
        return disconnect(app, self.server)

    def connection_established(self, app: Application) -> NetworkState:
        """
        The connection has been established.
        """
        return ConnectedState(self.server)

    def connection_failed(self, app: Application) -> NetworkState:
        """
        The connection has been established.
        """
        error = ""  # TODO
        return ConnectionErrorState(self.server, error)


class ConnectedState(NetworkState):
    """
    The network is currently connected to a server.
    """

    def __init__(self, server: Server):
        self.server = server
        # TODO
        # self.time_started =
        # self.valid_until =
        # self.bytes_received =
        # self.bytes_uploaded =

    def disconnect(self, app: Application) -> NetworkState:
        return disconnect(app, self.server)

    def certificate_expired(self, app: Application) -> NetworkState:
        """
        The certificate for this connection has expired.
        """
        return CertificateExpiredState(self.server)


class DisconnectedState(NetworkState):
    """
    The network is currently connected to a server.
    """

    def __init__(self, server: Server):
        self.server = server

    def reconnect(self, app: Application) -> NetworkState:
        return connect(app, self.server)


class CertificateExpiredState(NetworkState):
    """
    The network is currently connected to a server.
    """

    def __init__(self, server: Server):
        self.server = server

    def renew_certificate(self, app: Application) -> NetworkState:
        """
        Re-estabilish a connection to the server.
        """
        # TODO perform actual renewal
        return connect(app, self.server)


class ConnectionErrorState(NetworkState):
    """
    The network is currently connected to a server.
    """

    def __init__(self, server: Server, error: str):
        self.server = server
        self.error = error

    def reconnect(self, app: Application) -> NetworkState:
        return connect(app, self.server)
