# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import os

import dbus.mainloop.glib
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import GObject, Gtk

logging.basicConfig(level=logging.INFO)

from eduvpn.util import get_prefix
from eduvpn.config import verify_key
from eduvpn.crypto import make_verifier
from eduvpn.manager import monitor_all_vpn
from eduvpn.steps.provider import update_providers
from eduvpn.actions.select import select_profile
from eduvpn.actions.add import new_provider
from eduvpn.actions.delete import delete_profile
from eduvpn.actions.vpn_status import vpn_change
from eduvpn.actions.switch import switched

logger = logging.getLogger(__name__)


class EduVpnApp:
    def __init__(self):
        """setup UI thingies, don't do any fetching or DBus communication yet"""

        # minimal global state to pass around data between steps where otherwise difficult
        self.selected_meta = None

        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(get_prefix(), 'share/eduvpn/eduvpn.ui'))

        # the signals coming from the GTK ui
        handlers = {
            "delete_window": Gtk.main_quit,
            "add_config": self.add,
            "del_config": self.delete,
            "select_config": self.select,
            "connect_set": self.switched,
        }

        self.builder.connect_signals(handlers)
        self.window = self.builder.get_object('eduvpn-window')
        self.verifier = make_verifier(verify_key)
        self.window.set_position(Gtk.WindowPosition.CENTER)

    def run(self):
        # attach a callback to VPN connection monitor
        monitor_all_vpn(self.vpn_change)
        self.window.show_all()
        update_providers(self.builder)

    def add(self, _):
        new_provider(builder=self.builder, verifier=self.verifier)

    def delete(self, _):
        delete_profile(builder=self.builder)

    def select(self, _):
        self.selected_meta = select_profile(builder=self.builder, verifier=self.verifier)

    def vpn_change(self, *args, **kwargs):
        """called when the status of a VPN connection changes"""
        vpn_change(self.builder)

    def switched(self, selection, _):
        """called when the user releases the connection switch"""
        switched(meta=self.selected_meta, builder=self.builder)


def main():
    GObject.threads_init()
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    edu_vpn_app = EduVpnApp()
    edu_vpn_app.run()
    Gtk.main()

