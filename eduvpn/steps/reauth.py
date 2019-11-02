# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from eduvpn.steps.browser import browser_step
from eduvpn.metadata import Metadata
from typing import Dict


logger = logging.getLogger(__name__)


def reauth(meta, verifier, builder, lets_connect):  # type: (Metadata, str, Gtk.builder, bool) -> None
    """called when the authorization is expired"""
    logger.info(u"looks like authorization is expired or removed")
    window = builder.get_object('eduvpn-window')
    dialog = Gtk.MessageDialog(window, Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION,
                               Gtk.ButtonsType.YES_NO,
                               "Authorization for {} is expired or removed.".format(meta.display_name))
    dialog.format_secondary_text("Do you want to re-authorize?")
    response = dialog.run()
    if response == Gtk.ResponseType.YES:
        meta.token = {None: None}
        browser_step(builder, meta, verifier, force_token_refresh=True, lets_connect=lets_connect)
    elif response == Gtk.ResponseType.NO:
        pass
    dialog.hide()
