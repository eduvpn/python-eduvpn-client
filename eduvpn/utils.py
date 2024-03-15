import logging
import os
import sys
import threading
import traceback
from functools import lru_cache, partial, wraps
from gettext import gettext
from os import environ, path
from sys import prefix
from typing import Callable, Optional, Union

from eduvpn_common.event import class_state_transition
from eduvpn_common.main import WrappedError
from eduvpn_common.state import State, StateType

logger = logging.getLogger(__file__)


def get_logger(name_space: str) -> logging.Logger:
    return logging.getLogger(name_space)


def handle_exceptions(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))


def get_ui_state(state: State) -> int:
    # The UI state will have as identifier the last state id + offset of the state
    # So for example the UI DEREGISTERED state will come directly after the last normal state
    return len(State) + state


ERROR_STATE = 2 * len(State) + 1


def handle_exception(common, exception):
    log_exception(exception)
    common.event_handler.run(
        get_ui_state(ERROR_STATE), get_ui_state(ERROR_STATE), exception
    )


def model_transition(state: State, state_type: StateType) -> Callable:
    def decorator(func):
        @run_in_background_thread(str(func))
        def inner(self, other_state, data):
            # The model converts the data
            try:
                model_converted = func(self, other_state, data)
            except Exception as e:
                handle_exception(self.common, e)
                return

            other_ui_state = get_ui_state(other_state)
            ui_state = get_ui_state(state)
            # We can then pass it to the UI
            if state_type == StateType.ENTER:
                self.common.event_handler.run(other_ui_state, ui_state, model_converted)
            else:
                self.common.event_handler.run(ui_state, other_ui_state, model_converted)

        # Add the inner function on the state transition
        class_state_transition(state, state_type)(inner)

        # Return the inner function to be called
        return inner

    return decorator


def ui_transition(state: State, state_type: StateType) -> Callable:
    def decorator(func):
        @run_in_glib_thread
        @class_state_transition(get_ui_state(state), state_type)
        def inner(self, other_state, data):
            func(self, other_state, data)

        return inner

    return decorator


def cmd_transition(state: State, state_type: StateType):
    def decorator(func):
        @class_state_transition(get_ui_state(state), state_type)
        def inner(self, other_state, data):
            func(self, other_state, data)

        return inner

    return decorator


def init_logger(debug: bool, logfile, mode):
    log_format = (
        "%(asctime)s - %(threadName)s - %(levelname)s - %(name)s"
        " - %(filename)s:%(lineno)d - %(message)s"
    )
    os.makedirs(
        os.path.dirname(logfile),
        mode=mode,
        exist_ok=True,
    )
    if debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(logfile),
            logging.StreamHandler(),
        ],
    )
    # Log unhandled exceptions
    sys.excepthook = handle_exceptions


def log_exception(exception: Exception):
    if isinstance(exception, WrappedError) and exception.misc:
        logger.debug(f"eduvpn-common misc error returned: {str(exception)}")
    else:
        # Other exceptions are already logged by Go
        logger.error(f"exception occurred: {str(exception)}")
        traceback.print_exc()


@lru_cache(maxsize=1)
def get_prefix() -> str:
    """
    Returns the Python prefix where eduVPN is installed

    returns:
        path to Python installation prefix
    """
    target = "share/eduvpn/builder/mainwindow.ui"
    local = f"{path.dirname(path.abspath(path.abspath(__file__)))}/data"
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


def run_in_background_thread(name: Optional[str] = None) -> Callable:
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


def run_in_glib_thread(func: Union[partial, Callable]) -> Callable:
    """
    Decorator for functions that must always run
    in the main GTK thread.
    """
    from gi.repository import GLib

    @wraps(func)
    def main_gtk_thread_func(*args, **kwargs):
        GLib.idle_add(partial(func, *args, **kwargs))

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


def translated_property(text: str) -> property:
    return property(lambda self: gettext(text))  # type: ignore
