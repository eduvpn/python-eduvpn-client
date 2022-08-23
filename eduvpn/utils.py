import sys
from typing import Optional, Callable
import threading
from functools import lru_cache, partial, wraps
from gettext import gettext
from logging import getLogger
from os import path, environ
from sys import prefix
from requests import Session
from requests.adapters import HTTPAdapter, Retry
import eduvpn_common.event as common
from eduvpn_common.state import State, StateType

logger = getLogger(__file__)


def get_logger(name_space: str):
    return getLogger(name_space)


@lru_cache(maxsize=1)
def get_prefix() -> str:
    """
    Returns the Python prefix where eduVPN is installed

    returns:
        path to Python installation prefix
    """
    target = "share/eduvpn/builder/mainwindow.ui"
    local = path.dirname(path.dirname(path.abspath(__file__)))
    options = [local, path.expanduser("~/.local"), "/usr/local", prefix]
    for option in options:
        logger.debug(f"looking for '{target}' in '{option}'")
        if path.isfile(path.join(option, target)):
            return option
    raise Exception("Can't find eduVPN installation")


def get_config_dir() -> str:
    return environ.get("XDG_CONFIG_HOME", "~/.config")


def thread_helper(func: Callable, *, name: Optional[str] = None) -> threading.Thread:
    """
    Runs a function in a thread

    args:
        func (lambda): a function to run in the background
    """
    thread = threading.Thread(target=func, name=name)
    thread.daemon = True
    thread.start()
    return thread


def get_ui_state(state: State) -> int:
    # The UI state will have as identifier the last state id + offset of the state
    # So for example the UI DEREGISTERED state will come directly after the last normal state
    return len(State) + state


def ui_transition(state: State, state_type: StateType):
    def decorator(func):
        @run_in_main_gtk_thread
        @common.class_state_transition(get_ui_state(state), state_type)
        def inner(self, other_state, data):
            func(self, other_state, data)

        return inner

    return decorator


def model_transition(state: State, state_type: StateType):
    def decorator(func):
        @run_in_background_thread(str(func))
        def inner(self, other_state, data):
            # The model converts the data
            model_converted = func(self, other_state, data)

            other_ui_state = get_ui_state(other_state)
            ui_state = get_ui_state(state)
            # We can then pass it to the UI
            if state_type == StateType.Enter:
                self.common.event.run(other_ui_state, ui_state, model_converted)
            else:
                self.common.event.run(ui_state, other_ui_state, model_converted)

        # Add the inner function on the state transition
        common.class_state_transition(state, state_type)(inner)

        # Return the inner function to be called
        return inner

    return decorator


def run_in_background_thread(name: Optional[str] = None):
    """
    Decorator for functions that must always run
    in a background thread.
    """

    def decorator(func):
        @wraps(func)
        def background_func(*args, **kwargs):
            thread_helper(partial(func, *args, **kwargs), name=name)

        return background_func

    return decorator


def run_in_main_gtk_thread(func):
    """
    Decorator for functions that must always run
    in the main GTK thread.
    """
    from gi.repository import GLib

    @wraps(func)
    def main_gtk_thread_func(*args, **kwargs):
        GLib.idle_add(func, *args, **kwargs)

    return main_gtk_thread_func


def run_periodically(
    func: Callable[[], None],
    interval: float,
    name: Optional[str] = None,
) -> Callable[[], None]:
    """
    Run a funtion periodically in a background thread.

    The given function is called every `interval` seconds,
    until either it returns False
    or until the returned cancel callback is called.
    """
    if name is None:
        name = "run-periodically"
    event = threading.Event()

    @run_in_background_thread(name)
    def run_periodic_thread():
        if func() is False:
            return

        while 1:
            if event.wait(interval):
                return
            elif func() is False:
                return

    run_periodic_thread()
    return event.set


def run_delayed(
    func: Callable[[], None],
    delay: float,
    name: Optional[str] = None,
) -> Callable[[], None]:
    """
    Run a function with a delay.

    The given function is called once when
    `delay` seconds have passed.
    If the delay is less then zero, the function is called as soon as possible.
    Call the returned callback to cancel calling the delayed function.
    """
    if name is None:
        name = "run-delayed"
    event = threading.Event()

    @run_in_background_thread(name)
    def run_delayed_thread():
        if event.wait(delay):
            return
        else:
            func()

    run_delayed_thread()
    return event.set


def cancel_at_context_end(cancel_callback: Callable[[], None]):
    """
    This generator is intended to be used with
    `state_machine.transition_level_callback`
    to cancel a thread when a state is exited.
    """
    try:
        yield
    finally:
        cancel_callback()


if sys.version_info < (3, 9):
    # Backported from Python 3.10
    # https://github.com/python/cpython/blob/3.10/Lib/functools.py#L651
    def cache(func):
        from functools import lru_cache

        return lru_cache(maxsize=None)(func)

else:
    from functools import cache  # noqa: W0611


def get_human_readable_bytes(total_bytes: int) -> str:
    """
    Helper function to calculate the human readable bytes.
    E.g. B, kB, MB, GB, TB.
    """
    suffix = ""
    hr_bytes = float(total_bytes)
    for suffix in ["B", "kB", "MB", "GB", "TB"]:
        if hr_bytes < 1024.0:
            break
        if suffix != "TB":
            hr_bytes /= 1024.0

    if suffix == "B":
        return f"{int(hr_bytes)} {suffix}"
    return f"{hr_bytes:.2f} {suffix}"


def translated_property(text):
    return property(lambda self: gettext(text))  # type: ignore
