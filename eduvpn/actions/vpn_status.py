# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib
from eduvpn.notify import notify
from eduvpn.manager import active_connections
from eduvpn.util import metadata_of_selected

logger = logging.getLogger(__name__)


def vpn_change(builder):
    logger.info("VPN status change")
    switch = builder.get_object('connect-switch')
    ipv4_label = builder.get_object('ipv4-label')
    ipv6_label = builder.get_object('ipv6-label')

    # get the currently selected uuid
    meta = metadata_of_selected(builder=builder)

    selected_uuid_active = False
    for active in active_connections():
        try:
            if active.Uuid == meta.uuid:
                selected_uuid_active = True
                if active.State == 2:  # activated
                    logger.info("setting ip for {}".format(meta.uuid))
                    logger.info("setting switch ON")
                    switch.set_active(True)
                    GLib.idle_add(lambda: ipv4_label.set_text(active.Ip4Config.AddressData[0]['address']))
                    GLib.idle_add(lambda: ipv6_label.set_text(active.Ip6Config.AddressData[0]['address']))
                    notify("eduVPN connected", "Connected to '{}'".format(meta.display_name))
                elif active.State == 1:  # activating
                    logger.info("setting switch ON")
                    switch.set_active(True)
                    notify("eduVPN connecting...", "Activating '{}'".format(meta.display_name))
                else:
                    logger.info("clearing ip for '{}'".format(meta.uuid))
                    logger.info("setting switch OFF")
                    switch.set_active(False)
                    GLib.idle_add(lambda: ipv4_label.set_text(""))
                    GLib.idle_add(lambda: ipv6_label.set_text(""))
                break
        except Exception as e:
            logger.warning("probably race condition in network manager: {}".format(e))
            pass

    if not selected_uuid_active:
        logger.info("Our selected profile not active {}".format(meta.uuid))
        notify("eduVPN Disconnected", "Disconnected from '{}'".format(meta.display_name))
        logger.info("setting switch OFF")
        switch.set_active(False)
        GLib.idle_add(lambda: ipv4_label.set_text(""))
        GLib.idle_add(lambda: ipv6_label.set_text(""))
