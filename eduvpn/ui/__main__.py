import logging
import signal
import sys
from os import geteuid
from sys import exit, argv

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

logger = logging.getLogger(__name__)
log_format = format_ = '%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s'


# def parse_args(args: List[str]) -> Optional[str]:
#     parser = ArgumentParser(description='The eduVPN gui client')
#     args = parser.parse_args(args)
#     return args.search

def signal_handler(sig, frame):
    sys.exit(0)


def main_loop(args=None, lets_connect=False):
    if args is None:
        args = sys.argv
    logging.basicConfig(level=logging.DEBUG, format=log_format)

    signal.signal(signal.SIGINT, signal_handler)

    # parse_args(args)

    if geteuid() == 0:
        logger.error(f"Running client as root is not supported (yet)")
        exit(1)

    # import this later so the logging is properly configured
    from eduvpn.ui.ui import EduVpnGui

    edu_vpn_gui = EduVpnGui(lets_connect)
    edu_vpn_gui.run()

    Gtk.main()


# def main(args: List[str]):
def main(args=None):
    main_loop(args)


def letsconnect(args=None):
    main_loop(args, lets_connect=True)


if __name__ == '__main__':
    main(args=argv)
