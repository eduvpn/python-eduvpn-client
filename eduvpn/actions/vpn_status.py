# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk
from eduvpn.notify import notify, init_notify
from eduvpn.manager import list_active
from eduvpn.util import metadata_of_selected
from typing import Optional


logger = logging.getLogger(__name__)


def vpn_change(builder, lets_connect, state=0, reason=0):
    # type: (Gtk.builder, bool, Optional[int], Optional[int]) -> None
    logger.info("VPN status change")
    switch = builder.get_object('connect-switch')
    ipv4_label = builder.get_object('ipv4-label')
    ipv6_label = builder.get_object('ipv6-label')

    # get the currently selected uuid
    meta = metadata_of_selected(builder=builder)

    if not meta:
        logger.info("VPN status changed but no profile selected")
        return

    notification = init_notify(lets_connect)

    selected_uuid_active = False
    for active in list_active():
        try:
            if active.Uuid == meta.uuid:
                selected_uuid_active = True
                if active.State == 2:  # activated
                    logger.info(u"setting ip for {}".format(meta.uuid))
                    logger.info(u"setting switch ON")
                    switch.set_active(True)
                    GLib.idle_add(lambda: ipv4_label.set_text(active.Ip4Config.AddressData[0]['address']))
                    GLib.idle_add(lambda: ipv6_label.set_text(active.Ip6Config.AddressData[0]['address']))
                    notify(notification, u"eduVPN connected", u"Connected to '{}'".format(meta.display_name))
                elif active.State == 1:  # activating
                    logger.info(u"setting switch ON")
                    switch.set_active(True)
                    notify(notification, u"eduVPN connecting...", u"Activating '{}'".format(meta.display_name))
                else:
                    logger.info(u"clearing ip for '{}'".format(meta.uuid))
                    logger.info(u"setting switch OFF")
                    switch.set_active(False)
                    GLib.idle_add(lambda: ipv4_label.set_text(""))
                    GLib.idle_add(lambda: ipv6_label.set_text(""))
                break
        except Exception as e:
            logger.warning(u"probably race condition in network manager: {}".format(e))
            raise

    if not selected_uuid_active:
        logger.info(u"Our selected profile not active {}".format(meta.uuid))
        notify(notification, u"eduVPN Disconnected", u"Disconnected from '{}'".format(meta.display_name))
        logger.info(u"setting switch OFF")
        switch.set_active(False)
        GLib.idle_add(lambda: ipv4_label.set_text("-"))
        GLib.idle_add(lambda: ipv6_label.set_text("-"))
