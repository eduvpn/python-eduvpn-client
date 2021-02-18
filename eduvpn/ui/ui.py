# eduvpngui - The GNU/Linux eduVPN GUI client
#
# Copyright: 2017-2020, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from typing import Any
import os
import webbrowser
import logging

import gi
gi.require_version('Gtk', '3.0')  # noqa: E402
gi.require_version('NM', '1.0')  # noqa: E402
from gi.repository import Gtk

from ..settings import HELP_URL
from ..interface import state as interface_state
from ..server import CustomServer
from ..app import Application
from ..state_machine import (
    ENTER, EXIT, transition_callback, transition_edge_callback)
from ..utils import get_prefix, run_in_main_gtk_thread
from . import search
from .utils import show_ui_component


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


class EduVpnGui:
    def __init__(self, lets_connect: bool):
        """
        Initialize all data structures needed in the GUI
        """
        self.lets_connect = lets_connect

        self.builder: Any = Gtk.Builder()

        prefix = get_prefix()
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
                self.on_connection_switch_state_set
        }
        self.builder.connect_signals(handlers)

        # Hide all objects that are visible on only some pages.
        for name in variable_objects:
            self.show_component(name, False)

        self.app = Application(run_in_main_gtk_thread)

    def run(self):
        logger.info("starting ui")
        self.show_component('applicationWindow', True)
        self.app.connect_state_transition_callbacks(self)
        self.app.initialize()

    # ui functions

    def show_component(self, component: str, show: bool):
        show_ui_component(self.builder, component, show)

    def show_back_button(self, show: bool):
        self.show_component('backButton', show)
        self.show_component('backButtonEventBox', show)

    def set_search_text(self, text: str):
        self.builder.get_object('findYourInstituteSearch').set_text(text)

    # network state transition callbacks

    # TODO

    # interface state transition callbacks

    @transition_callback(interface_state.InterfaceState)
    def default_transition_callback(self, old_state, new_state):
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
            search.init_server_search(self.builder)
            search.connect_selection_handlers(
                self.builder, self.on_select_server)

    @transition_edge_callback(EXIT, interface_state.configure_server_states)
    def exit_search(self, old_state, new_state):
        if not isinstance(new_state, interface_state.configure_server_states):
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

    @transition_edge_callback(ENTER, interface_state.OAuthSetup)
    def enter_OAuthSetup(self, old_state, new_state):
        self.show_component('openBrowserPage', True)

    @transition_edge_callback(EXIT, interface_state.OAuthSetup)
    def exit_OAuthSetup(self, old_state, new_state):
        self.show_component('openBrowserPage', False)

    @transition_edge_callback(ENTER, interface_state.ChooseProfile)
    def enter_ChooseProfile(self, old_state, new_state):
        self.show_component('chooseProfilePage', True)
        self.show_component('profileTreeView', True)

        from gi.repository import Gtk, GObject
        profile_tree_view = self.builder.get_object('profileTreeView')
        text_cell = Gtk.CellRendererText()
        text_cell.set_property("size-points", 14)  # type: ignore
        col = Gtk.TreeViewColumn(None, text_cell, text=0)  # type: ignore
        profile_tree_view.append_column(col)
        profiles_list_model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_PYOBJECT)  # type: ignore
        profile_tree_view.set_model(profiles_list_model)

        selection = profile_tree_view.get_selection()
        selection.connect("changed", self.on_profile_selection_changed)

        profiles_list_model.clear()  # type: ignore
        for profile in new_state.profiles:
            profiles_list_model.append([str(profile), profile])  # type: ignore

    @transition_edge_callback(EXIT, interface_state.ChooseProfile)
    def exit_ChooseProfile(self, old_state, new_state):
        self.show_component('chooseProfilePage', False)
        self.show_component('profileTreeView', False)

        profile_tree_view = self.builder.get_object('profileTreeView')
        selection = profile_tree_view.get_selection()
        selection.disconnect_by_func(self.on_profile_selection_changed)

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
            self.app.network_transition('reconnect')
        else:
            self.app.network_transition('disconnect')
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
