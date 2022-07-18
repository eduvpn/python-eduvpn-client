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

logger = logging.getLogger(__name__)

class ServerInfo:
    def __init__(self, display_name, support_contact, location):
        self.display_name = display_name
        self.support_contact = support_contact
        self.flag_path = None

        if location:
            self.flag_path = SecureInternetLocation(location).flag_path
            self.display_name = f"{retrieve_country_name(location)}\n (via {self.display_name})"

class ApplicationModel:
    def __init__(self, common: EduVPN):
        self.common = common
        self.server_db = ServerDatabase()
        self.common.register_class_callbacks(self)
        self.current_server = None

    @model_transition("No_Server", common.StateType.Enter)
    def get_previous_servers(self, old_state: str, data: str):
        return None

    @model_transition("Search_Server", common.StateType.Enter)
    def parse_discovery(self, old_state: str, _):
        disco_orgs = self.common.get_disco_organizations()
        disco_servers = self.common.get_disco_servers()
        return self.server_db.disco_parse(disco_orgs, disco_servers)

    @model_transition("Loading_Server", common.StateType.Enter)
    def loading_server(self, old_state: str, data: str):
        return data

    @model_transition("Ask_Profile", common.StateType.Enter)
    def parse_profiles(self, old_state: str, profiles_json: str):
        profiles_parsed = json.loads(profiles_json)['info']['profile_list']
        profiles = []
        for profile in profiles_parsed:
            profiles.append(Profile(**profile))
        return profiles

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

    def get_server_info(self, json_data: str):
        server_info_json = json.loads(json_data)
        server_display_name = extract_translation(server_info_json.get('display_name') or "Unknown Server")
        server_display_contact = server_info_json.get('support_contact')
        server_display_location = server_info_json.get('country_code')
        server_info = ServerInfo(server_display_name, server_display_contact, server_display_location)

        # parse server
        identifier = server_info_json.get('identifier')
        server_type = server_info_json.get('server_type')
        if server_type and identifier:
            if server_type == "secure_internet":
                self.current_server = OrganisationServer(server_display_name, identifier)
            elif server_type == "institute_access":
                self.current_server = InstituteAccessServer(identifier, server_display_name)
            elif server_type == "custom_server":
                self.current_server = CustomServer(identifier)
        else:
            # TODO: Log an error or something?
        return server_info

    @model_transition("Has_Config", common.StateType.Enter)
    def parse_config(self, old_state: str, data: str):
        return self.get_server_info(data)

    @run_in_background_thread('browser-open')
    def open_browser(self, url):
        webbrowser.open(url)

    @model_transition("Connected", common.StateType.Enter)
    def parse_connected(self, old_state: str, data: str):
        return self.get_server_info(data)

    @model_transition("Connecting", common.StateType.Enter)
    def parse_connecting(self, old_state: str, data: str):
        return data

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
                self.common.set_connected()
            elif state == nm.ConnectionState.CONNECTING:
                self.common.set_connecting()
            else:
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
