import logging
import webbrowser
import signal
import sys
from datetime import datetime, timedelta
from typing import Any, Callable, Iterator, Optional
from eduvpn_common.error import WrappedError, ErrorLevel
from eduvpn_common.discovery import DiscoOrganization, DiscoServer
from eduvpn_common.main import EduVPN
from eduvpn_common.server import Server, InstituteServer, SecureInternetServer
from eduvpn_common.state import State, StateType
from eduvpn.server import ServerDatabase

from eduvpn.connection import Connection

from eduvpn import nm
from eduvpn.config import Configuration
from eduvpn.utils import (
    model_transition,
    run_in_background_thread,
    run_in_main_gtk_thread,
)
from eduvpn.variants import ApplicationVariant
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def now() -> datetime:
    return datetime.now()


class Validity:
    def __init__(self, end: datetime) -> None:
        self.end = end

    @property
    def remaining(self) -> timedelta:
        """
        Return the duration from now until expiry.
        """
        return self.end - now()

    @property
    def is_expired(self) -> bool:
        """
        Return True if the validity has expired.
        """
        return now() >= self.end


class ApplicationModelTransitions:
    def __init__(self, common: EduVPN, variant: ApplicationVariant) -> None:
        self.common = common
        self.common.register_class_callbacks(self)
        self.server_db = ServerDatabase(common, variant.use_predefined_servers)

    @model_transition(State.NO_SERVER, StateType.ENTER)
    def get_previous_servers(self, old_state: str, servers):
        has_wireguard = nm.is_wireguard_supported()
        self.common.set_support_wireguard(has_wireguard)
        return servers

    @model_transition(State.SEARCH_SERVER, StateType.ENTER)
    def parse_discovery(self, old_state: str, _):
        saved_servers = self.common.get_saved_servers()
        # Whether or not the SEARCH_SERVER screen
        # should be the 'main' screen
        is_main = len(saved_servers) == 0
        return (self.server_db.disco, is_main)

    @model_transition(State.LOADING_SERVER, StateType.ENTER)
    def loading_server(self, old_state: str, data: str):
        return data

    @model_transition(State.CHOSEN_SERVER, StateType.ENTER)
    def chosen_server(self, old_state: str, data: str):
        return data

    @model_transition(State.DISCONNECTING, StateType.ENTER)
    def disconnecting(self, old_state: str, server):
        return server

    @model_transition(State.ASK_PROFILE, StateType.ENTER)
    def parse_profiles(self, old_state: str, profiles):
        return profiles

    @model_transition(State.ASK_LOCATION, StateType.ENTER)
    def parse_locations(self, old_state: str, locations: List[str]):
        return locations

    @model_transition(State.AUTHORIZED, StateType.ENTER)
    def authorized(self, old_state: str, data: str):
        return data

    @model_transition(State.OAUTH_STARTED, StateType.ENTER)
    def start_oauth(self, old_state: str, url: str):
        self.open_browser(url)
        return url

    @model_transition(State.REQUEST_CONFIG, StateType.ENTER)
    def parse_request_config(self, old_state: str, data: str):
        return data

    @model_transition(State.DISCONNECTED, StateType.ENTER)
    def parse_config(self, old_state: str, server):
        return server

    @run_in_background_thread("open-browser")
    def open_browser(self, url):
        webbrowser.open(url)

    @model_transition(State.CONNECTED, StateType.ENTER)
    def parse_connected(self, old_state: str, server):
        return server

    @model_transition(State.CONNECTING, StateType.ENTER)
    def parse_connecting(self, old_state: str, server):
        return server


class ApplicationModel:
    def __init__(self, common: EduVPN, config, variant: ApplicationVariant, nm_manager) -> None:
        self.common = common
        self.config = config
        self.transitions = ApplicationModelTransitions(common, variant)
        self.variant = variant
        self.nm_manager = nm_manager
        self.common.register_class_callbacks(self)

    @property
    def server_db(self):
        return self.transitions.server_db

    @property
    def current_server(self):
        return self.common.get_current_server()

    @current_server.setter
    def current_server(self, current_server):
        self.transitions.current_server = current_server

    def get_expiry(self, expire_time: datetime) -> Validity:
        return Validity(expire_time)

    def change_secure_location(self):
        self.common.change_secure_location()

    def set_secure_location(self, location_id: str):
        self.common.set_secure_location(location_id)

    def set_search_server(self):
        self.common.set_search_server()

    def cancel_oauth(self):
        self.common.cancel_oauth()

    def go_back(self):
        self.common.go_back()

    def should_renew_button(self) -> int:
        return self.common.should_renew_button()

    def add(self, server, callback=None):
        if isinstance(server, InstituteServer):
            self.common.add_institute_acces(server.url)
        elif isinstance(server, DiscoServer):
            self.common.add_institute_access(server.base_url)
        elif isinstance(server, SecureInternetServer) or isinstance(
            server, DiscoOrganization
        ):
            self.common.add_secure_internet_home(server.org_id)
        elif isinstance(server, Server):
            self.common.add_custom_server(server.url)
        else:
            raise Exception("Server cannot be added")

        if callback:
            callback(str(server))

    def remove(self, server):
        if isinstance(server, InstituteServer):
            self.common.remove_institute_access(server.url)
        elif isinstance(server, SecureInternetServer):
            self.common.remove_secure_internet()
        elif isinstance(server, Server):
            self.common.remove_custom_server(server.url)

    def connect(
        self, server, callback: Optional[Callable] = None, ensure_exists=False
    ) -> None:
        config = None
        config_type = None
        if ensure_exists:
            self.add(server)
        if isinstance(server, InstituteServer):
            config, config_type = self.common.get_config_institute_access(
                server.url, self.config.prefer_tcp
            )
        elif isinstance(server, DiscoServer):
            config, config_type = self.common.get_config_institute_access(
                server.base_url, self.config.prefer_tcp
            )
        elif isinstance(server, SecureInternetServer) or isinstance(server, DiscoOrganization):
            config, config_type = self.common.get_config_secure_internet(server.org_id, self.config.prefer_tcp)
        elif isinstance(server, Server):
            config, config_type = self.common.get_config_custom_server(server.url, self.config.prefer_tcp)

        default_gateway = True
        current_profile = server.profiles.current
        if current_profile is not None:
            default_gateway = current_profile.default_gateway

        def on_connected():
            self.common.set_connected()
            if callback:
                callback()

        def on_connect(_):
            self.nm_manager.activate_connection(on_connected)

        @run_in_main_gtk_thread
        def connect(config, config_type):
            connection = Connection.parse(config, config_type)
            connection.connect(self.nm_manager, default_gateway, on_connect)

        self.common.set_connecting()
        connect(config, config_type)

    # https://github.com/eduvpn/documentation/blob/v3/API.md#session-expiry
    def renew_session(self):
        was_connected = self.is_connected()

        def reconnect():
            # Delete the OAuth access and refresh token
            # Start the OAuth authorization flow
            self.common.renew_session()
            # Automatically reconnect to the server
            self.activate_connection()

        if was_connected:
            # Call /disconnect and reconnect with callback
            self.deactivate_connection(reconnect)
        else:
            reconnect()

    @run_in_main_gtk_thread
    def disconnect(self, callback: Optional[Callable] = None) -> None:
        self.nm_manager.deactivate_connection(callback)

    def set_profile(self, profile, connect=False):
        was_connected = self.is_connected()

        def do_profile():
            # Set the profile ID
            self.common.set_profile(profile.identifier)

            # Connect if we should and if we were previously connected
            if connect and was_connected:
                self.activate_connection()

        # Deactivate connection if we are connected
        # and the connection should be modified
        # the do_profile will be called in the callback
        if was_connected and connect:
            self.deactivate_connection(do_profile)
        else:
            do_profile()

    def activate_connection(self):
        if not self.current_server:
            return

        self.connect(self.current_server)

    def deactivate_connection(self, callback: Optional[Callable] = None) -> None:
        self.common.set_disconnecting()

        @run_in_background_thread("on-disconnected")
        def on_disconnected():
            self.common.set_disconnected()
            if callback:
                callback()

        self.disconnect(on_disconnected)

    def search_predefined(self, query: str) -> Iterator[Any]:
        return self.server_db.search_predefined(query)

    def search_custom(self, query: str) -> Iterator[Any]:
        return self.server_db.search_custom(query)

    def is_no_server(self) -> bool:
        return self.common.in_fsm_state(State.NO_SERVER)

    def is_search_server(self) -> bool:
        return self.common.in_fsm_state(State.SEARCH_SERVER)

    def is_connected(self) -> bool:
        return self.common.in_fsm_state(State.CONNECTED)

    def is_disconnected(self) -> bool:
        return self.common.in_fsm_state(State.DISCONNECTED)

    def is_oauth_started(self) -> bool:
        return self.common.in_fsm_state(State.OAUTH_STARTED)

class Application:
    def __init__(self, variant: ApplicationVariant, common: EduVPN) -> None:
        self.variant = variant
        self.nm_manager = nm.NMManager(variant)
        self.common = common
        directory = variant.config_prefix
        self.config = Configuration.load(directory)
        self.model = ApplicationModel(common, self.config, variant, self.nm_manager)
        def signal_handler(_signal, _frame):
            if self.model.is_oauth_started():
                self.common.cancel_oauth()
            self.common.go_back()
            self.common.deregister()
            sys.exit(1)
        signal.signal(signal.SIGINT, signal_handler)


    def on_network_update_callback(self, state, initial=False):
        try:
            if state == nm.ConnectionState.CONNECTED:
                if self.model.is_disconnected() or initial:
                    self.common.set_connected()
            elif state == nm.ConnectionState.CONNECTING:
                if self.model.is_disconnected():
                    self.common.set_connecting()
            elif state == nm.ConnectionState.DISCONNECTED:
                if self.model.is_connected():
                    self.common.set_disconnecting()
                    self.common.set_disconnected(cleanup=False)
        except:
            return

    @run_in_main_gtk_thread
    def initialize_network(self, needs_update=True) -> None:
        """
        Determine the current network state.
        """
        # Check if a previous network configuration exists.
        uuid = self.nm_manager.existing_connection
        if uuid:
            self.on_network_update_callback(self.nm_manager.connection_state, needs_update)

        @run_in_background_thread("on-network-update")
        def update(state):
            self.on_network_update_callback(state, False)

        self.nm_manager.subscribe_to_status_changes(update)
