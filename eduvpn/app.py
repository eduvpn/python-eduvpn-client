from typing import Optional
import logging
from gettext import gettext as _
from .server import AnyServer, ServerDatabase, SecureInternetLocation, InstituteAccessServer, OrganisationServer, CustomServer
from . import nm
import json
from .variants import ApplicationVariant
from .config import Configuration
from .utils import run_periodically
from eduvpn_common.main import EduVPN
from eduvpn.connection import Connection
import webbrowser
from .utils import run_in_background_thread, run_in_main_gtk_thread

logger = logging.getLogger(__name__)



class ApplicationModel:
    def __init__(self, common: EduVPN):
        self.common = common
        self.server_db = ServerDatabase()

    def activate_connection(self):
        print("ACTIVATE CONNECTION")

    def deactivate_connection(self):
        print("DEACTIVATE CONNECTION")

    def parse_locations(self, locations_json) -> [SecureInternetLocation]:
        locations = json.loads(locations_json)
        location_classes = []

        for location in locations:
            location_classes.append(SecureInternetLocation(location))

        return location_classes

    @property
    def configured_servers(self):
        disco_orgs = self.common.get_disco_organizations()
        disco_servers = self.common.get_disco_servers()
        return self.server_db.disco_parse(disco_orgs, disco_servers)

    @property
    def servers(self):
        return self.server_db.servers

    @run_in_background_thread('browser-open')
    def open_browser(self, url):
        webbrowser.open(url)

    @run_in_background_thread('connect')
    def connect(self, server: AnyServer):
        print("CONNECT")
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
            uuid = nm.get_uuid(self.common)
            nm.activate_connection(client, uuid, on_connected)

        @run_in_main_gtk_thread
        def connect(common, config, config_type):
            connection = Connection.parse(common, config, config_type)
            connection.connect(on_connect)

        connect(self.common, config, config_type)

    def search_predefined(self, query: str):
        return self.server_db.search_predefined(query)

    def search_custom(self, query: str):
        return self.server_db.search_custom(query)


class Application:
    def __init__(self, variant: ApplicationVariant, make_func_threadsafe, common: EduVPN):
        self.variant = variant
        self.make_func_threadsafe = make_func_threadsafe
        self.model = ApplicationModel(common)
        self.current_network_uuid: Optional[str] = None

    def initialize(self):
        self.initialize_network()

    def initialize_network(self):
        """
        Determine the current network state.
        """
        # Check if a previous network configuration exists.
        uuid = nm.get_existing_configuration_uuid()
        if uuid:
            self.current_network_uuid = uuid
            # Check what server corresponds to the configuration.
            # TODO: get single configured:
            # server = server_db.get_single_configured
            server = None
            if server is None:
                # There is a network configuration,
                # but no record of what server corresponds to it.
                # TODO: Implement with Go
                pass
            else:
                # TODO: Implement with Go
                pass
        else:
            # TODO: Implement with Go
            pass

        def on_network_update_callback(state):
            print("Network state update")

        nm.subscribe_to_status_changes(on_network_update_callback)
