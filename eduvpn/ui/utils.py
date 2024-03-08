from gettext import gettext as _
from gettext import ngettext
from typing import Tuple

import gi
from eduvpn_common.error import WrappedError

from eduvpn.connection import Validity
from eduvpn.utils import run_in_glib_thread

GtkAvailable = True
try:
    gi.require_version("Gtk", "3.0")  # noqa: E402
    from gi.repository import Gtk  # type: ignore
except ValueError:
    GtkAvailable = False


IGNORE_ID = -13
QUIT_ID = -14


@run_in_glib_thread
def style_widget(widget, class_name: str, style: str):
    assert GtkAvailable
    style_context = widget.get_style_context()
    provider = Gtk.CssProvider.new()
    provider.load_from_data(f".{class_name} {{{style}}}".encode("utf-8"))  # type: ignore
    style_context.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    style_context.add_class(class_name.split(":")[0])


def should_show_error(error: Exception):
    if isinstance(error, WrappedError):
        if "cancelled OAuth" in str(error):
            return False
    return True


def get_validity_text(validity: Validity) -> Tuple[bool, str, str]:
    if validity is None:
        return (False, _("N/A"), _("Valid for: <b>unknown</b>"))
    if validity.is_expired:
        return (True, _("expired"), _("This session has expired"))
    delta = validity.remaining
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days == 0:
        if hours == 0:
            if minutes == 0:
                return (
                    False,
                    f"{seconds}s",
                    ngettext(
                        "Valid for: <b>{0} second</b>",
                        "Valid for: <b>{0} seconds</b>",
                        seconds,
                    ).format(seconds),
                )
            else:
                # Round up minutes
                round_up_minutes = minutes
                label_text = "Valid for"
                if seconds > 30:
                    round_up_minutes += 1
                    label_text = "Valid for less than"
                if seconds < 30:
                    label_text = "Valid for more than"
                return (
                    False,
                    f"{minutes}m {seconds}s",
                    ngettext(
                        label_text + ": <b>{0} minute</b>",
                        label_text + ": <b>{0} minutes</b>",
                        round_up_minutes,
                    ).format(round_up_minutes),
                )
        else:
            # Round up hours
            round_up_hours = hours
            label_text = "Valid for"
            if minutes > 30:
                round_up_hours += 1
                label_text = "Valid for less than"
            if minutes < 30:
                label_text = "Valid for more than"
            return (
                False,
                f"{hours}h {minutes}m {seconds}s",
                ngettext(
                    label_text + ": <b>{0} hour</b>",
                    label_text + ": <b>{0} hours</b>",
                    round_up_hours,
                ).format(round_up_hours),
            )
    else:
        return (False, f"{days}d {hours}h {minutes}m {seconds}s", "")


@run_in_glib_thread
def show_ui_component(component, show: bool) -> None:
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


@run_in_glib_thread
def show_error_dialog(
    parent, name: str, title: str, message: str, only_quit: bool = False
):
    assert GtkAvailable
    dialog = Gtk.MessageDialog(  # type: ignore
        parent=parent,
        type=Gtk.MessageType.INFO,  # type: ignore
        title=name,
        message_format=title,
    )

    if not only_quit:
        dialog.add_buttons(_("Ignore and continue"), IGNORE_ID)  # type: ignore

    dialog.add_buttons(  # type: ignore
        _("Quit client"),
        QUIT_ID,
    )
    dialog.format_secondary_text(message)  # type: ignore
    dialog.show()  # type: ignore
    close = dialog.run()  # type: ignore
    dialog.destroy()  # type: ignore
    if close == QUIT_ID or only_quit:
        parent.close()
