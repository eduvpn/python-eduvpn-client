# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from eduvpn.util import get_prefix
from eduvpn.crypto import make_verifier
from eduvpn.manager import monitor_all_vpn
from eduvpn.steps.start import refresh_start
from eduvpn.actions.select import select_profile
from eduvpn.actions.add import new_provider
from eduvpn.actions.delete import delete_profile
from eduvpn.actions.vpn_status import vpn_change
from eduvpn.actions.switch import switched
from typing import Any, Iterable


logger = logging.getLogger(__name__)

builder_files = (
    'window.ui',
    '2fa.ui',
    'yubi_enroll.ui',
    'totp_enroll.ui',
    'connection_type.ui',
    'custom_url.ui',
    'fetch.ui',
    'instances.ui',
    'profiles.ui',
    'redirecturl.ui',
    'token.ui',
)  # type: Iterable[str]


class EduVpnApp:
    def __init__(self, secure_internet_uri, institute_access_uri, verify_key, lets_connect):  # type: (str, str, str, bool) -> None
        """setup UI thingies, don't do any fetching or DBus communication yet"""

        self.secure_internet_uri = secure_internet_uri  # type: str
        self.institute_access_uri = institute_access_uri  # type: str

        self.lets_connect = lets_connect  # type: bool

        # minimal global state to pass around data between steps where otherwise difficult
        self.selected_meta = None  # type: Any
        self.prefix = get_prefix()  # type: Any
        self.builder = Gtk.Builder()  # type: Any
        for b in builder_files:
            p = os.path.join(self.prefix, 'share/eduvpn/builder', b)
            if not os.access(p, os.R_OK):
                logger.error("Can't find {}! That is quite an important file.".format(p))
                raise Exception
            self.builder.add_from_file(p)

        # the signals coming from the GTK ui
        handlers = {
            "delete_window": Gtk.main_quit,
            "add_config": self.add,
            "del_config": self.delete,
            "select_config": self.select,
            "connect_set": self.switched,
        }

        self.builder.connect_signals(handlers)
        self.window = self.builder.get_object('eduvpn-window')  # type: Any
        self.verifier = make_verifier(verify_key)  # type: Any
        self.window.set_position(Gtk.WindowPosition.CENTER)

    def run(self):
        #type: () -> None
        # attach a callback to VPN connection monitor
        monitor_all_vpn(self.vpn_change)
        self.window.show_all()
        refresh_start(self.builder, self.lets_connect)

    def add(self, _):
        #type: (Any) -> None
        new_provider(builder=self.builder, verifier=self.verifier,
                     secure_internet_uri=self.secure_internet_uri,
                     institute_access_uri=self.institute_access_uri,
                     lets_connect=self.lets_connect)

    def delete(self, _):
        #type: (Any) -> None
        delete_profile(builder=self.builder, lets_connect=self.lets_connect)

    def select(self, *args):
        #type: (Any) -> None
        self.selected_meta = select_profile(builder=self.builder, verifier=self.verifier,
                                            lets_connect=self.lets_connect)

    def vpn_change(self, state, reason):  # type: (str, str) -> None
        """called when the status of a VPN connection changes"""
        logger.debug("VPN status change, state: {}, reason: {}".format(state, reason))
        vpn_change(self.builder, self.lets_connect, state, reason)

    def switched(self, selection, _):  # type: (dict, Any) -> None
        """called when the user releases the connection switch"""
        switched(meta=self.selected_meta, builder=self.builder, verifier=self.verifier, lets_connect=self.lets_connect)
