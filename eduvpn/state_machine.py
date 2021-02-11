from typing import Any, Union, Callable, Type, Tuple
import enum


State = Any
Callback = Callable[[State, State], None]
StateTargets = Union[Type[State], Tuple[Type[State]]]


class TransitionEdge(enum.Enum):
    """
    The edge of a state lifetime.

    The edge is `enter` when the state starts,
    and `exit` when it ends.
    """

    enter = enum.auto()
    exit = enum.auto()


ENTER = TransitionEdge.enter
EXIT = TransitionEdge.exit


TRANSITION_CALLBACK_MARKER = '__transition_callback_for_state'

def setattr_list_item(obj, attr, item):
    try:
        list_attr = getattr(obj, attr)
    except AttributeError:
        list_attr = []
        setattr(obj, attr, list_attr)
    list_attr.append(item)

def transition_callback(state_targets: StateTargets):
    """
    Decorator factory to mark a method as a transition callback for all transitions.

    Note the argument is the base class for states of the state machine
    to register transition events of.
    Without this, there would be no way to know which
    state machine this callback targets.
    """
    if not isinstance(state_targets, tuple):
        # Normalise argument to tuple.
        state_targets = (state_targets, )

    def decorator(func: Callback):
        for state_type in state_targets:
            setattr_list_item(func, TRANSITION_CALLBACK_MARKER, (None, state_type))
        return func

    return decorator

def transition_edge_callback(edge: TransitionEdge, state_targets: StateTargets):
    """
    Decorator factory to mark a method as a transition callback
    for specific state transition edges.
    """
    if not isinstance(state_targets, tuple):
        # Normalise argument to tuple.
        state_targets = (state_targets, )

    def decorator(func: Callback):
        for state_type in state_targets:
            setattr_list_item(func, TRANSITION_CALLBACK_MARKER, (edge, state_type))
        return func

    return decorator

def _find_transition_callbacks(obj: Any, base_state_type: Type[State]):
    for attr in dir(obj):
        callback = getattr(obj, attr)
        try:
            registrations = getattr(callback, TRANSITION_CALLBACK_MARKER)
        except AttributeError:
            pass
        else:
            for edge, state_type in registrations:
                if issubclass(state_type, base_state_type):
                    yield callback, edge, state_type


class InvalidStateTransition(Exception):
    def __init__(self, name: str):
        self.name = name


class StateMachine:
    """
    State machine wrapper that allows registering transition callbacks.
    """

    def __init__(self, initial_state: State):
        self._state = initial_state
        self._callbacks = {}

    @property
    def state(self) -> State:
        """
        Obtain the current state.

        The state can be changed by calling `transition()`
        with the name of a transition of the current state.
        """
        # The state is behind a property to prevent setting it directly.
        return self._state

    def transition(self, transition: str, *args, **kwargs):
        """
        Transition to a new state.

        This method is *not* thread-safe,
        all calls should be made from the same thread.
        """
        old_state = self._state
        try:
            transition_func = getattr(old_state, transition)
        except AttributeError as e:
            raise InvalidStateTransition(transition) from e
        new_state = transition_func(*args, **kwargs)
        self._call_edge_callbacks(EXIT, old_state, new_state)
        self._state = new_state
        self._call_generic_callbacks(old_state, new_state)
        self._call_edge_callbacks(ENTER, old_state, new_state)
        return new_state

    def register_generic_callback(self, callback: Callback):
        """
        Register a callback for all transitions.
        """
        self._callbacks.setdefault(None, set()).add(callback)

    def register_edge_callback(self, state_type: Type[State], edge: TransitionEdge, callback: Callback):
        """
        Register a callback for specific transition edges.
        """
        self._callbacks.setdefault((state_type, edge), set()).add(callback)

    def connect_object_callbacks(self, obj, base_state_type: Type[State]):
        """
        Register all state transition callback methods decorated with
        `@transition_callback()` and `@transition_edge_callback()` of an object.

        Provide the base class of states for this state machine
        as the second argument to filter registrations for this
        state machine only.
        Only method registered to a subclass of this base class
        will be connected.
        """
        for callback, edge, state_type in _find_transition_callbacks(obj, base_state_type):
            if edge is None:
                # This callback targets all events.
                self.register_generic_callback(callback)
            else:
                # This callback targets a specific state edge.
                self.register_edge_callback(state_type, edge, callback)

    def _call_generic_callbacks(self, old_state: State, new_state: State):
        for callback in self._callbacks.get(None, []):
            callback(old_state, new_state)

    def _call_edge_callbacks(self, edge: TransitionEdge, old_state: State, new_state: State):
        state = new_state if edge is ENTER else old_state
        for callback in self._callbacks.get((state.__class__, edge), []):
            callback(old_state, new_state)


class BaseState:
    """
    Base class for all state machine states.
    """

    def __repr__(self):
        fields = ','.join(f' {k}={v!r}' for k, v in self.__dict__.items())
        return f'<{self.__class__.__name__}{fields}>'

    def has_transition(self, name: str) -> bool:
        """
        Return True if this state defines the transition function.
        """
        return hasattr(self, name)

    def copy(self, **fields):
        """
        Return a copy of this state, with some fields altered.
        """
        return self.__class__(**{**self.__dict__, **fields})
