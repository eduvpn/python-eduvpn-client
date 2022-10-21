import gi

from gettext import gettext as _
from gettext import ngettext
from eduvpn.app import Validity
from eduvpn_common.error import WrappedError, ErrorLevel
from eduvpn.utils import run_in_main_gtk_thread
gi.require_version("Gtk", "3.0")  # noqa: E402
from gi.repository import Gtk
from gi.overrides.Gtk import Widget
from typing import Tuple


@run_in_main_gtk_thread
def style_widget(widget: Gtk.Widget, class_name: str, style: str):
    style_context = widget.get_style_context()
    provider = Gtk.CssProvider.new()
    provider.load_from_data(f".{class_name} {{{style}}}".encode("utf-8"))
    style_context.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    style_context.add_class(class_name.split(":")[0])


@run_in_main_gtk_thread
def style_tree_view(window, tree_view):
    # Get the background from the window to 'blend' the tree view
    style_context = window.get_style_context()
    background = style_context.get_background_color(Gtk.StateFlags.NORMAL).to_string()
    # grayish
    bordercolor = "#B2BEB5"
    # Organgeish in the style of the eduVPN logo
    background_hl = "#E24301"
    # Plain white
    textcolor_hl = "#ffffff"
    style_widget(tree_view, "TreeView", f"background-color: {background}; border-top-color: {bordercolor};")
    style_widget(tree_view, "TreeView:hover", f"color: {textcolor_hl}; background-color: {background_hl}; border-top-color: {bordercolor}")


def should_show_error(error: Exception):
    if isinstance(error, WrappedError):
        return error.level != ErrorLevel.ERR_INFO
    return True


def get_validity_text(validity: Validity) -> Tuple[bool, str]:
    if validity is None:
        return (False, _(f"Valid for: <b>unknown</b>"))
    if validity.is_expired:
        return (True, _("This session has expired"))
    delta = validity.remaining
    days = delta.days
    hours = delta.seconds // 3600
    if days == 0:
        if hours == 0:
            minutes = delta.seconds // 60
            if minutes == 0:
                seconds = delta.seconds
                return (False, ngettext(
                    "Valid for: <b>{0} second</b>",
                    "Valid for: <b>{0} seconds</b>",
                    seconds,
                ).format(seconds))
            else:
                return (False, ngettext(
                    "Valid for: <b>{0} minute</b>",
                    "Valid for: <b>{0} minutes</b>",
                    minutes,
                ).format(minutes))
        else:
            return (False, ngettext(
                "Valid for: <b>{0} hour</b>", "Valid for: <b>{0} hours</b>", hours
            ).format(hours))
    else:
        dstr = ngettext(
            "Valid for: <b>{0} day</b>", "Valid for: <b>{0} days</b>", days
        ).format(days)
        hstr = ngettext(" and <b>{0} hour</b>", " and <b>{0} hours</b>", hours).format(
            hours
        )
        return (False, (dstr + hstr))


@run_in_main_gtk_thread
def show_ui_component(component: Widget, show: bool) -> None:
    """
    Set the visibility of a UI component.
    """
    if show:
        component.show()  # type: ignore
    else:
        component.hide()  # type: ignore


def link_markup(link: str) -> str:
    try:
        _scheme, rest = link.split(":", 1)
        if rest.startswith("//"):
            rest = rest[2:]
    except ValueError:
        return link
    else:
        return f'<a href="{link}">{rest}</a>'


@run_in_main_gtk_thread
def show_error_dialog(parent, name: str, title: str, message: str, only_quit: bool = False):
    dialog = Gtk.MessageDialog(  # type: ignore
        parent=parent,
        type=Gtk.MessageType.INFO,  # type: ignore
        title=name,
        message_format=title,
    )

    ignore_id = -13
    quit_id = -14
    if not only_quit:
        dialog.add_buttons(_("Ignore and continue"), ignore_id)

    dialog.add_buttons(
        _("Quit client"), quit_id,
    )
    dialog.format_secondary_text(message)  # type: ignore
    dialog.show()  # type: ignore
    close = dialog.run()  # type: ignore
    dialog.destroy()  # type: ignore
    if close == quit_id or only_quit:
        parent.close()
