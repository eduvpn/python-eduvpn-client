import logging
import os
import sys

import gi

gi.require_version("Gtk", "3.0")  # noqa: E402

import eduvpn_common.main as common
from gi.repository import Gtk

from eduvpn.i18n import country
from eduvpn.ui.app import EduVpnGtkApplication
from eduvpn.variants import EDUVPN, LETS_CONNECT

logger = logging.getLogger(__name__)


def main_loop(args=None, app_variant=EDUVPN):
    if os.geteuid() == 0:
        print("Running client as root is not supported")
        sys.exit(1)

    if args is None:
        args = sys.argv

    try:
        variant_settings = app_variant.settings
        _common = common.EduVPN(*variant_settings, language=country())
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
