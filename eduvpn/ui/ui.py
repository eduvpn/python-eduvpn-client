# eduvpngui - The GNU/Linux eduVPN GUI client
#
# Copyright: 2017-2020, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import os
import webbrowser
from gettext import gettext as _
from typing import Type, Optional

import gi

gi.require_version("Gtk", "3.0")  # noqa: E402
gi.require_version("NM", "1.0")  # noqa: E402
from functools import partial

from eduvpn_common.state import State, StateType
from eduvpn_common.error import ErrorLevel, WrappedError
from gi.repository import Gdk, GdkPixbuf, GLib, GObject, Gtk

from eduvpn.nm import nm_available, nm_managed
from eduvpn.server import StatusImage
from eduvpn.settings import FLAG_PREFIX
from eduvpn.i18n import country, retrieve_country_name
from eduvpn.settings import HELP_URL
from eduvpn.utils import (ERROR_STATE, get_prefix, get_ui_state, run_in_main_gtk_thread, run_in_background_thread,
                     run_periodically, ui_transition)
from eduvpn.ui import search
from eduvpn.ui.stats import NetworkStats
from eduvpn.ui.utils import get_validity_text, link_markup, show_error_dialog, show_ui_component, style_tree_view, style_widget
from datetime import datetime
from gi.overrides.Gdk import Event, EventButton
from gi.overrides.Gtk import Box, Builder, Button, TreePath, TreeView, TreeViewColumn
from gi.repository.Gtk import EventBox, SearchEntry, Switch

logger = logging.getLogger(__name__)


UPDATE_EXPIRY_INTERVAL = 1.0  # seconds
UPDATE_RENEW_INTERVAL = 60.0  # seconds

def get_flag_path(country_code: str) -> Optional[str]:
        path = f'{FLAG_PREFIX}{country_code}@1,5x.png'
        if os.path.exists(path):
            return path
        else:
            return None

def get_template_path(filename: str) -> str:
    return os.path.join(get_prefix(), "share/eduvpn/builder", filename)


class EduVpnGtkWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "EduVpnGtkWindow"

    def __new__(cls: Type['EduVpnGtkWindow'], application: Type['EduVpnGtkApplication']) -> "EduVpnGtkWindow":
        builder = Gtk.Builder()
        builder.add_from_file(get_template_path("mainwindow.ui"))  # type: ignore
        window = builder.get_object("eduvpn")  # type: ignore
        window.setup(builder, application)  # type: ignore
        window.set_application(application)  # type: ignore
        return window

    def setup(self, builder: Builder, application: Type['EduVpnGtkApplication']) -> None:  # type: ignore
        self.eduvpn_app = application
        self.app = self.eduvpn_app.app  # type: ignore
        self.common = self.eduvpn_app.common
        handlers = {
            "on_configure_settings": self.on_configure_settings,
            "on_get_help": self.on_get_help,
            "on_go_back": self.on_go_back,
            "on_add_other_server": self.on_add_other_server,
            "on_add_custom_server": self.on_add_custom_server,
            "on_cancel_oauth_setup": self.on_cancel_oauth_setup,
            "on_change_location": self.on_change_location,
            "on_server_row_activated": self.on_server_row_activated,
            "on_server_row_pressed": self.on_server_row_pressed,
            "on_search_changed": self.on_search_changed,
            "on_search_activate": self.on_search_activate,
            "on_switch_connection_state": self.on_switch_connection_state,
            "on_toggle_connection_info": self.on_toggle_connection_info,
            "on_profile_row_activated": self.on_profile_row_activated,
            "on_profile_combo_changed": self.on_profile_combo_changed,
            "on_location_row_activated": self.on_location_row_activated,
            "on_acknowledge_error": self.on_acknowledge_error,
            "on_renew_session_clicked": self.on_renew_session_clicked,
            "on_config_prefer_tcp": self.on_config_prefer_tcp,
            "on_config_nm_system_wide": self.on_config_nm_system_wide,
            "on_close_window": self.on_close_window,
        }
        builder.connect_signals(handlers)

        self.is_selected = False

        self.app_logo = builder.get_object("appLogo")

        self.page_stack = builder.get_object("pageStack")
        self.settings_button = builder.get_object("settingsButton")
        self.back_button_container = builder.get_object("backButtonEventBox")

        self.server_list_container = builder.get_object("serverListContainer")

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
        self.change_location_button = builder.get_object("changeLocationButton")
        self.location_list = builder.get_object("locationTreeView")
        self.profile_list = builder.get_object("profileTreeView")

        self.find_server_page = builder.get_object("findServerPage")
        self.find_server_search_form = builder.get_object("findServerSearchForm")
        self.find_server_search_input = builder.get_object("findServerSearchInput")
        self.find_server_image = builder.get_object("findServerImage")
        self.find_server_label = builder.get_object("findServerLabel")


        self.main_overlay = builder.get_object("mainOverlay")

        # Create a revealer
        self.clipboard = self.create_clipboard()
        self.error_revealer = None
        self.error_revealer_label = None
        self.create_error_revealer()

        self.add_custom_server_button_container = builder.get_object(
            "addCustomServerRow"
        )
        self.add_other_server_button_container = builder.get_object("addOtherServerRow")

        self.connection_page = builder.get_object("connectionPage")
        self.connection_status_image = builder.get_object("connectionStatusImage")
        self.connection_status_label = builder.get_object("connectionStatusLabel")
        self.connection_session_label = builder.get_object("connectionSessionLabel")
        self.connection_switch = builder.get_object("connectionSwitch")
        self.connection_info_expander = builder.get_object("connectionInfoExpander")
        self.connection_info_downloaded = builder.get_object(
            "connectionInfoDownloadedText"
        )
        self.connection_info_uploaded = builder.get_object("connectionInfoUploadedText")
        self.connection_info_ipv4address = builder.get_object(
            "connectionInfoIpv4AddressText"
        )
        self.connection_info_ipv6address = builder.get_object(
            "connectionInfoIpv6AddressText"
        )
        self.connection_info_thread_cancel = None
        self.connection_validity_thread_cancel = None
        self.connection_renew_thread_cancel = None
        self.connection_info_stats = None

        self.server_image = builder.get_object("serverImage")
        self.server_label = builder.get_object("serverLabel")
        self.server_support_label = builder.get_object("supportLabel")

        self.renew_session_button = builder.get_object("renewSessionButton")
        self.select_profile_combo = builder.get_object("selectProfileCombo")
        self.select_profile_text = builder.get_object("selectProfileText")

        self.oauth_page = builder.get_object("openBrowserPage")
        self.oauth_cancel_button = builder.get_object("cancelBrowserButton")

        self.settings_page = builder.get_object('settingsPage')
        self.setting_config_prefer_tcp = builder.get_object('settingConfigPreferTCP')
        self.setting_config_nm_system_wide = builder.get_object('settingConfigNMSystemWide')

        self.loading_page = builder.get_object("loadingPage")
        self.loading_title = builder.get_object("loadingTitle")
        self.loading_message = builder.get_object("loadingMessage")

        self.error_page = builder.get_object("errorPage")
        self.error_text = builder.get_object("errorText")
        self.error_acknowledge_button = builder.get_object("errorAcknowledgeButton")

        self.set_title(self.app.variant.name)  # type: ignore
        self.set_icon_from_file(self.app.variant.icon)  # type: ignore
        if self.app.variant.logo:
            self.app_logo.set_from_file(self.app.variant.logo)
        if self.app.variant.server_image:
            self.find_server_image.set_from_file(self.app.variant.server_image)
        if not self.app.variant.use_predefined_servers:
            self.find_server_label.set_text(_("Server address"))
            self.find_server_search_input.set_placeholder_text(
                _("Enter the server address")
            )

        # Track the currently shown page so we can return to it
        # when the settings page is closed.
        self.current_shown_page = None

        # We track the switch state so we can distinguish
        # the switch being set by the ui from the user toggling it.
        self.connection_switch_state: Optional[bool] = None

    def initialize(self) -> None:
        if not nm_available():
            show_error_dialog(
                self,
                _("Error"),
                _("NetworkManager not available"),
                _(
                    "The application will not be able to configure the network. Please install and set up NetworkManager."
                ),
            )
        elif not nm_managed():
            show_error_dialog(
                self,
                _("Error"),
                _("NetworkManager not managing device"),
                _(
                    "The application will not be able to configure the network. NetworkManager is installed but no device of the primary connection is currently managed by it."
                ),
            )

        @run_in_background_thread('register')
        def register():
            try:
                self.common.register_class_callbacks(self)
                self.enter_deregistered()
                self.common.register(debug=self.eduvpn_app.debug)
                self.exit_deregistered()
                self.app.initialize_network()
            except Exception as e:
                show_error_dialog(self, _("Fatal Error"), _("Fatal error while starting the client"), str(e), True)

        register()

    @run_in_background_thread('call-model')
    def call_model(self, func_name: str, *args):
        func = getattr(self.app.model, func_name, None)
        if func:
            try:
                func(*(args))
            except WrappedError as e:
                if e.level != ErrorLevel.ERR_INFO:
                    self.show_error_revealer(str(e))
            except Exception as e:
                self.show_error_revealer(str(e))
        else:
            raise Exception(f"No such function: {func_name}")

    @run_in_main_gtk_thread
    def enter_deregistered(self):
        self.show_loading_page(
            _("Loading client"),
            _("The client is loading the servers."),
        )

    @run_in_main_gtk_thread
    def exit_deregistered(self):
        self.hide_loading_page()

    @ui_transition(ERROR_STATE, StateType.ENTER)
    def enter_error_state(self, old_state: str, error: str):
        self.show_error_revealer(error)

    @run_in_main_gtk_thread
    def create_clipboard(self):
        return Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

    @run_in_main_gtk_thread
    def create_error_revealer(self):
        # Creat the revealer and set the properties
        self.error_revealer = Gtk.Revealer.new()
        self.error_revealer.set_valign(Gtk.Align.END)
        self.error_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.error_revealer.set_transition_duration(200)
        #self.error_revealer.set_vexpand(False)

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
        style_widget(error_revealer_close_button, "errorRevealerButton", "background-color: transparent; padding: 0px;")

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
        style_widget(error_revealer_clipboard_button, "errorRevealerClipboardButton", "background-color: transparent; padding: 0px;")

        # Create the label
        self.error_revealer_label = Gtk.Label.new("<b>Error occurred</b>: Example error")
        self.error_revealer_label.set_use_markup(True)
        self.error_revealer_label.set_margin_bottom(20)
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
        style_widget(error_revealer_frame, "errorClass", "margin-left: 20px; margin-right: 20px; background-color: #B00020; margin-top: 0px; padding: 0px; color: rgba(255, 255, 255, 1);")
        error_revealer_frame.add(error_revealer_box)
        error_revealer_frame.show()

        # Add the frame to the revealer and show it
        self.error_revealer.add(error_revealer_frame)
        self.error_revealer.show()

        # add the error revealer to the main overlay
        self.main_overlay.add_overlay(self.error_revealer)


    @run_in_main_gtk_thread
    def show_error_revealer(self, error: str) -> None:
        self.error_revealer.set_reveal_child(True)
        self.error_revealer_label.set_text(f"The following error was reported: <i>{GLib.markup_escape_text(error)}</i>.\n See the log file for more information.")
        self.error_revealer_label.set_use_markup(True)

    @run_in_main_gtk_thread
    def copy_error_revealer(self, _button) -> None:
        self.clipboard.set_text(self.error_revealer_label.get_text(), -1)
        self.eduvpn_app.enter_ClipboardError()

    @run_in_main_gtk_thread
    def hide_error_revealer(self, _button) -> None:
        self.error_revealer.set_reveal_child(False)

    # ui functions
    def show_back_button(self, show: bool) -> None:
        show_ui_component(self.back_button_container, show)

    def set_search_text(self, text: str) -> None:
        self.find_server_search_input.set_text(text)

    def show_loading_page(self, title: str, message: str) -> None:
        self.show_page(self.loading_page)
        self.loading_title.set_text(title)
        self.loading_message.set_text(message)

    def hide_loading_page(self) -> None:
        self.hide_page(self.loading_page)

    def set_connection_switch_state(self, state: bool) -> None:
        self.connection_switch_state = state
        self.connection_switch.set_state(state)

    def show_page(self, page: Box) -> None:
        """
        Show a collection of pages.
        """
        self.page_stack.set_visible_child(page)
        self.current_shown_page = page

    def hide_page(self, page: Box) -> None:
        """
        Show a collection of pages.
        """
        self.current_shown_page = None

    def is_on_settings_page(self) -> bool:
        return self.page_stack.get_visible_child() is self.settings_page

    def enter_settings_page(self) -> None:
        assert not self.is_on_settings_page()
        self.setting_config_nm_system_wide.set_state(self.app.config.nm_system_wide)
        self.setting_config_prefer_tcp.set_state(self.app.config.prefer_tcp)
        self.page_stack.set_visible_child(self.settings_page)
        self.show_back_button(True)

    def leave_settings_page(self) -> None:
        assert self.is_on_settings_page()
        self.page_stack.set_visible_child(self.current_shown_page)
        self.show_back_button(False)

    def recreate_profile_combo(self, server_info) -> None:
        # Create a store of profiles
        profile_store = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_PYOBJECT)
        active_profile = 0
        for index, profile in enumerate(server_info.profiles.profiles):
            if profile == server_info.profiles.current:
                active_profile = index
            profile_store.append([str(profile), profile])

        # Create a new combobox
        # We create a new one every time because Gtk has some weird behaviour regarding the width of the combo box
        # When we add items that are large, the combobox resizes to fit the content
        # However, when we add items again that are all smaller (e.g. for a new server), the combo box does not shrink back
        # The only proper way seems to be to recreate the combobox every time
        combo = Gtk.ComboBoxText.new()
        combo.set_model(profile_store)
        combo.set_active(active_profile)
        combo.set_halign(Gtk.Align.CENTER)
        combo.connect("changed", self.on_profile_combo_changed)

        # Get the position of the current combobox in the connection page
        position = self.connection_page.child_get_property(
            self.select_profile_combo, "position"
        )

        # Destroy the combobox and add the new one
        self.select_profile_combo.destroy()
        self.connection_page.pack_start(combo, True, True, 0)
        self.connection_page.reorder_child(combo, position)
        self.select_profile_combo = combo

        self.select_profile_combo.show()
        self.select_profile_text.set_text("Select Profile: ")

    # network state transition callbacks
    def update_connection_server(self, server_info) -> None:
        if not server_info:
            return

        if len(server_info.profiles.profiles) <= 1:
            self.select_profile_text.hide()
            self.select_profile_combo.hide()
        else:
            self.select_profile_text.show()
            self.recreate_profile_combo(server_info)

        if hasattr(server_info, "country_code"):
            self.server_label.set_text(f"{retrieve_country_name(server_info.country_code)}\n(via {server_info.display_name})")
            flag_path = get_flag_path(server_info.country_code)
            if flag_path:
                self.server_image.set_from_file(flag_path)
                self.server_image.show()
            else:
                self.server_image.hide()
        else:
            self.server_label.set_text(server_info.display_name)
            self.server_image.hide()

        if hasattr(server_info, "support_contact") and server_info.support_contact:
            support_text = (
                _("Support:")
                + "\n"
                + "\n".join(map(link_markup, server_info.support_contact))
            )
            self.server_support_label.set_markup(support_text)
            self.server_support_label.show()
        else:
            self.server_support_label.hide()

    # every second
    def update_connection_validity(self, expire_time: datetime) -> None:
        is_expired, expiry_text = get_validity_text(self.app.model.get_expiry(expire_time))
        self.connection_session_label.show()
        self.connection_session_label.set_markup(expiry_text)

        # The connection is expired, show a notification
        if is_expired:
            # Be extra sure the renew button is shown
            self.renew_session_button.show()

            # Stop updating the text
            if self.connection_validity_thread_cancel:
                self.connection_validity_thread_cancel()

            self.eduvpn_app.enter_SessionExpiredState()


    # Show renew button or not
    def update_connection_renew(self) -> None:
        if self.app.model.should_renew_button():
            # Stop polling for updates as we're done toggling the button
            if self.connection_renew_thread_cancel:
                self.connection_renew_thread_cancel()

            # This is the first time that the renew session button will be visible
            # Show a notification that it is pending expiry
            if not self.renew_session_button.is_visible():
                self.eduvpn_app.enter_SessionPendingExpiryState()
            self.renew_session_button.show()
        else:
            self.renew_session_button.hide()

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
    def enter_connecting(self, old_state: str, data):
        self.connection_status_label.set_text(_("Connecting..."))
        self.connection_status_image.set_from_file(StatusImage.CONNECTING.path)
        self.set_connection_switch_state(True)
        # Disable the profile combo box and switch
        self.connection_switch.set_sensitive(False)
        self.select_profile_combo.set_sensitive(False)

    @ui_transition(State.CONNECTING, StateType.LEAVE)
    def exit_connecting(self, old_state: str, data):
        # Re-enable the profile combo box and switch
        self.connection_switch.set_sensitive(True)
        self.select_profile_combo.set_sensitive(True)

    @ui_transition(State.DISCONNECTING, StateType.ENTER)
    def enter_disconnecting(self, old_state: str, data):
        self.connection_status_label.set_text(_("Disconnecting..."))
        self.connection_status_image.set_from_file(StatusImage.CONNECTING.path)
        self.set_connection_switch_state(False)
        # Disable the profile combo box and switch
        self.connection_switch.set_sensitive(False)
        self.select_profile_combo.set_sensitive(False)

    @ui_transition(State.DISCONNECTING, StateType.LEAVE)
    def exit_disconnecting(self, old_state: str, data):
        # Re-enable the profile combo box and switch
        self.connection_switch.set_sensitive(True)
        self.select_profile_combo.set_sensitive(True)

    # interface state transition callbacks

    @ui_transition(State.SEARCH_SERVER, StateType.ENTER)
    def enter_search(self, old_state: str, data):
        servers, is_main = data
        self.show_back_button(not is_main)
        self.set_search_text("")
        self.find_server_search_input.grab_focus()
        search.show_result_components(self, True)
        search.show_search_components(self, True)
        search.update_results(self, servers)
        search.init_server_search(self)

    @ui_transition(State.SEARCH_SERVER, StateType.LEAVE)
    def exit_search(self, new_state: str, data: str):
        self.show_back_button(False)
        search.show_result_components(self, False)
        search.show_search_components(self, False)
        search.exit_server_search(self)

    # TODO: Implement with Go callback
    def exit_ConfigureCustomServer(self, old_state, new_state):
        if not self.app.variant.use_predefined_servers:
            self.add_custom_server_button_container.hide()

    @ui_transition(State.NO_SERVER, StateType.ENTER)
    def enter_MainState(self, old_state: str, servers):
        search.show_result_components(self, True)
        self.add_other_server_button_container.show()
        search.init_server_search(self)
        search.update_results(self, servers)
        self.change_location_button.show()

        # Do not go in a loop by checking old state
        if not servers and old_state != get_ui_state(State.SEARCH_SERVER):
            self.call_model("set_search_server")

    @ui_transition(State.NO_SERVER, StateType.LEAVE)
    def exit_MainState(self, old_state, new_state):
        search.show_result_components(self, False)
        self.add_other_server_button_container.hide()
        search.exit_server_search(self)
        self.change_location_button.hide()

    @ui_transition(State.OAUTH_STARTED, StateType.ENTER)
    def enter_oauth_setup(self, old_state, url):
        self.show_page(self.oauth_page)
        self.oauth_cancel_button.show()

    @ui_transition(State.OAUTH_STARTED, StateType.LEAVE)
    def exit_oauth_setup(self, old_state, data):
        self.hide_page(self.oauth_page)
        self.oauth_cancel_button.hide()

    @ui_transition(State.AUTHORIZED, StateType.ENTER)
    def enter_OAuthRefreshToken(self, new_state, data):
        self.show_loading_page(
            _("Sucessfully authorized"),
            _("You have sucessfully authorized the eduVPN Linux client."),
        )

    @ui_transition(State.AUTHORIZED, StateType.LEAVE)
    def exit_OAuthRefreshToken(self, old_state, data):
        self.hide_loading_page()

    @ui_transition(State.CHOSEN_SERVER, StateType.ENTER)
    def enter_chosenServerInformation(self, new_state, data):
        self.show_loading_page(
            _("Chosen"),
            _("The server has been chosen and is loading."),
        )

    @ui_transition(State.CHOSEN_SERVER, StateType.LEAVE)
    def exit_chosenServerInformation(self, old_state, data):
        self.hide_loading_page()

    @ui_transition(State.LOADING_SERVER, StateType.ENTER)
    def enter_LoadingServerInformation(self, new_state, data):
        self.show_loading_page(
            _("Loading"),
            _("The server details are being loaded."),
        )

    @ui_transition(State.LOADING_SERVER, StateType.LEAVE)
    def exit_LoadingServerInformation(self, old_state, data):
        self.hide_loading_page()

    @ui_transition(State.ASK_PROFILE, StateType.ENTER)
    def enter_ChooseProfile(self, new_state, profiles):
        self.show_page(self.choose_profile_page)
        self.profile_list.show()

        profile_tree_view = self.profile_list
        profiles_list_model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_PYOBJECT)

        if len(profile_tree_view.get_columns()) == 0:
            # Only initialize this tree view once.
            text_cell = Gtk.CellRendererText()
            text_cell.set_property("size-points", 14)
            text_cell.set_property("ypad", 10)

            column = Gtk.TreeViewColumn(None, text_cell, text=0)
            profile_tree_view.append_column(column)

        style_tree_view(self, profile_tree_view)
        profile_tree_view.set_model(profiles_list_model)
        profiles_list_model.clear()
        for profile in profiles.profiles:
            profiles_list_model.append([str(profile), profile])

    @ui_transition(State.ASK_PROFILE, StateType.LEAVE)
    def exit_ChooseProfile(self, old_state, data):
        self.show_back_button(False)
        self.hide_page(self.choose_profile_page)
        self.profile_list.hide()

    @ui_transition(State.ASK_LOCATION, StateType.ENTER)
    def enter_ChooseSecureInternetLocation(self, old_state, locations):
        self.show_back_button(True)
        self.show_page(self.choose_location_page)
        self.location_list.show()

        location_tree_view = self.location_list
        location_list_model = Gtk.ListStore(
            GObject.TYPE_STRING, GdkPixbuf.Pixbuf, GObject.TYPE_PYOBJECT
        )

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

            style_tree_view(self, location_tree_view)
            location_tree_view.set_model(location_list_model)

        location_list_model.clear()
        for location in locations:
            flag_path = get_flag_path(location)
            if flag_path is None:
                logger.warning(
                    f"No flag found for country code {location}"
                )
                flag = None
            else:
                flag = GdkPixbuf.Pixbuf.new_from_file(flag_path)
            location_list_model.append([retrieve_country_name(location), flag, location])

    @ui_transition(State.ASK_LOCATION, StateType.LEAVE)
    def exit_ChooseSecureInternetLocation(self, old_state, new_state):
        self.show_back_button(False)
        self.hide_loading_page()
        self.hide_page(self.choose_location_page)
        self.location_list.hide()

    def enter_ConfiguringConnection(self) -> None:
        self.show_loading_page(
            _("Configuring"),
            _("Your connection is being configured."),
        )

    def exit_ConfiguringConnection(self, old_state: str, data) -> None:
        self.hide_loading_page()

    @ui_transition(State.REQUEST_CONFIG, StateType.ENTER)
    def enter_RequestConfig(self, old_state: str, data):
        if old_state != get_ui_state(State.DISCONNECTED):
            self.enter_ConfiguringConnection()
        else:
            self.enter_connecting(old_state, data)

    @ui_transition(State.REQUEST_CONFIG, StateType.LEAVE)
    def exit_RequestConfig(self, old_state: str, data):
        self.exit_ConfiguringConnection(old_state, data)

    @ui_transition(State.DISCONNECTED, StateType.ENTER)
    def enter_ConnectionStatus(self, old_state: str, server_info):
        self.show_back_button(True)
        self.stop_validity_renew()
        self.stop_connection_info()
        self.show_page(self.connection_page)
        self.update_connection_status(False)
        self.update_connection_server(server_info)

    @ui_transition(State.DISCONNECTED, StateType.LEAVE)
    def exit_ConnectionStatus(self, old_state, new_state):
        self.show_back_button(False)
        self.hide_page(self.connection_page)
        self.pause_connection_info()

    @ui_transition(State.CONNECTED, StateType.ENTER)
    def enter_ConnectedState(self, old_state, server_info):
        self.show_page(self.connection_page)
        self.show_back_button(False)
        is_expanded = self.connection_info_expander.get_expanded()
        if is_expanded:
            self.start_connection_info()
        self.update_connection_status(True)
        self.update_connection_server(server_info)
        self.start_validity_renew(server_info)

    def start_validity_renew(self, server_info) -> None:
        self.connection_validity_thread_cancel = run_periodically(
            run_in_main_gtk_thread(
                partial(self.update_connection_validity, server_info.expire_time)
            ),
            UPDATE_EXPIRY_INTERVAL,
            "update-validity",
        )
        self.connection_renew_thread_cancel = run_periodically(
            run_in_main_gtk_thread(self.update_connection_renew),
            UPDATE_RENEW_INTERVAL,
            "update-renew",
        )

    def stop_validity_renew(self) -> None:
        if self.connection_validity_thread_cancel:
            self.connection_validity_thread_cancel()
            self.connection_validity_thread_cancel = None

        if self.connection_renew_thread_cancel:
            self.connection_renew_thread_cancel()
            self.connection_renew_thread_cancel = None

    # ui callbacks
    def on_configure_settings(self, widget: EventBox, event: EventButton) -> None:
        logger.debug("clicked on configure settings")
        if self.is_on_settings_page():
            self.leave_settings_page()
        else:
            self.enter_settings_page()

    def on_get_help(self, widget, event):
        logger.debug("clicked on get help")
        webbrowser.open(HELP_URL)

    def on_go_back(self, widget: EventBox, event: EventButton) -> None:
        logger.debug("clicked on go back")
        if self.is_on_settings_page():
            self.leave_settings_page()
            return

        self.call_model('go_back')

    def on_add_other_server(self, button: Button) -> None:
        logger.debug("clicked on add other server")

        self.call_model("set_search_server")

    def on_add_custom_server(self, button) -> None:
        logger.debug("clicked on add custom server")
        server = CustomServer(self.app.interface_state.address)
        self.app.interface_transition("connect_to_server", server)

    def on_server_row_activated(self, widget: TreeView, row: TreePath, _col: TreeViewColumn) -> None:
        model = widget.get_model()
        server = model[row][1]
        logger.debug(f"activated server: {server!r}")

        if self.app.model.is_search_server():
            self.call_model("add", server)
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
        dialog.add_buttons(
            _("Remove server"), gtk_remove_id, _("Do nothing"), gtk_nop_id
        )
        dialog.format_secondary_text(_(f"Are you sure you want to remove server {str(server)}?"))  # type: ignore
        dialog.show()  # type: ignore
        response = dialog.run()  # type: ignore
        dialog.destroy()  # type: ignore

        if response == gtk_remove_id:
            logger.debug(f"doing server remove for: {server!r}")
            self.call_model("remove", server)
        else:
            logger.debug(f"cancelled server remove for: {server!r}")

    def server_change_profile(self, server):
        print("Change profile", str(server))

    def on_server_row_pressed(self, widget: TreeView, event: EventButton) -> None:
        # Exit if not a press
        if event.type != Gdk.EventType.BUTTON_PRESS:
            return

        # Not in the main screen
        if not self.app.model.is_no_server():
            return

        # Not a right click
        if event.button != 3:
            return

        (model, tree_iter) = widget.get_selection().get_selected()
        if tree_iter is None:
            return None

        row = model[tree_iter]
        server = row[1]

        cancel_item = Gtk.ImageMenuItem.new_from_stock(stock_id=Gtk.STOCK_CLOSE)
        cancel_item.set_always_show_image(True)
        cancel_item.show()

        remove_item = Gtk.ImageMenuItem.new_from_stock(stock_id=Gtk.STOCK_REMOVE)
        remove_item.connect("activate", lambda _: self.server_ask_remove(server))
        remove_item.set_always_show_image(True)
        remove_item.set_label(_("Remove server"))
        remove_item.show()

        menu = Gtk.Menu()
        menu.append(remove_item)

        menu.append(cancel_item)
        menu.attach_to_widget(widget)
        menu.popup_at_pointer()

    def on_cancel_oauth_setup(self, _):
        logger.debug("clicked on cancel oauth setup")

        self.call_model("cancel_oauth")

    def on_change_location(self, _):
        self.call_model("change_secure_location")

    def on_search_changed(self, _: Optional[SearchEntry]=None) -> None:
        query = self.find_server_search_input.get_text()
        logger.debug(f"entered server search query: {query}")
        if self.app.variant.use_predefined_servers and query.count(".") < 2:
            results = self.app.model.search_predefined(query)
            search.update_results(self, results)
        else:
            # Anything with two periods is interpreted
            # as a custom server address.
            results = self.app.model.search_custom(query)
            search.update_results(self, results)

    def on_search_activate(self, _=None):
        logger.debug("activated server search")
        # TODO

    def on_switch_connection_state(self, _switch: Switch, state: bool) -> bool:
        logger.debug("clicked on switch connection state")

        if state is not self.connection_switch_state:
            self.connection_switch_state = state
            # The user has toggled the connection switch,
            # as opposed to the ui itself setting it.
            if state:
                self.call_model("activate_connection")
            else:
                self.call_model("deactivate_connection")
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
        if not self.app.model.is_connected():
            logger.info("Connection Info: VPN is not active")
            return

        def update_connection_info_callback():
            # Do nothing if we have no stats object
            if not self.connection_info_stats:
                return
            download = self.connection_info_stats.download
            upload = self.connection_info_stats.upload
            ipv4 = self.connection_info_stats.ipv4
            ipv6 = self.connection_info_stats.ipv6
            self.connection_info_downloaded.set_text(download)
            self.connection_info_uploaded.set_text(upload)
            self.connection_info_ipv4address.set_text(ipv4)
            self.connection_info_ipv6address.set_text(ipv6)

        if not self.connection_info_stats:
            self.connection_info_stats = NetworkStats()

        if not self.connection_info_thread_cancel:
            # Run every second in the background
            self.connection_info_thread_cancel = run_periodically(
                update_connection_info_callback, 1
            )

    def on_toggle_connection_info(self, _):
        logger.debug("clicked on connection info")
        was_expanded = self.connection_info_expander.get_expanded()

        if not was_expanded:
            self.start_connection_info()
        else:
            self.pause_connection_info()

    def on_profile_row_activated(self, widget: TreeView, row: TreePath, _col: TreeViewColumn) -> None:
        model = widget.get_model()
        profile = model[row][1]
        logger.debug(f"activated profile: {profile!r}")

        self.call_model("set_profile", profile)

    def profile_ask_reconnect(self) -> bool:
        gtk_reconnect_id = -10
        gtk_nop_id = -11
        dialog = Gtk.MessageDialog(  # type: ignore
            parent=self,
            type=Gtk.MessageType.QUESTION,  # type: ignore
            title=_("Profile"),
            message_format=_("New profile selected"),
        )
        dialog.add_buttons(
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

        model = combo.get_model()
        _profile_display, profile = model[tree_iter][:2]
        logger.debug(f"selected combo profile: {profile!r}")

        # Profile is already the current, do nothing
        if profile == self.app.model.current_server.profiles.current:
            return

        # If we are already connected we should ask if we want to reconnect
        if self.app.model.is_connected():
            # Asking for reconnect was not successful
            # Restore the previous profile
            if not self.profile_ask_reconnect():
                combo.set_active(
                    self.app.model.current_server.profiles.current_index
                )
                return

        # Set profile and connect
        self.call_model("set_profile", profile, True)

    def on_location_row_activated(self, widget, row, _col):
        model = widget.get_model()
        location = model[row][2]
        logger.debug(f"activated location: {location!r}")

        self.call_model("set_secure_location", location)
        self.show_loading_page("Loading location", "The location is being configured")

    def on_acknowledge_error(self, event):
        logger.debug("clicked on acknowledge error")
        self.app.interface_transition("acknowledge_error")

    def on_renew_session_clicked(self, event):
        logger.debug("clicked on renew session")

        self.call_model("renew_session")

    def on_config_prefer_tcp(self, _switch: Switch, state: bool) -> None:
        logger.debug("clicked on setting: 'prefer tcp'")
        self.app.config.prefer_tcp = state

    def on_config_nm_system_wide(self, switch, state: bool):
        logger.debug("clicked on setting: 'nm system wide'")
        self.app.config.nm_system_wide = state

    def on_close_window(self, window: "EduVpnGtkWindow", event: Event) -> bool:
        logger.debug("clicked on close window")
        self.hide()
        application = self.get_application()
        if application:
            application.on_window_closed()
        return True

    def on_reopen_window(self):
        self.app.interface_transition("restart")
        self.show()
        self.present()
