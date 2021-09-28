import logging
from gettext import gettext as _

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gio, Gtk

from .. import i18n
from .. import notify
from ..utils import run_in_main_gtk_thread
from ..variants import ApplicationVariant
from ..app import Application
from .ui import EduVpnGtkWindow


logger = logging.getLogger(__name__)


LOG_FORMAT = format_ = (
    '%(asctime)s - %(threadName)s - %(levelname)s - %(name)s'
    ' - %(filename)s:%(lineno)d - %(message)s'
)


class EduVpnGtkApplication(Gtk.Application):
    def __init__(self, *args, app_variant, **kwargs):
        super().__init__(
            *args,
            application_id=app_variant.app_id,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
            **kwargs
        )

        self.app = Application(app_variant, run_in_main_gtk_thread)
        # Only allow a single window and track it on the app.
        self.window = None

        self.add_main_option(
            'version',
            ord('v'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "print version and exit",
            None,
        )
        self.add_main_option(
            'debug',
            ord('d'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "enable debug logging",
            None,
        )

    def do_startup(self):
        logger.debug('startup')
        Gtk.Application.do_startup(self)
        i18n.initialize(self.app.variant)
        notify.initialize(self.app.variant)
        self.app.initialize()

    def do_shutdown(self):
        logger.debug('shutdown')
        Gtk.Application.do_shutdown(self)

    def do_activate(self):
        logger.debug('activate')
        if not self.window:
            self.window = EduVpnGtkWindow(application=self)
        self.window.present()

    def do_command_line(self, command_line):
        logger.debug(f'command line: {command_line}')
        options = command_line.get_options_dict()
        # unpack the commandline args into a dict
        options = options.end().unpack()

        if 'version' in options:
            from eduvpn import __version__
            print(f"eduVPN Linux client version {__version__}")
            return 0

        if 'debug' in options:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

        self.activate()
        return 0

    def on_quit(self, action, param):
        logger.debug('quit')
        self.quit()
