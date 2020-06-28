import logging
import sys
import signal

import gi
gi.require_version('Gtk', '3.0')
from os import geteuid
from sys import exit, argv
from gi.repository import GObject, Gtk
from pathlib import Path
from typing import Optional, List
from requests_oauthlib import OAuth2Session
from eduvpn.menu import menu, profile_choice, write_to_nm_choice, secure_internet_choice
from eduvpn.nm import save_connection
from eduvpn.oauth2 import get_oauth
from eduvpn.remote import get_info, list_profiles, get_config, create_keypair, list_orgs, list_servers
from eduvpn.settings import CLIENT_ID, ORGANISATION_URI, SERVER_URI
from eduvpn.storage import write_config
from eduvpn.crypto import make_verifier
from argparse import ArgumentParser
logger = logging.getLogger(__name__)
log_format = format_ = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'


# def parse_args(args: List[str]) -> Optional[str]:
#     parser = ArgumentParser(description='The eduVPN gui client')
#     args = parser.parse_args(args)
#     return args.search

def signal_handler(sig, frame):
    sys.exit(0)


# def main(args: List[str]):
def main(args=None):
    if args is None:
        args = sys.argv
    logging.basicConfig(level=logging.INFO)

    signal.signal(signal.SIGINT, signal_handler)

    # parse_args(args)

    if geteuid() == 0:
        logger.error(u"Running eduVPN client as root is not supported (yet)")
        exit(1)

    GObject.threads_init()

    # import this later so the logging is properly configured
    from eduvpngui.ui import EduVpnGui

    edu_vpn_gui = EduVpnGui(lets_connect=False)
    edu_vpn_gui.run()

    Gtk.main()


def letsconnect():
    raise NotImplementedError("todo :)")


if __name__ == '__main__':
    main(args=argv)
