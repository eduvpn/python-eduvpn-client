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
    ENTER, EXIT, transition_callback, transition_edge_callback)
from ..crypto import Validity
from ..nm import nm_available
from ..utils import run_in_main_gtk_thread, run_periodically
from .. import notify
from . import search
from .utils import show_ui_component, link_markup, show_error_dialog

GtkTemplate = Gtk.Template  # type: ignore

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


def allow_certificate_renewal(validity: Optional[Validity]):
    if validity is None:
        return True
    return datetime.utcnow() >= validity.fraction(RENEWAL_ALLOW_FRACTION)


@GtkTemplate(filename="share/eduvpn/builder/mainwindow.ui")
class EduVpnGtkWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "ApplicationWindow"

    # child elements

    app_logo = GtkTemplate.Child('appLogo')

    settings_button = GtkTemplate.Child('settingsButton')
    back_button_container = GtkTemplate.Child('backButtonEventBox')

    server_list_container = GtkTemplate.Child('serverListContainer')

    institute_list_header = GtkTemplate.Child('instituteAccessHeader')
    secure_internet_list_header = GtkTemplate.Child('secureInternetHeader')
    other_server_list_header = GtkTemplate.Child('otherServersHeader')

    institute_list = GtkTemplate.Child('instituteTreeView')
    secure_internet_list = GtkTemplate.Child('secureInternetTreeView')
    other_server_list = GtkTemplate.Child('otherServersTreeView')

    choose_profile_page = GtkTemplate.Child('chooseProfilePage')
    choose_location_page = GtkTemplate.Child('chooseLocationPage')
    location_list = GtkTemplate.Child('locationTreeView')
    profile_list = GtkTemplate.Child('profileTreeView')

    find_server_page = GtkTemplate.Child('findServerPage')
    find_server_search_form = GtkTemplate.Child('findServerSearchForm')
    find_server_search_input = GtkTemplate.Child('findServerSearchInput')
    find_server_image = GtkTemplate.Child('findServerImage')
    find_server_label = GtkTemplate.Child('findServerLabel')

    add_custom_server_button_container = GtkTemplate.Child('addCustomServerRow')
    add_other_server_button_container = GtkTemplate.Child('addOtherServerRow')

    connection_page = GtkTemplate.Child('connectionPage')
    connection_status_image = GtkTemplate.Child('connectionStatusImage')
    connection_status_label = GtkTemplate.Child('connectionStatusLabel')
    connection_status_sub_label = GtkTemplate.Child('connectionStatusSubLabel')
    connection_switch = GtkTemplate.Child('connectionSwitch')
    connection_sub_page = GtkTemplate.Child('currentConnectionSubPage')

    server_image = GtkTemplate.Child('serverImage')
    server_label = GtkTemplate.Child('serverLabel')
    server_support_label = GtkTemplate.Child('supportLabel')

    renew_session_button = GtkTemplate.Child('renewSessionButton')

    oauth_page = GtkTemplate.Child('openBrowserPage')
    oauth_cancel_button = GtkTemplate.Child('cancelBrowserButton')

    settings_page = GtkTemplate.Child('settingsPage')

    loading_page = GtkTemplate.Child('loadingPage')
    loading_title = GtkTemplate.Child('loadingTitle')
    loading_message = GtkTemplate.Child('loadingMessage')

    error_page = GtkTemplate.Child('errorPage')
    error_text = GtkTemplate.Child('errorText')
    error_acknowledge_button = GtkTemplate.Child('errorAcknowledgeButton')

    def __init__(self, *, application: Application):  # type: ignore
        # Fix the cwd for the image paths in the interface template to resolve.
        os.chdir('share/eduvpn/builder')

        super().__init__(application=application)  # type: ignore
        self.app = application.app  # type: ignore

        # TODO implement settings page (issue #334)
        self.settings_button.hide()

        self.set_title(self.app.variant.name)  # type: ignore
        self.set_icon_from_file(self.app.variant.icon)  # type: ignore
        if self.app.variant.logo:
            self.app_logo.set_from_file(self.app.variant.logo)
        if self.app.variant.server_image:
            self.find_server_image.set_from_file(self.app.variant.server_image)
        if not self.app.variant.use_predefined_servers:
            self.find_server_label.set_text(_("Server address"))
            self.find_server_search_input.set_placeholder_text(_("Enter the server address"))

        self.app.connect_state_transition_callbacks(self, initialize=True)

        if not nm_available():
            show_error_dialog(
                self,
                name=_("Error"),
                title=_("NetworkManager not available"),
                message=_("The application will not be able to configure the network."))

    # ui functions

    def show_back_button(self, show: bool):
        show_ui_component(self.back_button_container, show)

    def set_search_text(self, text: str):
        self.find_server_search_input.set_text(text)

    def show_loading_page(self, title: str, message: str):
        self.loading_page.show()
        self.loading_title.set_text(title)
        self.loading_message.set_text(message)

    def hide_loading_page(self):
        self.loading_page.hide()

    # network state transition callbacks

    @transition_callback(network_state.NetworkState)
    def default_network_transition_callback(self, old_state, new_state):
        if isinstance(self.app.interface_state, interface_state.ConnectionStatus):
            self.update_connection_status()

    @transition_edge_callback(ENTER, network_state.CertificateExpiredState)
    def enter_CertificateExpiredState(self, old_state, new_state):
        notification = notify.Notification(self.app.variant)
        notification.show(
            title=_("Your session has expired"),
            message=_(
                "Renew the session "
                "to continue using this connection."),
        )

    def update_connection_server(self):
        server = self.app.interface_state.server
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
        expiry_text = get_validity_text(self.app.interface_state.validity)
        self.connection_status_sub_label.set_markup(expiry_text)

        if (hasattr(self.app.network_state, 'renew_certificate') and (
                isinstance(self.app.network_state, network_state.CertificateExpiredState) or (
                allow_certificate_renewal(self.app.interface_state.validity)))):
            self.connection_sub_page.show()
            self.renew_session_button.show()
        else:
            self.renew_session_button.hide()

    def update_connection_status(self):
        self.connection_status_label.set_text(self.app.network_state.status_label)
        self.connection_status_image.set_from_file(self.app.network_state.status_image.path)

        self.update_connection_validity()

        assert not (hasattr(self.app.network_state, 'reconnect') and hasattr(self.app.network_state, 'disconnect'))
        if hasattr(self.app.network_state, 'reconnect'):
            self.connection_sub_page.show()
            self.connection_switch.show()
            self.connection_switch.set_state(False)
        elif hasattr(self.app.network_state, 'disconnect'):
            self.connection_sub_page.show()
            self.connection_switch.show()
            self.connection_switch.set_state(True)
        else:
            self.connection_sub_page.hide()
            self.connection_switch.hide()

    # interface state transition callbacks

    @transition_callback(interface_state.InterfaceState)
    def default_interface_transition_callback(self, old_state, new_state):
        # Only show the 'go back' button if
        # the corresponding transition is available.
        self.show_back_button(new_state.has_transition('go_back'))

    @transition_edge_callback(ENTER, interface_state.ConfigureSettings)
    def enter_ConfigureSettings(self, old_state, new_state):
        self.settings_page.show()

    @transition_edge_callback(EXIT, interface_state.ConfigureSettings)
    def exit_ConfigureSettings(self, old_state, new_state):
        self.settings_page.hide()

    @transition_edge_callback(ENTER, interface_state.configure_server_states)
    def enter_search(self, old_state, new_state):
        if not new_state.search_query:
            self.set_search_text('')
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
        self.oauth_page.show()
        in_setup_state = isinstance(new_state, interface_state.OAuthSetup)
        show_ui_component(self.oauth_cancel_button, in_setup_state)

    @transition_edge_callback(EXIT, interface_state.OAuthSetupPending)
    @transition_edge_callback(EXIT, interface_state.OAuthSetup)
    def exit_oauth_setup(self, old_state, new_state):
        self.oauth_page.hide()
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
        self.choose_profile_page.show()
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
        self.choose_profile_page.hide()
        self.profile_list.hide()

    @transition_edge_callback(ENTER, interface_state.ChooseSecureInternetLocation)
    def enter_ChooseSecureInternetLocation(self, old_state, new_state):
        self.choose_location_page.show()
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
        self.choose_location_page.hide()
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
        self.connection_page.show()
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
        self.connection_page.hide()

        if hasattr(self, '_cancel_validity_updates'):
            self._cancel_validity_updates()
            del self._cancel_validity_updates

    @transition_edge_callback(ENTER, interface_state.ErrorState)
    def enter_ErrorState(self, old_state, new_state):
        self.error_page.show()
        self.error_text.set_text(new_state.message)
        has_next_transition = new_state.next_transition is not None
        show_ui_component(self.error_acknowledge_button, has_next_transition)

    @transition_edge_callback(EXIT, interface_state.ErrorState)
    def exit_ErrorState(self, old_state, new_state):
        self.error_page.hide()

    # ui callbacks

    @GtkTemplate.Callback()
    def on_configure_settings(self, widget, event):
        logger.debug("clicked on configure settings")
        self.app.interface_transition('toggle_settings')

    @GtkTemplate.Callback()
    def on_get_help(self, widget, event):
        logger.debug("clicked on get help")
        webbrowser.open(HELP_URL)

    @GtkTemplate.Callback()
    def on_go_back(self, widget, event):
        logger.debug("clicked on go back")
        self.app.interface_transition('go_back')

    @GtkTemplate.Callback()
    def on_add_other_server(self, button) -> None:
        logger.debug("clicked on add other server")
        self.app.interface_transition('configure_new_server')

    @GtkTemplate.Callback()
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

    @GtkTemplate.Callback()
    def on_cancel_oauth_setup(self, _):
        logger.debug("clicked on cancel oauth setup")
        self.app.interface_transition('oauth_setup_cancel')

    @GtkTemplate.Callback()
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

    @GtkTemplate.Callback()
    def on_search_activate(self, _=None):
        logger.debug("activated server search")
        # TODO

    @GtkTemplate.Callback()
    def on_switch_connection_state(self, switch, state):
        logger.debug("clicked on switch connection state")
        if state:
            self.app.interface_transition('activate_connection')
        else:
            self.app.interface_transition('deactivate_connection')
        return True

    @GtkTemplate.Callback()
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

    @GtkTemplate.Callback()
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

    @GtkTemplate.Callback()
    def on_acknowledge_error(self, event):
        logger.debug("clicked on acknowledge error")
        self.app.interface_transition('acknowledge_error')

    @GtkTemplate.Callback()
    def on_renew_session_clicked(self, event):
        logger.debug("clicked on renew certificate")
        self.app.network_transition('renew_certificate')

    @GtkTemplate.Callback()
    def on_close_window(self, window, event):
        logger.debug("clicked on close window")
        self.hide()
        self.get_application().on_window_closed()
        return True

    def on_reopen_window(self):
        self.app.interface_transition('restart')
        self.show()
        self.present()
