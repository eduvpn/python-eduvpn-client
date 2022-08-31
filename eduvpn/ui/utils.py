import gi

from gettext import gettext as _
from gettext import ngettext
from eduvpn.app import Validity
gi.require_version("Gtk", "3.0")  # noqa: E402
from gi.repository import Gtk
from gi.overrides.Gtk import Widget

def get_validity_text(validity: Validity) -> str:
    if validity is None:
        return _(f"Valid for: <b>unknown</b>")
    if validity.is_expired:
        return _("This session has expired")
    delta = validity.remaining
    days = delta.days
    hours = delta.seconds // 3600
    if days == 0:
        if hours == 0:
            minutes = delta.seconds // 60
            if minutes == 0:
                seconds = delta.seconds
                return ngettext(
                    "Valid for: <b>{0} second</b>",
                    "Valid for: <b>{0} seconds</b>",
                    seconds,
                ).format(seconds)
            else:
                return ngettext(
                    "Valid for: <b>{0} minute</b>",
                    "Valid for: <b>{0} minutes</b>",
                    minutes,
                ).format(minutes)
        else:
            return ngettext(
                "Valid for: <b>{0} hour</b>", "Valid for: <b>{0} hours</b>", hours
            ).format(hours)
    else:
        dstr = ngettext(
            "Valid for: <b>{0} day</b>", "Valid for: <b>{0} days</b>", days
        ).format(days)
        hstr = ngettext(" and <b>{0} hour</b>", " and <b>{0} hours</b>", hours).format(
            hours
        )
        return dstr + hstr


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


def show_error_dialog(parent, name: str, title: str, message: str):
    dialog = Gtk.MessageDialog(  # type: ignore
        parent=parent,
        type=Gtk.MessageType.INFO,  # type: ignore
        buttons=Gtk.ButtonsType.OK,  # type: ignore
        title=name,
        message_format=title,
    )
    dialog.format_secondary_text(message)  # type: ignore
    dialog.show()  # type: ignore
    dialog.run()  # type: ignore
    dialog.destroy()  # type: ignore
