import eduvpn_common.main as common
from eduvpn_common.state import State, StateType

from eduvpn.app import ApplicationModel
from eduvpn.settings import (
    CLIENT_ID,
    CONFIG_PREFIX,
    LETSCONNECT_CLIENT_ID,
    LETSCONNECT_CONFIG_PREFIX,
)
from eduvpn.utils import cmd_transition, run_in_background_thread
from eduvpn.ui.search import group_servers, ServerGroup, update_results
from eduvpn.ui.utils import get_validity_text
import eduvpn.nm as nm
from eduvpn.server import (
    ServerDatabase,
    InstituteAccessServer,
    OrganisationServer,
    CustomServer,
)

import argparse
import sys


class CommandLine:
    def __init__(self, common):
        self.common = common
        self.model = ApplicationModel(self.common)
        self.common.register_class_callbacks(self)
        self.servers = None

    @cmd_transition(State.ASK_LOCATION, StateType.Enter)
    def on_ask_location(self, old_state: State, locations):
        print("This secure internet server has the following available locations:")
        for index, location in enumerate(locations):
            print(f"[{index+1}]: {str(location)}")

        while True:
            location_nr = input("Please select a location to continue connecting: ")
            try:
                location_index = int(location_nr)

                if location_index < 1 or location_index > len(locations):
                    print(f"Invalid location choice: {location_index}")
                    continue
                # FIXME: This should just accept a location instead of the country code
                # The model should convert this to a location
                # This needs fixing in the normal GTK UI as well
                self.model.set_secure_location(
                    locations[location_index - 1].country_code
                )
                return
            except ValueError:
                print(f"Input is not a number: {location_nr}")

    @cmd_transition(State.ASK_PROFILE, StateType.Enter)
    def on_ask_profile(self, old_state: State, profiles):
        print("This server has multiple profiles.")
        for index, profile in enumerate(profiles):
            print(f"[{index+1}]: {str(profile)}")

        while True:
            profile_nr = input(
                "Please select a profile number to continue connecting: "
            )
            try:
                profile_index = int(profile_nr)

                if profile_index < 1 or profile_index > len(profiles):
                    print(f"Invalid profile choice: {profile_index}")
                    continue
                self.model.set_profile(profiles[profile_index - 1])
                return
            except ValueError:
                print(f"Input is not a number: {profile_nr}")

    @cmd_transition(State.NO_SERVER, StateType.Enter)
    def on_saved_servers(self, old_state: State, servers):
        self.servers = servers

    @cmd_transition(State.OAUTH_STARTED, StateType.Enter)
    def on_oauth_started(self, old_state: State, url: str):
        print(f"Authorization needed. Your browser has been opened with url: {url}")

    def status(self, _):
        if not self.model.is_connected():
            print("You are currently not connected to a server", file=sys.stderr)
            sys.exit(1)

        print(f"Connected to: {str(self.model.current_server)}")
        expiry = self.model.current_server_info.expire_time
        valid_for = get_validity_text(self.model.get_expiry(expiry)).replace("<b>", "").replace("</b>", "")
        print(valid_for)
        print(f"Current profile: {str(self.model.current_server_info.current_profile)}")

    def get_grouped_index(self, servers, index):
        if index < 0 or index >= len(servers):
            return None

        grouped_servers = group_servers(servers)
        servers_added = grouped_servers[ServerGroup.INSTITUTE_ACCESS]
        servers_added += grouped_servers[ServerGroup.SECURE_INTERNET]
        servers_added += grouped_servers[ServerGroup.OTHER]
        return servers_added[index]

    def ask_server_input(self, servers):
        print("Multiple servers found:\n")
        self.list_groups(group_servers(servers))

        while True:
            server_nr = input("\nPlease select a server number to connect to: ")
            try:
                server_index = int(server_nr)
                server = self.get_grouped_index(servers, server_index - 1)
                if not server:
                    print(f"Invalid server number: {server_index}")
                else:
                    return server
            except ValueError:
                print(f"Input is not a number: {server_nr}")

    def get_server_search(self, search_query):
        server_db = ServerDatabase()
        disco_orgs = self.common.get_disco_organizations()
        disco_servers = self.common.get_disco_servers()
        server_db.disco_parse(disco_orgs, disco_servers)
        servers = list(server_db.search_predefined(search_query))
        if search_query.count(".") >= 2:
            servers.append(CustomServer(search_query))

        if len(servers) == 0:
            print(f"No servers found with query: {search_query}")
            return None

        if len(servers) == 1:
            print(f"One server found: {str(servers[0])}")
            ask = input("Do you want to connect to it (y/n): ")

            if ask in ["y", "yes"]:
                return servers[0]
            else:
                return None

        return self.ask_server_input(servers)

    def connect_server(self, server):
        def connect(callback=None):
            try:
                self.model.connect(server, callback)
            except Exception as e:
                print("Error connecting:", e, file=sys.stderr)
                if callback:
                    callback()

        nm.action_with_mainloop(connect)

    def connect_new(self, arg):
        variables = vars(arg)
        search_query = variables["search"]
        url = variables["url"]
        custom_url = variables["custom_url"]
        org_id = variables["orgid"]
        number = variables["number"]
        number_all = variables["number_all"]

        server = None
        if search_query:
            server = self.get_server_search(search_query)
        elif url:
            server = InstituteAccessServer(url, "Institute Server")
        elif org_id:
            server = OrganisationServer("Organisation Server", org_id)
        elif custom_url:
            server = CustomServer(custom_url)
        elif number is not None:
            server = self.get_grouped_index(self.servers, number - 1)
            if not server:
                print(f"Configured server with number: {number} does not exist")
        elif number_all is not None:
            server_db = ServerDatabase()
            disco_orgs = self.common.get_disco_organizations()
            disco_servers = self.common.get_disco_servers()
            server_db.disco_parse(disco_orgs, disco_servers)
            servers = server_db.servers
            server = self.get_grouped_index(servers, number_all - 1)
            if not server:
                print(
                    f"Server with number: {number_all} does not exist. Maybe the server list had an update? Make sure to re-run list --all"
                )

        if not server:
            print("No server found to connect to, exiting...")
            return

        self.connect_server(server)

    def disconnect(self, _):
        def disconnect(callback=None):
            try:
                self.model.deactivate_connection(callback)
            except Exception as e:
                print(
                    "An error occurred while trying to disconnect. Are you connected?"
                )
                print("Error disconnecting:", e, file=sys.stderr)
                if callback:
                    callback()

        nm.action_with_mainloop(disconnect)

    def list_groups(self, grouped_servers):
        index = 1
        if len(grouped_servers[ServerGroup.INSTITUTE_ACCESS]) > 0:
            print("============================")
            print("Institute Access Servers")
            print("============================")
        for institute in grouped_servers[ServerGroup.INSTITUTE_ACCESS]:
            print(f"[{index}]: {str(institute)} (URL: {institute.base_url})")
            index += 1

        if len(grouped_servers[ServerGroup.SECURE_INTERNET]) > 0:
            print("\n============================")
            print("Secure Internet Server")
            print("============================")
        for secure in grouped_servers[ServerGroup.SECURE_INTERNET]:
            print(f"[{index}]: {str(secure)} (Org ID: {secure.org_id})")
            index += 1

        if len(grouped_servers[ServerGroup.OTHER]) > 0:
            print("\n============================")
            print("Custom Servers")
            print("============================")
        for custom in grouped_servers[ServerGroup.OTHER]:
            print(f"[{index}]: {str(custom)} (URL)")
            index += 1
        if index > 1:
            print("The number for the server is in [brackets]")

    def list(self, arg):
        args = vars(arg)
        servers = self.servers
        if args["all"]:
            server_db = ServerDatabase()
            disco_orgs = self.common.get_disco_organizations()
            disco_servers = self.common.get_disco_servers()
            server_db.disco_parse(disco_orgs, disco_servers)
            servers = server_db.servers
        self.list_groups(group_servers(servers))

    def initialize(self):
        uuid = nm.get_existing_configuration_uuid()
        if uuid:
            state = nm.get_connection_state()

            if state == nm.ConnectionState.CONNECTED:
                self.common.set_connected()

    def start(self):
        self.common.register(debug=True)
        self.initialize()
        parser = argparse.ArgumentParser(description="The eduVPN command line client")
        parser.set_defaults(func=lambda _: parser.print_usage())
        subparsers = parser.add_subparsers(title="subcommands")

        connect_parser = subparsers.add_parser("connect", help="Connect to a server")
        connect_group = connect_parser.add_mutually_exclusive_group(required=True)
        connect_group.add_argument(
            "--search", type=str, help="connect to a server by searching for one"
        )
        connect_group.add_argument(
            "--orgid",
            type=str,
            help="connect to a secure internet server using the organisation ID",
        )
        connect_group.add_argument(
            "--url",
            type=str,
            help="connect to an institute access server using the URL",
        )
        connect_group.add_argument(
            "--custom-url", type=str, help="connect to a custom server using the URL"
        )
        connect_group.add_argument(
            "--number",
            type=int,
            help="connect to an already configured server using the number. Run the 'list' subcommand to see the currently configured servers with their number",
        )
        connect_group.add_argument(
            "--number-all",
            type=int,
            help="connect to a server using the number for all servers. Run the 'list --all' command to see all the available servers with their number",
        )
        connect_group.set_defaults(func=self.connect_new)

        disconnect_parser = subparsers.add_parser(
            "disconnect", help="Disconnect the currently active server"
        )
        disconnect_parser.set_defaults(func=self.disconnect)

        status_parser = subparsers.add_parser(
            "status", help="See the current status of eduVPN"
        )
        status_parser.set_defaults(func=self.status)

        list_parser = subparsers.add_parser("list", help="List all configured servers")
        list_parser.add_argument("--all", action="store_true")
        list_parser.set_defaults(func=self.list)

        parsed = parser.parse_args()
        parsed.func(parsed)


def eduvpn():
    _common = common.EduVPN(CLIENT_ID, str(CONFIG_PREFIX))
    cmd = CommandLine(_common)
    cmd.start()


def letsconnect():
    _common = common.EduVPN(LETSCONNECT_CLIENT_ID, str(LETSCONNECT_CONFIG_PREFIX))
    cmd = CommandLine(_common)
    cmd.start()


if __name__ == "__main__":
    eduvpn()
