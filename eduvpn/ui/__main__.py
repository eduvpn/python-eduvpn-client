import logging
import traceback
import signal
import sys
from os import geteuid
from sys import exit

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

logger = logging.getLogger(__name__)
log_format = format_ = '%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s'


def signal_handler(sig, frame):
    sys.exit(0)


def main_loop(lets_connect=False):
    logging.basicConfig(level=logging.DEBUG, format=log_format)

    signal.signal(signal.SIGINT, signal_handler)

    if geteuid() == 0:
        logger.error(f"Running client as root is not supported (yet)")
        exit(1)

    try:
        # import this later so the logging is properly configured
        from eduvpn.ui.ui import EduVpnGui

        edu_vpn_gui = EduVpnGui(lets_connect)
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


def eduvpn():
    main_loop()


def letsconnect():
    main_loop(lets_connect=True)


if __name__ == '__main__':
    eduvpn()
