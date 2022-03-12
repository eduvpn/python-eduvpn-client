from typing import Optional
import logging
import enum
from functools import partial
from time import sleep
from . import nm
from . import settings
from .state_machine import BaseState
from .app import Application
from .server import ConfiguredServer as Server
from .utils import run_in_background_thread, translated_property

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

    status_label = translated_property("Connection state unknown")
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
        return enter_unknown_state(app)

    def set_error(self, app: Application, message: Optional[str] = None) -> 'NetworkState':
        return ConnectionErrorState(message)


class InitialNetworkState(NetworkState):
    """
    The state of the network when the app starts.

    This is a transient state until
    the actual network state is obtained.
    """

    def found_previous_connection(self, app: Application) -> NetworkState:
        """
        A previously established connection was found.
        """
        state = get_network_state(app)
        if isinstance(state, (DisconnectedState, UnknownState)):
            app.interface_transition('no_active_connection_found')
        else:
            app.interface_transition('found_active_connection')
        return state

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

    status_label = translated_property("Disconnected")


def connect(app: Application) -> NetworkState:
    """
    Estabilish a connection to the server.
    """
    client = nm.get_client()
    assert app.current_network_uuid is not None
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
    assert app.current_network_uuid is not None
    nm.deactivate_connection(
        client,
        app.current_network_uuid,
        callback,
    )
    return DisconnectedState()


def reconnect(app: Application) -> NetworkState:
    """
    Disconnect and then connect again.
    """
    disconnect(app, update_state=False)
    return ReconnectingState()


UNKNOWN_STATE_MAX_RETRIES = 5


def enter_unknown_state(app: Application) -> NetworkState:
    # Set the state temporarily to unknown but keep polling for updates,
    # since we don't always get notified by the update callback.
    @run_in_background_thread('poll-network-state')
    def determine_network_state_thread():
        counter = 0
        state = nm.get_connection_state()
        while state is nm.ConnectionState.UNKNOWN:
            if counter > UNKNOWN_STATE_MAX_RETRIES:
                # After a number of retries, assume we've disconnected
                # so the user can try to connect again.
                state = nm.ActiveConnectionState.DISCONNECTED
                logger.debug(
                    "network state has been unknown for too long,"
                    " fall back to disconnected state"
                )
                break
            sleep(1)
            counter += 1
            if not isinstance(app.network_state, UnknownState):
                return
            state = nm.get_connection_state()
            logger.debug(f"polling network state: {state}")
        app.make_func_threadsafe(on_state_update_callback)(app, state)

    determine_network_state_thread()
    return UnknownState()


def on_state_update_callback(app: Application, state: nm.ConnectionState):
    """
    Callback for whenever a connection state changes.
    """
    if state is nm.ConnectionState.CONNECTING:
        app.network_transition('set_connecting')
    elif state is nm.ConnectionState.CONNECTED:
        app.network_transition('set_connected')
    elif state is nm.ConnectionState.DISCONNECTED:
        app.network_transition('set_disconnected')
    elif state is nm.ConnectionState.FAILED:
        app.network_transition('set_error')
    elif state is nm.ConnectionState.UNKNOWN:
        app.network_transition('set_unknown')
    else:
        raise ValueError(state)


def on_any_update_callback(app: Application):
    """
    Callback for whenever a connection state might have changed.
    """
    state = nm.get_connection_state()
    on_state_update_callback(app, state)


def get_network_state(app: Application) -> NetworkState:
    """
    Get the network state that corresponds to the connection state.
    """
    state = nm.get_connection_state()
    if state is nm.ConnectionState.CONNECTING:
        return ConnectingState()
    elif state is nm.ConnectionState.CONNECTED:
        return ConnectedState()
    elif state is nm.ConnectionState.DISCONNECTED:
        return DisconnectedState()
    elif state is nm.ConnectionState.FAILED:
        return ConnectionErrorState(None)
    elif state is nm.ConnectionState.UNKNOWN:
        return enter_unknown_state(app)
    else:
        raise ValueError(state)


class ConnectingState(NetworkState):
    """
    The network is currently trying to connect to a server.
    """

    status_label = translated_property("Preparing to connect")
    status_image = StatusImage.CONNECTING

    def start_new_connection(self,
                             app: Application,
                             server: Server,
                             ) -> NetworkState:
        return reconnect(app)

    def disconnect(self, app: Application) -> NetworkState:
        """
        Abort connecting.
        """
        return disconnect(app)


class ConnectedState(NetworkState):
    """
    The network is currently connected to a server.
    """

    status_label = translated_property("Connection active")
    status_image = StatusImage.CONNECTED

    def start_new_connection(self,
                             app: Application,
                             server: Server,
                             ) -> NetworkState:
        return reconnect(app)

    def disconnect(self, app: Application) -> NetworkState:
        return disconnect(app)


class DisconnectedState(NetworkState):
    """
    The network is not currently connected to a server,
    but a configured connection exists.
    """

    status_label = translated_property("Disconnected")
    status_image = StatusImage.NOT_CONNECTED

    def reconnect(self, app: Application) -> NetworkState:
        return connect(app)


class ReconnectingState(NetworkState):
    """
    The network is currently disconnecting
    and will connect again when ready.
    """

    status_label = translated_property("Preparing to connect")
    status_image = StatusImage.CONNECTING

    def set_unknown(self, app: Application) -> NetworkState:
        return connect(app)

    def set_disconnected(self, app: Application) -> NetworkState:
        return connect(app)


class ConnectionErrorState(NetworkState):
    """
    The network could not connect because an error occured.
    """

    status_label = translated_property("Connection failed")
    status_image = StatusImage.NOT_CONNECTED

    def __init__(self, error: Optional[str]):
        self.error = error

    def reconnect(self, app: Application) -> NetworkState:
        return connect(app)


class UnknownState(NetworkState):
    """
    The network state could not be determined.
    """

    def reconnect(self, app: Application) -> NetworkState:
        return connect(app)
