# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib
from eduvpn.notify import notify
from eduvpn.actions.activate import activate_connection
from eduvpn.manager import disconnect_provider
from eduvpn.util import error_helper

logger = logging.getLogger(__name__)


def switched(meta, builder):
    switch = builder.get_object('connect-switch')
    state = switch.get_active()
    logger.info("switch activated, old state {}".format(state))
    if not state:
        logger.info("setting switch ON")
        GLib.idle_add(lambda: switch.set_active(True))
        activate_connection(meta=meta, builder=builder)
    else:
        notify("eduVPN disconnecting...", "Disconnecting from {}".format(meta.display_name))
        logger.info("setting switch OFF")
        GLib.idle_add(lambda: switch.set_active(False))
        try:
            disconnect_provider(meta.uuid)
        except Exception as e:
            window = builder.get_object('eduvpn-window')
            error_helper(window, "can't disconnect", "{}: {}".format(type(e).__name__, str(e)))
            GLib.idle_add(lambda: switch.set_active(True))
            raise
