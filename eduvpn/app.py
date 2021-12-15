import logging
from datetime import datetime
from gettext import gettext as _
from .server import ServerDatabase, ServerSignatureError
from . import nm
from . import storage
from .variants import ApplicationVariant
from .state_machine import StateMachine, InvalidStateTransition
from .config import Configuration
from .utils import run_in_background_thread, run_delayed, cancel_at_context_end


logger = logging.getLogger(__name__)


class Application:
    def __init__(self, variant: ApplicationVariant, make_func_threadsafe):
        self.variant = variant
        self.make_func_threadsafe = make_func_threadsafe
        from .network import NetworkState, InitialNetworkState
        from .session import (
            SessionState, InitialSessionState,
            SessionActiveState, SessionPendingExpiryState,
        )
        from .interface.state import InterfaceState, InitialInterfaceState
        self.network_state_machine: StateMachine[NetworkState]
        self.session_state_machine: StateMachine[SessionState]
        self.interface_state_machine: StateMachine[InterfaceState]
        self.network_state_machine = StateMachine(InitialNetworkState())
        self.session_state_machine = StateMachine(InitialSessionState())
        self.interface_state_machine = StateMachine(InitialInterfaceState())
        self.server_db = ServerDatabase()
        self.current_network_uuid = None
        self.session_state_machine.register_level_callback(
            SessionActiveState, self.context_session_active)
        self.session_state_machine.register_level_callback(
            SessionPendingExpiryState, self.context_session_pending_expiry)

    def initialize(self):
        self.initialize_network()
        if self.variant.use_predefined_servers:
            self.initialize_server_db()
        self.config = Configuration.load()

    def initialize_network(self):
        """
        Determine the current network state.
        """
        # Check if a previous network configuration exists.
        uuid = nm.get_existing_configuration_uuid()
        if uuid:
            self.current_network_uuid = uuid
            # Check what server corresponds to the configuration.
            server = self.server_db.get_single_configured()
            if server is None:
                # There is a network configuration,
                # but no record of what server corresponds to it.
                self.session_transition('no_previous_session_found')
            else:
                validity = storage.get_current_validity(server.oauth_login_url)
                self.session_transition('found_active_session', server, validity)
        else:
            self.session_transition('no_previous_session_found')

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
        try:
            self.server_db.update()
        except ServerSignatureError as e:
            self.interface_transition_threadsafe(
                'encountered_exception',
                _("Received a bad signature from server {server}").format(server=e.uri))
        else:
            self.interface_transition_threadsafe('server_db_finished_loading')

    @property
    def network_state(self):
        """
        Get the current state of the network.
        """
        return self.network_state_machine.state

    @property
    def session_state(self):
        """
        Get the current state of the session.
        """
        return self.session_state_machine.state

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
        self.network_state_machine.connect_object_callbacks(
            obj, NetworkState)
        from .session import SessionState
        self.session_state_machine.connect_object_callbacks(
            obj, SessionState)
        from .interface.state import InterfaceState
        self.interface_state_machine.connect_object_callbacks(
            obj, InterfaceState)

    def _base_transition(self, state_machine, state_machine_name, transition, *args, **kwargs):
        """
        Perform a transition on a state machine.
        """
        logger.debug(
            f'{state_machine_name} transitioning: '
            f'{state_machine.state} -> {transition}')
        try:
            state_machine.transition(
                transition, self, *args, **kwargs)
        except InvalidStateTransition:
            logger.error(
                f'invalid {state_machine_name} state transition: '
                f'{state_machine.state} -> {transition}')
        else:
            logger.debug(
                f'{state_machine_name} transitioned: '
                f'{transition} -> {state_machine.state}')

    def network_transition(self, transition, *args, **kwargs):
        """
        Perform a transition on the network state.
        """
        self._base_transition(
            self.network_state_machine,
            'network',
            transition,
            *args,
            **kwargs,
        )

    def session_transition(self, transition, *args, **kwargs):
        """
        Perform a transition on the network state.
        """
        self._base_transition(
            self.session_state_machine,
            'session',
            transition,
            *args,
            **kwargs,
        )

    def interface_transition(self, transition, *args, **kwargs):
        """
        Perform a transition on the interface state.
        """
        self._base_transition(
            self.interface_state_machine,
            'interface',
            transition,
            *args,
            **kwargs,
        )

    def network_transition_threadsafe(self, transition, *args, **kwargs):
        """
        Threadsafe version of `network_transition()`.
        """
        transit = self.make_func_threadsafe(self.network_transition)
        transit(transition, *args, **kwargs)

    def session_transition_threadsafe(self, transition, *args, **kwargs):
        """
        Threadsafe version of `session_transition()`.
        """
        transit = self.make_func_threadsafe(self.session_transition)
        transit(transition, *args, **kwargs)

    def interface_transition_threadsafe(self, transition, *args, **kwargs):
        """
        Threadsafe version of `network_transition()`.
        """
        transit = self.make_func_threadsafe(self.interface_transition)
        transit(transition, *args, **kwargs)

    def context_session_active(self, state):
        expiry_duration = (state.validity.pending_expiry_time - datetime.utcnow()).total_seconds()

        def on_session_pending_expiry():
            self.session_transition_threadsafe('pending_expiry')

        return cancel_at_context_end(run_delayed(on_session_pending_expiry, expiry_duration))

    def context_session_pending_expiry(self, state):
        expiry_duration = (state.validity.end - datetime.utcnow()).total_seconds()

        def on_session_expired():
            self.session_transition_threadsafe('has_expired')

        return cancel_at_context_end(run_delayed(on_session_expired, expiry_duration))
