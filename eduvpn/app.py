import json
import logging
import os
import signal
import webbrowser
from typing import Any, Callable, Iterator, Optional, TextIO

from eduvpn_common.main import EduVPN, ServerType, WrappedError
from eduvpn_common.state import State, StateType
from eduvpn_common.types import ProxyReady, ProxySetup, ReadRxBytes

from eduvpn import nm
from eduvpn.config import Configuration
from eduvpn.connection import (
    Config,
    Connection,
    parse_config,
    parse_expiry,
    parse_tokens,
)
from eduvpn.keyring import DBusKeyring, InsecureFileKeyring, TokenKeyring
from eduvpn.server import ServerDatabase, parse_profiles, parse_required_transition
from eduvpn.utils import (
    handle_exception,
    model_transition,
    run_in_background_thread,
    run_in_glib_thread,
)
from eduvpn.variants import ApplicationVariant

logger = logging.getLogger(__name__)


class ApplicationModelTransitions:
    def __init__(self, common: EduVPN, variant: ApplicationVariant) -> None:
        self.common = common
        self.common.register_class_callbacks(self)
        self.server_db = ServerDatabase(common, variant.use_predefined_servers)

    @model_transition(State.MAIN, StateType.ENTER)
    def get_previous_servers(self, old_state: State, data):
        logger.debug(f"Transition: MAIN, old state: {old_state}")
        return self.server_db.configured

    @model_transition(State.DEREGISTERED, StateType.ENTER)
    def deregistered(self, old_state: State, data: str):
        logger.debug(f"Transition: DEREGISTERED, old state: {old_state}")
        return data

    @model_transition(State.ADDING_SERVER, StateType.ENTER)
    def adding_server(self, old_state: State, data: str):
        logger.debug(f"Transition: ADDING_SERVER, old state: {old_state}")
        return data

    @model_transition(State.GETTING_CONFIG, StateType.ENTER)
    def getting_config(self, old_state: State, data: str):
        logger.debug(f"Transition: GETTING_CONFIG, old state: {old_state}")
        return data

    @model_transition(State.DISCONNECTED, StateType.ENTER)
    def disconnected_server(self, old_state: State, data: str):
        logger.debug(f"Transition: DISCONNECTED, old state: {old_state}")
        return self.server_db.current

    @model_transition(State.DISCONNECTING, StateType.ENTER)
    def disconnecting(self, old_state: State, data):
        logger.debug(f"Transition: DISCONNECTING, old state: {old_state}")
        return self.server_db.current

    @model_transition(State.ASK_PROFILE, StateType.ENTER)
    def ask_profile(self, old_state: State, data: str):
        logger.debug(f"Transition: ASK_PROFILE, old state: {old_state}")
        cookie, profiles = parse_required_transition(data, get=parse_profiles)

        def set_profile(prof):
            self.common.cookie_reply(cookie, prof)

        return (set_profile, profiles)

    @model_transition(State.ASK_LOCATION, StateType.ENTER)
    def ask_location(self, old_state: State, data):
        cookie, locations = parse_required_transition(data)

        def set_location(loc):
            self.common.cookie_reply(cookie, loc)

        return (set_location, locations)

    @model_transition(State.OAUTH_STARTED, StateType.ENTER)
    def start_oauth(self, old_state: State, url: str):
        logger.debug(f"Transition: OAUTH_STARTED, old state: {old_state}")
        self.open_browser(url)
        return url

    @model_transition(State.GOT_CONFIG, StateType.ENTER)
    def parse_config(self, old_state: State, data):
        logger.debug(f"Transition: GOT_CONFIG, old state: {old_state}")
        return data

    @run_in_background_thread("open-browser")
    def open_browser(self, url):
        logger.debug(f"Opening web browser with url: {url}")
        webbrowser.open(url)
        # Explicitly wait to not have zombie processes
        # See https://bugs.python.org/issue5993
        logger.debug("Running os.wait for browser")
        try:
            os.wait()
        except ChildProcessError:
            pass
        logger.debug("Done waiting for browser")

    @model_transition(State.CONNECTED, StateType.ENTER)
    def parse_connected(self, old_state: State, data):
        logger.debug(f"Transition: CONNECTED, old state: {old_state}")
        server = self.server_db.current
        expire_times = parse_expiry(self.common.get_expiry_times())
        return (server, expire_times)

    @model_transition(State.CONNECTING, StateType.ENTER)
    def parse_connecting(self, old_state: State, data):
        logger.debug(f"Transition: CONNECTING, old state: {old_state}")
        return self.server_db.current


class ApplicationModel:
    def __init__(
        self,
        common: EduVPN,
        config,
        variant: ApplicationVariant,
        nm_manager,
    ) -> None:
        self.common = common
        self.config = config
        self.keyring: TokenKeyring = DBusKeyring(variant)
        if not self.keyring.available:
            self.keyring = InsecureFileKeyring(variant)
        self.transitions = ApplicationModelTransitions(common, variant)
        self.variant = variant
        self.nm_manager = nm_manager
        self._was_tcp = False
        self._should_failover = False
        self._peer_ips_proxy = None

    def register(self, debug: bool):
        self.common.register(debug=debug)
        self.common.set_token_handler(self.load_tokens, self.save_tokens)

    def cancel(self):
        # Cancel any eduvpn-common operation
        self.common.cancel()

        # Cancel any NetworkManager operation
        self.nm_manager.cancel()

    @property
    def server_db(self):
        return self.transitions.server_db

    @property
    def current_server(self):
        return self.server_db.current

    def get_failover_rx(self, filehandler: Optional[TextIO]) -> int:
        rx_bytes = self.nm_manager.get_stats_bytes(filehandler)
        if rx_bytes is None:
            return -1
        return rx_bytes

    def should_failover(self):
        if self._should_failover:
            logger.debug("eduvpn-common reports we should failover")

            if self._was_tcp:
                logger.debug(
                    "Protocol is not WireGuard and TCP was not previously triggered, failover should not continue"
                )
                return False
            return True

        logger.debug("Failover should not continue")
        return False

    def reconnect_tcp(self, callback: Callable):
        def on_reconnected(success: bool):
            callback(success)

        self.reconnect(on_reconnected, prefer_tcp=True)

    def start_failover(self, callback: Callable):
        try:
            rx_bytes_file = self.nm_manager.open_stats_file("rx_bytes")
            if rx_bytes_file is None:
                logger.debug("Failed to initialize failover, failed to open rx bytes file")
                callback(False)
                return
            endpoint = self.nm_manager.failover_endpoint_ip
            if endpoint is None:
                logger.debug("Failed to initialize failover, failed to get endpoint")
                callback(False)
                return
            mtu = self.nm_manager.mtu
            if mtu is None:
                logger.debug("failed to get MTU for failover, setting MTU to 1000")
                mtu = 1000
            logger.debug(
                f"starting failover with gateway {endpoint} and MTU {mtu} for protocol {self.nm_manager.protocol}"
            )
            dropped = self.common.start_failover(
                endpoint,
                mtu,
                ReadRxBytes(lambda: self.get_failover_rx(rx_bytes_file)),
            )

            if dropped:
                logger.debug("Failover exited, connection is dropped")
                if self.common.in_state(State.CONNECTED):
                    self.reconnect_tcp(callback)
                    return
                # Dropped but not relevant anymore
                callback(False)
                return
            else:
                logger.debug("Failover exited, connection is NOT dropped")
                callback(False)
                return
        except WrappedError as e:
            logger.debug(f"Failed failover, error: {e}")
            callback(False)
            return

    def change_secure_location(self, country_code: str):
        server = self.server_db.secure_internet
        if server.country_code == country_code:
            return
        self.common.set_secure_location(server.org_id, country_code)
        self.common.set_state(State.MAIN)

    def go_back(self):
        self.cancel()
        self.common.set_state(State.MAIN)

    def add(self, server, callback=None):
        # TODO: handle discovery types
        self.common.add_server(server.category_id, server.identifier)
        if callback:
            callback(server)

    def remove(self, server):
        self.common.remove_server(server.category_id, server.identifier)
        # Delete tokens from the keyring
        self.clear_tokens(server.category_id, server.identifier)
        self.common.set_state(State.MAIN)

    def connect_get_config(self, server, prefer_tcp: bool = False) -> Config:
        # We prefer TCP if the user has set it or UDP is determined to be blocked
        # TODO: handle discovery and tokens
        config = self.common.get_config(server.category_id, server.identifier, prefer_tcp)
        return parse_config(config)

    def clear_tokens(self, server_type: int, server_id: str):
        attributes = {
            "server": server_id,
            "category": str(ServerType(server_type)),
        }
        try:
            cleared = self.keyring.clear(attributes)
            if not cleared:
                logger.debug("Tokens were not cleared")
        except Exception as e:
            logger.debug("Failed clearing tokens with exception")
            logger.debug(e, exc_info=True)

    def load_tokens(self, server_id: str, server_type: int) -> Optional[str]:
        attributes = {"server": server_id, "category": str(ServerType(server_type))}
        try:
            tokens_json = self.keyring.load(attributes)
            if tokens_json is None:
                logger.debug("No tokens available")
                return None
            tokens = json.loads(tokens_json)
            expires = tokens.get("expires_at", None)
            if expires is None:
                expires = tokens.get("expires", None)
            if expires is None:
                logger.warning("failed to parse expires")
                return None
            d = {
                "access_token": tokens["access"],
                "refresh_token": tokens["refresh"],
                "expires_at": int(expires),
            }
            return json.dumps(d)
        except Exception as e:
            logger.debug("Failed loading tokens with exception:")
            logger.debug(e, exc_info=True)
            return None

    def save_tokens(self, server_id: str, server_type: int, tokens: str):
        tokens_parsed = parse_tokens(tokens)
        if tokens is None or (tokens_parsed.access == "" and tokens_parsed.refresh == ""):
            logger.warning("Got empty tokens, not saving them to the keyring")
            return
        tokens_dict = {}
        tokens_dict["access"] = tokens_parsed.access
        tokens_dict["refresh"] = tokens_parsed.refresh
        tokens_dict["expires_at"] = str(tokens_parsed.expires)
        attributes = {"server": server_id, "category": str(ServerType(server_type))}
        label = f"{server_id} - OAuth Tokens"
        try:
            self.keyring.save(label, attributes, json.dumps(tokens_dict))
        except Exception as e:
            logger.error("Failed saving tokens with exception:")
            logger.error(e, exc_info=True)

    def on_proxy_setup(self, fd, peer_ips):
        logger.debug(f"got proxy fd: {fd}, peer_ips: {peer_ips}")
        self._peer_ips_proxy = json.loads(peer_ips)

    @run_in_background_thread("start-proxy")
    def start_proxy(self, proxy, callback):
        try:
            self.common.start_proxyguard(
                proxy.listen,
                proxy.source_port,
                proxy.peer,
                ProxySetup(self.on_proxy_setup),
                ProxyReady(lambda: callback()),
            )
        except Exception as e:
            handle_exception(self.common, e)

    def connect(
        self,
        server,
        callback: Optional[Callable] = None,
        prefer_tcp: bool = False,
    ) -> None:
        # Variable to be used as a last resort or for debugging
        # to override the prefer TCP setting
        if os.environ.get("EDUVPN_PREFER_TCP", "0") == "1":
            prefer_tcp = True
        config = self.connect_get_config(server, prefer_tcp=prefer_tcp)
        if not config:
            logger.warning("no configuration available")
            if callback:
                callback(False)
            return

        self._was_tcp = prefer_tcp
        self._should_failover = config.should_failover

        def on_connected(success: bool):
            if success:
                self.common.set_state(State.CONNECTED)
            else:
                self.common.set_state(State.DISCONNECTING)
                self.common.set_state(State.DISCONNECTED)
            if callback:
                callback(success)

        def on_connect(success: bool):
            if success:
                self.nm_manager.activate_connection(on_connected)
            else:
                self.common.set_state(State.DISCONNECTING)
                self.common.set_state(State.DISCONNECTED)
                if callback:
                    callback(False)

        @run_in_glib_thread
        def connect(config):
            self.common.set_state(State.CONNECTING)
            connection = Connection.parse(config)
            connection.connect(
                self.nm_manager,
                config.default_gateway,
                self.config.allow_wg_lan,
                config.dns_search_domains,
                config.proxy,
                self._peer_ips_proxy,
                on_connect,
            )
            self._peer_ips_proxy = None

        if config.proxy:
            self.start_proxy(config.proxy, lambda: connect(config))
        else:
            connect(config)

    def reconnect(self, callback: Optional[Callable] = None, prefer_tcp: bool = False):
        def on_disconnected(success: bool):
            if success:
                self.activate_connection(callback, prefer_tcp=prefer_tcp)

        # Reconnect
        self.deactivate_connection(on_disconnected)

    # https://github.com/eduvpn/documentation/blob/v3/API.md#session-expiry
    def renew_session(self, callback: Optional[Callable] = None):
        was_connected = self.common.in_state(State.CONNECTED)

        @run_in_background_thread("reconnect")
        def reconnect(success: bool = True):
            if not success:
                if callback:
                    callback(False)
                return
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

    def disconnect(self, callback: Optional[Callable] = None) -> None:
        self.nm_manager.deactivate_connection(callback)

    def set_profile(self, profile: str, connect=False):
        was_connected = self.common.in_state(State.CONNECTED)

        def do_profile(success: bool = True):
            if not success:
                return
            # Set the profile ID
            self.common.set_profile(profile)

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
        if not self.common.in_state(State.DISCONNECTED) and not self.common.in_state(State.MAIN):
            if callback:
                logger.error("invalid state to activate connection")
                callback(False)
            return
        if not self.current_server:
            if callback:
                logger.error("failed to get current server")
                callback(False)
            return

        def on_connected(success: bool):
            if callback:
                callback(success)

        self.connect(self.current_server, on_connected, prefer_tcp=prefer_tcp)

    @run_in_background_thread("cleanup")
    def cleanup(self, callback: Callable):
        # We retry this cleanup 2 times
        retries = 2

        # Try to cleanup with a number of retries
        for i in range(retries):
            logger.debug("Cleaning up tokens...")
            try:
                self.common.cleanup()
            except Exception as e:
                # We can try again
                if i < retries - 1:
                    logger.debug(
                        f"Got an error: {str(e)} while cleaning up, try number: {i+1}. This could mean the connection was not fully disconnected yet. Trying again..."
                    )
                else:
                    # All retries are done
                    logger.debug(f"Got an error: {str(e)} while cleaning up, after full retries: {i+1}.")
            else:
                break
        callback()

    def deactivate_connection(self, callback: Optional[Callable] = None) -> None:
        if not self.common.in_state(State.CONNECTED):
            return
        self.common.set_state(State.DISCONNECTING)

        def on_disconnected(success: bool):
            if success:
                self.cleanup()
                self.common.set_state(State.DISCONNECTED)
                if callback:
                    callback(True)
            else:
                self.common.set_state(State.CONNECTED)
                if callback:
                    callback(False)

        self.disconnect(on_disconnected)

    def search_predefined(self, query: str) -> Iterator[Any]:
        return self.server_db.search_predefined(query)

    def search_custom(self, query: str) -> Iterator[Any]:
        return self.server_db.search_custom(query)


class Application:
    def __init__(self, variant: ApplicationVariant, common: EduVPN) -> None:
        self.variant = variant
        self.nm_manager = nm.NMManager(variant)
        self.common = common
        directory = variant.config_prefix
        self.config = Configuration.load(directory)
        self.model = ApplicationModel(common, self.config, variant, self.nm_manager)

        def signal_handler(_signal, _frame):
            self.model.cancel()
            self.common.deregister()

        signal.signal(signal.SIGINT, signal_handler)

    def on_network_update_callback(self, state, initial=False):
        try:
            if state == nm.ConnectionState.CONNECTED:
                if not self.common.in_state(State.GOT_CONFIG) and not initial:
                    return
                if not initial:
                    self.common.set_state(State.CONNECTING)
                # Already connected
                self.common.set_state(State.CONNECTED)
            elif state == nm.ConnectionState.CONNECTING:
                self.common.set_state(State.CONNECTING)
            elif state == nm.ConnectionState.DISCONNECTED:
                if not self.common.in_state(State.CONNECTED):
                    return
                self.common.set_state(State.DISCONNECTING)
                self.common.set_state(State.DISCONNECTED)
        except Exception:
            return

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
