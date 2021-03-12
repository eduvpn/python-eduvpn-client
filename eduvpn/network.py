from typing import Optional
import logging
import enum
from functools import partial
from time import sleep
from datetime import datetime
from . import nm
from . import settings
from .state_machine import BaseState
from .app import Application
from .server import ConfiguredServer as Server
from .utils import run_in_background_thread


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

    status_label = "Connection state unknown"
    status_image = StatusImage.DEFAULT

    def start_new_connection(self,
                             app: Application,
                             server: Server,
                             ) -> 'NetworkState':
        if isinstance(app.network_state, (ConnectingState, ConnectedState)):
            disconnect(app, update_state=False)
        return connect(app)

    def set_connecting(self, app: Application) -> 'NetworkState':
        return ConnectingState()

    def set_connected(self, app: Application) -> 'NetworkState':
        return ConnectedState()

    def set_disconnected(self, app: Application) -> 'NetworkState':
        return DisconnectedState()

    def set_unknown(self, app: Application) -> 'NetworkState':
        return enter_unknown_state(app)

    def set_error(self, app: Application, message: Optional[str] = None) -> 'NetworkState':
        return ConnectionErrorState(message)

    def set_certificate_expired(self, app: Application) -> 'NetworkState':
        return CertificateExpiredState()


class InitialNetworkState(NetworkState):
    """
    The state of the network when the app starts.

    This is a transient state until
    the actual network state is obtained.
    """

    def found_active_connection(self,
                                app: Application,
                                server: Server,
                                expiry: Optional[datetime],
                                ) -> NetworkState:
        """
        An already active connection was found.
        """
        app.interface_transition('found_active_connection', server, expiry)
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

    status_label = "Disconnected"


def connect(app: Application) -> NetworkState:
    """
    Estabilish a connection to the server.
    """
    client = nm.get_client()
    nm.activate_connection(
        client,
        app.current_network_uuid,
        partial(on_any_update_callback, app),
    )
    return ConnectingState()


def disconnect(app: Application, *, update_state=True) -> NetworkState:
    """
    Break the connection to the server.
    """
    client = nm.get_client()
    callback = None
    if update_state:
        callback = partial(on_any_update_callback, app)
    nm.deactivate_connection(
        client,
        app.current_network_uuid,
        callback,
    )
    return DisconnectedState()


def enter_unknown_state(app: Application) -> NetworkState:
    # Set the state temporarily to unknown but keep polling for updates,
    # since we don't always get notified by the update callback.
    @run_in_background_thread('poll-network-state')
    def determine_network_state_thread():
        _, status = nm.connection_status(nm.get_client())
        while status is nm.NM.ActiveConnectionState.UNKNOWN or status is None:
            sleep(1)
            if not isinstance(app.network_state, UnknownState):
                return
            _, status = nm.connection_status(nm.get_client())
            logger.debug(f"polling network state: {status}")
        handle_active_connection_status(app, status)

    determine_network_state_thread()
    return UnknownState()


def on_status_update_callback(app: Application, status: nm.NM.VpnConnectionState):
    """
    Callback for whenever a connection status changes.
    """
    if status in [nm.NM.VpnConnectionState.CONNECT,
                  nm.NM.VpnConnectionState.IP_CONFIG_GET,
                  nm.NM.VpnConnectionState.PREPARE]:
        app.network_transition('set_connecting')
    elif status is nm.NM.VpnConnectionState.ACTIVATED:
        app.network_transition('set_connected')
    elif status is nm.NM.VpnConnectionState.DISCONNECTED:
        app.network_transition('set_disconnected')
    elif status is nm.NM.VpnConnectionState.FAILED:
        app.network_transition('set_error')
    elif status is nm.NM.VpnConnectionState.NEED_AUTH:
        app.network_transition('set_error')
    elif status is nm.NM.VpnConnectionState.UNKNOWN:
        app.network_transition('set_unknown')
    else:
        raise ValueError(status)


def on_any_update_callback(app: Application):
    """
    Callback for whenever a connection status might have changed.
    """
    _, status = nm.connection_status(nm.get_client())
    if status is None:
        app.network_transition('set_unknown')
    else:
        handle_active_connection_status(app, status)


def handle_active_connection_status(app: Application, status: nm.NM.ActiveConnectionState):
    if status is nm.NM.ActiveConnectionState.ACTIVATING:
        app.network_transition('set_connecting')
    elif status is nm.NM.ActiveConnectionState.ACTIVATED:
        app.network_transition('set_connected')
    elif status in [nm.NM.ActiveConnectionState.DEACTIVATED,
                    nm.NM.ActiveConnectionState.DEACTIVATING]:
        app.network_transition('set_disconnected')
    elif status is nm.NM.ActiveConnectionState.UNKNOWN:
        app.network_transition('set_unknown')
    else:
        raise ValueError(status)


class ConnectingState(NetworkState):
    """
    The network is currently trying to connect to a server.
    """

    status_label = "Preparing to connect"
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

    status_label = "Connection active"
    status_image = StatusImage.CONNECTED

    def disconnect(self, app: Application) -> NetworkState:
        return disconnect(app)


class DisconnectedState(NetworkState):
    """
    The network is not currently connected to a server,
    but a configured connection exists.
    """

    status_label = "Disconnected"
    status_image = StatusImage.NOT_CONNECTED

    def reconnect(self, app: Application) -> NetworkState:
        return connect(app)


class CertificateExpiredState(NetworkState):
    """
    The network could not connect because the certifcate has expired.
    """

    status_label = "Certificate expired"
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

    status_label = "Connection failed"
    status_image = StatusImage.NOT_CONNECTED

    def __init__(self, error: Optional[str]):
        self.error = error

    def reconnect(self, app: Application) -> NetworkState:
        return connect(app)


class UnknownState(NetworkState):
    """
    The network state could not be determined.
    """
