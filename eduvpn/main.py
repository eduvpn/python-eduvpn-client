# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import gi
from os import geteuid
from sys import exit
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, Gtk
from eduvpn.util import have_dbus
from argparse import ArgumentParser
from eduvpn import __version__
from eduvpn import config
from typing import Tuple
from eduvpn.ui import EduVpnApp


logger = logging.getLogger(__name__)
log_format = format_ = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'


def parse_args():  # type: () -> Tuple[int, str, str, str, bool]
    """Parses command line arguments."""
    parser = ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true', help="enable debug logging")
    parser.add_argument('-v', '--version', action='store_true', help="print version and exit")
    parser.add_argument('-t', '--test', action='store_true', help="use test discovery servers")
    parser.add_argument('-l', '--lets_connect', action='store_true', help="Enable 'Let's Connect!' mode")
    args = parser.parse_args()

    if args.version:
        print("eduVPN Linux client version {}".format(__version__))
        exit(0)

    if args.debug:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(level=level, format=format_)

    if args.test:
        logger.warning("using test discovery URLs")
        return (level, config.secure_internet_uri_dev, config.institute_access_uri_dev, config.verify_key_dev,
                args.lets_connect)
    else:
        logger.debug("using production discovery URLs")
        return level, config.secure_internet_uri, config.institute_access_uri, config.verify_key, args.lets_connect


def init(lets_connect):
    # type: (bool) -> EduVpnApp
    level, secure_internet_uri, institute_access_uri, verify_key, lets_connect_arg = parse_args()
    lets_connect = lets_connect or lets_connect_arg
    if geteuid() == 0:
        logger.error("Running eduVPN client as root is not supported (yet)")
        exit(1)
    GObject.threads_init()

    if have_dbus():
        import dbus.mainloop.glib
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    # import this later so the logging is properly configured
    from eduvpn.ui import EduVpnApp

    edu_vpn_app = EduVpnApp(secure_internet_uri=secure_internet_uri,
                            institute_access_uri=institute_access_uri,
                            verify_key=verify_key, lets_connect=lets_connect)
    edu_vpn_app.run()
    return edu_vpn_app


def main_eduvpn():  # type: () -> int
    """Start the app in EduVPN mode."""
    init(lets_connect=False)
    Gtk.main()
    return 0


def main_lets_connect():   # type: () -> int
    """Start the app in Let's connect mode."""
    init(lets_connect=True)
    Gtk.main()
    return 0
