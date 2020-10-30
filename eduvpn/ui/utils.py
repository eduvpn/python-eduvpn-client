from eduvpn.utils import logger
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


# ui thread
def error_helper(parent: Gtk.GObject, msg_big: str, msg_small: str) -> None:  # type: ignore
    """
    Shows a GTK error message dialog.
    args:
        parent (GObject): A GTK Window
        msg_big (str): the big string
        msg_small (str): the small string
    """
    logger.error(f"{msg_big}: {msg_small}")
    error_dialog = Gtk.MessageDialog(parent, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, str(msg_big))  # type: ignore
    error_dialog.format_secondary_text(str(msg_small))  # type: ignore
    error_dialog.run()  # type: ignore
    error_dialog.hide()  # type: ignore
