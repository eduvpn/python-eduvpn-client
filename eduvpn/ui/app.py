import logging
from gettext import gettext as _

import gi

gi.require_version("Gtk", "3.0")  # noqa: E402
from eduvpn_common.main import EduVPN
from gi.repository import Gio, GLib, Gtk

from .. import i18n, notify
from ..app import Application
from ..utils import run_in_main_gtk_thread
from ..variants import ApplicationVariant
from .ui import EduVpnGtkWindow

logger = logging.getLogger(__name__)


LOG_FORMAT = format_ = (
    "%(asctime)s - %(threadName)s - %(levelname)s - %(name)s"
    " - %(filename)s:%(lineno)d - %(message)s"
)


class EduVpnGtkApplication(Gtk.Application):
    # TODO: Go type hint
    def __init__(
        self, *args, app_variant: ApplicationVariant, common: EduVPN, **kwargs
    ):
        super().__init__(  # type: ignore
            *args,
            application_id=app_variant.app_id,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,  # type: ignore
            **kwargs,
        )

        self.app = Application(app_variant, run_in_main_gtk_thread, common)
        self.common = common
        # Only allow a single window and track it on the app.
        self.window = None

        self.add_main_option(  # type: ignore
            "version",
            ord("v"),
            GLib.OptionFlags.NONE,  # type: ignore
            GLib.OptionArg.NONE,  # type: ignore
            "print version and exit",
            None,
        )
        self.add_main_option(  # type: ignore
            "debug",
            ord("d"),
            GLib.OptionFlags.NONE,  # type: ignore
            GLib.OptionArg.NONE,  # type: ignore
            "enable debug logging",
            None,
        )

    def do_startup(self):
        logger.debug("startup")
        Gtk.Application.do_startup(self)
        i18n.initialize(self.app.variant)
        notify.initialize(self.app.variant)
        self.connection_notification = notify.Notification(self.app.variant)

    def do_shutdown(self):
        logger.debug("shutdown")
        self.connection_notification.hide()
        Gtk.Application.do_shutdown(self)

    def do_activate(self):
        logger.debug("activate")
        if not self.window:
            self.window = EduVpnGtkWindow(application=self)
            self.window.initialize()
            self.window.present()
            self.app.initialize()
        else:
            self.window.on_reopen_window()

    def do_command_line(self, command_line):
        logger.debug(f"command line: {command_line}")
        options = command_line.get_options_dict()
        # unpack the commandline args into a dict
        options = options.end().unpack()

        if "version" in options:
            from eduvpn import __version__

            print(f"eduVPN Linux client version {__version__}")
            return 0

        if "debug" in options:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

        self.activate()
        return 0

    def on_quit(self, action=None, _param=None):
        logger.debug("quit")
        # Deregister the common library to save settings
        self.common.deregister()
        self.quit()

    def on_window_closed(self):
        logger.debug("window closed")
        # TODO: Go, only quit while no active connection
        self.on_quit()

    # TODO: Implement with Go callback
    def enter_ConnectingState(self, old_state, new_state):
        self.connection_notification.show(
            title=_("Connecting"),
            message=_(
                "The connection is being established. "
                "This should only take a moment."
            ),
        )

    # TODO: Implement with Go callback
    def enter_ConnectedState(self, old_state, new_state):
        self.connection_notification.show(
            title=_("Connected"), message=_("You are now connected to your server.")
        )

    # TODO: Implement with Go callback
    def enter_SessionPendingExpiryState(self, old_state, new_state):
        self.connection_notification.show(
            title=_("Connected"),
            message=_(
                "Your session is about to expire. "
                "Renew the session to remain connected."
            ),
        )

    # TODO: Implement with Go callback
    def enter_ReconnectingState(self, old_state, new_state):
        self.connection_notification.show(
            title=_("Connecting"),
            message=_(
                "The connection is being established. "
                "This should only take a moment."
            ),
        )

    # TODO: Implement with Go callback
    def enter_DisconnectedState(self, old_state, new_state):
        self.connection_notification.hide()

    # TODO: Implement with Go callback
    def enter_SessionExpiredState(self, old_state, new_state):
        self.connection_notification.show(
            title=_("Session expired"), message=_("Your session has expired.")
        )

    # TODO: Implement with Go callback
    def enter_ConnectionErrorState(self, old_state, new_state):
        message = _("An error occured")
        if new_state.error:
            message = f"{message}: {new_state.error}"
        self.connection_notification.show(title=_("Connection Error"), message=message)

    # TODO: Implement with Go callback
    def enter_NoActiveConnection(self, old_state, new_state):
        if not self.window.is_visible():
            # Quit the app if no window is open when the connection is deactivated.
            logger.debug("connection deactivated while window closed")
            self.on_quit()
