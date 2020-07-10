import threading
from functools import lru_cache
from logging import getLogger
from os import path
from sys import prefix
from typing import Callable

logger = getLogger(__file__)

try:
    import gi

    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk
except (ImportError, ValueError) as e:
    logger.warning("GTK not available")


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
        logger.debug(u"looking for '{}' in '{}'".format(target, option))
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


# ui thread
def error_helper(parent: 'Gtk.GObject', msg_big: str, msg_small: str) -> None:  # type: ignore
    """
    Shows a GTK error message dialog.
    args:
        parent (GObject): A GTK Window
        msg_big (str): the big string
        msg_small (str): the small string
    """
    logger.error(u"{}: {}".format(msg_big, msg_small))
    error_dialog = Gtk.MessageDialog(parent, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, str(msg_big))  # type: ignore
    error_dialog.format_secondary_text(str(msg_small))  # type: ignore
    error_dialog.run()  # type: ignore
    error_dialog.hide()  # type: ignore
