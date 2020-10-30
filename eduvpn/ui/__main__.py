from typing import List
import logging
import traceback
import signal
from argparse import ArgumentParser
from os import geteuid
from sys import exit, argv
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from eduvpn import __version__
from eduvpn.nm import init_dbus_system_bus

logger = logging.getLogger(__name__)
log_format = format_ = '%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s'


def parse_args(args: List[str]) -> int:
    """
    Parses command line arguments:
    returns:
        logging_level
    """
    parser = ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true', help="enable debug logging")
    parser.add_argument('-v', '--version', action='store_true', help="print version and exit")
    args = parser.parse_args(args=args)

    if args.version:
        print("eduVPN Linux client version {}".format(__version__))
        exit(0)

    if args.debug:
        level = logging.DEBUG
    else:
        level = logging.INFO

    return level


def signal_handler(*_, **__):
    exit(0)


def main_loop(args=None, lets_connect=False):
    if args is None:
        args = argv[1:]
    loglevel = parse_args(args)
    logging.basicConfig(level=loglevel, format=log_format)

    signal.signal(signal.SIGINT, signal_handler)

    if geteuid() == 0:
        logger.error(f"Running client as root is not supported (yet)")
        exit(1)

    try:
        # import this later so the logging is properly configured
        from eduvpn.ui.ui import EduVpnGui

        edu_vpn_gui = EduVpnGui(lets_connect)
        init_dbus_system_bus(edu_vpn_gui.nm_status_cb)
        edu_vpn_gui.run()
    except Exception as e:
        fatal_reason = f"Caught exception: {e}"
        logger.error(fatal_reason)
        logging.error(traceback.format_exc())
        dialog = Gtk.MessageDialog(flags=Gtk.DialogFlags.MODAL,
                                   type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.OK,
                                   message_format=fatal_reason)
        dialog.connect("response", Gtk.main_quit)
        dialog.show()

    Gtk.main()


# def main(args: List[str]):
def main(args=None):
    main_loop(args)


def letsconnect(args=None):
    main_loop(args, lets_connect=True)


if __name__ == '__main__':
    main()
