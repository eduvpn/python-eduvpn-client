from typing import Optional
import logging
from gettext import gettext as _
from .server import PredefinedServer, ServerDatabase, SecureInternetLocation, InstituteAccessServer, OrganisationServer, CustomServer, Profile
from .i18n import extract_translation, retrieve_country_name
from . import nm
import json
from .variants import ApplicationVariant
from .config import Configuration
from .utils import run_periodically
from eduvpn_common.main import EduVPN
import eduvpn_common.event as common
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
    def __init__(self, display_name, support_contact, profiles, current_profile, expire_time, location):
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
    def current_profile_name(self):
        if not self.current_profile:
            return "Unknown"
        return str(self.current_profile)

class ApplicationModel:
    def __init__(self, common: EduVPN):
        self.common = common
        self.server_db = ServerDatabase()
        self.common.register_class_callbacks(self)
        self.current_server = None
        self.is_connected = False

    def get_expiry(self, expire_time):
        return Validity(expire_time)

    @model_transition("No_Server", common.StateType.Enter)
    def get_previous_servers(self, old_state: str, data: str):
        previous_servers = json.loads(data)
        configured_servers = []
        for server_dict in previous_servers.get('custom_servers', {}):
            server, _ = self.get_server_info(server_dict, "custom_server")
            if server:
                configured_servers.append(server)

        for server_dict in previous_servers.get('institute_access_servers', {}):
            server, _ = self.get_server_info(server_dict, "institute_access")
            if server:
                configured_servers.append(server)

        server_dict = previous_servers.get('secure_internet_server')
        if server_dict:
            server, server_info = self.get_server_info(server_dict, "secure_internet")
            server.display_name = server_info.country_name
            if server:
                configured_servers.append(server)
        return configured_servers

    @model_transition("Search_Server", common.StateType.Enter)
    def parse_discovery(self, old_state: str, _):
        disco_orgs = self.common.get_disco_organizations()
        disco_servers = self.common.get_disco_servers()
        return self.server_db.disco_parse(disco_orgs, disco_servers)

    @model_transition("Loading_Server", common.StateType.Enter)
    def loading_server(self, old_state: str, data: str):
        return data

    def parse_profiles_dict(self, profiles_dict):
        profiles = []
        for profile in profiles_dict:
            profiles.append(Profile(**profile))
        return profiles

    @model_transition("Ask_Profile", common.StateType.Enter)
    def parse_profiles(self, old_state: str, profiles_json: str):
        profiles_parsed = json.loads(profiles_json)['info']['profile_list']
        return self.parse_profiles_dict(profiles_parsed)

    @model_transition("Ask_Location", common.StateType.Enter)
    def parse_locations(self, old_state: str, locations_json) -> [SecureInternetLocation]:
        locations = json.loads(locations_json)
        location_classes = []

        for location in locations:
            location_classes.append(SecureInternetLocation(location))

        return location_classes

    @model_transition("Authorized", common.StateType.Enter)
    def authorized(self, old_state: str, data: str):
        return data

    @model_transition("OAuth_Started", common.StateType.Enter)
    def start_oauth(self, old_state: str, url: str):
        self.open_browser(url)
        return url

    @model_transition("Request_Config", common.StateType.Enter)
    def parse_request_config(self, old_state: str, data: str):
        return data

    def get_server_info(self, server_info_dict: str, server_type=None):
        server_display_name = extract_translation(server_info_dict.get('display_name') or "Unknown Server")
        server_display_contact = server_info_dict.get('support_contact')
        server_display_location = server_info_dict.get('country_code')
        server_display_profiles = []
        current_profile = None

        profiles_dict = server_info_dict.get('profiles')
        expire_time = server_info_dict.get('expire_time')

        if profiles_dict:
            if profiles_dict['info']['profile_list'] is not None:
                server_display_profiles = self.parse_profiles_dict(profiles_dict['info']['profile_list'])

                for profile in server_display_profiles:
                    if profile.profile_id == profiles_dict.get('current_profile'):
                        current_profile = profile

        server_info = ServerInfo(server_display_name, server_display_contact, server_display_profiles, current_profile, expire_time, server_display_location)

        # parse server
        identifier = server_info_dict.get('identifier')
        server_type = server_info_dict.get('server_type')
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

    @model_transition("Has_Config", common.StateType.Enter)
    def parse_config(self, old_state: str, data: str):
        server, server_info = self.get_server_info(json.loads(data))
        self.current_server = server
        return server_info

    @run_in_background_thread('browser-open')
    def open_browser(self, url):
        webbrowser.open(url)

    @model_transition("Connected", common.StateType.Enter)
    def parse_connected(self, old_state: str, data: str):
        server, server_info = self.get_server_info(json.loads(data))
        self.current_server = server
        return server_info

    @model_transition("Connecting", common.StateType.Enter)
    def parse_connecting(self, old_state: str, data: str):
        return data

    @run_in_background_thread('change-secure-location')
    def change_secure_location(self):
        self.common.change_secure_location()

    @run_in_background_thread('set-secure-location')
    def set_secure_location(self, location_id: str):
        self.common.set_secure_location(location_id)

    def should_renew_button(self):
        return self.common.should_renew_button()

    @run_in_background_thread('connect')
    def connect(self, server: PredefinedServer):
        config = None
        config_type = None
        if isinstance(server, InstituteAccessServer):
            config, config_type = self.common.get_config_institute_access(server.base_url)
        elif isinstance(server, OrganisationServer):
            config, config_type = self.common.get_config_secure_internet(server.org_id)
        elif isinstance(server, CustomServer):
            config, config_type = self.common.get_config_custom_server(server.address)

        def on_connected():
            self.is_connected = True
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
    @run_in_background_thread('renew-session')
    def renew_session(self):
        was_connected = self.is_connected
        if self.is_connected:
            # Call /disconnect
            self.deactivate_connection()
        # Delete the OAuth access and refresh token
        # Start the OAuth authorization flow
        self.common.renew_session()
        # Automatically reconnect to the server and profile if (and only if) the client was previously connected.
        if was_connected:
            self.activate_connection()

    @run_in_main_gtk_thread
    def disconnect(self):
        client = nm.get_client()
        uuid = nm.get_uuid()
        nm.deactivate_connection(client, uuid)

    def activate_connection(self):
        if not self.current_server:
            return

        self.connect(self.current_server)

    def deactivate_connection(self):
        self.disconnect()
        self.is_connected = False
        self.common.set_disconnected()

    def search_predefined(self, query: str):
        return self.server_db.search_predefined(query)

    def search_custom(self, query: str):
        return self.server_db.search_custom(query)


class Application:
    def __init__(self, variant: ApplicationVariant, make_func_threadsafe, common: EduVPN):
        self.variant = variant
        self.make_func_threadsafe = make_func_threadsafe
        self.common = common
        self.config = Configuration.load()
        self.model = ApplicationModel(common)
        self.current_network_uuid: Optional[str] = None

    def initialize(self):
        self.initialize_network()

    def on_network_update_callback(self, state):
        try:
            if state == nm.ConnectionState.CONNECTED:
                self.model.is_connected = True
                self.common.set_connected()
            elif state == nm.ConnectionState.CONNECTING:
                self.common.set_connecting()
            else:
                self.model.is_connected = False
                self.common.set_disconnected()
        except:
            return

    def initialize_network(self):
        """
        Determine the current network state.
        """
        # Check if a previous network configuration exists.
        uuid = nm.get_existing_configuration_uuid()
        if uuid:
            self.on_network_update_callback(nm.get_connection_state())
        else:
            # TODO: Implement with Go
            pass

        nm.subscribe_to_status_changes(self.on_network_update_callback)
