from typing import (
    TypeVar, Generic, Any, Union, Optional, Callable,
    Type, Tuple, List, Dict, Set, Generator)
import enum
from contextlib import contextmanager


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

ANY_TRANSITION = object()
LEVEL_CONTEXT = object()


# typing aliases
State = TypeVar('State')
StateType = Type[State]
StateTargets = Union[StateType, Tuple[StateType, ...]]
TransitionCallback = Callable[[State, State], None]
LevelContext = Generator[None, None, None]
LevelCallback = Callable[[State], LevelContext]
TransitionCallbackRegistry = Dict[
    Optional[Tuple[StateType, TransitionEdge]],
    Set[TransitionCallback]]
LevelCallbackRegistry = Dict[StateType, Set[LevelCallback]]


TRANSITION_CALLBACK_MARKER = '__transition_callback_for_state'


def setattr_list_item(obj, attr, item):
    try:
        list_attr = getattr(obj, attr)
    except AttributeError:
        list_attr = []
        setattr(obj, attr, list_attr)
    list_attr.append(item)


def normalise_state_targets(state_targets: StateTargets) -> Tuple[StateType, ...]:
    "Normalise state targets argument to tuple."
    if not isinstance(state_targets, tuple):
        return (state_targets, )
    else:
        return state_targets


def transition_callback(state_targets: StateTargets):
    """
    Decorator factory to mark a method as a
    transition callback for all transitions.

    Note the argument is the base class for states of the state machine
    to register transition events of.
    Without this, there would be no way to know which
    state machine this callback targets.
    """
    state_targets = normalise_state_targets(state_targets)

    def decorator(func: TransitionCallback):
        for state_type in state_targets:
            setattr_list_item(func,
                              TRANSITION_CALLBACK_MARKER,
                              (ANY_TRANSITION, state_type))
        return func

    return decorator


def transition_edge_callback(edge: TransitionEdge,
                             state_targets: StateTargets):
    """
    Decorator factory to mark a method as a transition callback
    for specific state transition edges.
    """
    state_targets = normalise_state_targets(state_targets)

    def decorator(func: TransitionCallback):
        for state_type in state_targets:
            setattr_list_item(func,
                              TRANSITION_CALLBACK_MARKER,
                              (edge, state_type))
        return func

    return decorator


def transition_level_callback(state_targets: StateTargets):
    """
    Decorator factory to mark a method as a level callback
    for specific state contexts.
    """
    state_targets = normalise_state_targets(state_targets)

    def decorator(func: LevelCallback):
        for state_type in state_targets:
            setattr_list_item(func,
                              TRANSITION_CALLBACK_MARKER,
                              (LEVEL_CONTEXT, state_type))
        return func

    return decorator


def _find_transition_callbacks(obj: Any, base_state_type: Type[State]):
    for attr in dir(obj):
        try:
            callback = getattr(obj, attr)
        except Exception:
            # Gtk raises RuntimeError for some attributes.
            continue
        try:
            registrations = getattr(callback, TRANSITION_CALLBACK_MARKER)
        except AttributeError:
            pass
        else:
            for trigger, state_type in registrations:
                if issubclass(state_type, base_state_type):
                    yield callback, trigger, state_type


class InvalidStateTransition(Exception):
    def __init__(self, name: str):
        self.name = name


class StateMachine(Generic[State]):
    """
    State machine wrapper that allows registering transition callbacks.
    """

    def __init__(self, initial_state: State):
        self.initial_state = initial_state
        self._state = initial_state
        self._transition_callbacks: TransitionCallbackRegistry = {}
        self._level_callbacks: LevelCallbackRegistry = {}
        self._active_contexts: List[LevelContext] = []

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
        if new_state is not old_state:
            with self.trigger_callbacks(old_state, new_state):
                self._state = new_state
        return new_state

    @contextmanager
    def trigger_callbacks(self, old_state: State, new_state: State):
        self._exit_contexts()
        self._call_edge_callbacks(EXIT, old_state, new_state)
        try:
            yield
        finally:
            self._call_generic_callbacks(old_state, new_state)
            self._call_edge_callbacks(ENTER, old_state, new_state)
            self._enter_contexts(new_state)

    def trigger_initial_callbacks(self):
        with self.trigger_callbacks(self.initial_state, self.state):
            pass

    def register_generic_callback(self, callback: TransitionCallback):
        """
        Register a callback for all transitions.
        """
        self._transition_callbacks.setdefault(None, set()).add(callback)

    def register_edge_callback(self,
                               state_type: Type[State],
                               edge: TransitionEdge,
                               callback: TransitionCallback):
        """
        Register a callback for specific transition edges.
        """
        self._transition_callbacks.setdefault((state_type, edge), set()).add(callback)

    def register_level_callback(self,
                                state_type: Type[State],
                                context: LevelCallback):
        """
        Register a context function for specific state.

        The function must return a generator that yields once
        to capture the life of a state.
        similar to contextlib.contextmanager,
        The returned generator is executed up to the yield
        when the state is entered,
        Then, when the state is exited, the generator is resumed
        and is required to stop.
        """
        self._level_callbacks.setdefault(state_type, set()).add(context)

    def connect_object_callbacks(self, obj, base_state_type: Type[State]):
        """
        Register all state transition callback methods decorated with
        `@transition_callback()` and `@transition_edge_callback()`
        of an object.

        Provide the base class of states for this state machine
        as the second argument to filter registrations for this
        state machine only.
        Only method registered to a subclass of this base class
        will be connected.
        """
        iterator = _find_transition_callbacks(obj, base_state_type)
        for callback, trigger, state_type in iterator:
            if trigger is ANY_TRANSITION:
                # This callback targets all events.
                self.register_generic_callback(callback)
            elif trigger is LEVEL_CONTEXT:
                # This callback targets a state context.
                self.register_level_callback(state_type, callback)
            elif isinstance(trigger, TransitionEdge):
                # This callback targets a specific state edge.
                self.register_edge_callback(state_type, trigger, callback)
            else:
                raise TypeError(trigger)

    def _call_generic_callbacks(self, old_state: State, new_state: State):
        for callback in self._transition_callbacks.get(None, []):
            callback(old_state, new_state)

    def _call_edge_callbacks(self,
                             edge: TransitionEdge,
                             old_state: State,
                             new_state: State):
        state = new_state if edge is ENTER else old_state
        for callback in self._transition_callbacks.get((state.__class__, edge), []):
            callback(old_state, new_state)

    def _enter_contexts(self, state: State):
        for callback in self._level_callbacks.get(state.__class__, []):
            generator = callback(state)
            try:
                next(generator)
            except StopIteration:
                # The generator is expected to yield exactly once.
                raise RuntimeError("generator didn't yield")
            self._active_contexts.append(generator)

    def _exit_contexts(self):
        while self._active_contexts:
            generator = self._active_contexts.pop()
            try:
                next(generator)
            except StopIteration:
                # The generator is expected to stop after it has yielded once.
                pass
            else:
                raise RuntimeError("generator didn't stop")


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
