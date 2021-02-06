import threading
from functools import lru_cache, partial, wraps
from logging import getLogger
from os import path
from sys import prefix
from typing import Callable

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
    target = 'share/eduvpn/builder/mainwindow.ui'
    local = path.dirname(path.dirname(path.abspath(__file__)))
    options = [local, path.expanduser('~/.local'), '/usr/local', prefix]
    for option in options:
        logger.debug(f"looking for '{target}' in '{option}'")
        if path.isfile(path.join(option, target)):
            return option
    raise Exception("Can't find eduVPN installation")


def thread_helper(func: Callable) -> threading.Thread:
    """
    Runs a function in a thread

    args:
        func (lambda): a function to run in the background
    """
    thread = threading.Thread(target=func)
    thread.daemon = True
    thread.start()
    return thread

def run_in_background_thread(func):
    """
    Decorator for functions that must always run
    in a background thread.
    """

    @wraps(func)
    def background_func(*args, **kwargs):
        thread_helper(partial(func, *args, **kwargs))

    return background_func

def run_in_main_gtk_thread(func):
    """
    Decorator for functions that must always run
    in the main GTK thread.
    """
    from gi.repository import GLib

    @wraps(func)
    def main_gtk_thread_func(*args, **kwargs):
        GLib.idle_add(partial(func, *args, **kwargs))

    return main_gtk_thread_func
