import logging

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from eduvpn.manager import delete_provider
from eduvpn.notify import notify
from eduvpn.util import error_helper
from eduvpn.steps.provider import update_providers


logger = logging.getLogger(__name__)


def delete_profile(selection, builder, window):
    """called when the user presses the - button"""
    logger.info("delete provider clicked")
    model, treeiter = selection.get_selected()
    if not treeiter:
        logger.info("nothing selected")
        return

    uuid, display_name, _, _ = model[treeiter]

    dialog = Gtk.MessageDialog(window, Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION,
                               Gtk.ButtonsType.YES_NO, "Are you sure you want to remove '{}'?".format(display_name))
    dialog.format_secondary_text("This action can't be undone.")
    response = dialog.run()
    if response == Gtk.ResponseType.YES:
        logger.info("deleting provider config")
        try:
            delete_provider(uuid)
            notify("eduVPN provider deleted", "Deleted '{}'".format(display_name))
        except Exception as e:
            error_helper(window, "can't delete profile", str(e))
            dialog.destroy()
            raise
        GLib.idle_add(lambda: update_providers(builder))
    elif response == Gtk.ResponseType.NO:
        logger.info("not deleting provider config")
    dialog.destroy()