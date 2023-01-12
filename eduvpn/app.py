import json
import logging
import webbrowser
import signal
import sys
from datetime import datetime
from typing import Any, Callable, Iterator, Optional
from eduvpn_common.discovery import DiscoOrganization, DiscoServer
from eduvpn_common.error import WrappedError
from eduvpn_common.main import EduVPN
from eduvpn_common.server import Server, InstituteServer, SecureInternetServer, Config, Token
from eduvpn_common.types import ReadRxBytes
from eduvpn_common.state import State, StateType
from eduvpn.keyring import DBusKeyring, InsecureFileKeyring, TokenKeyring
from eduvpn.server import ServerDatabase

from eduvpn.connection import Connection, Validity

from eduvpn import nm
from eduvpn.config import Configuration
from eduvpn.utils import (
    model_transition,
    run_in_background_thread,
    run_in_main_gtk_thread,
)
from eduvpn.variants import ApplicationVariant
from typing import List, TextIO

logger = logging.getLogger(__name__)


class ApplicationModelTransitions:
    def __init__(self, common: EduVPN, variant: ApplicationVariant) -> None:
        self.common = common
        self.common.register_class_callbacks(self)
        self.server_db = ServerDatabase(common, variant.use_predefined_servers)

    @model_transition(State.NO_SERVER, StateType.ENTER)
    def get_previous_servers(self, old_state: State, servers):
        logger.debug(f"Transition: NO_SERVER, old state: {old_state.name}")
        has_wireguard = nm.is_wireguard_supported()
        self.common.set_support_wireguard(has_wireguard)
        return servers

    @model_transition(State.SEARCH_SERVER, StateType.ENTER)
    def parse_discovery(self, old_state: State, _):
        logger.debug(f"Transition: SEARCH_SERVER, old state: {old_state.name}")
        saved_servers = self.common.get_saved_servers()
        # Whether or not the SEARCH_SERVER screen
        # should be the 'main' screen
        if saved_servers is not None:
            is_main = len(saved_servers) == 0
        else:
            is_main = True
        return (self.server_db.disco, is_main)

    @model_transition(State.LOADING_SERVER, StateType.ENTER)
    def loading_server(self, old_state: State, data: str):
        logger.debug(f"Transition: LOADING_SERVER, old state: {old_state.name}")
        return data

    @model_transition(State.CHOSEN_SERVER, StateType.ENTER)
    def chosen_server(self, old_state: State, data: str):
        logger.debug(f"Transition: CHOSEN_SERVER, old state: {old_state.name}")
        return data

    @model_transition(State.DISCONNECTING, StateType.ENTER)
    def disconnecting(self, old_state: State, server):
        logger.debug(f"Transition: DISCONNECTING, old state: {old_state.name}")
        return server

    @model_transition(State.ASK_PROFILE, StateType.ENTER)
    def parse_profiles(self, old_state: State, profiles):
        logger.debug(f"Transition: ASK_PROFILE, old state: {old_state.name}")
        return profiles

    @model_transition(State.ASK_LOCATION, StateType.ENTER)
    def parse_locations(self, old_state: State, locations: List[str]):
        logger.debug(f"Transition: ASK_LOCATION, old state: {old_state.name}")
        return locations

    @model_transition(State.AUTHORIZED, StateType.ENTER)
    def authorized(self, old_state: State, data: str):
        logger.debug(f"Transition: AUTHORIZED, old state: {old_state.name}")
        return data

    @model_transition(State.OAUTH_STARTED, StateType.ENTER)
    def start_oauth(self, old_state: State, url: str):
        logger.debug(f"Transition: OAUTH_STARTED, old state: {old_state.name}")
        self.open_browser(url)
        return url

    @model_transition(State.REQUEST_CONFIG, StateType.ENTER)
    def parse_request_config(self, old_state: State, data: str):
        logger.debug(f"Transition: REQUEST_CONFIG, old state: {old_state.name}")
        return data

    @model_transition(State.DISCONNECTED, StateType.ENTER)
    def parse_config(self, old_state: State, server):
        logger.debug(f"Transition: DISCONNECTED, old state: {old_state.name}")
        return server

    @run_in_background_thread("open-browser")
    def open_browser(self, url):
        logger.debug(f"Opening web browser with url: {url}")
        webbrowser.open(url)

    @model_transition(State.CONNECTED, StateType.ENTER)
    def parse_connected(self, old_state: State, server):
        logger.debug(f"Transition: CONNECTED, old state: {old_state.name}")
        return server

    @model_transition(State.CONNECTING, StateType.ENTER)
    def parse_connecting(self, old_state: State, server):
        logger.debug(f"Transition: CONNECTING, old state: {old_state.name}")
        return server


class ApplicationModel:
    def __init__(
        self, common: EduVPN, config, variant: ApplicationVariant, nm_manager
    ) -> None:
        self.common = common
        self.config = config
        self.keyring: TokenKeyring = DBusKeyring(variant)
        if not self.keyring.available:
            self.keyring = InsecureFileKeyring(variant)
        self.transitions = ApplicationModelTransitions(common, variant)
        self.variant = variant
        self.nm_manager = nm_manager
        self.udp_blocked = False
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

    def get_failover_rx(self, filehandler: Optional[TextIO]) -> int:
        rx_bytes = self.nm_manager.get_stats_bytes(filehandler)
        if rx_bytes is None:
            return -1
        return rx_bytes

    def should_failover(self):
        current_vpn_protocol = self.nm_manager.protocol
        if current_vpn_protocol != "WireGuard":
            logger.debug(
                f"Current protocol ({current_vpn_protocol}) does not support failover"
            )
            return False
        return True

    def start_failover(self):
        try:
            rx_bytes_file = self.nm_manager.open_stats_file("rx_bytes")
            if rx_bytes_file is None:
                logger.debug(
                    "Failed to initialize failover, failed to open rx bytes file"
                )
                return False
            endpoint = self.nm_manager.wg_endpoint_ip
            if endpoint is None:
                logger.debug(
                    "Failed to initialize failover, failed to get WireGuard endpoint"
                )
                return False
            wg_mtu = self.nm_manager.wireguard_mtu
            if wg_mtu is None:
                logger.debug(
                    "failed to get WireGuard MTU, setting MTU to 1000"
                )
                wg_mtu = 1000
            dropped = self.common.start_failover(
                endpoint, wg_mtu, ReadRxBytes(lambda: self.get_failover_rx(rx_bytes_file))
            )
            has_wireguard = nm.is_wireguard_supported()

            def on_reconnected():
                self.common.set_support_wireguard(has_wireguard)

            if dropped:
                logger.debug("Failover exited, connection is dropped")
                if self.is_connected():
                    has_wireguard = nm.is_wireguard_supported()

                    # Set udp blocked and disable wireguard
                    self.udp_blocked = True
                    self.common.set_support_wireguard(False)
                    self.reconnect(on_reconnected, prefer_tcp=True)
                    return True
                # Dropped but not relevant anymore
                return False
            else:
                logger.debug("Failover exited, connection is NOT dropped")
                return False
        except WrappedError as e:
            logger.debug(f"Failed to start failover, error: {e}")
            return False

    def cancel_failover(self):
        try:
            self.common.cancel_failover()
        except WrappedError as e:
            logger.debug(f"Failed to cancel failover, error: {e}")

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

        # Delete tokens from the keyring
        self.clear_tokens(server)

    def connect_get_config(self, server, tokens=None, prefer_tcp: bool = False) -> Optional[Config]:
        # We prefer TCP if the user has set it or UDP is determined to be blocked
        if isinstance(server, InstituteServer):
            return self.common.get_config_institute_access(
                server.url, prefer_tcp, tokens
            )
        elif isinstance(server, DiscoServer):
            return self.common.get_config_institute_access(
                server.base_url, prefer_tcp, tokens
            )
        elif isinstance(server, SecureInternetServer) or isinstance(
            server, DiscoOrganization
        ):
            return self.common.get_config_secure_internet(
                server.org_id, prefer_tcp, tokens
            )
        elif isinstance(server, Server):
            return self.common.get_config_custom_server(
                server.url, prefer_tcp, tokens
            )
        raise Exception("No server to get a config for")

    def clear_tokens(self, server):
        attributes = {
            "server": server.url,
            "category": server.category,
        }
        try:
            cleared = self.keyring.clear(attributes)
            if not cleared:
                logger.debug("Tokens were not cleared")
        except Exception as e:
            logger.debug("Failed clearing tokens with exception")
            logger.debug(e, exc_info=True)

    def load_tokens(self, server) -> Optional[Token]:
        attributes = {
            "server": server.url,
            "category": server.category
        }
        try:
            tokens_json = self.keyring.load(attributes)
            if tokens_json is None:
                logger.debug("No tokens available")
                return None
            tokens = json.loads(tokens_json)
            return Token(tokens["access"], tokens["refresh"], int(tokens["expires"]))
        except Exception as e:
            logger.debug("Failed loading tokens with exception:")
            logger.debug(e, exc_info=True)
            return None

    def save_tokens(self, server, tokens):
        tokens_dict = {}
        tokens_dict["access"] = tokens.access
        tokens_dict["refresh"] = tokens.refresh
        tokens_dict["expires"] = str(tokens.expires)
        attributes = {
            "server": server.url,
            "category": server.category,
        }
        label = f"{server.url} - OAuth Tokens"
        try:
            self.keyring.save(label, attributes, json.dumps(tokens_dict))
        except Exception as e:
            logger.debug("Failed saving tokens with exception:")
            logger.debug(e, exc_info=True)

    def connect(
            self, server, callback: Optional[Callable] = None, ensure_exists=False, prefer_tcp: bool = False
    ) -> None:
        config = None
        config_type = None
        if ensure_exists:
            self.add(server)

        tokens = self.load_tokens(server)
        config = self.connect_get_config(server, tokens, prefer_tcp=prefer_tcp)
        if not config:
            raise Exception("No configuration available")

        self.save_tokens(server, config.tokens)

        # Get the updated info from the go library
        # Because profiles can be switched
        # And we need the most updated profile settings for default gateway
        server = self.current_server

        default_gateway = True
        if server.profiles is not None and server.profiles.current is not None:
            default_gateway = server.profiles.current.default_gateway

        def on_connected():
            if callback:
                callback()

        def on_connect(_):
            self.nm_manager.activate_connection(on_connected)

        @run_in_main_gtk_thread
        def connect(config, config_type):
            connection = Connection.parse(str(config), config.config_type)
            connection.connect(self.nm_manager, default_gateway, on_connect)

        self.common.set_connecting()
        connect(config, config_type)

    def reconnect(self, callback: Optional[Callable] = None, prefer_tcp: bool = False):
        def on_connected():
            if callback:
                callback()

        def on_disconnected():
            self.activate_connection(on_connected, prefer_tcp=prefer_tcp)

        # Reconnect
        self.deactivate_connection(on_disconnected)

    # https://github.com/eduvpn/documentation/blob/v3/API.md#session-expiry
    def renew_session(self, callback: Optional[Callable] = None):
        was_connected = self.is_connected()

        def reconnect():
            # Delete the OAuth access and refresh token
            # Start the OAuth authorization flow
            self.common.renew_session()
            # Automatically reconnect to the server
            self.activate_connection(callback)

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

    def activate_connection(self, callback: Optional[Callable] = None, prefer_tcp: bool = False):
        if not self.current_server:
            return

        self.connect(self.current_server, callback, prefer_tcp=prefer_tcp)

    def deactivate_connection(self, callback: Optional[Callable] = None) -> None:
        self.common.set_disconnecting()

        @run_in_background_thread("on-disconnected")
        def on_disconnected():
            server = self.current_server
            tokens = None
            if server:
                tokens = self.load_tokens(server)
            else:
                logger.warning("Unable to get tokens for /disconnect, no server")
            self.common.set_disconnected(True, tokens)
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

    def is_connecting(self) -> bool:
        return self.common.in_fsm_state(State.CONNECTING)

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
            self.common.deregister()
            sys.exit(1)

        signal.signal(signal.SIGINT, signal_handler)

    def on_network_update_callback(self, state, initial=False):
        try:
            if state == nm.ConnectionState.CONNECTED:
                if self.model.is_connecting() or initial:
                    self.common.set_connected()
            elif state == nm.ConnectionState.CONNECTING:
                if self.model.is_disconnected():
                    self.common.set_connecting()
            elif state == nm.ConnectionState.DISCONNECTED:
                if self.model.is_connected():
                    self.common.set_disconnecting()
                    self.common.set_disconnected(cleanup=False)
        except Exception:
            return

    @run_in_main_gtk_thread
    def initialize_network(self, needs_update=True) -> None:
        """
        Determine the current network state.
        """
        # Check if a previous network configuration exists.
        uuid = self.nm_manager.existing_connection
        if uuid:
            self.on_network_update_callback(
                self.nm_manager.connection_state, needs_update
            )

        @run_in_background_thread("on-network-update")
        def update(state):
            self.on_network_update_callback(state, False)

        self.nm_manager.subscribe_to_status_changes(update)
