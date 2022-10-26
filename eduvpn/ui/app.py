import logging
from gettext import gettext as _

import os
import gi

gi.require_version("Gtk", "3.0")  # noqa: E402
from eduvpn_common.main import EduVPN
from eduvpn_common.state import State, StateType
from gi.repository import Gio, GLib, Gtk

from eduvpn import i18n, notify
from eduvpn.app import Application
from eduvpn.settings import CONFIG_DIR_MODE
from eduvpn.utils import run_in_background_thread, ui_transition
from eduvpn.variants import ApplicationVariant
from eduvpn.ui.ui import EduVpnGtkWindow
from eduvpn.ui.utils import get_validity_text
from gi.repository.Gio import ApplicationCommandLine

logger = logging.getLogger(__name__)


LOG_FORMAT = format_ = (
    "%(asctime)s - %(threadName)s - %(levelname)s - %(name)s"
    " - %(filename)s:%(lineno)d - %(message)s"
)


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
        Gtk.Application.do_startup(self)
        i18n.initialize(self.app.variant)
        notify.initialize(self.app.variant)
        self.connection_notification = notify.Notification(self.app.variant)

    def do_shutdown(self) -> None:  # type: ignore
        logger.debug("shutdown")
        self.connection_notification.hide()
        Gtk.Application.do_shutdown(self)

    def do_activate(self) -> None:
        logger.debug("activate")
        if not self.window:
            self.window = EduVpnGtkWindow(application=self)
            self.window.present()
            self.window.initialize()
        else:
            self.window.on_reopen_window()

    def do_command_line(self, command_line: ApplicationCommandLine) -> int:  # type: ignore
        logger.debug(f"command line: {command_line}")
        options = command_line.get_options_dict()
        ## unpack the commandline args into a dict
        options = options.end().unpack()

        if "version" in options:
            from eduvpn import __version__

            print(f"eduVPN Linux client version {__version__}")
            return 0

        self.debug = "debug" in options

        if self.debug:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO
        os.makedirs(os.path.dirname(self.app.variant.logfile), mode=CONFIG_DIR_MODE, exist_ok=True)
        logging.basicConfig(level=log_level,
                            format=LOG_FORMAT,
                            handlers=[
                                logging.FileHandler(self.app.variant.logfile),
                                logging.StreamHandler()
                            ])

        self.activate()
        return 0

    def on_quit(self, action: None = None, _param: None = None) -> None:
        logger.debug("quit")
        # Deregister the common library to save settings
        try:
            self.common.deregister()
        # Deregister is best effort
        except Exception as e:
            logger.debug("failed deregistering library", e)
        self.quit()

    def on_window_closed(self) -> None:
        logger.debug("window closed")
        if not self.app.model.is_connected():
            self.on_quit()

    def enter_ClipboardError(self):
        self.connection_notification.show(
            title=_("Error Copied"),
            message=_(
                "The error message has been copied to your clipboard. "
                "Report it at https://github.com/eduvpn/python-eduvpn-client if you think it is an issue."
            ),
        )

    def enter_Added(self, display_name):
        self.connection_notification.show(
            title=_("Added"),
            message=_(
                f"The server {display_name} has been added. "
                "Connect to it by clicking on it."
            ),
        )

    @ui_transition(State.CONNECTING, StateType.ENTER)
    def enter_ConnectingState(self, old_state, new_state):
        self.connection_notification.show(
            title=_("Connecting"),
            message=_(
                "The connection is being established. "
                "This should only take a moment."
            ),
        )

    @ui_transition(State.CONNECTED, StateType.ENTER)
    def enter_ConnectedState(self, old_state, new_state):
        self.connection_notification.show(
            title=_("Connected"), message=_("You are now connected to your server.")
        )

    def enter_SessionPendingExpiryState(self):
        self.connection_notification.show(
            title=_("Connected"),
            message=_(
                "Your session is about to expire. "
                "Renew the session to remain connected."
            ),
        )

    @ui_transition(State.DISCONNECTED, StateType.ENTER)
    def enter_DisconnectedState(self, old_state, server):
        is_expired, _text = get_validity_text(
            self.app.model.get_expiry(server.expire_time)
        )
        reason = ""
        if is_expired:
            reason = " due to expiry"
        self.connection_notification.show(
            title=_("Disconnected"),
            message=_(f"You have been disconnected from your server{reason}."),
        )

    def enter_SessionExpiredState(self):
        self.connection_notification.show(
            title=_("Session expired"), message=_("Your session has expired.")
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
