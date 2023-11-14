import logging
import os
import sys

import gi

gi.require_version("Gtk", "3.0")  # noqa: E402

import eduvpn_common.main as common  # noqa: E402
from gi.repository import Gtk  # noqa: E402

from eduvpn_base.i18n import country  # noqa: E402
from eduvpn_base.ui.app import EduVpnGtkApplication  # noqa: E402

logger = logging.getLogger(__name__)


def main_loop(variant):
    if os.geteuid() == 0:
        print("Running client as root is not supported")
        sys.exit(1)

    try:
        variant_settings = variant.settings
        _common = common.EduVPN(*variant_settings, language=country())
        app = EduVpnGtkApplication(app_variant=variant, common=_common)
        app.run(sys.argv)
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
