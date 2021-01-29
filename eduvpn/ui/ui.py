# eduvpngui - The GNU/Linux eduVPN GUI client
#
# Copyright: 2017-2020, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import os
import re
import webbrowser
from logging import getLogger
from pathlib import Path
from typing import Any, List

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('NM', '1.0')
from gi.repository import NM  # type: ignore
from gi.repository import Gtk, GObject, GLib, GdkPixbuf
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2.rfc6749.tokens import OAuth2Token

from eduvpn.utils import get_prefix, thread_helper
from eduvpn.storage import get_uuid, get_all_metadatas
from eduvpn.i18n import extract_translation, retrieve_country_name
from eduvpn.nm import get_client, save_connection, nm_available, activate_connection, deactivate_connection, \
    init_dbus_system_bus
from eduvpn.oauth2 import get_oauth
from eduvpn.remote import get_info, create_keypair, get_config, list_profiles
from eduvpn.settings import CLIENT_ID, IMAGE_PREFIX, HELP_URL, LETS_CONNECT_LOGO, LETS_CONNECT_NAME, \
    LETS_CONNECT_ICON, SERVER_ILLUSTRATION
from eduvpn.storage import set_metadata, get_current_metadata, set_auth_url, write_config, get_auth_url
from eduvpn.ui.backend import BackendData
from eduvpn.ui.vpn_connection import VpnConnection
from eduvpn.ui.utils import get_flag_image_file, error_helper
from eduvpn import actions

logger = getLogger(__name__)

builder_files: List[str] = ['mainwindow.ui']


class EduVpnGui:

    def __init__(self, lets_connect: bool) -> None:
        """
        Initialize all data structures needed in the GUI
        """
        self.lets_connect: bool = lets_connect

        self.prefix: str = get_prefix()
        self.builder: Any = Gtk.Builder()

        self.client: Any = get_client()

        self.auto_connect: bool = False
        self.act_on_switch: bool = False

        for b in builder_files:
            p = os.path.join(self.prefix, 'share/eduvpn/builder', b)
            if not os.access(p, os.R_OK):
                logger.error(f"Can't find {p}! That is quite an important file.")
                raise Exception
            self.builder.add_from_file(p)

        handlers = {
            "delete_window": Gtk.main_quit,
            "on_settings_button_released": self.on_settings_button_released,
            "on_help_button_released": self.on_help_button_released,
            "on_back_button_released": self.on_back_button_released,
            "on_search_changed": self.on_search_changed,
            "on_activate_changed": self.on_activate_changed,
            "on_add_other_server_button_clicked": self.on_add_other_server_button_clicked,
            "on_cancel_browser_button_clicked": self.on_cancel_browser_button_clicked,
            "on_connection_switch_state_set": self.on_connection_switch_state_set
        }

        self.builder.connect_signals(handlers)
        self.selection_handlers_connected = False
        self.window = self.builder.get_object('applicationWindow')
        self.logo_image = self.builder.get_object('logoImage')

        self.back_button = self.builder.get_object('backButton')
        self.back_button_event_box = self.builder.get_object('backButtonEventBox')

        self.find_your_institute_page = self.builder.get_object('findYourInstitutePage')
        self.institute_tree_view = self.builder.get_object('instituteTreeView')
        self.secure_internet_tree_view = self.builder.get_object('secureInternetTreeView')
        self.other_servers_tree_view = self.builder.get_object('otherServersTreeView')
        self.find_your_institute_spacer = self.builder.get_object('findYourInstituteSpacer')
        self.find_your_institute_image = self.builder.get_object('findYourInstituteImage')
        self.find_your_institute_label = self.builder.get_object('findYourInstituteLabel')

        self.add_other_server_row = self.builder.get_object('addOtherServerRow')
        self.add_other_server_button = self.builder.get_object('addOtherServerButton')
        self.find_your_institute_window = self.builder.get_object('findYourInstituteScrolledWindow')

        self.institute_access_header = self.builder.get_object('instituteAccessHeader')
        self.secure_internet_header = self.builder.get_object('secureInternetHeader')
        self.other_servers_header = self.builder.get_object('otherServersHeader')
        self.find_your_institute_search = self.builder.get_object('findYourInstituteSearch')

        self.choose_profile_page = self.builder.get_object('chooseProfilePage')
        self.profile_tree_view = self.builder.get_object('profileTreeView')

        self.choose_location_page = self.builder.get_object('chooseLocationPage')
        self.location_tree_view = self.builder.get_object('locationTreeView')

        self.open_browser_page = self.builder.get_object('openBrowserPage')

        self.connection_page = self.builder.get_object('connectionPage')
        self.server_label = self.builder.get_object('serverLabel')
        self.server_image = self.builder.get_object('serverImage')
        self.support_label = self.builder.get_object('supportLabel')
        self.connection_status_image = self.builder.get_object('connectionStatusImage')
        self.connection_status_label = self.builder.get_object('connectionStatusLabel')
        self.connection_sub_status = self.builder.get_object('connectionSubStatus')
        self.profiles_sub_page = self.builder.get_object('profilesSubPage')
        self.current_connection_sub_page = self.builder.get_object('currentConnectionSubPage')
        self.connection_sub_page = self.builder.get_object('connectionSubPage')
        self.connection_info_top_row = self.builder.get_object('connectionInfoTopRow')
        self.connection_info_grid = self.builder.get_object('connectionInfoGrid')
        self.duration_value_label = self.builder.get_object('durationValueLabel')
        self.downloaded_value_label = self.builder.get_object('downloadedValueLabel')
        self.uploaded_value_label = self.builder.get_object('uploadedValueLabel')
        self.ipv4_value_label = self.builder.get_object('ipv4ValueLabel')
        self.ipv6_value_label = self.builder.get_object('ipv6ValueLabel')
        self.connection_info_bottom_row = self.builder.get_object('connectionInfoBottomRow')
        self.connection_switch = self.builder.get_object('connectionSwitch')

        self.settings_page = self.builder.get_object('settingsPage')

        self.message_page = self.builder.get_object('messagePage')
        self.message_label = self.builder.get_object('messageLabel')
        self.message_text = self.builder.get_object('messageText')
        self.message_button = self.builder.get_object('messageButton')

        self.institute_list_model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_INT)  # type: ignore
        self.secure_internet_list_model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_INT)  # type: ignore
        self.other_servers_list_model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_INT)  # type: ignore
        self.profiles_list_model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_INT)  # type: ignore
        self.locations_list_model = Gtk.ListStore(GObject.TYPE_STRING, GdkPixbuf.Pixbuf,  # type: ignore
                                                  GObject.TYPE_INT)  # type: ignore

        self.connections: List[VpnConnection] = []
        self.select_existing_connection = False

        try:
            self.data = BackendData(lets_connect=lets_connect)
        except Exception as e:
            msg = f"Got exception {e} initializing backend data"
            logger.error(msg)
        else:
            init_dbus_system_bus(self.nm_status_cb)

            self.init_search_list()
            self.show_back_button(False)
            self.read_connections()
            if self.lets_connect:
                self.logo_image.set_from_file(LETS_CONNECT_LOGO)
                self.find_your_institute_image.set_from_file(SERVER_ILLUSTRATION)
                self.find_your_institute_label.set_text("Server address")
                self.add_other_server_button.set_label("Add server")
                self.add_other_server_row.show()
                self.window.set_title(LETS_CONNECT_NAME)
                self.window.set_icon_from_file(LETS_CONNECT_ICON)
            else:
                self.add_other_server_row.hide()

    def read_connections(self):
        """
        Read all vpn connections from storage
        """
        logger.debug("read_connections")
        self.connections = []
        for auth_url, props in get_all_metadatas().items():
            vpn_connection = VpnConnection()
            vpn_connection.auth_url = auth_url
            vpn_connection.api_url = props['api_url']
            vpn_connection.server_name = props['display_name']
            vpn_connection.support_contact = props['support_contact']
            vpn_connection.profile_id = props['profile_id']
            vpn_connection.token_endpoint = props['token_endpoint']
            vpn_connection.authorization_endpoint = props['authorization_endpoint']
            vpn_connection.token = OAuth2Token(props['token'])
            vpn_connection.type = props['con_type']
            vpn_connection.country_id = props['country_id']
            self.connections.append(vpn_connection)

    def nm_status_cb(self,
                     state_code: NM.VpnConnectionState = NM.VpnConnectionState.UNKNOWN,
                     reason_code: NM.VpnConnectionStateReason = NM.VpnConnectionStateReason.UNKNOWN):
        """
        This method is called when a DBUS VPN state change event is received.

        Handles auto connect when that is enabled.
        """
        if type(state_code) != NM.VpnConnectionState:
            state_code = NM.VpnConnectionState(state_code)

        if type(reason_code) != NM.VpnConnectionStateReason:
            reason_code = NM.VpnConnectionStateReason(state_code)

        self.update_connection_state(state_code)
        logger.debug(f"nm_status_cb state: {state_code.value_name}, reason: {reason_code.value_name}")
        self.connection_switch.set_state(state_code == NM.VpnConnectionState.ACTIVATED)
        if self.auto_connect:
            if state_code == NM.VpnConnectionState.DISCONNECTED:
                self.activate_connection()
            elif state_code == NM.VpnConnectionState.ACTIVATED:
                self.auto_connect = False
                self.act_on_switch = True
                self.data.vpn_connection = self.data.new_vpn_connection
                self.show_connection(False)
                self.show_back_button()
                self.data.uuid = get_uuid()
                self.read_connections()

    def run(self) -> None:
        """
        Shows the main window and if there is already an active vpn connection shows the connection screen,
        otherwise the screen to select a previous connection or the initial screen when no previous selection was made.
        """
        logger.debug("run")
        self.window.show()
        try:
            self.data
            if self.data.connection_state == NM.VpnConnectionState.ACTIVATED:
                vc = self.data.vpn_connection
                auth_url = get_auth_url()
                if auth_url:
                    exists = get_current_metadata(auth_url)
                    if exists:
                        vc.auth_url = auth_url
                        vc.token, vc.token_endpoint, vc.authorization_endpoint, vc.api_url, vc.server_name, \
                            support_contact, vc.profile_id, vc.type, vc.country_code = exists
                self.act_on_switch = True
                self.show_connection(False)
                self.show_back_button()
            elif self.connections_available():
                self.show_connections()
            else:
                self.show_find_your_institute()
        except Exception as e:
            self.show_fatal(f"Got exception {e} can't reach the server, please quit")

    def on_settings_button_released(self, widget, event) -> None:
        """
        The settings button has been pressed, shows the settings screen.
        """
        logger.debug("on_settings_button_released")
        self.show_settings()

    def on_help_button_released(self, widget, event) -> None:
        """
        The help button has been pressed, open the web browser with information.
        """
        logger.debug("on_help_button_released")
        webbrowser.open(HELP_URL)

    def on_back_button_released(self, widget, event) -> None:
        """
        The back button has been pressed, act accordingly.
        """
        logger.debug("on_back_button_released")
        if self.connections_available():
            self.show_connections()
        else:
            self.show_find_your_institute()

    def on_add_other_server_button_clicked(self, button) -> None:
        """
        The add server button has been clicked, handle this differently for eduVPN and Let's Connect.
        """
        logger.debug("on_add_other_server_button_clicked")
        if self.lets_connect and len(self.find_your_institute_search.get_text()) > 0:
            logger.debug("on_add_other_server_button_clicked 1")
            self.handle_add_other_server(self.find_your_institute_search.get_text())
        else:
            logger.debug("on_add_other_server_button_clicked 2")
            self.show_add_other_server()

    def handle_add_other_server(self, name: str) -> None:
        self.data.new_vpn_connection.server_name = name
        self.data.new_vpn_connection.type = VpnConnection.ConnectionType.OTHER
        if name.count('.') > 1:
            if not name.lower().startswith('https://'):
                name = 'https://' + name
            if not name.lower().endswith('/'):
                name = name + '/'
            logger.debug(f"handle_add_other_server: {name}")
            if not self.lets_connect:
                self.disconnect_selection_handlers()
            self.show_empty()
            self.setup_connection(name)
        if not self.lets_connect:
            self.other_servers_tree_view.get_selection().unselect_all()

    def activate_other_server(self, name: str, index: int) -> None:
        logger.debug("activate_other_server")
        self.disconnect_selection_handlers()
        self.data.new_vpn_connection = self.connections[index]
        self.show_empty()
        self.setup_connection(self.data.new_vpn_connection.auth_url)

    def on_other_server_selection_changed(self, selection) -> None:
        logger.debug("on_other_server_selection_changed")
        logger.debug(f"# selected rows: {selection.count_selected_rows()}")
        (model, tree_iter) = selection.get_selected()
        if tree_iter is not None:
            if self.select_existing_connection:
                self.activate_other_server(model[tree_iter][0], model[tree_iter][1])
            else:
                self.handle_add_other_server(model[tree_iter][0])
        selection.unselect_all()

    def on_cancel_browser_button_clicked(self, _) -> None:
        logger.debug("on_cancel_browser_button_clicked")
        self.show_find_your_institute()

    def on_search_changed(self, _=None) -> None:
        logger.debug(f"on_search_changed: {self.find_your_institute_search.get_text()}")
        self.update_search_lists(self.find_your_institute_search.get_text())

    def on_activate_changed(self, _=None) -> None:
        name = self.find_your_institute_search.get_text()
        logger.debug(f"on_activate_changed: {name}")
        if self.lets_connect and len(self.institute_list_model) == 0:  # type: ignore
            self.handle_add_other_server(name)
        else:
            if len(name) == 0:
                return
            one_institute_available = len(self.institute_list_model) == 1  # type: ignore
            no_institute_available = len(self.institute_list_model) == 0  # type: ignore
            one_secure_internet_available = len(self.secure_internet_list_model) == 1  # type: ignore
            no_secure_internet_available = len(self.secure_internet_list_model) == 0  # type: ignore
            one_other_server_available = len(self.other_servers_list_model) == 1  # type: ignore
            no_other_server_available = len(self.other_servers_list_model) == 0  # type: ignore

            if one_institute_available and no_secure_internet_available and no_other_server_available:
                self.handle_add_institute(self.institute_list_model[0][0],  # type: ignore
                                          self.institute_list_model[0][1])  # type: ignore
            if no_institute_available and one_secure_internet_available and no_other_server_available:
                self.handle_add_secure_internet(self.secure_internet_list_model[0][0],  # type: ignore
                                                self.secure_internet_list_model[0][1])  # type: ignore
            if no_institute_available and no_secure_internet_available and one_other_server_available:
                self.handle_add_other_server(self.other_servers_list_model[0][0])  # type: ignore

    def handle_add_institute(self, name: str, index: int) -> None:
        self.data.new_vpn_connection.server_name = name
        self.data.new_vpn_connection.type = VpnConnection.ConnectionType.INSTITUTE
        self.disconnect_selection_handlers()
        base_url = str(self.data.institute_access[index]['base_url'])

        self.data.new_vpn_connection.support_contact = self.data.institute_access[index].get('support_contact', None)
        if not self.data.new_vpn_connection.support_contact:
            self.data.new_vpn_connection.support_contact = []

        logger.debug(f"handle_add_institute: {self.data.new_vpn_connection.server_name} {base_url}")
        self.show_empty()
        self.setup_connection(base_url, [], False)

    def activate_institute(self, name: str, index: int) -> None:
        logger.debug("activate_institute")
        self.disconnect_selection_handlers()
        self.data.new_vpn_connection = self.connections[index]
        self.show_empty()
        self.setup_connection(self.data.new_vpn_connection.auth_url, [], False)

    def on_institute_selection_changed(self, selection) -> None:
        logger.debug("on_institute_selection_changed")
        logger.debug(f"# selected rows: {selection.count_selected_rows()}")
        (model, tree_iter) = selection.get_selected()
        selection.unselect_all()
        if tree_iter is not None:
            if self.select_existing_connection:
                self.activate_institute(model[tree_iter][0], model[tree_iter][1])
            else:
                self.handle_add_institute(model[tree_iter][0], model[tree_iter][1])
        # else:
        #     selection.unselect_all()

    def handle_add_secure_internet(self, name: str, index: int) -> None:
        self.disconnect_selection_handlers()
        self.data.new_vpn_connection.server_name = name
        self.data.secure_internet_home = self.data.organisations[index]['secure_internet_home']
        self.data.new_vpn_connection.type = VpnConnection.ConnectionType.SECURE
        self.connect_selection_handlers()
        self.data.secure_internet_home = self.data.organisations[index]['secure_internet_home']
        logger.debug(
            f"handle_add_secure_internet: {self.data.new_vpn_connection.server_name} {self.data.secure_internet_home}")
        self.show_empty()
        self.setup_connection(self.data.secure_internet_home, self.data.secure_internet, True)

    def activate_secure_internet(self, name: str, index: int) -> None:
        logger.debug("activate_secure_internet")
        self.disconnect_selection_handlers()
        self.data.new_vpn_connection = self.connections[index]
        self.show_empty()
        self.setup_connection(self.data.new_vpn_connection.auth_url, self.data.secure_internet, True)

    def on_secure_internet_selection_changed(self, selection) -> None:
        logger.debug("on_secure_internet_selection_changed")
        logger.debug(f"# selected rows: {selection.count_selected_rows()}")
        (model, tree_iter) = selection.get_selected()
        if tree_iter is not None:
            if self.select_existing_connection:
                self.activate_secure_internet(model[tree_iter][0], model[tree_iter][1])
            else:
                self.handle_add_secure_internet(model[tree_iter][0], model[tree_iter][1])
        selection.unselect_all()

    def on_connection_switch_state_set(self, switch, state):
        logger.debug(f"on_connection_switch_state_set: {state}")
        if self.act_on_switch:
            if state:
                self.activate_connection()
            else:
                self.deactivate_connection()
        return True

    def activate_connection(self) -> None:
        logger.debug("Activating connection")
        self.data.uuid = get_uuid()
        if self.data.uuid:
            GLib.idle_add(lambda: activate_connection(self.client, self.data.uuid))
        else:
            raise Exception("No UUID configured, can't activate connection")

    def deactivate_connection(self) -> None:
        logger.debug("Deactivating connection")
        self.data.uuid = get_uuid()
        if self.data.uuid:
            GLib.idle_add(lambda: deactivate_connection(self.client, self.data.uuid))
        else:
            raise Exception("No UUID configured, can't deactivate connection")

    def init_search_list(self) -> None:
        logger.debug("init_search_list")
        text_cell = Gtk.CellRendererText()
        text_cell.set_property("size-points", 14)  # type: ignore
        col = Gtk.TreeViewColumn(None, text_cell, text=0)  # type: ignore
        self.institute_tree_view.append_column(col)
        self.institute_tree_view.set_model(self.institute_list_model)
        col = Gtk.TreeViewColumn(None, text_cell, text=0)  # type: ignore
        self.secure_internet_tree_view.append_column(col)
        self.secure_internet_tree_view.set_model(self.secure_internet_list_model)
        col = Gtk.TreeViewColumn(None, text_cell, text=0)  # type: ignore
        self.other_servers_tree_view.append_column(col)
        self.other_servers_tree_view.set_model(self.other_servers_list_model)
        col = Gtk.TreeViewColumn(None, text_cell, text=0)  # type: ignore
        self.profile_tree_view.append_column(col)
        self.profile_tree_view.set_model(self.profiles_list_model)
        renderer_pixbuf = Gtk.CellRendererPixbuf()
        column_pixbuf = Gtk.TreeViewColumn("Image", renderer_pixbuf, pixbuf=1)  # type: ignore
        self.location_tree_view.append_column(column_pixbuf)
        col = Gtk.TreeViewColumn(None, text_cell, text=0)  # type: ignore
        self.location_tree_view.append_column(col)
        self.location_tree_view.set_model(self.locations_list_model)
        # self.update_search_lists()

    def update_search_lists(self, search_string="") -> None:
        logger.debug(f"update_search_lists: f{search_string}")
        if self.lets_connect and len(self.institute_list_model) == 0:  # type: ignore
            self.find_your_institute_window.hide()
            self.update_lc_first_search_list(search_string)
        else:
            self.find_your_institute_window.show()
            self.update_all_search_lists(search_string)

    def update_all_search_lists(self, search_string="") -> None:
        logger.debug(f"update_all_search_lists: f{search_string}")
        selection = self.institute_tree_view.get_selection()
        self.disconnect_selection_handlers()
        self.institute_list_model.clear()  # type: ignore
        self.secure_internet_list_model.clear()  # type: ignore
        self.other_servers_list_model.clear()  # type: ignore
        for i, row in enumerate(self.data.institute_access):
            display_name = extract_translation(row['display_name'])
            if re.search(search_string, display_name, re.IGNORECASE):
                self.institute_list_model.append([display_name, i])  # type: ignore
        for i, row in enumerate(self.data.organisations):
            display_name = extract_translation(row['display_name'])
            if re.search(search_string, display_name, re.IGNORECASE):
                self.secure_internet_list_model.append([display_name, i])  # type: ignore
        self.show_search_lists()
        self.connect_selection_handlers()

    def update_lc_first_search_list(self, search_string="") -> None:
        logger.debug(f"update_lc_first_search_list: {search_string}")

    def show_find_your_institute(self, clear_text=True) -> None:
        logger.debug("show_find_your_institute")
        self.select_existing_connection = False
        self.data.profiles = {}
        self.data.locations = []
        self.data.secure_internet_home = ""
        self.data.oauth = None
        self.data.new_vpn_connection = VpnConnection()
        self.act_on_switch = False

        self.find_your_institute_page.show()
        self.find_your_institute_image.show()
        self.find_your_institute_spacer.show()
        self.find_your_institute_label.show()
        self.find_your_institute_search.show()
        self.add_other_server_row.hide()

        self.find_your_institute_search.disconnect_by_func(self.on_search_changed)
        if clear_text:
            self.find_your_institute_search.set_text("")
        self.find_your_institute_search.grab_focus()

        self.settings_page.hide()
        self.choose_profile_page.hide()
        self.choose_location_page.hide()
        self.open_browser_page.hide()
        self.connection_page.hide()
        self.message_page.hide()
        self.show_back_button(False)
        if self.lets_connect:
            self.add_other_server_row.show()
        else:
            self.add_other_server_row.hide()
        self.find_your_institute_search.connect("search-changed", self.on_search_changed)
        self.update_search_lists()

    def show_connections(self) -> None:
        logger.debug("show_connections")
        self.select_existing_connection = True
        self.disconnect_selection_handlers()

        self.institute_list_model.clear()  # type: ignore
        self.secure_internet_list_model.clear()  # type: ignore
        self.other_servers_list_model.clear()  # type: ignore

        for i, connection in enumerate(self.connections):
            formatted = f"{connection.server_name} {connection.profile_id}"
            if not self.lets_connect:
                if connection.type == VpnConnection.ConnectionType.INSTITUTE:
                    self.institute_list_model.append([formatted, i])  # type: ignore
                elif connection.type == VpnConnection.ConnectionType.SECURE:
                    self.secure_internet_list_model.append([formatted, i])  # type: ignore
            if connection.type == VpnConnection.ConnectionType.OTHER:
                self.other_servers_list_model.append([formatted, i])  # type: ignore

        self.find_your_institute_page.show()
        self.find_your_institute_image.hide()
        self.find_your_institute_spacer.hide()
        self.find_your_institute_label.hide()
        self.find_your_institute_search.hide()
        self.add_other_server_row.show()

        self.settings_page.hide()
        self.choose_profile_page.hide()
        self.choose_location_page.hide()
        self.open_browser_page.hide()
        self.connection_page.hide()
        self.message_page.hide()
        self.show_back_button(False)

        if len(self.institute_list_model) > 0:  # type: ignore
            self.institute_access_header.show()
            self.institute_tree_view.show()
        else:
            self.institute_access_header.hide()
            self.institute_tree_view.hide()
        if len(self.secure_internet_list_model):  # type: ignore
            self.secure_internet_header.show()
            self.secure_internet_tree_view.show()
        else:
            self.secure_internet_header.hide()
            self.secure_internet_tree_view.hide()
        if len(self.other_servers_list_model) > 0:  # type: ignore
            self.other_servers_header.show()
            self.other_servers_tree_view.show()
        else:
            self.other_servers_header.hide()
            self.other_servers_tree_view.hide()

        self.connect_selection_handlers()

    def connections_available(self) -> bool:
        logger.debug("connections_available")
        for connection in self.connections:
            if not self.lets_connect:
                return True
            elif connection.type == VpnConnection.ConnectionType.OTHER:
                return True
        return False

    def show_add_other_server(self) -> None:
        logger.debug("show_add_other_server")
        self.show_find_your_institute()

    def show_settings(self) -> None:
        logger.debug("show_settings")
        self.find_your_institute_page.hide()
        self.settings_page.show()
        self.choose_profile_page.hide()
        self.choose_location_page.hide()
        self.open_browser_page.hide()
        self.connection_page.hide()
        self.message_page.hide()
        self.show_back_button()
        self.add_other_server_row.hide()

    def show_choose_profile(self) -> None:
        logger.debug("show_choose_profile")
        if len(self.data.profiles) > 1:
            self.find_your_institute_page.hide()
            self.settings_page.hide()
            self.choose_profile_page.show()
            self.choose_location_page.hide()
            self.open_browser_page.hide()
            self.connection_page.hide()
            self.message_page.hide()
            self.show_back_button()
            self.add_other_server_row.hide()
            select = self.profile_tree_view.get_selection()
            select.unselect_all()
            select.connect("changed", self.on_profile_selection_changed)
        else:
            logger.warning("ERROR: should only be called when there are profiles to choose from")
            self.show_settings()

    def show_choose_location(self) -> None:
        logger.debug("show_choose_location")
        if len(self.data.locations) > 1:
            self.find_your_institute_page.hide()
            self.settings_page.hide()
            self.choose_profile_page.hide()
            self.choose_location_page.show()
            self.open_browser_page.hide()
            self.connection_page.hide()
            self.message_page.hide()
            self.show_back_button()
            self.add_other_server_row.hide()
            select = self.location_tree_view.get_selection()
            select.unselect_all()
            select.connect("changed", self.on_location_selection_changed)
        else:
            logger.warning("ERROR: should only be called when there are profiles to choose from")
            self.show_settings()

    def show_open_browser(self) -> None:
        """
        Show the open browser screen
        """
        logger.debug("show_open_browser")
        self.find_your_institute_page.hide()
        self.settings_page.hide()
        self.choose_profile_page.hide()
        self.choose_location_page.hide()
        self.open_browser_page.show()
        self.connection_page.hide()
        self.message_page.hide()
        self.show_back_button(False)
        self.add_other_server_row.hide()

    def show_connection(self, start_connection: bool = True) -> None:
        logger.debug("show_connection")
        self.find_your_institute_page.hide()
        self.settings_page.hide()
        self.choose_profile_page.hide()
        self.choose_location_page.hide()
        self.open_browser_page.hide()
        self.connection_page.show()
        self.message_page.hide()
        self.show_back_button()
        self.add_other_server_row.hide()
        self.connection_info_top_row.hide()
        self.profiles_sub_page.hide()
        self.connection_sub_page.hide()
        self.connection_info_grid.hide()
        self.connection_info_bottom_row.hide()
        self.server_image.hide()
        self.server_label.set_text(self.data.vpn_connection.server_name)
        flag_image_file = get_flag_image_file(self.data.vpn_connection.country_code)
        if flag_image_file:
            self.server_image.set_from_file(flag_image_file)
            self.server_image.show()
        else:
            self.server_image.hide()

        support = ""
        if len(self.data.vpn_connection.support_contact) > 0:
            support = "Support: " + ", ".join(self.data.vpn_connection.support_contact)
        self.support_label.set_text(support)
        if start_connection:
            self.show_back_button()
            self.act_on_switch = False
            logger.debug(f"vpn_state: {self.data.connection_state}")
            self.auto_connect = True
            if self.data.connection_state == NM.VpnConnectionState.ACTIVATED:
                GLib.idle_add(lambda: self.deactivate_connection())
            else:
                self.activate_connection()
        else:
            self.show_back_button(True, False)

    def show_empty(self) -> None:
        logger.debug("show_empty")
        self.find_your_institute_page.hide()
        self.settings_page.hide()
        self.choose_profile_page.hide()
        self.choose_location_page.hide()
        self.open_browser_page.hide()
        self.connection_page.hide()
        self.message_page.hide()
        self.show_back_button(True, False)
        self.add_other_server_row.hide()
        self.connection_info_top_row.hide()
        self.profiles_sub_page.hide()
        self.connection_sub_page.hide()
        self.connection_info_grid.hide()
        self.connection_info_bottom_row.hide()

    def show_message(self, label, text, callback) -> None:
        logger.debug(f"show_message: {label} {text}")
        self.find_your_institute_page.hide()
        self.settings_page.hide()
        self.choose_profile_page.hide()
        self.choose_location_page.hide()
        self.open_browser_page.hide()
        self.connection_page.hide()
        self.show_back_button(True, False)
        self.add_other_server_row.hide()
        self.connection_info_top_row.hide()
        self.profiles_sub_page.hide()
        self.connection_sub_page.hide()
        self.connection_info_grid.hide()
        self.connection_info_bottom_row.hide()
        self.message_page.show()
        self.message_label.set_text(label)
        self.message_text.set_text(text)
        self.message_button.connect("clicked", callback)

    def show_fatal(self, text) -> None:
        logger.debug(f"show_fatal: {text}")
        self.show_message("Fatal error", text, Gtk.main_quit)

    def update_connection_state(self, state: NM.VpnConnectionState) -> None:
        logger.debug(f"update_connection_state: {state}")
        self.data.connection_state = state

        connection_state_mapping = {
            NM.VpnConnectionState.UNKNOWN: ["Connection state unknown", "desktop-default.png"],
            NM.VpnConnectionState.PREPARE: ["Preparing to connect", "desktop-connecting.png"],
            NM.VpnConnectionState.NEED_AUTH: ["Needs authorization credentials", "desktop-connecting.png"],
            NM.VpnConnectionState.CONNECT: ["Connection is being established", "desktop-connecting.png"],
            NM.VpnConnectionState.IP_CONFIG_GET: ["Getting an IP address", "desktop-connecting.png"],
            NM.VpnConnectionState.ACTIVATED: ["Connection active", "desktop-connected.png"],
            NM.VpnConnectionState.FAILED: ["Connection failed", "desktop-not-connected.png"],
            NM.VpnConnectionState.DISCONNECTED: ["Disconnected", "desktop-default.png"],
        }
        self.connection_status_label.set_text(connection_state_mapping[state][0])
        self.connection_status_image.set_from_file(IMAGE_PREFIX + connection_state_mapping[state][1])
        if state == NM.VpnConnectionState.UNKNOWN:
            self.current_connection_sub_page.hide()
        else:
            self.current_connection_sub_page.show()

    def on_profile_selection_changed(self, selection) -> None:
        logger.debug("on_profile_selection_changed")
        logger.debug(f"# selected rows: {selection.count_selected_rows()}")
        (model, tree_iter) = selection.get_selected()
        if tree_iter is not None:
            display_name = model[tree_iter][0]
            i = model[tree_iter][1]
            # self.data.vpn_connection.profile_name = display_name
            selection.disconnect_by_func(self.on_profile_selection_changed)
            selection.unselect_all()
            self.data.new_vpn_connection.profile_id = str(self.data.profiles[i]['profile_id'])
            logger.debug(f"on_profile_selection_changed: {display_name} {self.data.new_vpn_connection.profile_id}")
            self.finalize_configuration(self.data.new_vpn_connection.profile_id)
        else:
            selection.unselect_all()

    def show_search_lists(self) -> None:
        logger.debug("show_search_lists")
        name = self.find_your_institute_search.get_text()
        search_term = len(name) > 0
        dot_count = name.count('.')

        if dot_count > 1:
            self.other_servers_list_model.clear()  # type: ignore
            self.other_servers_list_model.append([name, 0])  # type: ignore

        if search_term:
            self.find_your_institute_image.hide()
            self.find_your_institute_spacer.hide()
            self.add_other_server_row.hide()
        else:
            self.find_your_institute_image.show()
            self.find_your_institute_spacer.show()
            self.add_other_server_row.hide()

        if len(self.institute_list_model) > 0 and search_term:  # type: ignore
            self.institute_access_header.show()
            self.institute_tree_view.show()
        else:
            self.institute_access_header.hide()
            self.institute_tree_view.hide()
        if len(self.secure_internet_list_model) > 0 and search_term:  # type: ignore
            self.secure_internet_header.show()
            self.secure_internet_tree_view.show()
        else:
            self.secure_internet_header.hide()
            self.secure_internet_tree_view.hide()
        if len(self.other_servers_list_model) > 0 and search_term:  # type: ignore
            self.other_servers_header.show()
            self.other_servers_tree_view.show()
        else:
            self.other_servers_header.hide()
            self.other_servers_tree_view.hide()

    def on_location_selection_changed(self, selection) -> None:
        logger.debug("on_location_selection_changed")
        logger.debug(f"# selected rows: {selection.count_selected_rows()}")
        (model, tree_iter) = selection.get_selected()
        if tree_iter is not None:
            self.data.new_vpn_connection.server_name = model[tree_iter][0]
            display_name = model[tree_iter][0]
            i = model[tree_iter][2]
            selection.disconnect_by_func(self.on_location_selection_changed)
            logger.debug(self.data.locations[i])
            base_url = str(self.data.locations[i]['base_url'])
            self.data.new_vpn_connection.country_code = self.data.locations[i]['country_code']
            if 'support_contact' in self.data.locations[i]:
                self.data.new_vpn_connection.support_contact = self.data.locations[i]['support_contact']
            logger.debug(f"on_location_selection_changed: {display_name} {base_url}")
            self.show_empty()
            thread_helper(lambda: handle_location_thread(base_url, self))
        selection.unselect_all()

    def location_selected(self, base_url):
        self.show_empty()
        thread_helper(lambda: handle_location_thread(base_url, self))

    def setup_connection(self, auth_url, secure_internet: list = [], interactive: bool = False) -> None:
        logger.debug(f"setup_connection auth_url:{auth_url} secure_internet:{secure_internet} interactive:{interactive}")

        self.data.new_vpn_connection.auth_url = auth_url
        self.data.locations = secure_internet

        logger.debug(f"starting procedure with auth_url: {self.data.new_vpn_connection.auth_url}")
        exists = get_current_metadata(self.data.new_vpn_connection.auth_url)

        if exists:
            token, self.data.new_vpn_connection.token_endpoint, self.data.new_vpn_connection.authorization_endpoint, api_url, \
                display_name, support_contact, self.data.new_vpn_connection.profile_id, self.data.new_vpn_connection.type, self.data.new_vpn_connection.country_code = exists
            thread_helper(lambda: restoring_token_thread(token, self.data.new_vpn_connection.token_endpoint, self))
        else:
            self.show_open_browser()
            thread_helper(lambda: fetch_token_thread(self))

    def token_available(self) -> None:
        """
        Called when the token is available
        """
        logger.debug("token_available")
        if self.data.locations:
            thread_helper(lambda: handle_secure_internet_thread(self))
        else:
            self.handle_profiles()

    def handle_profiles(self) -> None:
        logger.debug(f"handle_profiles using api_url: {self.data.new_vpn_connection.api_url}")
        thread_helper(lambda: handle_profiles_thread(self))

    def finalize_configuration(self, profile_id) -> None:
        logger.debug("finalize_configuration")
        self.show_connection(False)
        thread_helper(lambda: finalize_configuration_thread(profile_id, self))

    def configuration_finalized_cb(self, result):
        logger.debug(f"configuration_finalized_cb: {result}")
        GLib.idle_add(lambda: self.show_connection())

    def configuration_finalized(self, config, private_key, certificate) -> None:
        logger.debug("configuration_finalized")

        set_metadata(
            auth_url=self.data.new_vpn_connection.auth_url,
            token=self.data.oauth.token,
            token_endpoint=self.data.new_vpn_connection.token_endpoint,
            authorization_endpoint=self.data.new_vpn_connection.authorization_endpoint,
            api_url=self.data.new_vpn_connection.api_url,
            display_name=self.data.new_vpn_connection.server_name,
            support_contact=self.data.new_vpn_connection.support_contact,
            profile_id=self.data.new_vpn_connection.profile_id,
            con_type=self.data.new_vpn_connection.type,
            country_id=self.data.new_vpn_connection.country_code
        )
        if nm_available():
            logger.info("nm available:")
            save_connection(self.client, config, private_key, certificate, self.configuration_finalized_cb)
        else:
            target = Path('eduVPN.ovpn').resolve()
            write_config(config, private_key, certificate, target)
            GLib.idle_add(lambda: self.connection_written())

    def connection_written(self) -> None:
        logger.debug("connection_written")
        self.show_connection()

    def show_back_button(self, show: bool = True, enabled: bool = True):
        logger.debug("show_back_button")
        if show:
            self.back_button.show()
        else:
            self.back_button.hide()
        self.back_button_event_box.set_sensitive(enabled)

    def connect_selection_handlers(self):
        if not self.selection_handlers_connected:
            select = self.institute_tree_view.get_selection()
            select.unselect_all()
            select.connect("changed", self.on_institute_selection_changed)
            select = self.secure_internet_tree_view.get_selection()
            select.unselect_all()
            select.connect("changed", self.on_secure_internet_selection_changed)
            select = self.other_servers_tree_view.get_selection()
            select.unselect_all()
            select.connect("changed", self.on_other_server_selection_changed)
            self.selection_handlers_connected = True

    def disconnect_selection_handlers(self):
        if self.selection_handlers_connected:
            select = self.institute_tree_view.get_selection()
            select.disconnect_by_func(self.on_institute_selection_changed)
            select = self.secure_internet_tree_view.get_selection()
            select.disconnect_by_func(self.on_secure_internet_selection_changed)
            select = self.other_servers_tree_view.get_selection()
            select.disconnect_by_func(self.on_other_server_selection_changed)
            self.selection_handlers_connected = False

    def handle_error(self, msg: str):
        error_helper(self.window, msg, msg)
        self.show_find_your_institute(clear_text=True)


def fetch_token_thread(gui: EduVpnGui) -> None:
    logger.debug("fetching token")
    try:
        gui.data.new_vpn_connection.api_url, gui.data.oauth, gui.data.new_vpn_connection.token_endpoint, \
            gui.data.new_vpn_connection.authorization_endpoint = actions.fetch_token(gui.data.new_vpn_connection.auth_url)
        GLib.idle_add(lambda: gui.token_available())
    except Exception as e:
        msg = f"Got exception {e} requesting {gui.data.new_vpn_connection.auth_url}"
        logger.debug(msg)
        GLib.idle_add(lambda: gui.handle_error(msg))


def restoring_token_thread(token, token_endpoint, gui: EduVpnGui) -> None:
    logger.debug("token exists, restoring")
    gui.data.oauth = OAuth2Session(client_id=CLIENT_ID, token=token, auto_refresh_url=token_endpoint)
    gui.data.oauth.refresh_token(token_url=gui.data.new_vpn_connection.token_endpoint)
    gui.data.new_vpn_connection.api_url, _, _ = get_info(gui.data.new_vpn_connection.auth_url)
    GLib.idle_add(lambda: gui.token_available())


def handle_location_thread(base_url: str, gui: EduVpnGui) -> None:
    logger.debug("fetching location info")
    gui.data.new_vpn_connection.api_url, _, _ = get_info(base_url)
    GLib.idle_add(lambda: gui.handle_profiles())


def handle_profiles_thread(gui: EduVpnGui) -> None:
    logger.debug("handle_profiles_thread")
    gui.data.oauth.refresh_token(token_url=gui.data.new_vpn_connection.token_endpoint)
    gui.data.profiles = list_profiles(gui.data.oauth, gui.data.new_vpn_connection.api_url)
    if gui.select_existing_connection:
        # if we already have a profile and it still exists use that one
        for profile in gui.data.profiles:
            if gui.data.new_vpn_connection.profile_id == profile['profile_id']:
                GLib.idle_add(lambda: gui.finalize_configuration(gui.data.new_vpn_connection.profile_id))
                return
    if len(gui.data.profiles) > 1:
        # if there are profiles to choose from ask the user
        gui.profiles_list_model.clear()  # type: ignore
        for i, profile in enumerate(gui.data.profiles):
            gui.profiles_list_model.append([profile['display_name'], i])  # type: ignore
        GLib.idle_add(lambda: gui.show_choose_profile())
    else:
        # there is only one profile, use that
        gui.data.new_vpn_connection.profile_id = str(gui.data.profiles[0]['profile_id'])
        GLib.idle_add(lambda: gui.finalize_configuration(gui.data.new_vpn_connection.profile_id))


def handle_secure_internet_thread(gui: EduVpnGui) -> None:
    logger.debug("handle_secure_internet_thread")
    if gui.select_existing_connection:
        # if we already have a country code and it still exists use that one
        for location in gui.data.locations:
            if gui.data.new_vpn_connection.country_code == location['country_code']:
                base_url = str(location['base_url'])
                GLib.idle_add(lambda: gui.location_selected(base_url))
                return
    if len(gui.data.secure_internet) > 1:
        gui.locations_list_model.clear()  # type: ignore
        for i, location in enumerate(gui.data.locations):
            flag_image_file = get_flag_image_file(location['country_code'])
            if flag_image_file:
                flag_image = GdkPixbuf.Pixbuf.new_from_file(flag_image_file)  # type: ignore
                country_name = retrieve_country_name(location['country_code'])
                gui.locations_list_model.append([country_name, flag_image, i])  # type: ignore

        GLib.idle_add(lambda: gui.show_choose_location())
    else:
        base_url = str(gui.data.locations[0]['base_url'])
        GLib.idle_add(lambda: gui.finalize_configuration(base_url))


def finalize_configuration_thread(profile_id: str, gui: EduVpnGui) -> None:
    logger.debug("finalize_configuration_thread")
    config = get_config(gui.data.oauth, gui.data.new_vpn_connection.api_url, profile_id)
    private_key, certificate = create_keypair(gui.data.oauth, gui.data.new_vpn_connection.api_url)

    set_auth_url(gui.data.new_vpn_connection.auth_url)
    GLib.idle_add(lambda: gui.configuration_finalized(config, private_key, certificate))
