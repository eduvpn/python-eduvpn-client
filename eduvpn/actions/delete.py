# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from eduvpn.manager import delete_provider
from eduvpn.notify import notify
from eduvpn.util import error_helper, metadata_of_selected
from eduvpn.steps.provider import update_providers


logger = logging.getLogger(__name__)


def delete_profile(builder):
    """called when the user presses the - button"""
    logger.info("delete provider clicked")
    meta = metadata_of_selected(builder)

    if not meta:
        logger.info("nothing selected")
        return

    window = builder.get_object('eduvpn-window')

    dialog = Gtk.MessageDialog(window, Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO,
                               "Are you sure you want to remove '{}'?".format(meta.display_name))
    dialog.format_secondary_text("This action can't be undone.")
    response = dialog.run()
    if response == Gtk.ResponseType.YES:
        logger.info("deleting provider config")
        try:
            delete_provider(meta.uuid)
            notify("eduVPN provider deleted", "Deleted '{}'".format(meta.display_name))
        except Exception as e:
            error_helper(window, "can't delete profile", str(e))
            dialog.destroy()
            raise
        GLib.idle_add(lambda: update_providers(builder))
    elif response == Gtk.ResponseType.NO:
        logger.info("not deleting provider config")
    dialog.destroy()
