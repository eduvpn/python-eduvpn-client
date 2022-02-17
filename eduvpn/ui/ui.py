# eduvpngui - The GNU/Linux eduVPN GUI client
#
# Copyright: 2017-2020, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from typing import Optional
import os
import webbrowser
import logging
from datetime import datetime
from gettext import gettext as _, ngettext

import gi
gi.require_version('Gtk', '3.0')  # noqa: E402
gi.require_version('NM', '1.0')  # noqa: E402
from gi.repository import Gtk, GObject, GdkPixbuf

from ..settings import HELP_URL
from ..interface import state as interface_state
from .. import network as network_state
from ..server import CustomServer
from ..app import Application
from ..state_machine import (
    ENTER, EXIT, transition_callback, transition_edge_callback,
    transition_level_callback)
from ..session import Validity
from .. import session as session_state
from ..nm import nm_available, nm_managed
from ..utils import (
    get_prefix, run_in_main_gtk_thread, run_periodically, cancel_at_context_end)
from . import search
from .utils import show_ui_component, link_markup, show_error_dialog

logger = logging.getLogger(__name__)


UPDATE_EXIPRY_INTERVAL = 1.  # seconds

RENEWAL_ALLOW_FRACTION = .8


def get_validity_text(validity: Optional[Validity]) -> str:
    if validity is None:
        return _("Valid for <b>unknown</b>")
    expiry = validity.end
    now = datetime.utcnow()
    if expiry <= now:
        return _("This session has expired")
    delta = expiry - now
    days = delta.days
    hours = delta.seconds // 3600
    if days == 0:
        if hours == 0:
            minutes = delta.seconds // 60
            return ngettext("Valid for <b>{0} minute</b>",
                            "Valid for <b>{0} minutes</b>", minutes).format(minutes)
        else:
            return ngettext("Valid for <b>{0} hour</b>",
                            "Valid for <b>{0} hours</b>", hours).format(hours)
    else:
        dstr = ngettext("Valid for <b>{0} day</b>",
                        "Valid for <b>{0} days</b>", days).format(days)
        hstr = ngettext(" and <b>{0} hour</b>",
                        " and <b>{0} hours</b>", hours).format(hours)
        return dstr + hstr


def get_template_path(filename: str) -> str:
    return os.path.join(get_prefix(), 'share/eduvpn/builder', filename)


class EduVpnGtkWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "EduVpnGtkWindow"

    def __new__(cls, application: Application):
        builder = Gtk.Builder()
        builder.add_from_file(get_template_path('mainwindow.ui'))  # type: ignore
        window = builder.get_object('eduvpn')  # type: ignore
        window.setup(builder, application)  # type: ignore
        window.set_application(application)  # type: ignore
        return window

    def setup(self, builder, application: Application):
        self.app = application.app  # type: ignore
        handlers = {
            "on_configure_settings": self.on_configure_settings,
            "on_get_help": self.on_get_help,
            "on_go_back": self.on_go_back,
            "on_add_other_server": self.on_add_other_server,
            "on_add_custom_server": self.on_add_custom_server,
            "on_cancel_oauth_setup": self.on_cancel_oauth_setup,
            "on_select_server": self.on_select_server,
            "on_search_changed": self.on_search_changed,
            "on_search_activate": self.on_search_activate,
            "on_switch_connection_state": self.on_switch_connection_state,
            "on_profile_selection_changed": self.on_profile_selection_changed,
            "on_location_selection_changed": self.on_location_selection_changed,
            "on_acknowledge_error": self.on_acknowledge_error,
            "on_renew_session_clicked": self.on_renew_session_clicked,
            "on_config_force_tcp": self.on_config_force_tcp,
            "on_close_window": self.on_close_window,
        }
        builder.connect_signals(handlers)

        self.app_logo = builder.get_object('appLogo')

        self.page_stack = builder.get_object('pageStack')
        self.settings_button = builder.get_object('settingsButton')
        self.back_button_container = builder.get_object('backButtonEventBox')

        self.server_list_container = builder.get_object('serverListContainer')

        self.institute_list_header = builder.get_object('instituteAccessHeader')
        self.secure_internet_list_header = builder.get_object('secureInternetHeader')
        self.other_server_list_header = builder.get_object('otherServersHeader')

        self.institute_list = builder.get_object('instituteTreeView')
        self.secure_internet_list = builder.get_object('secureInternetTreeView')
        self.other_server_list = builder.get_object('otherServersTreeView')

        self.choose_profile_page = builder.get_object('chooseProfilePage')
        self.choose_location_page = builder.get_object('chooseLocationPage')
        self.location_list = builder.get_object('locationTreeView')
        self.profile_list = builder.get_object('profileTreeView')

        self.find_server_page = builder.get_object('findServerPage')
        self.find_server_search_form = builder.get_object('findServerSearchForm')
        self.find_server_search_input = builder.get_object('findServerSearchInput')
        self.find_server_image = builder.get_object('findServerImage')
        self.find_server_label = builder.get_object('findServerLabel')

        self.add_custom_server_button_container = builder.get_object('addCustomServerRow')
        self.add_other_server_button_container = builder.get_object('addOtherServerRow')

        self.connection_page = builder.get_object('connectionPage')
        self.connection_status_image = builder.get_object('connectionStatusImage')
        self.connection_status_label = builder.get_object('connectionStatusLabel')
        self.connection_session_label = builder.get_object('connectionSessionLabel')
        self.connection_switch = builder.get_object('connectionSwitch')

        self.server_image = builder.get_object('serverImage')
        self.server_label = builder.get_object('serverLabel')
        self.server_support_label = builder.get_object('supportLabel')

        self.renew_session_button = builder.get_object('renewSessionButton')

        self.oauth_page = builder.get_object('openBrowserPage')
        self.oauth_cancel_button = builder.get_object('cancelBrowserButton')

        self.settings_page = builder.get_object('settingsPage')
        self.setting_config_force_tcp = builder.get_object('settingConfigForceTCP')

        self.loading_page = builder.get_object('loadingPage')
        self.loading_title = builder.get_object('loadingTitle')
        self.loading_message = builder.get_object('loadingMessage')

        self.error_page = builder.get_object('errorPage')
        self.error_text = builder.get_object('errorText')
        self.error_acknowledge_button = builder.get_object('errorAcknowledgeButton')

        self.set_title(self.app.variant.name)  # type: ignore
        self.set_icon_from_file(self.app.variant.icon)  # type: ignore
        if self.app.variant.logo:
            self.app_logo.set_from_file(self.app.variant.logo)
        if self.app.variant.server_image:
            self.find_server_image.set_from_file(self.app.variant.server_image)
        if not self.app.variant.use_predefined_servers:
            self.find_server_label.set_text(_("Server address"))
            self.find_server_search_input.set_placeholder_text(_("Enter the server address"))

        # Track the currently shown page so we can return to it
        # when the settings page is closed.
        self.current_shown_page = None

        # We track the switch state so we can distinguish
        # the switch being set by the ui from the user toggling it.
        self.connection_switch_state: Optional[bool] = None

    def initialize(self):
        self.app.connect_state_transition_callbacks(self)

        if not nm_available():
            show_error_dialog(
                self,
                name=_("Error"),
                title=_("NetworkManager not available"),
                message=_("The application will not be able to configure the network. Please install and set up NetworkManager."))
        elif not nm_managed():
            show_error_dialog(
                self,
                name=_("Error"),
                title=_("NetworkManager not managing device"),
                message=_("The application will not be able to configure the network. NetworkManager is installed but no device of the primary connection is currently managed by it."))

    # ui functions

    def show_back_button(self, show: bool):
        show_ui_component(self.back_button_container, show)

    def set_search_text(self, text: str):
        self.find_server_search_input.set_text(text)

    def show_loading_page(self, title: str, message: str):
        self.show_page(self.loading_page)
        self.loading_title.set_text(title)
        self.loading_message.set_text(message)

    def hide_loading_page(self):
        self.hide_page(self.loading_page)

    def set_connection_switch_state(self, state: bool):
        self.connection_switch_state = state
        self.connection_switch.set_state(state)

    def show_page(self, page):
        """
        Show a collection of pages.
        """
        self.page_stack.set_visible_child(page)
        self.current_shown_page = page

    def hide_page(self, page):
        """
        Show a collection of pages.
        """
        self.current_shown_page = None

    def is_on_settings_page(self) -> bool:
        return self.page_stack.get_visible_child() is self.settings_page

    def enter_settings_page(self):
        assert not self.is_on_settings_page()
        self.setting_config_force_tcp.set_state(self.app.config.force_tcp)
        self.page_stack.set_visible_child(self.settings_page)
        self.show_back_button(True)

    def leave_settings_page(self):
        assert self.is_on_settings_page()
        self.page_stack.set_visible_child(self.current_shown_page)
        self.show_back_button(self.app.interface_state.has_transition('go_back'))

    # network state transition callbacks

    @transition_callback(network_state.NetworkState)
    def default_network_transition_callback(self, old_state, new_state):
        if isinstance(self.app.interface_state, interface_state.ConnectionStatus):
            self.update_connection_status()

    def update_connection_server(self):
        if isinstance(self.app.session_state,
                      (session_state.InitialSessionState,
                       session_state.NoSessionState)):
            self.server_label.set_text('')
            self.server_image.hide()
            self.server_support_label.hide()
            return
        else:
            server = self.app.session_state.server

        self.server_label.set_text(str(server))

        server_image_path = getattr(server, 'image_path', None)
        if server_image_path:
            self.server_image.set_from_file(server_image_path)
            self.server_image.show()
        else:
            self.server_image.hide()

        if getattr(server, 'support_contact', []):
            support_text = _("Support:") + "\n" + "\n".join(map(link_markup, server.support_contact))
            self.server_support_label.set_markup(support_text)
            self.server_support_label.show()
        else:
            self.server_support_label.hide()

    def update_connection_validity(self):
        if isinstance(self.app.session_state,
                      (session_state.InitialSessionState,
                       session_state.NoSessionState)):
            self.connection_session_label.hide()
        else:
            expiry_text = get_validity_text(self.app.session_state.validity)
            self.connection_session_label.show()
            self.connection_session_label.set_markup(expiry_text)

    def update_connection_status(self):
        self.connection_status_label.set_text(self.app.network_state.status_label)
        self.connection_status_image.set_from_file(self.app.network_state.status_image.path)

        self.update_connection_validity()

        assert not (self.app.network_state.has_transition('reconnect') and self.app.network_state.has_transition('disconnect'))
        if self.app.network_state.has_transition('reconnect'):
            if self.app.session_state.is_active:
                self.connection_switch.show()
                self.set_connection_switch_state(False)
            else:
                self.connection_switch.hide()
        elif self.app.network_state.has_transition('disconnect'):
            self.connection_switch.show()
            self.set_connection_switch_state(True)
        else:
            self.connection_switch.hide()

        if self.app.session_state.has_transition('renew'):
            if isinstance(self.app.session_state, session_state.SessionExpiredState) and not isinstance(self.app.network_state, network_state.DisconnectedState):
                # The user needs to disconnect first.
                self.renew_session_button.hide()
            else:
                self.renew_session_button.show()
        else:
            self.renew_session_button.hide()

    # session state transition callbacks

    @transition_callback(session_state.SessionState)
    def default_session_transition_callback(self, old_state, new_state):
        if isinstance(self.app.interface_state, interface_state.ConnectionStatus):
            self.update_connection_status()

    # interface state transition callbacks

    @transition_callback(interface_state.InterfaceState)
    def default_interface_transition_callback(self, old_state, new_state):
        # Only show the 'go back' button if
        # the corresponding transition is available.
        self.show_back_button(new_state.has_transition('go_back'))

    @transition_edge_callback(ENTER, interface_state.configure_server_states)
    def enter_search(self, old_state, new_state):
        if not isinstance(old_state, interface_state.configure_server_states):
            self.find_server_search_input.grab_focus()
            search.show_result_components(self, True)
            search.show_search_components(self, True)
            search.init_server_search(self)
            search.connect_selection_handlers(self, self.on_select_server)

    @transition_edge_callback(EXIT, interface_state.configure_server_states)
    def exit_search(self, old_state, new_state):
        if not isinstance(new_state, interface_state.configure_server_states):
            search.show_result_components(self, False)
            search.show_search_components(self, False)
            search.exit_server_search(self)
            search.disconnect_selection_handlers(self, self.on_select_server)
            self.set_search_text('')

    @transition_edge_callback(
        ENTER, interface_state.PendingConfigurePredefinedServer)
    def enter_PendingConfigurePredefinedServer(self, old_state, new_state):
        search.update_results(self, [])
        if not isinstance(old_state, interface_state.configure_server_states):
            self.set_search_text(new_state.search_query)

    @transition_edge_callback(ENTER, interface_state.ConfigurePredefinedServer)
    def enter_ConfigurePredefinedServer(self, old_state, new_state):
        search.update_results(self, new_state.results)
        if not isinstance(old_state, interface_state.configure_server_states):
            self.set_search_text(new_state.search_query)

    @transition_edge_callback(ENTER, interface_state.ConfigureCustomServer)
    def enter_ConfigureCustomServer(self, old_state, new_state):
        if self.app.variant.use_predefined_servers:
            search.update_results(self, [CustomServer(new_state.address)])
            if not isinstance(old_state, interface_state.configure_server_states):
                self.set_search_text(new_state.address)
        else:
            entered_address = len(new_state.address) > 0
            show_ui_component(self.add_custom_server_button_container, entered_address)

    @transition_edge_callback(EXIT, interface_state.ConfigureCustomServer)
    def exit_ConfigureCustomServer(self, old_state, new_state):
        if not self.app.variant.use_predefined_servers:
            self.add_custom_server_button_container.hide()

    @transition_edge_callback(ENTER, interface_state.MainState)
    def enter_MainState(self, old_state, new_state):
        search.show_result_components(self, True)
        self.add_other_server_button_container.show()
        search.update_results(self, new_state.servers)
        search.init_server_search(self)
        search.connect_selection_handlers(self, self.on_select_server)

    @transition_edge_callback(EXIT, interface_state.MainState)
    def exit_MainState(self, old_state, new_state):
        search.show_result_components(self, False)
        self.add_other_server_button_container.hide()
        search.exit_server_search(self)
        search.disconnect_selection_handlers(self, self.on_select_server)

    @transition_edge_callback(ENTER, interface_state.OAuthSetupPending)
    @transition_edge_callback(ENTER, interface_state.OAuthSetup)
    def enter_oauth_setup(self, old_state, new_state):
        self.show_page(self.oauth_page)
        in_setup_state = isinstance(new_state, interface_state.OAuthSetup)
        show_ui_component(self.oauth_cancel_button, in_setup_state)

    @transition_edge_callback(EXIT, interface_state.OAuthSetupPending)
    @transition_edge_callback(EXIT, interface_state.OAuthSetup)
    def exit_oauth_setup(self, old_state, new_state):
        self.hide_page(self.oauth_page)
        self.oauth_cancel_button.hide()

    @transition_edge_callback(ENTER, interface_state.OAuthRefreshToken)
    def enter_OAuthRefreshToken(self, old_state, new_state):
        self.show_loading_page(
            _("Finishing Authorization"),
            _("The authorization token is being finished."),
        )

    @transition_edge_callback(EXIT, interface_state.OAuthRefreshToken)
    def exit_OAuthRefreshToken(self, old_state, new_state):
        self.hide_loading_page()

    @transition_edge_callback(ENTER, interface_state.LoadingServerInformation)
    def enter_LoadingServerInformation(self, old_state, new_state):
        self.show_loading_page(
            _("Loading"),
            _("The server details are being loaded."),
        )

    @transition_edge_callback(EXIT, interface_state.LoadingServerInformation)
    def exit_LoadingServerInformation(self, old_state, new_state):
        self.hide_loading_page()

    @transition_edge_callback(ENTER, interface_state.ChooseProfile)
    def enter_ChooseProfile(self, old_state, new_state):
        self.show_page(self.choose_profile_page)
        self.profile_list.show()

        profile_tree_view = self.profile_list
        profiles_list_model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_PYOBJECT)

        if len(profile_tree_view.get_columns()) == 0:
            # Only initialize this tree view once.
            text_cell = Gtk.CellRendererText()
            text_cell.set_property("size-points", 14)

            column = Gtk.TreeViewColumn(None, text_cell, text=0)
            profile_tree_view.append_column(column)

            profile_tree_view.set_model(profiles_list_model)

        profiles_list_model.clear()
        for profile in new_state.profiles:
            profiles_list_model.append([str(profile), profile])

    @transition_edge_callback(EXIT, interface_state.ChooseProfile)
    def exit_ChooseProfile(self, old_state, new_state):
        self.hide_page(self.choose_profile_page)
        self.profile_list.hide()

    @transition_edge_callback(ENTER, interface_state.ChooseSecureInternetLocation)
    def enter_ChooseSecureInternetLocation(self, old_state, new_state):
        self.show_page(self.choose_location_page)
        self.location_list.show()

        location_tree_view = self.location_list
        location_list_model = Gtk.ListStore(GObject.TYPE_STRING, GdkPixbuf.Pixbuf, GObject.TYPE_PYOBJECT)

        if len(location_tree_view.get_columns()) == 0:
            # Only initialize this tree view once.
            text_cell = Gtk.CellRendererText()
            text_cell.set_property("size-points", 14)

            renderer_pixbuf = Gtk.CellRendererPixbuf()
            column = Gtk.TreeViewColumn("Image", renderer_pixbuf, pixbuf=1)
            location_tree_view.append_column(column)

            column = Gtk.TreeViewColumn(None, text_cell, text=0)
            location_tree_view.append_column(column)

            location_tree_view.set_model(location_list_model)

        location_list_model.clear()
        for location in new_state.locations:
            if location.flag_path is None:
                logger.warning(f"No flag found for country code {location.country_code}")
                flag = None
            else:
                flag = GdkPixbuf.Pixbuf.new_from_file(location.flag_path)
            location_list_model.append([location.country_name, flag, location])

    @transition_edge_callback(EXIT, interface_state.ChooseSecureInternetLocation)
    def exit_ChooseSecureInternetLocation(self, old_state, new_state):
        self.hide_page(self.choose_location_page)
        self.location_list.hide()

    @transition_edge_callback(ENTER, interface_state.ConfiguringConnection)
    def enter_ConfiguringConnection(self, old_state, new_state):
        self.show_loading_page(
            _("Configuring"),
            _("Your connection is being configured."),
        )

    @transition_edge_callback(EXIT, interface_state.ConfiguringConnection)
    def exit_ConfiguringConnection(self, old_state, new_state):
        self.hide_loading_page()

    @transition_edge_callback(ENTER, interface_state.ConnectionStatus)
    def enter_ConnectionStatus(self, old_state, new_state):
        self.show_page(self.connection_page)
        self.update_connection_server()
        self.update_connection_status()

    @transition_edge_callback(EXIT, interface_state.ConnectionStatus)
    def exit_ConnectionStatus(self, old_state, new_state):
        self.hide_page(self.connection_page)

    @transition_level_callback(interface_state.ConnectionStatus)
    def context_ConnectionStatus(self, state):
        return cancel_at_context_end(run_periodically(
            run_in_main_gtk_thread(self.update_connection_validity),
            UPDATE_EXIPRY_INTERVAL,
            'update-validity',
        ))

    @transition_edge_callback(ENTER, interface_state.ErrorState)
    def enter_ErrorState(self, old_state, new_state):
        self.show_page(self.error_page)
        self.error_text.set_text(new_state.message)
        has_next_transition = new_state.next_transition is not None
        show_ui_component(self.error_acknowledge_button, has_next_transition)

    @transition_edge_callback(EXIT, interface_state.ErrorState)
    def exit_ErrorState(self, old_state, new_state):
        self.hide_page(self.error_page)

    # ui callbacks

    def on_configure_settings(self, widget, event):
        logger.debug("clicked on configure settings")
        if self.is_on_settings_page():
            self.leave_settings_page()
        else:
            self.enter_settings_page()

    def on_get_help(self, widget, event):
        logger.debug("clicked on get help")
        webbrowser.open(HELP_URL)

    def on_go_back(self, widget, event):
        logger.debug("clicked on go back")
        if self.is_on_settings_page():
            self.leave_settings_page()
        else:
            self.app.interface_transition('go_back')

    def on_add_other_server(self, button) -> None:
        logger.debug("clicked on add other server")
        self.app.interface_transition('configure_new_server')

    def on_add_custom_server(self, button) -> None:
        logger.debug("clicked on add custom server")
        server = CustomServer(self.app.interface_state.address)
        self.app.interface_transition('connect_to_server', server)

    def on_select_server(self, selection):
        logger.debug("selected server search result")
        (model, tree_iter) = selection.get_selected()
        selection.unselect_all()
        if tree_iter is None:
            logger.info("selection empty")
        else:
            row = model[tree_iter]
            server = row[1]
            logger.debug(f"selected server: {server!r}")
            self.app.interface_transition('connect_to_server', server)

    def on_cancel_oauth_setup(self, _):
        logger.debug("clicked on cancel oauth setup")
        self.app.interface_transition('oauth_setup_cancel')

    def on_search_changed(self, _=None):
        query = self.find_server_search_input.get_text()
        logger.debug(f"entered server search query: {query}")
        if self.app.variant.use_predefined_servers and query.count('.') < 2:
            self.app.interface_transition(
                'enter_search_query', search_query=query)
        else:
            # Anything with two periods is interpreted
            # as a custom server address.
            self.app.interface_transition(
                'enter_custom_address', address=query)

    def on_search_activate(self, _=None):
        logger.debug("activated server search")
        # TODO

    def on_switch_connection_state(self, switch, state):
        logger.debug("clicked on switch connection state")
        if state is not self.connection_switch_state:
            self.connection_switch_state = state
            # The user has toggled the connection switch,
            # as opposed to the ui itself setting it.
            if state:
                self.app.interface_transition('activate_connection')
            else:
                self.app.interface_transition('deactivate_connection')
        return True

    def on_profile_selection_changed(self, selection):
        logger.debug("selected profile")
        (model, tree_iter) = selection.get_selected()
        selection.unselect_all()
        if tree_iter is None:
            logger.debug("selection empty")
        else:
            row = model[tree_iter]
            profile = row[1]
            logger.debug(f"selected profile: {profile!r}")
            self.app.interface_transition('select_profile', profile)

    def on_location_selection_changed(self, selection):
        logger.debug("selected location")
        (model, tree_iter) = selection.get_selected()
        selection.unselect_all()
        if tree_iter is None:
            logger.debug("selection empty")
        else:
            row = model[tree_iter]
            location = row[2]
            logger.debug(f"selected location: {location!r}")
            self.app.interface_transition('select_secure_internet_location', location)

    def on_acknowledge_error(self, event):
        logger.debug("clicked on acknowledge error")
        self.app.interface_transition('acknowledge_error')

    def on_renew_session_clicked(self, event):
        logger.debug("clicked on renew session")
        self.app.session_transition('renew')

    def on_config_force_tcp(self, switch, state: bool):
        logger.debug("clicked on setting: 'force tcp'")
        self.app.config.force_tcp = state

    def on_close_window(self, window, event):
        logger.debug("clicked on close window")
        self.hide()
        self.get_application().on_window_closed()
        return True

    def on_reopen_window(self):
        self.app.interface_transition('restart')
        self.show()
        self.present()
