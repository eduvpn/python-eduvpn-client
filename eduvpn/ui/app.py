import logging
from gettext import gettext as _

import gi
gi.require_version("Gtk", "3.0")  # noqa: E402
from gi.repository import GLib, Gio, Gtk

from .. import i18n
from .. import notify
from ..utils import run_in_main_gtk_thread
from ..state_machine import ENTER, transition_edge_callback
from ..variants import ApplicationVariant
from ..app import Application
from .. import network as network_state
from .. import session as session_state
from .ui import EduVpnGtkWindow


logger = logging.getLogger(__name__)


LOG_FORMAT = format_ = (
    '%(asctime)s - %(threadName)s - %(levelname)s - %(name)s'
    ' - %(filename)s:%(lineno)d - %(message)s'
)


NO_WINDOW_QUIT_NETWORK_STATES = (
    network_state.UnconnectedState,
    network_state.DisconnectedState,
)


class EduVpnGtkApplication(Gtk.Application):
    def __init__(self, *args, app_variant: ApplicationVariant, **kwargs):
        super().__init__(  # type: ignore
            *args,
            application_id=app_variant.app_id,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,  # type: ignore
            **kwargs
        )

        self.app = Application(app_variant, run_in_main_gtk_thread)
        # Only allow a single window and track it on the app.
        self.window = None

        self.add_main_option(  # type: ignore
            'version',
            ord('v'),
            GLib.OptionFlags.NONE,  # type: ignore
            GLib.OptionArg.NONE,  # type: ignore
            "print version and exit",
            None,
        )
        self.add_main_option(  # type: ignore
            'debug',
            ord('d'),
            GLib.OptionFlags.NONE,  # type: ignore
            GLib.OptionArg.NONE,  # type: ignore
            "enable debug logging",
            None,
        )

    def do_startup(self):
        logger.debug('startup')
        Gtk.Application.do_startup(self)
        i18n.initialize(self.app.variant)
        notify.initialize(self.app.variant)
        self.connection_notification = notify.Notification(self.app.variant)
        self.app.connect_state_transition_callbacks(self)

    def do_shutdown(self):
        logger.debug('shutdown')
        self.connection_notification.hide()
        Gtk.Application.do_shutdown(self)

    def do_activate(self):
        logger.debug('activate')
        if not self.window:
            self.window = EduVpnGtkWindow(application=self)
            self.window.initialize()
            self.window.present()
            self.app.initialize()
        else:
            self.window.on_reopen_window()

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

    def on_quit(self, action=None, param=None):
        logger.debug('quit')
        self.quit()

    def on_window_closed(self):
        logger.debug('window closed')
        if isinstance(self.app.network_state, NO_WINDOW_QUIT_NETWORK_STATES):
            # Quit the app if no connection is active on window close.
            logger.debug("window closed while no active connection")
            self.on_quit()

    @transition_edge_callback(ENTER, network_state.ConnectingState)
    def enter_ConnectingState(self, old_state, new_state):
        self.connection_notification.show(
            title=_("Connecting"),
            message=_(
                "The connection is being established. "
                "This should only take a moment."
            ))

    @transition_edge_callback(ENTER, network_state.ConnectedState)
    def enter_ConnectedState(self, old_state, new_state):
        self.connection_notification.show(
            title=_("Connected"),
            message=_("You are now connected to your server."))

    @transition_edge_callback(ENTER, session_state.SessionPendingExpiryState)
    def enter_SessionPendingExpiryState(self, old_state, new_state):
        self.connection_notification.show(
            title=_("Connected"),
            message=_(
                "Your session is about to expire. "
                "Renew the session to remain connected."
            ))

    @transition_edge_callback(ENTER, network_state.ReconnectingState)
    def enter_ReconnectingState(self, old_state, new_state):
        self.connection_notification.show(
            title=_("Connecting"),
            message=_(
                "The connection is being established. "
                "This should only take a moment."
            ))

    @transition_edge_callback(ENTER, network_state.DisconnectedState)
    def enter_DisconnectedState(self, old_state, new_state):
        self.connection_notification.hide()

    @transition_edge_callback(ENTER, session_state.SessionExpiredState)
    def enter_SessionExpiredState(self, old_state, new_state):
        self.connection_notification.show(
            title=_("Session expired"),
            message=_("Your session has expired."))

    @transition_edge_callback(ENTER, network_state.ConnectionErrorState)
    def enter_ConnectionErrorState(self, old_state, new_state):
        message = _("An error occured")
        if new_state.error:
            message = f"{message}: {new_state.error}"
        self.connection_notification.show(
            title=_("Connection Error"),
            message=message)

    @transition_edge_callback(ENTER, NO_WINDOW_QUIT_NETWORK_STATES)
    def enter_NoActiveConnection(self, old_state, new_state):
        if not self.window.is_visible():
            # Quit the app if no window is open when the connection is deactivated.
            logger.debug("connection deactivated while window closed")
            self.on_quit()
