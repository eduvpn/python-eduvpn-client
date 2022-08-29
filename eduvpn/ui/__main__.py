import logging
import os
import sys

import gi

gi.require_version("Gtk", "3.0")  # noqa: E402
from typing import Tuple

import eduvpn_common.main as common
from gi.repository import Gtk

from eduvpn.settings import (CLIENT_ID, CONFIG_PREFIX, LETSCONNECT_CLIENT_ID,
                        LETSCONNECT_CONFIG_PREFIX)
from eduvpn.ui.app import EduVpnGtkApplication
from eduvpn.variants import EDUVPN, LETS_CONNECT

logger = logging.getLogger(__name__)


def get_variant_settings(variant) -> Tuple[str, str]:
    if variant == EDUVPN:
        return CLIENT_ID, str(CONFIG_PREFIX)
    return LETSCONNECT_CLIENT_ID, str(LETSCONNECT_CONFIG_PREFIX)


def main_loop(args=None, app_variant=EDUVPN):
    if os.geteuid() == 0:
        print("Running client as root is not supported")
        sys.exit(1)

    if args is None:
        args = sys.argv

    try:
        _common = common.EduVPN(*get_variant_settings(app_variant))
        app = EduVpnGtkApplication(app_variant=app_variant, common=_common)
        app.run(args)
    except Exception as e:
        message = "A fatal error occurred"
        logger.exception(message)
        dialog = Gtk.MessageDialog(
            text=f"{message}: {e!r}",
            message_type=Gtk.MessageType.ERROR,
            modal=True,
            buttons=Gtk.ButtonsType.OK,
        )
        dialog.connect("response", Gtk.main_quit)
        dialog.show()
        Gtk.main()
    except KeyboardInterrupt:
        pass


def eduvpn(args=None):
    main_loop(args, app_variant=EDUVPN)


def letsconnect(args=None):
    main_loop(args, app_variant=LETS_CONNECT)


if __name__ == "__main__":
    eduvpn()
