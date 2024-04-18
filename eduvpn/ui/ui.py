# eduvpngui - The GNU/Linux eduVPN GUI client
#
# Copyright: 2017-2020, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import os
import sys
import threading
from gettext import gettext as _
from typing import Callable, Optional, Tuple, Type

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("NM", "1.0")
from datetime import datetime, timedelta
from functools import partial

from eduvpn_common import __version__ as commonver
from eduvpn_common.state import State, StateType
from gi.overrides.Gdk import Event, EventButton  # type: ignore
from gi.overrides.Gtk import (  # type: ignore[import-untyped]
    Box,
    Builder,
    Button,
    TreePath,  # type: ignore
    TreeView,
    TreeViewColumn,
)
from gi.repository import GLib, GObject, Gdk, GdkPixbuf, Gtk
from gi.repository.Gtk import EventBox, SearchEntry, Switch  # type: ignore

from eduvpn import __version__
from eduvpn.connection import Validity
from eduvpn.i18n import retrieve_country_name
from eduvpn.server import StatusImage
from eduvpn.settings import FLAG_PREFIX, IMAGE_PREFIX
from eduvpn.ui import search
from eduvpn.ui.stats import NetworkStats
from eduvpn.ui.utils import (
    QUIT_ID,
    get_validity_text,
    link_markup,
    should_show_error,
    show_error_dialog,
    show_ui_component,
    style_widget,
)
from eduvpn.utils import (
    ERROR_STATE,
    ONLINEDETECT_STATE,
    get_prefix,
    get_ui_state,
    log_exception,
    run_in_background_thread,
    run_in_glib_thread,
    run_periodically,
    ui_transition,
)

logger = logging.getLogger(__name__)


UPDATE_EXPIRY_INTERVAL = 1.0  # seconds


def get_flag_path(country_code: str) -> Optional[str]:
    path = f"{FLAG_PREFIX}{country_code}@1,5x.png"
    if os.path.exists(path):
        return path
    else:
        return None


def get_template_path(filename: str) -> str:
    return os.path.join(get_prefix(), "share/eduvpn/builder", filename)


def get_images_path(filename: str) -> str:
    return os.path.join(IMAGE_PREFIX, filename)


# See:
# https://www.w3.org/TR/AERT/#color-contrast
# And https://stackoverflow.com/a/946734
# For how I came up with these magic values :^)
def is_dark(rgb):
    red = rgb.red * 255
    green = rgb.green * 255
    blue = rgb.blue * 255
    return (red * 0.299 + green * 0.587 + blue * 0.114) <= 186


class ValidityTimers:
    def __init__(self):
        self.cancel_timers = []
        self.num = 0

    def add_absolute(self, call: Callable, abstime: datetime):
        delta = abstime - datetime.now()
        # If time is already passed, call immediately
        delay = delta.total_seconds()
        if delay <= 0:
            call()
            return
        # else set a thread with delay
        timer = threading.Timer(delay, call)
        self.cancel_timers.append(timer)
        timer.start()

    def clean(self):
        for t in self.cancel_timers:
            t.cancel()
        self.cancel_timers = []


class EduVpnGtkWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "EduVpnGtkWindow"

    def __new__(
        cls: Type["EduVpnGtkWindow"],
        application: Type["EduVpnGtkApplication"],  # type: ignore  # noqa: F821
    ) -> "EduVpnGtkWindow":  # noqa: F821
        builder = Gtk.Builder()
        builder.add_from_file(get_template_path("mainwindow.ui"))  # type: ignore
        window = builder.get_object("eduvpn")  # type: ignore
        window.setup(builder, application)  # type: ignore
        window.set_application(application)  # type: ignore
        return window  # type: ignore

    def setup(self, builder: Builder, application: Type["EduVpnGtkApplication"]) -> None:  # type: ignore  # noqa: F821
        self.eduvpn_app = application
        self.app = self.eduvpn_app.app  # type: ignore
        self.common = self.eduvpn_app.common
        handlers = {
            "on_info_delete": self.on_info_delete,
            "on_settings_press_event": self.on_settings_button,
            "on_info_press_event": self.on_info_button,
            "on_go_back": self.on_go_back,
            "on_add_other_server": self.on_add_other_server,
            "on_add_custom_server": self.on_add_custom_server,
            "on_cancel_oauth_setup": self.on_cancel_oauth_setup,
            "on_change_location": self.on_change_location,
            "on_server_row_activated": self.on_server_row_activated,
            "on_server_row_pressed": self.on_server_row_pressed,
            "on_search_changed": self.on_search_changed,
            "on_allow_wg_lan_state_set": self.on_allow_wg_lan_state_set,
            "on_search_activate": self.on_search_activate,
            "on_switch_connection_state": self.on_switch_connection_state,
            "on_toggle_connection_info": self.on_toggle_connection_info,
            "on_profile_row_activated": self.on_profile_row_activated,
            "on_profile_combo_changed": self.on_profile_combo_changed,
            "on_location_row_activated": self.on_location_row_activated,
            "on_acknowledge_error": self.on_acknowledge_error,
            "on_reconnect_tcp_clicked": self.on_reconnect_tcp_clicked,
            "on_renew_session_clicked": self.on_renew_session_clicked,
            "on_close_window": self.on_close_window,
        }
        builder.connect_signals(handlers)
        self.is_searching_server = False

        style_context = self.get_style_context()  # type: ignore
        bg_color = style_context.get_background_color(Gtk.StateFlags.NORMAL)  # type: ignore
        self.is_dark_theme = is_dark(bg_color)

        dark_icons = {
            "infoButton": "question-icon-dark.png",
            "instituteIcon": "institute-icon-dark.png",
            "earthIcon": "earth-icon-dark.png",
            "serverIcon": "server-icon-dark.png",
        }

        if self.is_dark_theme:
            for _id, icon in dark_icons.items():
                obj = builder.get_object(_id)
                obj.set_from_file(get_images_path(icon))

        # Whether or not the profile that is selected is the 'same' one as before
        # This is used so it doesn't fully trigger the callback
        self.set_same_profile = False
        self.is_selected = False

        self.app_logo = builder.get_object("appLogo")
        self.app_logo_info = builder.get_object("appLogoInfo")
        self.info_support_box = builder.get_object("infoSupportBox")

        self.page_stack = builder.get_object("pageStack")
        self.back_button_container = builder.get_object("backButtonEventBox")

        self.server_list_container = builder.get_object("serverListContainer")

        self.info_version = builder.get_object("infoVersion")
        self.info_version.set_text(f"{__version__}")
        self.common_version = builder.get_object("commonVersion")
        self.common_version.set_text(f"{commonver}")
        self.info_log_location = builder.get_object("infoLogLocation")
        self.info_log_location.set_text(str(self.app.variant.logfile))

        self.institute_list_header = builder.get_object("instituteAccessHeader")
        self.secure_internet_list_header = builder.get_object("secureInternetHeader")
        self.other_server_list_header = builder.get_object("otherServersHeader")

        self.institute_list = builder.get_object("instituteScrolledView")
        self.secure_internet_list = builder.get_object("secureInternetScrolledView")
        self.other_server_list = builder.get_object("otherServersScrolledView")

        self.institute_list_tree = builder.get_object("instituteTreeView")
        self.secure_internet_list_tree = builder.get_object("secureInternetTreeView")
        self.other_server_list_tree = builder.get_object("otherServersTreeView")

        self.choose_profile_page = builder.get_object("chooseProfilePage")
        self.choose_location_page = builder.get_object("chooseLocationPage")
        self.change_location_combo = builder.get_object("changeLocationCombo")
        self.disable_change_location = False
        location_renderer_flag = Gtk.CellRendererPixbuf()
        self.change_location_combo.pack_start(location_renderer_flag, False)
        self.change_location_combo.add_attribute(location_renderer_flag, "pixbuf", 0)
        location_renderer_text = Gtk.CellRendererText()
        location_renderer_text.set_property("xpad", 5)
        self.change_location_combo.pack_start(location_renderer_text, True)
        self.change_location_combo.add_attribute(location_renderer_text, "text", 1)
        self.location_list = builder.get_object("locationTreeView")
        self.profile_list = builder.get_object("profileTreeView")

        self.find_server_page = builder.get_object("findServerPage")
        self.find_server_search_form = builder.get_object("findServerSearchForm")
        self.find_server_search_input = builder.get_object("findServerSearchInput")
        self.find_server_image = builder.get_object("findServerImage")
        self.find_server_label = builder.get_object("findServerLabel")

        self.main_overlay = builder.get_object("mainOverlay")

        self.previous_page_settings = None
        self.previous_back_button = False
        self.settings_page = builder.get_object("settingsPage")
        self.settings_button = builder.get_object("settingsButton")
        self.allow_wg_lan_switch = builder.get_object("allowWgLanSwitch")

        # Create a revealer
        self.clipboard = None
        self.initialize_clipboard()
        self.error_revealer = None
        self.error_revealer_label = None
        self.create_error_revealer()

        self.add_custom_server_button_container = builder.get_object("addCustomServerRow")
        self.add_other_server_button_container = builder.get_object("addOtherServerRow")

        self.connection_page = builder.get_object("connectionPage")
        self.connection_status_image = builder.get_object("connectionStatusImage")
        self.connection_status_label = builder.get_object("connectionStatusLabel")
        self.connection_session_label = builder.get_object("connectionSessionLabel")
        self.connection_info_duration_text = builder.get_object("connectionInfoDurationText")
        self.connection_switch = builder.get_object("connectionSwitch")
        self.connection_info_expander = builder.get_object("connectionInfoExpander")
        self.connection_info_downloaded = builder.get_object("connectionInfoDownloadedText")
        self.connection_info_protocol = builder.get_object("connectionInfoProtocolText")
        self.connection_info_uploaded = builder.get_object("connectionInfoUploadedText")
        self.connection_info_ipv4address = builder.get_object("connectionInfoIpv4AddressText")
        self.connection_info_ipv6address = builder.get_object("connectionInfoIpv6AddressText")
        self.connection_info_thread_cancel = None
        self.connection_validity_timers = ValidityTimers()
        self.connection_validity_thread_cancel: Optional[Callable] = None
        self.connection_info_stats = None
        self.current_shown_page = None

        self.disable_loading_page = False

        self.proxy_active_dialog = builder.get_object("proxyActiveDialog")
        self.proxy_active_dialog_remember = builder.get_object("proxyActiveRemember")

        self.info_dialog = builder.get_object("infoDialog")

        self.keyring_dialog = builder.get_object("keyringDialog")
        self.keyring_do_not_show = builder.get_object("keyringDoNotShow")

        self.server_image = builder.get_object("serverImage")
        self.server_label = builder.get_object("serverLabel")
        self.server_support_label = builder.get_object("supportLabel")

        self.renew_session_button = builder.get_object("renewSessionButton")
        self.reconnect_tcp_button = builder.get_object("reconnectTCPButton")
        self.reconnect_tcp_text = builder.get_object("reconnectTCPText")
        self.select_profile_combo = builder.get_object("selectProfileCombo")
        self.select_profile_text = builder.get_object("selectProfileText")

        self.oauth_page = builder.get_object("openBrowserPage")
        self.oauth_cancel_button = builder.get_object("cancelBrowserButton")

        self.loading_page = builder.get_object("loadingPage")
        self.loading_title = builder.get_object("loadingTitle")
        self.loading_message = builder.get_object("loadingMessage")

        self.set_title(self.app.variant.name)  # type: ignore
        self.set_icon_from_file(self.app.variant.icon)  # type: ignore
        if self.app.variant.logo:
            logo = self.app.variant.logo
            if self.is_dark_theme:
                logo = self.app.variant.logo_dark
            self.app_logo.set_from_file(logo)
            self.app_logo_info.set_from_file(logo)
        if self.app.variant.server_image:
            self.find_server_image.set_from_file(self.app.variant.server_image)
        if not self.app.variant.use_predefined_servers:
            self.find_server_label.set_text(_("Server address"))
            self.find_server_search_input.set_placeholder_text(_("Enter the server address"))
            self.info_support_box.hide()

        # We track the switch state so we can distinguish
        # the switch being set by the ui from the user toggling it.
        self.connection_switch_state: Optional[bool] = None

    def initialize(self) -> None:
        if not self.app.nm_manager.available:
            show_error_dialog(
                self,
                _("Error"),
                _("NetworkManager not available"),
                _(
                    "The application will not be able to configure the network. Please install and set up NetworkManager."
                ),
            )
        elif not self.app.nm_manager.managed:
            show_error_dialog(
                self,
                _("Error"),
                _("NetworkManager not managing device"),
                _(
                    "The application will not be able to configure the network. NetworkManager is installed but no device of the primary connection is currently managed by it."
                ),
            )

        @run_in_background_thread("register")
        def register():
            try:
                self.common.register_class_callbacks(self)
                self.enter_deregistered()
                self.app.model.register(debug=self.eduvpn_app.debug)
                self.exit_deregistered()
                self.app.initialize_network()
            except Exception as e:
                log_exception(e)
                if not should_show_error(e):
                    return
                show_error_dialog(
                    self,
                    _("Fatal Error"),
                    _("Fatal error while starting the client"),
                    str(e),
                    True,
                )

        register()

    @run_in_background_thread("call-model")
    def call_model(self, func_name: str, *args, callback: Optional[Callable] = None):
        func = getattr(self.app.model, func_name, None)
        if func:
            try:
                func(*(args))
                if callback:
                    callback(True)
            except Exception as e:
                if should_show_error(e):
                    self.show_error_revealer(str(e))
                log_exception(e)
                if callback:
                    callback(False, str(e))
        else:
            raise Exception(f"No such function: {func_name}")

    @run_in_glib_thread
    def enter_deregistered(self):
        self.show_loading_page(
            _("Loading client"),
            _("The client is loading the servers."),
        )

    @ui_transition(State.DEREGISTERED, StateType.ENTER)
    def enter_deregistered_transition(self, old_state: State, data: str):
        logger.debug("deregistered transition")
        self.close()
        sys.exit(0)

    @run_in_glib_thread
    def exit_deregistered(self):
        self.hide_loading_page()

    @ui_transition(ERROR_STATE, StateType.ENTER)  # type: ignore
    def enter_error_state(self, old_state: str, error: Exception):
        if should_show_error(error):
            self.show_error_revealer(str(error))

    @ui_transition(ONLINEDETECT_STATE, StateType.ENTER)  # type: ignore
    def enter_online_detect_state(self, old_state: str, data: str):
        self.connection_status_label.set_text(_("Connected, testing connection..."))
        self.connection_status_image.set_from_file(StatusImage.CONNECTING.path)
        self.set_connection_switch_state(True)

    @run_in_glib_thread
    def initialize_clipboard(self):
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

    @run_in_glib_thread
    def create_error_revealer(self):
        # Creat the revealer and set the properties
        self.error_revealer = Gtk.Revealer.new()
        self.error_revealer.set_valign(Gtk.Align.END)
        self.error_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.error_revealer.set_transition_duration(200)

        # Create a close button
        error_revealer_close_image = Gtk.Image.new_from_icon_name("window-close", Gtk.IconSize.BUTTON)
        error_revealer_close_button = Gtk.Button.new()
        error_revealer_close_button.set_halign(Gtk.Align.END)
        error_revealer_close_button.set_valign(Gtk.Align.START)
        error_revealer_close_button.set_always_show_image(True)
        error_revealer_close_button.set_image(error_revealer_close_image)
        error_revealer_close_button.set_relief(Gtk.ReliefStyle.NONE)
        error_revealer_close_button.connect("clicked", self.hide_error_revealer)
        error_revealer_close_button.show()
        style_widget(
            error_revealer_close_button,
            "errorRevealerButton",
            "background-color: transparent; padding: 0px;",
        )

        # Create a clipboard button
        error_revealer_clipboard_image = Gtk.Image.new_from_icon_name("edit-copy", Gtk.IconSize.BUTTON)
        error_revealer_clipboard_button = Gtk.Button.new()
        error_revealer_clipboard_button.set_halign(Gtk.Align.END)
        error_revealer_clipboard_button.set_valign(Gtk.Align.START)
        error_revealer_clipboard_button.set_always_show_image(True)
        error_revealer_clipboard_button.set_image(error_revealer_clipboard_image)
        error_revealer_clipboard_button.set_relief(Gtk.ReliefStyle.NONE)
        error_revealer_clipboard_button.connect("clicked", self.copy_error_revealer)
        error_revealer_clipboard_button.show()
        style_widget(
            error_revealer_clipboard_button,
            "errorRevealerClipboardButton",
            "background-color: transparent; padding: 0px;",
        )

        # Create the label
        self.error_revealer_label = Gtk.Label.new("<b>Error occurred</b>: Example error")
        self.error_revealer_label.set_use_markup(True)
        self.error_revealer_label.set_margin_bottom(20)
        self.error_revealer_label.set_margin_left(20)
        self.error_revealer_label.set_margin_right(20)
        self.error_revealer_label.set_line_wrap(True)
        self.error_revealer_label.set_selectable(True)
        self.error_revealer_label.show()

        # Create the title box and title label
        error_revealer_title = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 10)
        error_revealer_title_label = Gtk.Label.new("<b>Error occurred</b>")
        error_revealer_title_label.set_use_markup(True)
        error_revealer_title_label.show()
        # Add the buttons and the title label to the box
        error_revealer_title.pack_start(error_revealer_title_label, True, True, 0)
        error_revealer_title.pack_end(error_revealer_close_button, False, False, 0)
        error_revealer_title.pack_end(error_revealer_clipboard_button, False, False, 0)
        error_revealer_title.show()
        # Add the title box and the error label to a new box
        error_revealer_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 10)
        error_revealer_box.add(error_revealer_title)
        error_revealer_box.add(self.error_revealer_label)
        error_revealer_box.show()

        # Add a frame around the box
        error_revealer_frame = Gtk.Frame.new()
        error_revealer_frame.set_valign(Gtk.Align.END)
        style_widget(
            error_revealer_frame,
            "errorClass",
            "margin-left: 20px; margin-right: 20px; background-color: #B00020; margin-top: 0px; padding: 0px; color: rgba(255, 255, 255, 1);",
        )
        error_revealer_frame.add(error_revealer_box)
        error_revealer_frame.show()

        # Add the frame to the revealer and show it
        self.error_revealer.add(error_revealer_frame)
        self.error_revealer.show()
        self.shown_notification_times = set()

        # add the error revealer to the main overlay
        self.main_overlay.add_overlay(self.error_revealer)

    @run_in_glib_thread
    def show_error_revealer(self, error: str) -> None:
        if self.error_revealer is None or self.error_revealer_label is None:
            return
        self.error_revealer.set_reveal_child(True)
        self.error_revealer_label.set_text(
            f"""
The following error was reported: <i>{GLib.markup_escape_text(error)}</i>.

For detailed information, see the log file located at:
 - {GLib.markup_escape_text(str(self.app.variant.logfile))}"""
        )
        self.error_revealer_label.set_use_markup(True)

    @run_in_glib_thread
    def copy_error_revealer(self, _button) -> None:
        if self.error_revealer_label is None:
            return
        if self.clipboard is None:
            return
        self.clipboard.set_text(self.error_revealer_label.get_text(), -1)
        self.eduvpn_app.enter_CopiedAnError()  # type: ignore

    @run_in_glib_thread
    def hide_error_revealer(self, _button) -> None:
        if self.error_revealer is None:
            return
        self.error_revealer.set_reveal_child(False)

    # ui functions
    def show_back_button(self, show: bool) -> None:
        show_ui_component(self.back_button_container, show)

    def set_search_text(self, text: str) -> None:
        self.find_server_search_input.set_text(text)

    def show_loading_page(self, title: str, message: str) -> None:
        if self.disable_loading_page:
            self.connection_status_label.set_text(_(title))
            self.connection_status_image.set_from_file(StatusImage.CONNECTING.path)
            self.set_connection_switch_state(True)
            return
        self.show_page(self.loading_page)
        self.loading_title.set_text(title)
        self.loading_message.set_text(message)
        self.loading_page.show()

    def hide_loading_page(self) -> None:
        self.loading_page.hide()

    def set_connection_switch_state(self, state: bool) -> None:
        self.connection_switch_state = state
        self.connection_switch.set_state(state)
        self.connection_switch.set_active(state)

    def show_page(self, page: Box) -> None:
        """
        Show a collection of pages.
        """
        self.current_shown_page = page
        page.show()
        self.page_stack.set_visible_child(page)

    def hide_page(self, page: Box) -> None:
        """
        Show a collection of pages.
        """
        self.current_shown_page = None

    def get_profile_combo_sorted(self, server_info) -> Tuple[int, Gtk.ListStore]:
        profile_store = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_PYOBJECT)  # type: ignore
        active_profile = 0
        sorted_profiles = sorted(server_info.profiles.profiles.items(), key=lambda v: str(v[1]))
        index = 0
        for _id, profile in sorted_profiles:
            if _id == server_info.profiles.current_id:
                active_profile = index
            profile_store.append([str(profile), profile])  # type: ignore
            index += 1
        return active_profile, profile_store

    def recreate_profile_combo(self, server_info) -> None:
        # Create a store of profiles
        active_profile, profile_store = self.get_profile_combo_sorted(server_info)

        # Create a new combobox
        # We create a new one every time because Gtk has some weird behaviour regarding the width of the combo box
        # When we add items that are large, the combobox resizes to fit the content
        # However, when we add items again that are all smaller (e.g. for a new server), the combo box does not shrink back
        # The only proper way seems to be to recreate the combobox every time
        combo = Gtk.ComboBoxText.new()  # type: ignore
        # Sort the model too
        combo.set_model(profile_store)  # type: ignore
        combo.set_active(active_profile)
        combo.set_halign(Gtk.Align.CENTER)
        combo.connect("changed", self.on_profile_combo_changed)

        # Get the position of the current combobox in the connection page
        position = self.connection_page.child_get_property(self.select_profile_combo, "position")

        # Destroy the combobox and add the new one
        self.select_profile_combo.destroy()
        self.connection_page.pack_start(combo, True, True, 0)
        self.connection_page.reorder_child(combo, position)
        self.select_profile_combo = combo

        self.select_profile_combo.show()

    # network state transition callbacks
    def update_connection_server(self, server_info) -> None:
        if not server_info:
            return

        self.select_profile_text.show()
        self.recreate_profile_combo(server_info)

        if len(server_info.profiles.profiles) <= 1:
            self.select_profile_text.set_text("One Profile Available: ")
        else:
            self.select_profile_text.set_text("Select Profile: ")

        if hasattr(server_info, "country_code"):
            self.server_label.set_text(f"{retrieve_country_name(server_info.country_code)}\n(via {str(server_info)})")
            flag_path = get_flag_path(server_info.country_code)
            if flag_path:
                self.server_image.set_from_file(flag_path)
                self.server_image.show()
            else:
                self.server_image.hide()
        else:
            self.server_label.set_text(str(server_info))
            self.server_image.hide()

        if hasattr(server_info, "support_contact") and server_info.support_contact:
            support_text = _("Support:") + "\n" + "\n".join(map(link_markup, server_info.support_contact))
            self.server_support_label.set_markup(support_text)
            self.server_support_label.show()
        else:
            self.server_support_label.hide()

    # every second
    def update_connection_validity(self, validity: Validity) -> None:
        is_expired, detailed_text, expiry_text = get_validity_text(validity)
        self.connection_session_label.set_markup(expiry_text)
        if datetime.now() >= validity.countdown:
            self.connection_session_label.show()
        else:
            self.connection_session_label.hide()
        self.connection_info_duration_text.show()
        self.connection_info_duration_text.set_markup(detailed_text)

        # The connection is expired, show a notification
        if is_expired:
            # Be extra sure the renew button is shown
            self.renew_session_button.show()

            # Stop updating the text
            if self.connection_validity_thread_cancel:
                self.connection_validity_thread_cancel()

            self.eduvpn_app.enter_SessionExpiredState()

    # Shows notifications according to https://docs.eduvpn.org/server/v3/client-implementation-notes.html#expiry
    # The 0th case is handled with a separate notification inside of the expiry text handler
    def ensure_expiry_notification_text(self, validity: Validity) -> None:
        hours = [4, 2, 1]
        for h in hours:
            if h in self.shown_notification_times:
                continue
            delta = validity.remaining - timedelta(hours=h)
            total_secs = delta.total_seconds()
            if total_secs <= 0 and total_secs >= -120:
                self.eduvpn_app.enter_SessionPendingExpiryState(h)
                self.shown_notification_times.add(h)
                break

    # Show renew button or not
    def update_connection_renew(self, expire_time) -> None:
        if self.app.model.should_renew_button():
            # Show renew button
            self.renew_session_button.show()

            validity = self.app.model.get_expiry(expire_time)
            self.ensure_expiry_notification_text(validity)

    def update_connection_status(self, connected: bool) -> None:
        if connected:
            self.connection_status_label.set_text(_("Connected"))
            self.connection_status_image.set_from_file(StatusImage.CONNECTED.path)
            self.set_connection_switch_state(True)
        else:
            self.connection_status_label.set_text(_("Disconnected"))
            self.connection_status_image.set_from_file(StatusImage.NOT_CONNECTED.path)
            self.set_connection_switch_state(False)

    # session state transition callbacks

    @ui_transition(State.CONNECTING, StateType.ENTER)
    def enter_connecting(self, old_state: str, server_info):
        self.renew_session_button.hide()
        self.connection_info_expander.hide()
        self.connection_status_label.set_text(_("Connecting..."))
        self.connection_status_image.set_from_file(StatusImage.CONNECTING.path)
        self.set_connection_switch_state(True)
        # Disable the profile combo box and switch
        self.select_profile_combo.set_sensitive(False)
        self.connection_session_label.hide()
        self.update_connection_server(server_info)
        self.show_page(self.connection_page)

    @ui_transition(State.CONNECTING, StateType.LEAVE)
    def exit_connecting(self, old_state: str, data):
        # Re-enable the profile combo box and switch
        self.select_profile_combo.set_sensitive(True)

    @ui_transition(State.DISCONNECTING, StateType.ENTER)
    def enter_disconnecting(self, old_state: str, data):
        self.renew_session_button.hide()
        self.connection_status_label.set_text(_("Disconnecting..."))
        self.connection_status_image.set_from_file(StatusImage.CONNECTING.path)
        self.set_connection_switch_state(False)
        # Disable the profile combo box and switch
        self.select_profile_combo.set_sensitive(False)
        self.connection_switch.set_sensitive(False)
        self.connection_session_label.hide()

    @ui_transition(State.DISCONNECTING, StateType.LEAVE)
    def exit_disconnecting(self, old_state: str, data):
        # Re-enable the profile combo box and switch
        self.select_profile_combo.set_sensitive(True)
        self.connection_session_label.hide()
        self.connection_switch.set_sensitive(True)

    @run_in_background_thread("update-search-async")
    def update_search_async(self):
        try:
            self.app.model.server_db.disco_update()
        except Exception as e:
            self.show_error_revealer(str(e))
            return

        @run_in_glib_thread
        def update_results():
            # If we have left search server we should do nothing
            # We should find a better way to do this as this is pretty racy
            if not self.is_searching_server:
                return
            self.on_search_changed()

        update_results()

    @property
    def can_disable_secure_internet(self) -> bool:
        # We are not searching a server
        # We can thus not disable the secure internet view unconditionally
        if not self.is_searching_server:
            return False

        # A server is not available, we need to show the list
        if self.app.model.server_db.secure_internet is None:
            return False

        return True

    def enter_search(self, data):
        self.is_searching_server = True
        self.show_back_button(not data)
        self.set_search_text("")
        self.add_other_server_button_container.hide()
        self.change_location_combo.hide()
        self.find_server_search_input.grab_focus()
        search.show_result_components(self, True)
        search.show_search_components(self, True)
        search.update_results(self, self.app.model.server_db.disco)
        search.init_server_search(self)

        # asynchronously update the search results
        self.update_search_async()

    def exit_search(self):
        self.is_searching_server = False
        self.show_back_button(False)
        search.show_result_components(self, False)
        search.show_search_components(self, False)
        search.exit_server_search(self)

    def exit_ConfigureCustomServer(self, old_state, new_state):
        if not self.app.variant.use_predefined_servers:
            self.add_custom_server_button_container.hide()

    def fill_secure_location_combo(self, curr, locs):
        locs_store = Gtk.ListStore(GdkPixbuf.Pixbuf, GObject.TYPE_STRING, GObject.TYPE_STRING)
        active_loc = 0
        sorted_locs = sorted(locs, key=lambda x: retrieve_country_name(x))
        index = 0
        for loc in sorted_locs:
            if loc == curr:
                active_loc = index
            flag_path = get_flag_path(loc)
            pixbuf = None
            if flag_path:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(flag_path)
            locs_store.append([pixbuf, retrieve_country_name(loc), loc])
            index += 1
        self.change_location_combo.set_model(locs_store)
        self.disable_change_location = True
        self.change_location_combo.set_active(active_loc)
        self.disable_change_location = False

    @ui_transition(State.MAIN, StateType.ENTER)
    def enter_MainState(self, old_state: str, servers):
        self.disable_loading_page = False
        search.show_result_components(self, True)
        self.add_other_server_button_container.show()
        search.init_server_search(self)

        secure = self.app.model.server_db.secure_internet
        if secure:
            self.fill_secure_location_combo(secure.country_code, secure.locations)
            self.change_location_combo.show()

        search.update_results(self, servers)

        # Do not go in a loop by checking old state
        if not servers:
            self.enter_search(True)

        if all(
            [
                not self.app.model.keyring.secure,
                not self.app.config.ignore_keyring_warning,
                old_state == get_ui_state(State.DEREGISTERED),
            ]
        ):
            self.keyring_dialog.set_title(f"{self.app.variant.name} - Keyring Warning")
            self.keyring_dialog.show()
            _id = self.keyring_dialog.run()
            if _id == QUIT_ID:
                self.close()  # type: ignore
            self.keyring_dialog.destroy()
            self.app.config.ignore_keyring_warning = self.keyring_do_not_show.get_active()

    @ui_transition(State.MAIN, StateType.LEAVE)
    def exit_MainState(self, old_state, new_state):
        search.show_result_components(self, False)
        self.add_other_server_button_container.hide()
        search.exit_server_search(self)
        self.change_location_combo.hide()

    @ui_transition(State.OAUTH_STARTED, StateType.ENTER)
    def enter_oauth_setup(self, old_state, url):
        self.show_page(self.oauth_page)
        self.oauth_cancel_button.show()

    @ui_transition(State.OAUTH_STARTED, StateType.LEAVE)
    def exit_oauth_setup(self, old_state, data):
        self.hide_page(self.oauth_page)
        self.oauth_cancel_button.hide()

    @ui_transition(State.ADDING_SERVER, StateType.ENTER)
    def enter_chosenServerInformation(self, new_state, data):
        self.show_loading_page(
            _("Adding server"),
            _("Loading server information..."),
        )

    @ui_transition(State.ADDING_SERVER, StateType.LEAVE)
    def exit_chosenServerInformation(self, old_state, data):
        self.hide_loading_page()

    @ui_transition(State.GETTING_CONFIG, StateType.ENTER)
    def enter_GettingConfig(self, new_state, data):
        self.show_loading_page(
            _("Getting a VPN configuration"),
            _("Loading server information..."),
        )

    @ui_transition(State.GETTING_CONFIG, StateType.LEAVE)
    def exit_GettingConfig(self, old_state, data):
        self.hide_loading_page()

    @ui_transition(State.ASK_PROFILE, StateType.ENTER)
    def enter_ChooseProfile(self, new_state, data):
        self.show_back_button(True)
        self.show_page(self.choose_profile_page)
        self.profile_list.show()

        setter, profiles = data

        profile_tree_view = self.profile_list
        profiles_list_model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_PYOBJECT)

        if len(profile_tree_view.get_columns()) == 0:
            # Only initialize this tree view once.
            text_cell = Gtk.CellRendererText()
            text_cell.set_property("size-points", 14)
            text_cell.set_property("ypad", 10)

            column = Gtk.TreeViewColumn(None, text_cell, text=0)
            profile_tree_view.append_column(column)

        sorted_model = Gtk.TreeModelSort(model=profiles_list_model)
        sorted_model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        profile_tree_view.set_model(sorted_model)
        profiles_list_model.clear()
        for profile_id, profile in profiles.profiles.items():
            profiles_list_model.append([str(profile), (setter, profile_id)])

    @ui_transition(State.ASK_PROFILE, StateType.LEAVE)
    def exit_ChooseProfile(self, old_state, data):
        self.show_back_button(False)
        self.hide_page(self.choose_profile_page)
        self.profile_list.hide()

    @ui_transition(State.ASK_LOCATION, StateType.ENTER)
    def enter_ChooseSecureInternetLocation(self, old_state, data):
        self.show_back_button(True)
        self.show_page(self.choose_location_page)
        self.location_list.show()

        setter, locations = data

        location_tree_view = self.location_list
        location_list_model = Gtk.ListStore(GObject.TYPE_STRING, GdkPixbuf.Pixbuf, GObject.TYPE_PYOBJECT)

        if len(location_tree_view.get_columns()) == 0:
            # Only initialize this tree view once.
            text_cell = Gtk.CellRendererText()
            text_cell.set_property("size-points", 14)
            text_cell.set_property("ypad", 10)

            renderer_pixbuf = Gtk.CellRendererPixbuf()
            column = Gtk.TreeViewColumn("Image", renderer_pixbuf, pixbuf=1)
            location_tree_view.append_column(column)

            column = Gtk.TreeViewColumn(None, text_cell, text=0)
            location_tree_view.append_column(column)

            sorted_model = Gtk.TreeModelSort(model=location_list_model)
            sorted_model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
            location_tree_view.set_model(sorted_model)

        location_list_model.clear()
        for location in locations:
            flag_path = get_flag_path(location)
            if flag_path is None:
                logger.warning(f"No flag found for country code {location}")
                flag = None
            else:
                flag = GdkPixbuf.Pixbuf.new_from_file(flag_path)
            location_list_model.append([retrieve_country_name(location), flag, (setter, location)])

    @ui_transition(State.ASK_LOCATION, StateType.LEAVE)
    def exit_ChooseSecureInternetLocation(self, old_state, new_state):
        self.show_back_button(False)
        self.hide_loading_page()
        self.hide_page(self.choose_location_page)
        self.location_list.hide()

    @ui_transition(State.GOT_CONFIG, StateType.ENTER)
    def enter_GotConfig(self, old_state: str, server_info) -> None:
        self.enter_connecting(old_state, server_info)

    @ui_transition(State.GOT_CONFIG, StateType.LEAVE)
    def exit_GotConfig(self, old_state: str, new_state: str) -> None:
        self.exit_connecting(old_state, new_state)

    @ui_transition(State.DISCONNECTED, StateType.ENTER)
    def enter_ConnectionStatus(self, old_state: str, server_info):
        self.show_back_button(True)
        self.show_page(self.connection_page)
        self.update_connection_status(False)
        self.update_connection_server(server_info)
        self.reconnect_tcp_button.hide()
        self.reconnect_tcp_text.hide()
        self.renew_session_button.hide()
        self.connection_session_label.hide()

        # In this screen we want no loading pages
        self.disable_loading_page = True
        self.renew_session_button.hide()

    @ui_transition(State.DISCONNECTED, StateType.LEAVE)
    def exit_ConnectionStatus(self, old_state, new_state):
        self.show_back_button(False)
        self.hide_page(self.connection_page)

    @ui_transition(State.CONNECTED, StateType.LEAVE)
    def leave_ConnectedState(self, old_state, server_info):
        logger.debug("leave connected state")
        self.reconnect_tcp_button.hide()
        self.reconnect_tcp_text.hide()
        self.connection_info_expander.hide()

        # In this screen we want no loading pages
        self.disable_loading_page = True
        self.stop_validity_countdown()
        self.renew_session_button.hide()
        self.connection_session_label.hide()
        self.stop_validity_threads()
        self.stop_connection_info()

    @ui_transition(State.CONNECTED, StateType.ENTER)
    def enter_ConnectedState(self, old_state, server_data):
        self.renew_session_button.hide()
        server_info, validity = server_data
        self.connection_info_expander.show()
        self.connection_info_expander.set_expanded(False)
        self.show_back_button(False)
        self.start_connection_info()
        self.update_connection_status(True)
        self.update_connection_server(server_info)
        self.start_validity_countdown(validity)
        self.show_page(self.connection_page)

        # Show the button after a certain time period
        self.connection_validity_timers.add_absolute(self.renew_session_button.show, validity.button)

        # Show the notifications
        for t in validity.notifications:
            self.connection_validity_timers.add_absolute(partial(self.start_validity_expiry_notification, validity), t)

        if self.app.model.should_failover():
            self.reconnect_tcp_button.show()
            self.reconnect_tcp_text.show()
        else:
            self.reconnect_tcp_button.hide()
            self.reconnect_tcp_text.hide()

    def start_validity_countdown(self, validity) -> None:
        logger.debug("start validity countdown")
        self.connection_validity_thread_cancel = run_periodically(
            run_in_glib_thread(partial(self.update_connection_validity, validity)),
            UPDATE_EXPIRY_INTERVAL,
            "update-validity",
        )

    def stop_validity_countdown(self) -> None:
        logger.debug("stop validity countdown")
        if self.connection_validity_thread_cancel:
            self.connection_validity_thread_cancel()
            self.connection_validity_thread_cancel = None

    def start_validity_expiry_notification(self, validity) -> None:
        logger.debug(f"show expiry notification: {validity.end}")
        # If the time now is delta 5 seconds from expiry, disconnect
        d = datetime.now() - validity.end
        if abs(d.total_seconds()) <= 5:
            # Enter expiry
            self.eduvpn_app.enter_SessionExpiredState()

    def stop_validity_threads(self) -> None:
        logger.debug("stop validity threads")
        if self.connection_validity_thread_cancel:
            self.connection_validity_thread_cancel()
            self.connection_validity_thread_cancel = None
        self.connection_validity_timers.clean()

    def on_info_delete(self, widget, event):
        logger.debug("info dialog delete event")
        return widget.hide_on_delete()

    def on_info_button(self, widget: EventBox, event: EventButton) -> None:
        logger.debug("clicked info button")
        self.info_dialog.set_title(f"{self.app.variant.name} - Info")
        self.info_dialog.show()
        self.info_dialog.run()
        self.info_dialog.hide()

    def on_settings_button(self, widget: EventBox, event: EventButton) -> None:
        logger.debug("clicked settings button")
        if self.current_shown_page is None:
            return
        self.settings_button.hide()
        self.show_back_button(True)
        self.previous_page_settings = self.current_shown_page
        self.previous_back_button = self.back_button_container.props.visible
        self.settings_page.show()
        self.allow_wg_lan_switch.set_state(self.app.config.allow_wg_lan)
        self.show_page(self.settings_page)

    def on_go_back(self, widget: EventBox, event: EventButton) -> None:
        logger.debug("clicked on go back")
        # We are in the settings if we have stored the previous settings page
        # if so show the settings page and reset the previous page settings
        if self.previous_page_settings is not None:
            self.settings_button.show()
            self.show_back_button(self.previous_back_button)
            self.show_page(self.previous_page_settings)
            self.settings_page.hide()
            self.previous_page_settings = None
            self.previous_back_button = False
        else:
            self.call_model("go_back")
            if self.is_searching_server:
                self.exit_search()

    def on_add_other_server(self, button: Button) -> None:
        logger.debug("clicked on add other server")
        self.enter_search(False)

    def on_add_custom_server(self, button) -> None:
        logger.debug("clicked on add custom server")
        self.enter_search(False)

    def on_server_row_activated(self, widget: TreeView, row: TreePath, _col: TreeViewColumn) -> None:
        model = widget.get_model()
        server = model[row][1]
        logger.debug(f"activated server: {server!r}")

        def on_added(server):
            logger.debug(f"Server added, {str(server)}")

        if self.is_searching_server:
            self.is_searching_server = False
            self.call_model("add", server, on_added)
            self.exit_search()
        else:
            self.call_model("connect", server)

    def server_ask_remove(self, server):
        gtk_remove_id = -12
        gtk_nop_id = -11
        dialog = Gtk.MessageDialog(  # type: ignore
            parent=self,
            type=Gtk.MessageType.QUESTION,  # type: ignore
            title=_("Server"),
            message_format=_("Removing server"),
        )
        dialog.add_buttons(_("Remove server"), gtk_remove_id, _("Do nothing"), gtk_nop_id)
        dialog.format_secondary_text(_(f"Are you sure you want to remove server {str(server)}?"))  # type: ignore
        dialog.show()  # type: ignore
        response = dialog.run()  # type: ignore
        dialog.destroy()  # type: ignore

        if response == gtk_remove_id:
            logger.debug(f"doing server remove for: {server!r}")
            self.call_model("remove", server)
        else:
            logger.debug(f"cancelled server remove for: {server!r}")

    def on_server_row_pressed(self, widget: TreeView, event: EventButton) -> None:
        logger.debug("on server row pressed")
        # Exit if not a press
        if event.type != Gdk.EventType.BUTTON_PRESS:
            return

        # Not in the main screen
        if not self.common.in_state(State.MAIN) or self.is_searching_server:
            return

        # Not a right click
        if event.button != 3:
            return

        (model, tree_iter) = widget.get_selection().get_selected()
        if tree_iter is None:
            return None

        row = model[tree_iter]
        server = row[1]
        remove_item = Gtk.MenuItem()  # type: ignore
        remove_item.connect("activate", lambda _: self.server_ask_remove(server))
        remove_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 0)  # type: ignore
        remove_image = Gtk.Image.new_from_icon_name("edit-delete", Gtk.IconSize.MENU)  # type: ignore
        remove_label = Gtk.Label.new("Remove Server")  # type: ignore
        remove_box.pack_start(remove_image, False, False, 0)  # type: ignore
        remove_box.pack_start(remove_label, False, False, 8)  # type: ignore
        remove_item.add(remove_box)
        remove_item.show_all()

        menu = Gtk.Menu()  # type: ignore
        # Icons are already added so do not reserve extra space for them
        menu.set_reserve_toggle_size(0)  # type: ignore
        menu.append(remove_item)
        menu.attach_to_widget(widget)  # type: ignore
        menu.popup_at_pointer()

    def on_cancel_oauth_setup(self, _):
        logger.debug("clicked on cancel oauth setup")

        self.call_model("cancel")

    def on_change_location(self, combo):
        if self.disable_change_location:
            return
        tree_iter = combo.get_active_iter()

        if tree_iter is None:
            return

        model = combo.get_model()
        _loc_flag, _loc_display, location = model[tree_iter][:3]

        # Set profile and connect
        self.call_model("change_secure_location", location)

    def on_search_changed(self, _: Optional[SearchEntry] = None) -> None:
        query = self.find_server_search_input.get_text()
        if self.app.variant.use_predefined_servers and query.count(".") < 2:
            results = self.app.model.search_predefined(query)
            search.update_results(self, results)
        else:
            # Anything with two periods is interpreted
            # as a custom server address.
            results = self.app.model.search_custom(query)
            search.update_results(self, results)

    def on_allow_wg_lan_state_set(self, switch, state) -> None:
        self.app.config.allow_wg_lan = state

    def on_search_activate(self, _=None):
        logger.debug("activated server search")

    def on_switch_connection_state(self, _switch: Switch, state: bool) -> bool:
        logger.debug("clicked on switch connection state")

        if state is self.connection_switch_state:
            return True
        self.connection_switch_state = state

        @run_in_glib_thread
        def on_switch_on(success: bool, error: str = ""):
            if success:
                self.update_connection_status(True)
                return
            self.update_connection_status(False)
            # error not known, show a generic error
            if not error:
                self.show_error_revealer("failed to activate connection")

        @run_in_glib_thread
        def on_switch_off(success: bool, error: str = ""):
            if success:
                self.update_connection_status(False)
                return
            self.update_connection_status(True)
            # error not known, show a generic error
            if not error:
                self.show_error_revealer("failed to deactivate connection")

        # Cancel everything if something was in progress
        # We return if something from NM was canceled
        def on_canceled(success: bool, error: str = ""):
            # The user has toggled the connection switch,
            # as opposed to the ui itself setting it.
            if not success:
                if not error:
                    self.show_error_revealer(
                        "failed to activate connection as previous operations could not be canceled"
                    )
                return
            if state:
                # the second callback here is used if any exceptions happen
                self.call_model("activate_connection", on_switch_on)
            else:
                self.stop_connection_info()
                # the second callback here is used if any exceptions happen
                self.call_model("deactivate_connection", on_switch_off)

        self.call_model("cancel", callback=on_canceled)
        return True

    def pause_connection_info(self) -> None:
        if self.connection_info_thread_cancel:
            self.connection_info_thread_cancel()
            self.connection_info_thread_cancel = None

    def stop_connection_info(self) -> None:
        # Pause the thread
        self.pause_connection_info()

        # Further cleanup
        if self.connection_info_stats:
            self.connection_info_stats.cleanup()
            self.connection_info_stats = None

    def start_connection_info(self):
        if not self.common.in_state(State.CONNECTED):
            logger.info("Connection Info: VPN is not active")
            return

        @run_in_background_thread("update-connection-info")
        def update_connection_info_callback():
            # Do nothing if we have no stats object
            if not self.connection_info_stats:
                return
            try:
                download = self.connection_info_stats.download
                upload = self.connection_info_stats.upload
                protocol = self.connection_info_stats.protocol
                ipv4 = self.connection_info_stats.ipv4
                ipv6 = self.connection_info_stats.ipv6
            except ValueError as e:
                logger.warning(f"Got an error when trying to retrieve stats: {e}. The connection might be closed.")
                return

            @run_in_glib_thread
            def update_ui():
                self.connection_info_downloaded.set_text(download)
                self.connection_info_protocol.set_text(f"{GLib.markup_escape_text(protocol)}")
                self.connection_info_protocol.set_use_markup(True)
                self.connection_info_uploaded.set_text(upload)
                self.connection_info_ipv4address.set_text(ipv4)
                self.connection_info_ipv6address.set_text(ipv6)

            update_ui()

        if not self.connection_info_stats:
            self.connection_info_stats = NetworkStats(self.app.nm_manager)

        if not self.connection_info_thread_cancel:
            # Run every second in the background
            self.connection_info_thread_cancel = run_periodically(update_connection_info_callback, 1)

    def on_toggle_connection_info(self, _):
        logger.debug("clicked on connection info")

    def on_profile_row_activated(self, widget: TreeView, row: TreePath, _col: TreeViewColumn) -> None:
        model = widget.get_model()
        setter, profile = model[row][1]
        logger.debug(f"activated profile: {profile!r}")

        @run_in_background_thread("set-profile")
        def set_profile():
            try:
                setter(profile)
            except Exception as e:
                if should_show_error(e):
                    self.show_error_revealer(str(e))
                log_exception(e)

        set_profile()

    def profile_ask_reconnect(self) -> bool:
        gtk_reconnect_id = -10
        gtk_nop_id = -11
        dialog = Gtk.MessageDialog(  # type: ignore
            parent=self,
            type=Gtk.MessageType.QUESTION,  # type: ignore
            title=_("Profile"),
            message_format=_("New profile selected"),
        )
        dialog.add_buttons(  # type: ignore
            _("Reconnect"), gtk_reconnect_id, _("Stay connected"), gtk_nop_id
        )
        dialog.format_secondary_text(_("Do you want to apply the new profile by reconnecting?"))  # type: ignore
        dialog.show()  # type: ignore
        response = dialog.run()  # type: ignore
        dialog.destroy()  # type: ignore

        return response == gtk_reconnect_id

    def on_profile_combo_changed(self, combo):
        tree_iter = combo.get_active_iter()

        if tree_iter is None:
            return

        if self.set_same_profile:
            self.set_same_profile = False
            return

        model = combo.get_model()
        _profile_display, profile = model[tree_iter][:2]
        logger.debug(f"selected combo profile: {profile!r}")

        # Profile is already the current, do nothing
        if profile == self.app.model.current_server.profiles.current:
            return

        # If we are already connected we should ask if we want to reconnect
        if self.common.in_state(State.CONNECTED):
            # Asking for reconnect was not successful
            # Restore the previous profile
            if not self.profile_ask_reconnect():
                self.set_same_profile = True
                active_index, model = self.get_profile_combo_sorted(self.app.model.current_server)
                combo.set_model(model)
                combo.set_active(active_index)
                return

        # Set profile and connect
        self.call_model("set_profile", profile.identifier, True)

    def on_location_row_activated(self, widget, row, _col):
        model = widget.get_model()
        setter, location = model[row][2]
        logger.debug(f"activated location: {location!r}")

        @run_in_background_thread("set-location")
        def set_location():
            try:
                setter(location)
            except Exception as e:
                if should_show_error(e):
                    self.show_error_revealer(str(e))
                log_exception(e)

        set_location()
        self.show_loading_page("Loading location", "The location is being configured")

    def on_acknowledge_error(self, event):
        logger.debug("clicked on acknowledge error")

    def on_renew_session_clicked(self, event):
        logger.debug("clicked on renew session")

        def on_renew(success: bool):
            if success:
                return
            self.update_connection_status(False)
            self.show_error_revealer("failed to renew session")

        self.call_model("renew_session", on_renew)

    def on_reconnect_tcp_clicked(self, event):
        logger.debug("clicked on reconnect TCP")

        def on_reconnected(_: bool):
            logger.debug("done reconnecting with tcp")
            self.reconnect_tcp_button.hide()
            self.reconnect_tcp_text.hide()

        self.call_model("reconnect_tcp", on_reconnected)

    def on_close_window(self, window: "EduVpnGtkWindow", event: Event) -> bool:
        logger.debug("clicked on close window")

        def close():
            self.hide()  # type: ignore
            application = self.get_application()  # type: ignore
            if application:
                application.on_window_closed()  # type: ignore

        if not self.common.in_state(State.CONNECTED) or not self.app.nm_manager.proxy:
            close()
            return True

        quit_proxy = self.app.config.proxy_active_warning
        # We can also have None
        if quit_proxy is False:
            logger.warning("not closing client as you have remembered to not close the client when a proxy is active")
        if quit_proxy is None:
            self.proxy_active_dialog.set_title(f"{self.app.variant.name} - Proxy Warning")
            self.proxy_active_dialog.show()
            _id = self.proxy_active_dialog.run()
            quit_proxy = _id == QUIT_ID
            self.proxy_active_dialog.hide()
            if self.proxy_active_dialog_remember.get_active():
                self.app.config.proxy_active_warning = quit_proxy

        def deactivate_proxy_con(success):
            if not success:
                logger.debug("failed to deactivate proxy connection on quit")
            close()

        if quit_proxy:
            self.call_model("deactivate_connection", deactivate_proxy_con)

        return True

    def on_reopen_window(self):
        logger.debug("on reopen window")
        self.show()
        self.present()
