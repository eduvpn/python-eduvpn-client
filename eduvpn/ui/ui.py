# eduvpngui - The GNU/Linux eduVPN GUI client
#
# Copyright: 2017-2020, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from typing import Any, Optional
import os
import webbrowser
import logging
from datetime import datetime

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
    ENTER, EXIT, transition_callback, transition_edge_callback)
from ..crypto import Validity
from ..utils import get_prefix, run_in_main_gtk_thread, run_periodically
from ..i18n import init as i18n_init, f as i18n_f
from . import search
from .utils import show_ui_component, link_markup

logger = logging.getLogger(__name__)

builder_files = ['mainwindow.ui']

variable_objects = [
    'backButton',
    # 'backButtonEventBox',
    'findYourInstitutePage',
    'instituteTreeView',
    'secureInternetTreeView',
    'otherServersTreeView',
    'findYourInstituteSpacer',
    'findYourInstituteImage',
    'findYourInstituteLabel',
    'addOtherServerRow',
    'addOtherServerButton',
    'findYourInstituteScrolledWindow',
    'instituteAccessHeader',
    'secureInternetHeader',
    'otherServersHeader',
    'findYourInstituteSearch',
    'chooseProfilePage',
    'profileTreeView',
    'chooseLocationPage',
    'locationTreeView',
    'openBrowserPage',
    'connectionPage',
    'serverLabel',
    'serverImage',
    'supportLabel',
    'connectionStatusImage',
    'connectionStatusLabel',
    'connectionSubStatus',
    'profilesSubPage',
    'currentConnectionSubPage',
    'connectionSubPage',
    'connectionInfoTopRow',
    'connectionInfoGrid',
    'durationValueLabel',
    'downloadedValueLabel',
    'uploadedValueLabel',
    'ipv4ValueLabel',
    'ipv6ValueLabel',
    'connectionInfoBottomRow',
    'connectionSwitch',
    'settingsPage',
    'messagePage',
    'messageLabel',
    'messageText',
    'messageButton',
]


UPDATE_EXIPRY_INTERVAL = 1.  # seconds

RENEWAL_ALLOW_FRACTION = .8


def get_validity_text(validity: Optional[Validity]):
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
            return i18n_f(_("Valid for <b>{minutes:minute|minutes}</b>"))
        else:
            return i18n_f(_("Valid for <b>{hours:hour|hours}</b>"))
    else:
        return i18n_f(_("Valid for <b>{days:day|days}</b> and <b>{hours:hour|hours}</b>"))


def allow_certificate_renewal(validity: Optional[Validity]):
    if validity is None:
        return True
    return datetime.utcnow() >= validity.fraction(RENEWAL_ALLOW_FRACTION)


class EduVpnGui:
    def __init__(self, lets_connect: bool):
        """
        Initialize all data structures needed in the GUI
        """
        self.lets_connect = lets_connect

        self.builder: Any = Gtk.Builder()

        prefix = get_prefix()
        try:
            self.builder.set_translation_domain(i18n_init(lets_connect, prefix))
            logger.info(u"i18n successfully initialized")
        except Exception as e:
            logger.error(f"i18n initialization failed: {e}")

        for b in builder_files:
            p = os.path.join(prefix, 'share/eduvpn/builder', b)
            if not os.access(p, os.R_OK):
                logger.error(f"Can't find builder file {p}!")
                raise Exception
            self.builder.add_from_file(p)

        handlers = {
            "delete_window": Gtk.main_quit,
            "on_settings_button_released": self.on_settings_button_released,
            "on_help_button_released": self.on_help_button_released,
            "on_back_button_released": self.on_back_button_released,
            "on_search_changed": self.on_search_changed,
            "on_activate_changed": self.on_activate_changed,
            "on_add_other_server_button_clicked":
                self.on_add_other_server_button_clicked,
            "on_cancel_browser_button_clicked":
                self.on_cancel_oauth_setup_button_clicked,
            "on_connection_switch_state_set":
                self.on_connection_switch_state_set,
            "on_renew_session_clicked":
                self.on_renew_session_clicked,
        }
        self.builder.connect_signals(handlers)

        # Hide all objects that are visible on only some pages.
        for name in variable_objects:
            self.show_component(name, False)

        self.app = Application(run_in_main_gtk_thread)

        # TODO implement settings page (issue #334)
        self.show_component('settingsButton', False)

    def run(self):
        logger.info("starting ui")
        self.show_component('applicationWindow', True)
        self.app.connect_state_transition_callbacks(self)
        self.app.initialize()

    # ui functions

    def show_component(self, component_id: str, show: bool):
        show_ui_component(self.builder, component_id, show)

    def set_text(self, component_id: str, text: str):
        component = self.builder.get_object(component_id)
        component.set_text(text)

    def set_markup_text(self, component_id: str, text: str):
        component = self.builder.get_object(component_id)
        component.set_markup(text)

    def show_back_button(self, show: bool):
        self.show_component('backButton', show)
        self.show_component('backButtonEventBox', show)

    def set_search_text(self, text: str):
        self.set_text('findYourInstituteSearch', text)

    def show_message_page(self, title: str, message: str):
        self.show_component('loadingPage', True)
        self.show_component('loadingSpacer', True)
        self.show_component('loadingTitle', True)
        self.show_component('loadingMessage', True)
        self.show_component('loadingSpinner', True)
        self.set_text('loadingTitle', title)
        self.set_text('loadingMessage', message)

    def hide_message_page(self):
        self.show_component('loadingPage', False)

    # network state transition callbacks

    @transition_callback(network_state.NetworkState)
    def default_network_transition_callback(self, old_state, new_state):
        if isinstance(self.app.interface_state, interface_state.ConnectionStatus):
            self.update_connection_status()

    def update_connection_server(self):
        server = self.app.interface_state.server
        self.show_component('serverLabel', True)
        self.set_text('serverLabel', str(server))

        server_image_component = self.builder.get_object('serverImage')
        server_image_path = getattr(server, 'image_path', None)
        if server_image_path:
            server_image_component.set_from_file(server_image_path)
            server_image_component.show()
        else:
            server_image_component.hide()

        if getattr(server, 'support_contact', []):
            support_text = _("Support:") + "\n" + "\n".join(map(link_markup, server.support_contact))
            self.set_markup_text('supportLabel', support_text)
            self.show_component('supportLabel', True)
        else:
            self.show_component('supportLabel', False)

    def update_connection_validity(self):
        expiry_text = get_validity_text(self.app.interface_state.validity)
        self.set_markup_text('connectionSubStatus', expiry_text)

        if (hasattr(self.app.network_state, 'renew_certificate') and (
                isinstance(self.app.network_state, network_state.CertificateExpiredState) or (
                allow_certificate_renewal(self.app.interface_state.validity)))):
            self.show_component('currentConnectionSubPage', True)
            self.show_component('renewSessionButton', True)
        else:
            self.show_component('renewSessionButton', False)

    def update_connection_status(self):
        self.set_text('connectionStatusLabel', _(self.app.network_state.status_label))
        self.builder.get_object('connectionStatusImage').set_from_file(self.app.network_state.status_image.path)

        self.update_connection_validity()

        assert not (hasattr(self.app.network_state, 'reconnect') and hasattr(self.app.network_state, 'disconnect'))
        connection_switch = self.builder.get_object('connectionSwitch')
        if hasattr(self.app.network_state, 'reconnect'):
            self.show_component('currentConnectionSubPage', True)
            connection_switch.show()
            connection_switch.set_state(False)
        elif hasattr(self.app.network_state, 'disconnect'):
            self.show_component('currentConnectionSubPage', True)
            connection_switch.show()
            connection_switch.set_state(True)
        else:
            self.show_component('currentConnectionSubPage', False)
            connection_switch.hide()

    # interface state transition callbacks

    @transition_callback(interface_state.InterfaceState)
    def default_interface_transition_callback(self, old_state, new_state):
        # Only show the 'go back' button if
        # the corresponding transition is available.
        self.show_back_button(new_state.has_transition('go_back'))

    @transition_edge_callback(ENTER, interface_state.ConfigureSettings)
    def enter_ConfigureSettings(self, old_state, new_state):
        self.show_component('settingsPage', True)

    @transition_edge_callback(EXIT, interface_state.ConfigureSettings)
    def exit_ConfigureSettings(self, old_state, new_state):
        self.show_component('settingsPage', False)

    @transition_edge_callback(ENTER, interface_state.configure_server_states)
    def enter_search(self, old_state, new_state):
        if not isinstance(old_state, interface_state.configure_server_states):
            self.builder.get_object('findYourInstituteSearch').grab_focus()
            search.show_result_components(self.builder, True)
            search.show_search_components(self.builder, True)
            search.init_server_search(self.builder)
            search.connect_selection_handlers(
                self.builder, self.on_select_server)

    @transition_edge_callback(EXIT, interface_state.configure_server_states)
    def exit_search(self, old_state, new_state):
        if not isinstance(new_state, interface_state.configure_server_states):
            search.show_result_components(self.builder, False)
            search.show_search_components(self.builder, False)
            search.exit_server_search(self.builder)
            search.disconnect_selection_handlers(
                self.builder, self.on_select_server)
            self.set_search_text('')

    @transition_edge_callback(
        ENTER, interface_state.PendingConfigurePredefinedServer)
    def enter_PendingConfigurePredefinedServer(self, old_state, new_state):
        search.update_results(self.builder, [])
        if not isinstance(old_state, interface_state.configure_server_states):
            self.set_search_text(new_state.search_query)

    @transition_edge_callback(ENTER, interface_state.ConfigurePredefinedServer)
    def enter_ConfigurePredefinedServer(self, old_state, new_state):
        search.update_results(self.builder, new_state.results)
        if not isinstance(old_state, interface_state.configure_server_states):
            self.set_search_text(new_state.search_query)

    @transition_edge_callback(ENTER, interface_state.ConfigureCustomServer)
    def enter_ConfigureCustomServer(self, old_state, new_state):
        search.update_results(self.builder, [CustomServer(new_state.address)])
        if not isinstance(old_state, interface_state.configure_server_states):
            self.set_search_text(new_state.address)

    @transition_edge_callback(ENTER, interface_state.MainState)
    def enter_MainState(self, old_state, new_state):
        search.show_result_components(self.builder, True)
        self.show_component('addOtherServerRow', True)
        self.show_component('addOtherServerButton', True)
        search.update_results(self.builder, new_state.servers)
        search.init_server_search(self.builder)
        search.connect_selection_handlers(
            self.builder, self.on_select_server)

    @transition_edge_callback(EXIT, interface_state.MainState)
    def exit_MainState(self, old_state, new_state):
        search.show_result_components(self.builder, False)
        self.show_component('addOtherServerRow', False)
        self.show_component('addOtherServerButton', False)
        search.exit_server_search(self.builder)
        search.disconnect_selection_handlers(
            self.builder, self.on_select_server)

    @transition_edge_callback(ENTER, interface_state.OAuthSetupPending)
    @transition_edge_callback(ENTER, interface_state.OAuthSetup)
    def enter_oauth_setup(self, old_state, new_state):
        self.show_component('openBrowserPage', True)
        self.show_component('cancelBrowserButton',
                            isinstance(new_state, interface_state.OAuthSetup))

    @transition_edge_callback(EXIT, interface_state.OAuthSetupPending)
    @transition_edge_callback(EXIT, interface_state.OAuthSetup)
    def exit_oauth_setup(self, old_state, new_state):
        self.show_component('openBrowserPage', False)
        self.show_component('cancelBrowserButton', False)

    @transition_edge_callback(ENTER, interface_state.OAuthRefreshToken)
    def enter_OAuthRefreshToken(self, old_state, new_state):
        self.show_message_page(
            _("Finishing Authorization"),
            _("The authorization token is being finished."),
        )

    @transition_edge_callback(EXIT, interface_state.OAuthRefreshToken)
    def exit_OAuthRefreshToken(self, old_state, new_state):
        self.hide_message_page()

    @transition_edge_callback(ENTER, interface_state.LoadingServerInformation)
    def enter_LoadingServerInformation(self, old_state, new_state):
        self.show_message_page(
            _("Loading"),
            _("The server details are being loaded."),
        )

    @transition_edge_callback(EXIT, interface_state.LoadingServerInformation)
    def exit_LoadingServerInformation(self, old_state, new_state):
        self.hide_message_page()

    @transition_edge_callback(ENTER, interface_state.ChooseProfile)
    def enter_ChooseProfile(self, old_state, new_state):
        self.show_component('chooseProfilePage', True)
        self.show_component('profileTreeView', True)

        profile_tree_view = self.builder.get_object('profileTreeView')
        profiles_list_model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_PYOBJECT)

        if len(profile_tree_view.get_columns()) == 0:
            # Only initialize this tree view once.
            text_cell = Gtk.CellRendererText()
            text_cell.set_property("size-points", 14)

            column = Gtk.TreeViewColumn(None, text_cell, text=0)
            profile_tree_view.append_column(column)

            profile_tree_view.set_model(profiles_list_model)

        selection = profile_tree_view.get_selection()
        selection.connect("changed", self.on_profile_selection_changed)

        profiles_list_model.clear()
        for profile in new_state.profiles:
            profiles_list_model.append([str(profile), profile])

    @transition_edge_callback(EXIT, interface_state.ChooseProfile)
    def exit_ChooseProfile(self, old_state, new_state):
        self.show_component('chooseProfilePage', False)
        self.show_component('profileTreeView', False)

        profile_tree_view = self.builder.get_object('profileTreeView')
        selection = profile_tree_view.get_selection()
        selection.disconnect_by_func(self.on_profile_selection_changed)

    @transition_edge_callback(ENTER, interface_state.ChooseSecureInternetLocation)
    def enter_ChooseSecureInternetLocation(self, old_state, new_state):
        self.show_component('chooseLocationPage', True)
        self.show_component('locationTreeView', True)

        location_tree_view = self.builder.get_object('locationTreeView')
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

        selection = location_tree_view.get_selection()
        selection.connect("changed", self.on_location_selection_changed)

        location_list_model.clear()
        for location in new_state.locations:
            if location.flag_path is None:
                continue  # TODO
            else:
                flag = GdkPixbuf.Pixbuf.new_from_file(location.flag_path)
            location_list_model.append([location.country_name, flag, location])

    @transition_edge_callback(EXIT, interface_state.ChooseSecureInternetLocation)
    def exit_ChooseSecureInternetLocation(self, old_state, new_state):
        self.show_component('chooseLocationPage', False)
        self.show_component('locationTreeView', False)

        location_tree_view = self.builder.get_object('locationTreeView')
        selection = location_tree_view.get_selection()
        selection.disconnect_by_func(self.on_location_selection_changed)

    @transition_edge_callback(ENTER, interface_state.ConfiguringConnection)
    def enter_ConfiguringConnection(self, old_state, new_state):
        self.show_message_page(
            _("Configuring"),
            _("Your connection is being configured."),
        )

    @transition_edge_callback(EXIT, interface_state.ConfiguringConnection)
    def exit_ConfiguringConnection(self, old_state, new_state):
        self.hide_message_page()

    @transition_edge_callback(ENTER, interface_state.ConnectionStatus)
    def enter_ConnectionStatus(self, old_state, new_state):
        self.show_component('connectionPage', True)
        self.show_component('serverLabel', True)
        self.show_component('connectionStatusImage', True)
        self.show_component('connectionStatusLabel', True)
        self.show_component('connectionSubStatus', True)

        self.update_connection_server()
        self.update_connection_status()

        if hasattr(self, '_cancel_validity_updates'):
            # Cancel any previous threads, as they might have been cancelled
            # and there shouln't be multiple threads running.
            self._cancel_validity_updates()

        def update_connection_validity():
            # This function runs in a background thread.
            state = self.app.interface_state
            if not isinstance(state, interface_state.ConnectionStatus):
                # cancel this thread
                return False
            run_in_main_gtk_thread(self.update_connection_validity)()
            if datetime.utcnow() < state.validity.end:
                return True
            else:
                self.app.network_transition_threadsafe('set_certificate_expired')
                return False

        self._cancel_validity_updates = run_periodically(
            update_connection_validity,
            UPDATE_EXIPRY_INTERVAL,
            'update-validity',
        )

    @transition_edge_callback(EXIT, interface_state.ConnectionStatus)
    def exit_ConnectionStatus(self, old_state, new_state):
        self.show_component('connectionPage', False)

        if hasattr(self, '_cancel_validity_updates'):
            self._cancel_validity_updates()
            del self._cancel_validity_updates

    @transition_edge_callback(ENTER, interface_state.ErrorState)
    def enter_ErrorState(self, old_state, new_state):
        self.show_component('messagePage', True)
        self.show_component('messageLabel', True)
        self.show_component('messageText', True)
        self.set_text('messageLabel', _("Error"))
        self.set_text('messageText', new_state.message)
        self.show_component('messageButton', True)
        self.builder.get_object('messageButton').set_label(_("Ok"))
        button = self.builder.get_object('messageButton')
        button.connect("clicked", self.on_acknowledge_error)

    @transition_edge_callback(EXIT, interface_state.ErrorState)
    def exit_ErrorState(self, old_state, new_state):
        self.show_component('messagePage', False)
        button = self.builder.get_object('messageButton')
        button.disconnect_by_func(self.on_acknowledge_error)

    # ui callbacks

    def on_settings_button_released(self, widget, event):
        logger.debug("clicked settings button")
        self.app.interface_transition('toggle_settings')

    def on_help_button_released(self, widget, event):
        logger.debug("clicked help button")
        webbrowser.open(HELP_URL)

    def on_back_button_released(self, widget, event):
        logger.debug("clicked back button")
        self.app.interface_transition('go_back')

    def on_add_other_server_button_clicked(self, button) -> None:
        logger.debug("on_add_other_server_button_clicked")
        self.app.interface_transition('configure_new_server')

    def on_select_server(self, selection):
        logger.debug("selected search result")
        (model, tree_iter) = selection.get_selected()
        selection.unselect_all()
        if tree_iter is None:
            logger.info("selection empty")
        else:
            row = model[tree_iter]
            server = row[1]
            logger.debug(f"selected server: {server!r}")
            self.app.interface_transition('connect_to_server', server)

    def on_cancel_oauth_setup_button_clicked(self, _):
        self.app.interface_transition('oauth_setup_cancel')

    def on_search_changed(self, _=None):
        query = self.builder.get_object('findYourInstituteSearch').get_text()
        logger.debug(f"entered search query: {query}")
        if self.lets_connect or query.count('.') >= 2:
            # Anything with two periods is interpreted
            # as a custom server address.
            self.app.interface_transition(
                'enter_custom_address', address=query)
        else:
            self.app.interface_transition(
                'enter_search_query', search_query=query)

    def on_activate_changed(self, _=None):
        logger.debug("on_activate_changed")
        # TODO

    def on_connection_switch_state_set(self, switch, state):
        logger.debug("on_activate_changed")
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
            logger.info("selection empty")
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
            logger.info("selection empty")
        else:
            row = model[tree_iter]
            location = row[2]
            logger.debug(f"selected location: {location!r}")
            self.app.interface_transition('select_secure_internet_location', location)

    def on_acknowledge_error(self, event):
        self.app.interface_transition('acknowledge_error')

    def on_renew_session_clicked(self, event):
        self.app.network_transition('renew_certificate')
