# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import gi
from gi.repository import GLib, Gtk
from eduvpn.util import error_helper, thread_helper
from eduvpn.manager import store_provider, monitor_vpn
from eduvpn.notify import notify, init_notify
from eduvpn.steps.start import refresh_start
from eduvpn.actions.vpn_status import vpn_change
from eduvpn.steps.fetching import fetching_window
from eduvpn.metadata import Metadata
from typing import Any

logger = logging.getLogger(__name__)


def finalizing_step(builder, meta, config_dict, lets_connect):
    #type: (Gtk.builder, Metadata, dict, bool) -> None
    """finalise the add profile flow, add a configuration"""
    logger.info("finalizing step")
    fetching_window(builder=builder, lets_connect=lets_connect)
    dialog = builder.get_object('fetch-dialog')
    thread_helper(lambda: _background(meta=meta, dialog=dialog, builder=builder, config_dict=config_dict,
                                      lets_connect=lets_connect))
    dialog.run()


def _background(meta, dialog, builder, config_dict, lets_connect):
    #type: (Metadata, Any, Gtk.builder, dict, bool) -> None
    try:
        uuid = store_provider(meta, config_dict)
        monitor_vpn(uuid=uuid, callback=lambda *args, **kwargs: vpn_change(builder=builder, lets_connect=lets_connect))
        notification = init_notify(lets_connect)
        GLib.idle_add(lambda: notify(notification, "eduVPN provider added",
                                     "added provider '{}'".format(meta.display_name)))
    except Exception as e:
        error = e
        GLib.idle_add(lambda: error_helper(dialog, "can't store configuration", "{}: {}".format(type(error).__name__,
                                                                                                str(error))))
        GLib.idle_add(lambda: dialog.hide())
        raise
    else:
        GLib.idle_add(lambda: dialog.hide())
        GLib.idle_add(lambda: refresh_start(builder, lets_connect=lets_connect))
