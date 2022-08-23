from typing import Optional
import logging
from .server import (
    PredefinedServer,
    ServerDatabase,
    SecureInternetLocation,
    InstituteAccessServer,
    OrganisationServer,
    CustomServer,
    Profile,
)
from .i18n import extract_translation, retrieve_country_name
from . import nm
import json
from .variants import ApplicationVariant
from .config import Configuration
from eduvpn_common.main import EduVPN
from eduvpn_common.state import State, StateType
from eduvpn.connection import Connection
import webbrowser
from .utils import run_in_background_thread, run_in_main_gtk_thread, model_transition
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def now() -> datetime:
    return datetime.now()


class Validity:
    def __init__(self, end: datetime):
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


class ServerInfo:
    def __init__(
        self,
        display_name,
        support_contact,
        profiles,
        current_profile,
        expire_time,
        location,
    ):
        self.display_name = display_name
        self.support_contact = support_contact
        self.flag_path = None
        self.profiles = profiles
        self.current_profile = current_profile
        self.expire_time = datetime.fromtimestamp(expire_time)

        if location:
            self.flag_path = SecureInternetLocation(location).flag_path
            self.country_name = retrieve_country_name(location)
            self.display_name = f"{self.country_name}\n (via {self.display_name})"

    @property
    def current_profile_index(self):
        return self.profiles.index(self.current_profile)

    @property
    def current_profile_name(self):
        if not self.current_profile:
            return "Unknown"
        return str(self.current_profile)


class ApplicationModel:
    def __init__(self, common: EduVPN):
        self.common = common
        self.server_db = ServerDatabase()
        self.common.register_class_callbacks(self)
        # TODO: combine server and server info
        self.current_server = None
        self.current_server_info = None

    def get_expiry(self, expire_time):
        return Validity(expire_time)

    @model_transition(State.NO_SERVER, StateType.Enter)
    def get_previous_servers(self, old_state: str, data: str):
        previous_servers = json.loads(data)
        configured_servers = []
        for server_dict in previous_servers.get("custom_servers", {}):
            server, _ = self.get_server_info(server_dict, "custom_server")
            if server:
                configured_servers.append(server)

        for server_dict in previous_servers.get("institute_access_servers", {}):
            server, _ = self.get_server_info(server_dict, "institute_access")
            if server:
                configured_servers.append(server)

        server_dict = previous_servers.get("secure_internet_server")
        if server_dict:
            server, server_info = self.get_server_info(server_dict, "secure_internet")
            server.display_name = server_info.country_name
            if server:
                configured_servers.append(server)
        return configured_servers

    @model_transition(State.SEARCH_SERVER, StateType.Enter)
    def parse_discovery(self, old_state: str, _):
        disco_orgs = self.common.get_disco_organizations()
        disco_servers = self.common.get_disco_servers()
        return self.server_db.disco_parse(disco_orgs, disco_servers)

    @model_transition(State.LOADING_SERVER, StateType.Enter)
    def loading_server(self, old_state: str, data: str):
        return data

    @model_transition(State.DISCONNECTING, StateType.Enter)
    def disconnecting(self, old_state: str, data: str):
        return data

    def parse_profiles_dict(self, profiles_dict):
        profiles = []
        for profile in profiles_dict:
            profiles.append(Profile(**profile))
        return profiles

    @model_transition(State.ASK_PROFILE, StateType.Enter)
    def parse_profiles(self, old_state: str, profiles_json: str):
        profiles_parsed = json.loads(profiles_json)["info"]["profile_list"]
        return self.parse_profiles_dict(profiles_parsed)

    @model_transition(State.ASK_LOCATION, StateType.Enter)
    def parse_locations(
        self, old_state: str, locations_json
    ) -> [SecureInternetLocation]:
        locations = json.loads(locations_json)
        location_classes = []

        for location in locations:
            location_classes.append(SecureInternetLocation(location))

        return location_classes

    @model_transition(State.AUTHORIZED, StateType.Enter)
    def authorized(self, old_state: str, data: str):
        return data

    @model_transition(State.OAUTH_STARTED, StateType.Enter)
    def start_oauth(self, old_state: str, url: str):
        self.open_browser(json.loads(url))
        return url

    @model_transition(State.REQUEST_CONFIG, StateType.Enter)
    def parse_request_config(self, old_state: str, data: str):
        return data

    def get_server_info(self, server_info_dict: str, server_type=None):
        server_display_name = extract_translation(
            server_info_dict.get("display_name") or "Unknown Server"
        )
        server_display_contact = server_info_dict.get("support_contact")
        server_display_location = server_info_dict.get("country_code")
        server_display_profiles = []
        current_profile = None

        profiles_dict = server_info_dict.get("profiles")
        expire_time = server_info_dict.get("expire_time")

        if profiles_dict:
            if profiles_dict["info"]["profile_list"] is not None:
                server_display_profiles = self.parse_profiles_dict(
                    profiles_dict["info"]["profile_list"]
                )

                for profile in server_display_profiles:
                    if profile.profile_id == profiles_dict.get("current_profile"):
                        current_profile = profile

        server_info = ServerInfo(
            server_display_name,
            server_display_contact,
            server_display_profiles,
            current_profile,
            expire_time,
            server_display_location,
        )

        # parse server
        identifier = server_info_dict.get("identifier")
        server_type = server_info_dict.get("server_type")
        server = None
        if server_type and identifier:
            if server_type == "secure_internet":
                server = OrganisationServer(server_display_name, identifier)
            elif server_type == "institute_access":
                server = InstituteAccessServer(identifier, server_display_name)
            elif server_type == "custom_server":
                server = CustomServer(identifier)
        else:
            # TODO: Log an error or something?
            pass
        return server, server_info

    @model_transition(State.HAS_CONFIG, StateType.Enter)
    def parse_config(self, old_state: str, data: str):
        server, server_info = self.get_server_info(json.loads(data))
        self.current_server = server
        self.current_server_info = server_info
        return server_info

    @run_in_background_thread("browser-open")
    def open_browser(self, url):
        webbrowser.open(url)

    @model_transition(State.CONNECTED, StateType.Enter)
    def parse_connected(self, old_state: str, data: str):
        server, server_info = self.get_server_info(json.loads(data))
        self.current_server = server
        self.current_server_info = server_info
        return server_info

    @model_transition(State.CONNECTING, StateType.Enter)
    def parse_connecting(self, old_state: str, data: str):
        return data

    @run_in_background_thread("change-secure-location")
    def change_secure_location(self):
        self.common.change_secure_location()

    @run_in_background_thread("set-secure-location")
    def set_secure_location(self, location_id: str):
        self.common.set_secure_location(location_id)

    def should_renew_button(self):
        return self.common.should_renew_button()

    @run_in_background_thread("connect")
    def connect(self, server: PredefinedServer):
        config = None
        config_type = None
        if isinstance(server, InstituteAccessServer):
            config, config_type = self.common.get_config_institute_access(
                server.base_url
            )
        elif isinstance(server, OrganisationServer):
            config, config_type = self.common.get_config_secure_internet(server.org_id)
        elif isinstance(server, CustomServer):
            config, config_type = self.common.get_config_custom_server(server.address)

        def on_connected():
            self.common.set_connected()

        def on_connect(arg):
            client = nm.get_client()
            uuid = nm.get_uuid()
            nm.activate_connection(client, uuid, on_connected)

        @run_in_main_gtk_thread
        def connect(config, config_type):
            connection = Connection.parse(config, config_type)
            connection.connect(on_connect)

        self.current_server = server
        self.common.set_connecting()
        connect(config, config_type)

    # https://github.com/eduvpn/documentation/blob/v3/API.md#session-expiry
    @run_in_background_thread("renew-session")
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
    def disconnect(self, callback=None):
        client = nm.get_client()
        uuid = nm.get_uuid()
        nm.deactivate_connection(client, uuid, callback)

    def set_profile(self, profile, connect=False):
        was_connected = self.is_connected()

        def do_profile():
            # Set the profile ID
            self.common.set_profile(profile.id)

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

    @run_in_background_thread("deactivate")
    def deactivate_connection(self, callback=None):
        self.common.set_disconnecting()

        @run_in_background_thread("on-disconnected")
        def on_disconnected():
            self.common.set_disconnected()
            if callback:
                callback()

        self.disconnect(on_disconnected)

    def search_predefined(self, query: str):
        return self.server_db.search_predefined(query)

    def search_custom(self, query: str):
        return self.server_db.search_custom(query)

    def is_connected(self):
        return self.common.in_fsm_state(State.CONNECTED)

    def is_disconnected(self):
        return self.common.in_fsm_state(State.HAS_CONFIG)


class Application:
    def __init__(
        self, variant: ApplicationVariant, make_func_threadsafe, common: EduVPN
    ):
        self.variant = variant
        self.make_func_threadsafe = make_func_threadsafe
        self.common = common
        self.config = Configuration.load()
        self.model = ApplicationModel(common)
        self.current_network_uuid: Optional[str] = None

    def initialize(self):
        self.initialize_network()

    @run_in_background_thread("on-network-update")
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

    def initialize_network(self):
        """
        Determine the current network state.
        """
        # Check if a previous network configuration exists.
        uuid = nm.get_existing_configuration_uuid()
        if uuid:
            self.on_network_update_callback(nm.get_connection_state(), True)
        else:
            # TODO: Implement with Go
            pass

        nm.subscribe_to_status_changes(self.on_network_update_callback)
