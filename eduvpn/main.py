# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, Gtk, GLib
from eduvpn.util import have_dbus


def main():
    format_ = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=format_)
    GObject.threads_init()

    if have_dbus():
        import dbus.mainloop.glib
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    # import this later so the logging is properly configured
    from eduvpn.ui import EduVpnApp

    edu_vpn_app = EduVpnApp()
    edu_vpn_app.run()
    Gtk.main()
