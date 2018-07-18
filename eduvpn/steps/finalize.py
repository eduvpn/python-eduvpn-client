# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import gi
from gi.repository import GLib
from eduvpn.util import error_helper, thread_helper
from eduvpn.manager import store_provider, monitor_vpn
from eduvpn.notify import notify
from eduvpn.steps.provider import update_providers
from eduvpn.actions.vpn_status import vpn_change


logger = logging.getLogger(__name__)


def finalizing_step(builder, meta, config_dict):
    """finalise the add profile flow, add a configuration"""
    logger.info("finalizing step")
    dialog = builder.get_object('fetch-dialog')
    window = builder.get_object('eduvpn-window')
    dialog.set_transient_for(window)
    dialog.show_all()
    thread_helper(lambda: _background(meta=meta, dialog=dialog, builder=builder, config_dict=config_dict))
    dialog.run()


def _background(meta, dialog, builder, config_dict):
    try:
        uuid = store_provider(meta, config_dict)
        monitor_vpn(uuid=uuid, callback=lambda *args, **kwargs: vpn_change(builder=builder))
        GLib.idle_add(lambda: notify("eduVPN provider added", "added provider '{}'".format(meta.display_name)))
    except Exception as e:
        error = e
        GLib.idle_add(lambda: error_helper(dialog, "can't store configuration", "{}: {}".format(type(error).__name__,
                                                                                                str(error))))
        GLib.idle_add(lambda: dialog.hide())
        raise
    else:
        GLib.idle_add(lambda: dialog.hide())
        GLib.idle_add(lambda: update_providers(builder))
