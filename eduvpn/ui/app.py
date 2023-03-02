import logging
from gettext import gettext as _

import gi

gi.require_version("Gtk", "3.0")  # noqa: E402
from eduvpn_common.main import EduVPN
from eduvpn_common.state import State, StateType
from gi.repository import Gio, GLib, Gtk
from gi.repository.Gio import ApplicationCommandLine

from eduvpn import i18n, notify
from eduvpn.app import Application
from eduvpn.settings import CONFIG_DIR_MODE
from eduvpn.ui.ui import EduVpnGtkWindow
from eduvpn.utils import init_logger, run_in_background_thread, ui_transition
from eduvpn.variants import ApplicationVariant

logger = logging.getLogger(__name__)


class EduVpnGtkApplication(Gtk.Application):
    def __init__(
        self, *args, app_variant: ApplicationVariant, common: EduVPN, **kwargs
    ) -> None:
        super().__init__(  # type: ignore
            *args,
            application_id=app_variant.app_id,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,  # type: ignore
            **kwargs,
        )

        self.app = Application(app_variant, common)
        self.common = common
        self.common.register_class_callbacks(self)
        self.debug = False
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

    def do_startup(self) -> None:
        logger.debug("startup")
        Gtk.Application.do_startup(self)  # type: ignore
        i18n.initialize(self.app.variant)
        notify.initialize(self.app.variant)
        self.connection_notification = notify.Notification(self.app.variant)

    def do_shutdown(self) -> None:  # type: ignore
        logger.debug("shutdown")
        self.connection_notification.hide()
        Gtk.Application.do_shutdown(self)  # type: ignore

    def do_activate(self) -> None:
        logger.debug("activate")
        if not self.window:
            self.window = EduVpnGtkWindow(application=self)  # type: ignore
            self.window.present()  # type: ignore
            self.window.initialize()  # type: ignore
        else:
            self.window.on_reopen_window()

    def do_command_line(self, command_line: ApplicationCommandLine) -> int:  # type: ignore
        logger.debug(f"command line: {command_line}")
        options = command_line.get_options_dict()

        # unpack the commandline args into a dict
        options = options.end().unpack()

        if "version" in options:  # type: ignore
            from eduvpn import __version__

            print(f"{self.app.variant.name} client version {__version__}")
            return 0

        self.debug = "debug" in options  # type: ignore

        init_logger(self.debug, self.app.variant.logfile, CONFIG_DIR_MODE)

        self.activate()  # type: ignore
        return 0

    def on_quit(self, action: None = None, _param: None = None) -> None:
        logger.debug("quit")
        # Deregister the common library to save settings
        try:
            self.common.deregister()
        # Deregister is best effort
        except Exception as e:
            logger.debug("failed deregistering library", e)
        self.quit()  # type: ignore

    def on_window_closed(self) -> None:
        logger.debug("window closed")
        self.on_quit()

    def enter_CopiedAnError(self):
        self.connection_notification.show(
            title=_("Error Copied"),
            message=_(
                "The error message has been copied to your clipboard. "
                "Report it at https://github.com/eduvpn/python-eduvpn-client if you think it is an issue."
            ),
        )

    def enter_SessionPendingExpiryState(self):
        self.connection_notification.show(
            title=_("Connected"),
            message=_(
                "Your session is about to expire. "
                "Renew the session to remain connected."
            ),
        )

    def enter_SessionExpiredState(self):
        self.connection_notification.show(
            title=_("Session expired"),
            message=_(
                "Your session has expired. You have been disconnected from the VPN."
            ),
        )

        @run_in_background_thread("expired-deactivate")
        def expired_deactivate():
            self.app.model.deactivate_connection()

        expired_deactivate()

    @ui_transition(State.DISCONNECTED, StateType.ENTER)
    def enter_NoActiveConnection(self, old_state, new_state):
        if not self.window.is_visible():
            # Quit the app if no window is open when the connection is deactivated.
            logger.debug("connection deactivated while window closed")
            self.on_quit()
