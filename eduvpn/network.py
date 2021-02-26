import logging
import enum
from . import nm
from . import settings
from .state_machine import BaseState
from .app import Application
from .server import ConfiguredServer as Server


logger = logging.getLogger(__name__)


class StatusImage(enum.Enum):
    # The value is the image filename.
    DEFAULT = 'desktop-default.png'
    CONNECTING = 'desktop-connecting.png'
    CONNECTED = 'desktop-connected.png'
    NOT_CONNECTED = 'desktop-not-connected.png'

    @property
    def path(self):
        return settings.IMAGE_PREFIX + self.value


class NetworkState(BaseState):
    """
    Base class for all interface states.
    """

    status_label: str = "Connection state unknown"
    status_image = StatusImage.DEFAULT

    def start_new_connection(self,
                             app: Application,
                             server: Server,
                             ) -> 'NetworkState':
        return connect(app)

    def set_connecting(self, app: Application) -> 'NetworkState':
        return ConnectingState()

    def set_connected(self, app: Application) -> 'NetworkState':
        return ConnectedState()

    def set_disconnected(self, app: Application) -> 'NetworkState':
        return DisconnectedState()

    def set_unknown(self, app: Application) -> 'NetworkState':
        return UnknownState()


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
        return ConnectedState()

    def found_previous_connection(self,
                                  app: Application,
                                  server: Server,
                                  ) -> NetworkState:
        """
        A previously established connection was found.

        This will be the default connection to start.
        """
        app.interface_transition('no_active_connection_found')
        return DisconnectedState()

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

    status_label: str = "Disconnected"


def connect(app: Application) -> NetworkState:
    """
    Estabilish a connection to the server.
    """
    client = nm.get_client()
    nm.activate_connection(client, app.current_network_uuid)
    return ConnectingState()


def disconnect(app: Application) -> NetworkState:
    """
    Break the connection to the server.
    """
    client = nm.get_client()
    nm.deactivate_connection(client, app.current_network_uuid)
    return DisconnectedState()


class ConnectingState(NetworkState):
    """
    The network is currently trying to connect to a server.
    """

    status_label: str = "Preparing to connect"
    status_image = StatusImage.CONNECTING

    def disconnect(self, app: Application) -> NetworkState:
        """
        Abort connecting.
        """
        return disconnect(app)


class ConnectedState(NetworkState):
    """
    The network is currently connected to a server.
    """

    status_label: str = "Connection active"
    status_image = StatusImage.CONNECTED

    def disconnect(self, app: Application) -> NetworkState:
        return disconnect(app)


class DisconnectedState(NetworkState):
    """
    The network is not currently connected to a server,
    but a configured connection exists.
    """

    status_label: str = "Disconnected"
    status_image = StatusImage.NOT_CONNECTED

    def reconnect(self, app: Application) -> NetworkState:
        return connect(app)


class CertificateExpiredState(NetworkState):
    """
    The network could not connect because the certifcate has expired.
    """

    status_label: str = "Connection failed"
    status_image = StatusImage.NOT_CONNECTED

    def renew_certificate(self, app: Application) -> NetworkState:
        """
        Re-estabilish a connection to the server.
        """
        # TODO perform actual renewal
        return connect(app)


class ConnectionErrorState(NetworkState):
    """
    The network could not connect because an error occured.
    """

    status_label: str = "Connection failed"
    status_image = StatusImage.NOT_CONNECTED

    def __init__(self, error: str):
        self.error = error

    def reconnect(self, app: Application) -> NetworkState:
        return connect(app)


class UnknownState(NetworkState):
    """
    The network state could not be determined.
    """
