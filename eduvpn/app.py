import logging
from .server import ServerDatabase
from . import nm
from .state_machine import StateMachine, InvalidStateTransition
from .utils import run_in_background_thread


logger = logging.getLogger(__name__)


class Application:
    def __init__(self, make_func_threadsafe):
        self.make_func_threadsafe = make_func_threadsafe
        from .network import InitialNetworkState
        from .interface.state import InitialInterfaceState
        self.network_state_machine = StateMachine(InitialNetworkState())
        self.interface_state_machine = StateMachine(InitialInterfaceState())
        self.server_db = ServerDatabase()
        self.current_network_uuid = None

    def initialize(self):
        self.initialize_network()
        self.initialize_server_db()

    @run_in_background_thread('init-network')
    def initialize_network(self):
        """
        Determine the current network state.
        """
        # Check if a previous network configuration exists.
        uuid = nm.get_existing_configuration_uuid()
        kwargs = {}
        if uuid:
            self.current_network_uuid = uuid
            # Check what server corresponds to the configuration.
            server = self.server_db.get_single_configured()
            if server is None:
                # There is a network configuration,
                # but no record of what server corresponds to it.
                transition = 'no_previous_connection_found'
            else:
                status_uuid, status = nm.connection_status(nm.get_client())
                if status in [nm.NM.ActiveConnectionState.ACTIVATED,
                              nm.NM.ActiveConnectionState.ACTIVATING]:
                    assert uuid == status_uuid
                    transition = 'found_active_connection'
                    kwargs['server'] = server
                else:
                    transition = 'found_previous_connection'
                    kwargs['server'] = server
        else:
            transition = 'no_previous_connection_found'
        self.network_transition_threadsafe(transition, **kwargs)

        def on_network_update_callback(state, reason):
            network.on_status_update_callback(self, state)

        from . import network
        if not nm.subscribe_to_status_changes(on_network_update_callback):
            logger.warning(
                "unable to subscribe to network updates; "
                "the application may not reflect the current state"
            )

    @run_in_background_thread('init-server-db')
    def initialize_server_db(self):
        """
        Load the lists of organisations and servers.
        """
        self.server_db.update()
        self.interface_transition_threadsafe('server_db_finished_loading')

    @property
    def network_state(self):
        """
        Get the current state of the network.
        """
        return self.network_state_machine.state

    @property
    def interface_state(self):
        """
        Get the current state of the interface.
        """
        return self.interface_state_machine.state

    def connect_state_transition_callbacks(self, obj):
        """
        Register all state transition callback methods decorated with
        `@transition_callback()` and `@transition_edge_callback()`
        of an object.
        """
        from .network import NetworkState
        self.network_state_machine.connect_object_callbacks(obj, NetworkState)
        from .interface.state import InterfaceState
        self.interface_state_machine.connect_object_callbacks(
            obj, InterfaceState)

    def network_transition(self, transition, *args, **kwargs):
        """
        Perform a transition on the network state.
        """
        logger.info(
            f'network transitioning: '
            f'{self.network_state} -> {transition}')
        try:
            self.network_state_machine.transition(
                transition, self, *args, **kwargs)
        except InvalidStateTransition:
            logger.error(
                f'invalid network state transition: '
                f'{self.network_state} -> {transition}')
        else:
            logger.info(
                f'network transitioned: '
                f'{transition} -> {self.network_state}')

    def interface_transition(self, transition, *args, **kwargs):
        """
        Perform a transition on the interface state.
        """
        logger.info(
            f'interface transitioning: '
            f'{self.interface_state} -> {transition}')
        try:
            self.interface_state_machine.transition(
                transition, self, *args, **kwargs)
        except InvalidStateTransition:
            logger.error(
                f'invalid interface state transition: '
                f'{self.interface_state} -> {transition}')
        else:
            logger.info(
                f'interface transitioned: '
                f'{transition} -> {self.interface_state}')

    def network_transition_threadsafe(self, transition, *args, **kwargs):
        """
        Threadsafe version of `network_transition()`.
        """
        transit = self.make_func_threadsafe(self.network_transition)
        transit(transition, *args, **kwargs)

    def interface_transition_threadsafe(self, transition, *args, **kwargs):
        """
        Threadsafe version of `network_transition()`.
        """
        transit = self.make_func_threadsafe(self.interface_transition)
        transit(transition, *args, **kwargs)
