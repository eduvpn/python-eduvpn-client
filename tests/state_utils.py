import threading


TIMEOUT = 5


def wait_for_state_change(state_machine) -> bool:
    """
    Wait for the next state change.

    Return False if the waiting timed out.
    """
    event = threading.Event()
    state_machine.register_generic_callback(lambda *a: event.set())
    return event.wait(TIMEOUT)


def wait_until_state(state_machine, state_type):
    """
    Wait for a specific state type.

    Return False if the waiting timed out.
    """
    while not isinstance(state_machine.state, state_type):
        if not wait_for_state_change(state_machine):
            return False
    return True


class StateTestCaseMixin:
    def assertReachesInterfaceState(self, app, state_type):
        wait_until_state(app.interface_state_machine, state_type)
        self.assertIsInstance(app.interface_state, state_type)

    def assertReachesNetworkState(self, app, state_type):
        wait_until_state(app.network_state_machine, state_type)
        self.assertIsInstance(app.network_state, state_type)
