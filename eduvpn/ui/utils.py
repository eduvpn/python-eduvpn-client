from eduvpn.utils import logger
import gi
gi.require_version('Gtk', '3.0')  # noqa: E402
from gi.repository import Gtk, GObject


# ui thread
def error_helper(parent: GObject,  # type: ignore
                 msg_big: str,
                 msg_small: str) -> None:
    """
    Shows a GTK error message dialog.
    args:
        parent (GObject): A GTK Window
        msg_big (str): the big string
        msg_small (str): the small string
    """
    logger.error(f"{msg_big}: {msg_small}")
    error_dialog = Gtk.MessageDialog(  # type: ignore
        parent,
        0,
        Gtk.MessageType.ERROR,  # type: ignore
        Gtk.ButtonsType.OK,  # type: ignore
        str(msg_big),
    )
    error_dialog.format_secondary_text(str(msg_small))  # type: ignore
    error_dialog.run()  # type: ignore
    error_dialog.hide()  # type: ignore


def show_ui_component(builder, component: str, show: bool):
    """
    Set the visibility of a UI component.
    """
    component = builder.get_object(component)
    if show:
        component.show()  # type: ignore
    else:
        component.hide()  # type: ignore


def link_markup(link: str) -> str:
    try:
        scheme, rest = link.split(':', 1)
        if rest.startswith('//'):
            rest = rest[2:]
    except ValueError:
        return link
    else:
        return f'<a href="{link}">{rest}</a>'


def show_error_dialog(builder, name: str, title: str, message: str):
    dialog = Gtk.MessageDialog(  # type: ignore
        parent=builder.get_object('applicationWindow'),
        type=Gtk.MessageType.INFO,  # type: ignore
        buttons=Gtk.ButtonsType.OK,  # type: ignore
        title=name,
        message_format=title)
    dialog.format_secondary_text(message)  # type: ignore
    dialog.show()  # type: ignore
    dialog.run()  # type: ignore
    dialog.destroy()  # type: ignore
