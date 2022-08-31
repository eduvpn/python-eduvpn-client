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

def get_grouped_index(servers, index):
    if index < 0 or index >= len(servers):
        return None

    grouped_servers = group_servers(servers)
    servers_added = grouped_servers[ServerGroup.INSTITUTE_ACCESS]
    servers_added += grouped_servers[ServerGroup.SECURE_INTERNET]
    servers_added += grouped_servers[ServerGroup.OTHER]
    return servers_added[index]

class CommandLine:
    def __init__(self, common):
        self.common = common
        self.model = ApplicationModel(common)
        self.servers = []
        self.transitions = CommandLineTransitions(self.model)
        self.common.register_class_callbacks(self.transitions)

    def ask_server_input(self, servers, fallback_search=False):
        print("Multiple servers found:")
        self.list_groups(group_servers(servers))

        while True:
            if fallback_search:
                server_nr = input(
                    "\nPlease select a server number or enter a search query: "
                )
            else:
                server_nr = input("\nPlease select a server number: ")
            try:
                server_index = int(server_nr)
                server = get_grouped_index(servers, server_index - 1)
                if not server:
                    print(f"Invalid server number: {server_index}")
                else:
                    return server
            except ValueError:
                print(f"Input is not a number: {server_nr}")

                if fallback_search:
                    print("Using the term as a search query instead")
                    server = self.get_server_search(server_nr)
                    if server:
                        return server

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
            server = servers[0]
            print(f"One server found: {server.category_str} \"{server.detailed_str}\"")
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
                self.servers.append(server)
            except Exception as e:
                print("Error connecting:", e, file=sys.stderr)
                if callback:
                    callback()

        if not server:
            print("No server found to connect to, exiting...")
            return

        nm.action_with_mainloop(connect)

    def ask_server(self):
        if self.servers:
            answer = input("Do you want to connect to an existing server? (y/n):")

            if answer in ["y", "yes"]:
                return self.ask_server_input(self.servers)

        server_db = ServerDatabase()
        disco_orgs = self.common.get_disco_organizations()
        disco_servers = self.common.get_disco_servers()
        server_db.disco_parse(disco_orgs, disco_servers)
        servers = server_db.servers
        return self.ask_server_input(servers, fallback_search=True)

    def parse_server(self, variables):
        search_query = variables["search"]
        url = variables["url"]
        custom_url = variables["custom_url"]
        org_id = variables["orgid"]
        number = variables["number"]
        number_all = variables["number_all"]

        if search_query:
            server = self.get_server_search(search_query)
        elif url:
            server = InstituteAccessServer(url, "Institute Server")
        elif org_id:
            server = OrganisationServer("Organisation Server", org_id)
        elif custom_url:
            server = CustomServer(custom_url)
        elif number is not None:
            server = get_grouped_index(self.servers, number - 1)
            if not server:
                print(f"Configured server with number: {number} does not exist")
        elif number_all is not None:
            server_db = ServerDatabase()
            disco_orgs = self.common.get_disco_organizations()
            disco_servers = self.common.get_disco_servers()
            server_db.disco_parse(disco_orgs, disco_servers)
            servers = server_db.servers
            server = get_grouped_index(servers, number_all - 1)
            if not server:
                print(
                    f"Server with number: {number_all} does not exist. Maybe the server list had an update? Make sure to re-run list --all"
                )

    def status(self, _args={}):
        if not self.model.is_connected():
            print("You are currently not connected to a server", file=sys.stderr)
            return False

        print(f"Connected to: {str(self.model.current_server)}")
        expiry = self.model.current_server_info.expire_time
        valid_for = (
            get_validity_text(self.model.get_expiry(expiry))
            .replace("<b>", "")
            .replace("</b>", "")
        )
        print(valid_for)
        print(f"Current profile: {str(self.model.current_server_info.current_profile)}")

    def connect(self, variables={}):
        if self.model.is_connected():
            print("You are already connected to a server, please disconnect first", file=sys.stderr)
            return False

        if not variables:
            server = self.ask_server()
        else:
            server = self.parse_server(variables)

        return self.connect_server(server)

    def disconnect(self, _arg={}):
        if not self.model.is_connected():
            print("You are not connected to a server", file=sys.stderr)
            return False

        def disconnect(callback=None):
            try:
                self.model.deactivate_connection(callback)
            except Exception as e:
                print(
                    "An error occurred while trying to disconnect"
                )
                print("Error disconnecting:", e, file=sys.stderr)
                if callback:
                    callback()

        nm.action_with_mainloop(disconnect)

    def list_groups(self, grouped_servers):
        total_servers = 1
        if len(grouped_servers[ServerGroup.INSTITUTE_ACCESS]) > 0:
            print("============================")
            print("Institute Access Servers")
            print("============================")
        for institute in grouped_servers[ServerGroup.INSTITUTE_ACCESS]:
            print(f"[{total_servers}]: {institute.detailed_str}")
            total_servers += 1

        if len(grouped_servers[ServerGroup.SECURE_INTERNET]) > 0:
            print("\n============================")
            print("Secure Internet Server")
            print("============================")
        for secure in grouped_servers[ServerGroup.SECURE_INTERNET]:
            print(f"[{total_servers}]: {secure.detailed_str}")
            total_servers += 1

        if len(grouped_servers[ServerGroup.OTHER]) > 0:
            print("\n============================")
            print("Custom Servers")
            print("============================")
        for custom in grouped_servers[ServerGroup.OTHER]:
            print(f"[{total_servers}]: {custom.detailed_str}")
            total_servers += 1
        if total_servers > 1:
            print("The number for the server is in [brackets]")

    def list(self, args={}):
        servers = self.servers
        if args.get("all"):
            server_db = ServerDatabase()
            disco_orgs = self.common.get_disco_organizations()
            disco_servers = self.common.get_disco_servers()
            server_db.disco_parse(disco_orgs, disco_servers)
            servers = server_db.servers
        self.list_groups(group_servers(servers))

    def remove_server(self, server):
        if not server:
            print("No server chosen to remove")
            return False

        self.model.remove(server)
        if server in self.servers:
            self.servers.remove(server)

    def remove(self, args={}):
        if self.model.is_connected():
            print("Please disconnect from your server before doing any changes", file=sys.stderr)
            return False

        if not self.servers:
            print("There are no servers configured to remove", file=sys.stderr)
            return False

        if not args:
            server = self.ask_server_input(self.servers)
        else:
            server = get_grouped_index(self.servers, number - 1)
            if not server:
                print(f"Configured server with number: {number} does not exist")
        return self.remove_server(server)

    def help_interactive(self):
        print("Available commands: connect, disconnect, remove, status, list, help, quit")

    def interactive(self, _):
        print("Welcome to the eduVPN interactive commandline")
        self.help_interactive()
        command = ""
        while command != "quit":
            command = input("[eduVPN]: ")
            commands = {
                "connect": self.connect,
                "disconnect": self.disconnect,
                "remove": self.remove,
                "status": self.status,
                "list": self.list,
                "help": self.help_interactive,
                "quit": lambda: print("Exiting..."),
            }
            func = commands.get(command, self.help_interactive)
            func()

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

        institute_parser = subparsers.add_parser(
            "interactive", help="an interactive version of the command line"
        )
        institute_parser.set_defaults(func=self.interactive)

        connect_parser = subparsers.add_parser("connect", help="connect to a server")
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
        connect_group.set_defaults(func=lambda args: self.connect(vars(args)))

        disconnect_parser = subparsers.add_parser(
            "disconnect", help="disconnect the currently active server"
        )
        disconnect_parser.set_defaults(func=self.disconnect)

        list_parser = subparsers.add_parser("list", help="list all configured servers")
        list_parser.add_argument(
            "--all", action="store_true", help="list all available servers"
        )
        list_parser.set_defaults(func=lambda args: self.list(vars(args)))

        remove_parser = subparsers.add_parser("remove", help="remove a configured server")
        remove_parser.add_argument("--number", type=int, required=True, help="remove a configured server by number")
        remove_parser.set_defaults(func=lambda args: self.remove(vars(args)))

        status_parser = subparsers.add_parser(
            "status", help="see the current status of eduVPN"
        )
        status_parser.set_defaults(func=self.status)

        parsed = parser.parse_args()
        parsed.func(parsed)

        self.common.deregister()

class CommandLineTransitions:
    def __init__(self, model):
        self.model = model

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

    @cmd_transition(State.OAUTH_STARTED, StateType.Enter)
    def on_oauth_started(self, old_state: State, url: str):
        print(f"Authorization needed. Your browser has been opened with url: {url}")


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
