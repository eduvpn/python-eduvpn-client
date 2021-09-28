import gi
gi.require_version('Gtk', '3.0')  # noqa: E402
from gi.repository import Gtk


def show_ui_component(component, show: bool):
    """
    Set the visibility of a UI component.
    """
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


def show_error_dialog(parent, name: str, title: str, message: str):
    dialog = Gtk.MessageDialog(  # type: ignore
        parent=parent,
        type=Gtk.MessageType.INFO,  # type: ignore
        buttons=Gtk.ButtonsType.OK,  # type: ignore
        title=name,
        message_format=title)
    dialog.format_secondary_text(message)  # type: ignore
    dialog.show()  # type: ignore
    dialog.run()  # type: ignore
    dialog.destroy()  # type: ignore
