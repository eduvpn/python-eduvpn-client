import argparse

# readline is used! It is for going up and down in interactive mode
import readline  # noqa: F401
import signal
import sys
from functools import partial
from typing import Optional

import eduvpn_common.main as common
from eduvpn_common import __version__ as commonver
from eduvpn_common.state import State, StateType

import eduvpn.nm as nm
from eduvpn import __version__
from eduvpn.app import Application
from eduvpn.connection import parse_expiry
from eduvpn.i18n import retrieve_country_name
from eduvpn.server import (
    InstituteServer,
    Profile,
    SecureInternetServer,
    Server,
    ServerDatabase,
)
from eduvpn.settings import (
    CLIENT_ID,
    CONFIG_DIR_MODE,
    CONFIG_PREFIX,
    LETSCONNECT_CLIENT_ID,
    LETSCONNECT_CONFIG_PREFIX,
)
from eduvpn.ui.search import ServerGroup, group_servers
from eduvpn.ui.utils import get_validity_text, should_show_error, translated_error
from eduvpn.utils import (
    FAILOVERED_STATE,
    ONLINEDETECT_STATE,
    cmd_transition,
    init_logger,
    run_in_background_thread,
)
from eduvpn.variants import EDUVPN, LETS_CONNECT, ApplicationVariant


def get_grouped_index(servers, index, sort=True):
    if index < 0 or index >= len(servers):
        return None

    grouped_servers = group_servers(servers)
    if not sort:
        return (
            grouped_servers[ServerGroup.INSTITUTE_ACCESS]
            + grouped_servers[ServerGroup.SECURE_INTERNET]
            + grouped_servers[ServerGroup.OTHER]
        )[index]
    servers_added = sorted(grouped_servers[ServerGroup.INSTITUTE_ACCESS], key=lambda x: str(x))
    servers_added += sorted(grouped_servers[ServerGroup.SECURE_INTERNET], key=lambda x: str(x))
    servers_added += sorted(grouped_servers[ServerGroup.OTHER], key=lambda x: str(x))
    return servers_added[index]


def ask_profiles(setter, profiles, current: Optional[Profile] = None) -> bool:
    if len(profiles.profiles) == 1:
        _id, name = list(profiles.profiles.items())[0]
        print("There is only a single profile for this server:", name)
        setter(_id)
        return False

    # Multiple profiles, print the index
    sorted_profiles = sorted(profiles.profiles.items(), key=lambda pair: str(pair[1]))
    # Multiple profiles, print the index
    index = 0
    choices = []
    for _id, profile in sorted_profiles:
        print(f"[{index+1}]: {str(profile)}")
        choices.append(_id)
        index += 1

    # And ask for the 1 based index
    while True:
        profile_nr = input("Please select a profile number to continue connecting: ")
        try:
            profile_index = int(profile_nr)

            if profile_index < 1 or profile_index > len(choices):
                print(f"Invalid profile choice: {profile_index}")
                continue
            chosen = choices[profile_index - 1]
            if current is None or chosen != current.identifier:
                setter(choices[profile_index - 1])
                return True
            print("Selected profile is the same as the current profile")
            return False
        except ValueError:
            print(f"Input is not a number: {profile_nr}")


def ask_locations(setter, locations):
    # Create tuples of country name, location id
    location_tuples = []
    for loc in locations:
        country_name = retrieve_country_name(loc)
        location_tuples.append((country_name, loc))

    # Sort them and then print
    location_tuples.sort(key=lambda k: k[0])
    for index, location in enumerate(location_tuples):
        print(f"[{index+1}]: {location[0]}")

    while True:
        location_nr = input("Please select a location to continue: ")
        try:
            location_index = int(location_nr)

            if location_index < 1 or location_index > len(location_tuples):
                print(f"Invalid location choice: {location_index}")
                continue
            setter(location_tuples[location_index - 1][1])
            return
        except ValueError:
            print(f"Input is not a number: {location_nr}")


class CommandLine:
    def __init__(self, name: str, variant: ApplicationVariant, common):
        self.name = name
        self.variant = variant
        self.common = common
        self.app = Application(variant, common)
        self.nm_manager = self.app.nm_manager
        self.server_db = ServerDatabase(common, variant.use_predefined_servers)
        self.transitions = CommandLineTransitions(self.app, self.nm_manager)
        self.skip_yes = False
        self.common.register_class_callbacks(self.transitions)

    def ask_yes(self, label) -> bool:
        if self.skip_yes:
            return True
        while True:
            yesno = input(label)

            if yesno in ["y", "yes"]:
                return True
            if yesno in ["n", "no"]:
                return False
            print(f'Input "{yesno}" is not valid')

    def ask_server_input(self, servers, fallback_search=False, query=""):
        print("Multiple servers found:")
        self.list_groups(group_servers(servers), query == "")

        while True:
            if fallback_search:
                server_nr = input("\nPlease select a server number or enter a search query: ")
            else:
                server_nr = input("\nPlease select a server number: ")
            try:
                server_index = int(server_nr)
                server = get_grouped_index(servers, server_index - 1, query == "")
                if not server:
                    print(f"Invalid server number: {server_index}")
                else:
                    return server
            except ValueError:
                print(f"Input is not a number: {server_nr}")

                if fallback_search:
                    print("Using the term as a search query instead...")
                    server = self.get_server_search(server_nr)
                    if server:
                        return server

    def get_server_search(self, search_query):
        servers = self.get_discovery()
        servers = list(self.server_db.search_predefined(search_query))
        if search_query.count(".") >= 2:
            servers.append(Server(search_query, search_query))

        if len(servers) == 0:
            print(f"No servers found with query: {search_query}")
            return None

        if len(servers) == 1:
            server = servers[0]
            print(f'One server found: "{str(server)}" ({server.category_id})')
            is_yes = self.ask_yes("Do you want to connect to it (y/n): ")

            if is_yes:
                return servers[0]
            else:
                return None

        return self.ask_server_input(servers, query=search_query)

    def connect_server(self, server, prefer_tcp: bool):
        self.common.set_state(State.MAIN)

        def connect(callback=None):
            def connect_cb(success: bool = False):
                if callback:
                    callback()

            @run_in_background_thread("connect")
            def connect_background(server):
                try:
                    # Connect to the server and ensure it exists
                    not_exists = self.server_db.has(server) is None
                    if not_exists:
                        self.app.model.add(server)
                    self.app.model.connect(
                        server,
                        connect_cb,
                        prefer_tcp=prefer_tcp,
                    )
                except Exception as e:
                    if should_show_error(e):
                        print("Error connecting:", translated_error(e), file=sys.stderr)
                    if callback:
                        callback()

            connect_background(server)

        if not server:
            print("No server found to connect to, exiting...")
            return

        nm.action_with_mainloop(connect)
        if self.nm_manager.proxy is not None and self.common.in_state(State.CONNECTED):
            # make sure ctrl+c disconnects and then calls our original sighandler
            def quit_sigint(signal, frame):
                self.disconnect()
                self.app.cleanup_sigint(signal, frame)
                sys.exit(0)

            signal.signal(signal.SIGINT, quit_sigint)
            input(
                "\nYou are connected but we are proxying your connection over TCP, exiting the CLI will close the VPN. Press a key to exit...\n\n"
            )
            print("disconnecting and exiting...")
            self.disconnect()

    def ask_server_custom(self):
        custom = input("Enter a URL to connect to: ")
        return Server(custom, custom)

    def get_discovery(self):
        try:
            self.server_db.disco_update()
        except Exception as e:
            print(f"Failed to get discovery list: {str(e)}", file=sys.stderr)
            return []
        return self.server_db.disco

    def ask_server(self):
        if not self.variant.use_predefined_servers:
            return self.ask_server_custom()

        if self.server_db.configured:
            is_yes = self.ask_yes("Do you want to connect to an already configured server? (y/n): ")

            if is_yes:
                return self.ask_server_input(self.server_db.configured)

        servers = self.get_discovery()
        return self.ask_server_input(servers, fallback_search=True)

    def parse_server(self, variables):
        search_query = variables.get("search", None)
        url = variables.get("url", None)
        custom_url = variables.get("custom_url", None)
        org_id = variables.get("orgid", None)
        number = variables.get("number", None)
        number_all = variables.get("number_all", None)

        if search_query:
            server = self.get_server_search(search_query)
        elif url:
            server = InstituteServer(url, {"en": "Institute Server"}, [], None)
        elif org_id:
            server = SecureInternetServer(
                org_id,
                {"en": "Organisation Server"},
                [],
                None,
                "NL",
                [],
            )
        elif custom_url:
            server = Server(custom_url, {"en": "Custom Server"})
        elif number is not None:
            server = get_grouped_index(self.server_db.configured, number - 1)
            if not server:
                print(f"Configured server with number: {number} does not exist")
        elif number_all is not None:
            servers = self.get_discovery()
            server = get_grouped_index(servers, number_all - 1)
            if not server:
                print(
                    f"Server with number: {number_all} does not exist. Maybe the server list had an update? Make sure to re-run list --all"
                )
        return server

    def status(self, _args={}):
        if not self.common.in_state(State.CONNECTED):
            print("You are currently not connected to a server", file=sys.stderr)
            return False

        current = self.app.model.current_server
        print(f'Connected to: "{str(current)}" ({current.category_id})')
        validity = parse_expiry(self.common.get_expiry_times())
        valid_for = get_validity_text(validity)[1].replace("<b>", "").replace("</b>", "")
        print(f"Valid for: {valid_for}")
        print(f"Current profile: {str(current.profiles.current)}")
        if isinstance(current, SecureInternetServer):
            print(f"Current location: {retrieve_country_name(current.country_code)}")
        print(f"VPN Protocol: {self.nm_manager.protocol}")

    def connect(self, variables={}):
        if self.common.in_state(State.CONNECTED):
            print(
                "You are already connected to a server, please disconnect first",
                file=sys.stderr,
            )
            return False

        if not variables:
            server = self.ask_server()
        else:
            server = self.parse_server(variables)

        prefer_tcp = variables.get("tcp", False)

        return self.connect_server(server, prefer_tcp)

    def disconnect(self, _arg={}):
        if not self.common.in_state(State.CONNECTED):
            print("You are not connected to a server", file=sys.stderr)
            return False

        def disconnect(callback=None):
            try:
                self.app.model.deactivate_connection(callback)
            except Exception as e:
                if should_show_error(e):
                    print("An error occurred while trying to disconnect")
                    print("Error disconnecting:", translated_error(e), file=sys.stderr)
                if callback:
                    callback()

        nm.action_with_mainloop(disconnect)

    def list_groups(self, grouped_servers, sort=True):
        total_servers = 1
        if len(grouped_servers[ServerGroup.INSTITUTE_ACCESS]) > 0:
            print("============================")
            print("Institute Access Servers")
            print("============================")

        ias = grouped_servers[ServerGroup.INSTITUTE_ACCESS]
        if sort:
            ias = sorted(ias, key=lambda x: str(x))
        for institute in ias:
            print(f"[{total_servers}]: {str(institute)}")
            total_servers += 1

        sis = grouped_servers[ServerGroup.SECURE_INTERNET]
        if sis:
            sis = sorted(sis, key=lambda x: str(x))
        if len(grouped_servers[ServerGroup.SECURE_INTERNET]) > 0:
            print("============================")
            print("Secure Internet Server")
            print("============================")
        for secure in sis:
            print(f"[{total_servers}]: {str(secure)}")
            total_servers += 1

        custs = grouped_servers[ServerGroup.OTHER]
        if custs:
            custs = sorted(custs, key=lambda x: str(x))
        if len(grouped_servers[ServerGroup.OTHER]) > 0:
            print("============================")
            print("Custom Servers")
            print("============================")
        for custom in custs:
            print(f"[{total_servers}]: {str(custom)}")
            total_servers += 1
        if total_servers > 1:
            print("The number for the server is in [brackets]")

    def list(self, args={}):
        servers = self.server_db.configured
        if args.get("all"):
            servers = self.get_discovery()
        self.list_groups(group_servers(servers))

    def remove_server(self, server):
        if not server:
            print("No server chosen to remove", file=sys.stderr)
            return False

        self.app.model.remove(server)

    def change_profile(self, args={}):
        if not self.common.in_state(State.CONNECTED):
            print(
                "Please connect to a server first before changing profiles",
                file=sys.stderr,
            )
            return False

        server = self.app.model.current_server

        setter = self.app.model.set_profile
        print("Current profile:", server.profiles.current)

        if not ask_profiles(setter, server.profiles, server.profiles.current):
            return

        @run_in_background_thread("change-profile-reconnect")
        def reconnect(callback=None):
            try:
                self.app.model.reconnect(callback)
            except Exception as e:
                if should_show_error(e):
                    print("An error occurred while trying to reconnect for profile change")
                    print("Error reconnecting:", translated_error(e), file=sys.stderr)
                if callback:
                    callback()

        print("Reconnecting with the configured profile...")
        nm.action_with_mainloop(reconnect)

    def change_location(self, args={}):
        if not self.common.in_state(State.CONNECTED):
            print(
                "Please connect to a Secure Internet server first before changing locations",
                file=sys.stderr,
            )
            return False

        server = self.app.model.current_server
        if not isinstance(server, SecureInternetServer):
            print(
                "The currently connected server is not a Secure Internet server",
                file=sys.stderr,
            )
            return False

        print("Current location:", retrieve_country_name(server.country_code))

        def setter(loc):
            self.app.common.set_secure_location(server.org_id, loc)

        ask_locations(setter, server.locations)

        @run_in_background_thread("change-location-reconnect")
        def reconnect(callback=None):
            try:
                self.app.model.reconnect(callback)
            except Exception as e:
                if should_show_error(e):
                    print("An error occurred while trying to reconnect for location change")
                    print("Error reconnecting:", translated_error(e), file=sys.stderr)
                if callback:
                    callback()

        print("Reconnecting with the configured location...")
        nm.action_with_mainloop(reconnect)

    def renew(self, args={}):
        if not self.common.in_state(State.CONNECTED):
            print("Please connect to a server first before renewing", file=sys.stderr)
            return False

        def renew(callback):
            def renew_cb(success: bool = False):
                callback()

            @run_in_background_thread("renew")
            def renew_background():
                try:
                    self.app.model.renew_session(renew_cb)
                except Exception as e:
                    if should_show_error(e):
                        print("An error occurred while trying to renew")
                        print("Error renewing:", translated_error(e), file=sys.stderr)
                    if callback:
                        callback()

            renew_background()

        print("Disconnecting and renewing...")
        nm.action_with_mainloop(renew)

    def remove(self, args={}):
        if self.common.in_state(State.CONNECTED):
            print(
                "Please disconnect from your server before doing any changes",
                file=sys.stderr,
            )
            return False

        if not self.server_db.configured:
            print("There are no servers configured to remove", file=sys.stderr)
            return False

        if not args:
            server = self.ask_server_input(self.server_db.configured)
        else:
            number = args.get("number", None)
            if number is None:
                print("Please enter a number")
                return
            server = get_grouped_index(self.server_db.configured, number - 1)
            if not server:
                print(f"Configured server with number: {number} does not exist")
        return self.remove_server(server)

    def help_interactive(self, commands):
        command_keys = sorted(list(commands.keys()) + ["help"])
        print(f"Available commands: {', '.join(command_keys)}")

    def update_state(self, initial: bool = False):
        def update_state_callback(callback):
            state = self.nm_manager.connection_state
            self.app.on_network_update_callback(state, initial)

            # This exits the main loop and gives back control to the CLI
            callback()

        nm.action_with_mainloop(update_state_callback)

    def interactive(self, _):
        # Show a title and the help
        print(f"Welcome to the {self.name} interactive commandline")
        # Execute the right command
        commands = {
            "change-profile": self.change_profile,
            "connect": self.connect,
            "disconnect": self.disconnect,
            "renew": self.renew,
            "remove": self.remove,
            "status": self.status,
            "list": self.list,
            "quit": lambda: print("Exiting..."),
        }
        if self.variant.use_predefined_servers:
            commands["change-location"] = self.change_location
        self.help_interactive(commands)
        command = ""
        while command != "quit":
            # Ask for the command to execute
            command = input(f"[{self.name}]: ")

            # Update the state right before we execute
            self.update_state()

            func = commands.get(command, partial(self.help_interactive, commands))
            func()

    def start(self):
        parser = argparse.ArgumentParser(description=f"The {self.name} command line client")
        parser.set_defaults(func=lambda _: parser.print_usage())
        parser.add_argument("-d", "--debug", action="store_true", help="enable debugging")
        parser.add_argument("-y", "--yes", action="store_true", help="answer yes for y/n prompts")
        parser.add_argument("-v", "--version", action="store_true", help="get version info")
        subparsers = parser.add_subparsers(title="subcommands")

        interactive_parser = subparsers.add_parser("interactive", help="an interactive version of the command line")
        interactive_parser.set_defaults(func=self.interactive)

        renew_parser = subparsers.add_parser("renew", help="renew the validity for the currently connected server")
        renew_parser.set_defaults(func=self.renew)

        if self.variant.use_predefined_servers:
            change_profile_parser = subparsers.add_parser(
                "change-location",
                help="change the location for the currently connected secure internet server",
            )
            change_profile_parser.set_defaults(func=self.change_location)

        change_profile_parser = subparsers.add_parser(
            "change-profile",
            help="change the profile for the currently connected server",
        )
        change_profile_parser.set_defaults(func=self.change_profile)

        connect_parser = subparsers.add_parser("connect", help="connect to a server")
        connect_parser.add_argument(
            "-t",
            "--tcp",
            action="store_true",
            help="prefer to connect using TCP if available. Useful if your network blocks UDP connections and the client/NetworkManager does not properly detect issues",
        )
        connect_group = connect_parser.add_mutually_exclusive_group(required=True)
        if self.variant.use_predefined_servers:
            connect_group.add_argument(
                "-s",
                "--search",
                type=str,
                help="connect to a new server by searching for one",
            )
            connect_group.add_argument(
                "-o",
                "--orgid",
                type=str,
                help="connect to a new secure internet server using the organisation ID",
            )
            connect_group.add_argument(
                "-u",
                "--url",
                type=str,
                help="connect to a new institute access server using the URL",
            )
        connect_group.add_argument(
            "-c",
            "--custom-url",
            type=str,
            help="connect to a new custom server using the URL",
        )
        connect_group.add_argument(
            "-n",
            "--number",
            type=int,
            help="connect to an already configured server using the number. Run the 'list' subcommand to see the currently configured servers with their number",
        )
        if self.variant.use_predefined_servers:
            connect_group.add_argument(
                "-a",
                "--number-all",
                type=int,
                help="connect to a new server using the number for all servers. Run the 'list --all' command to see all the available servers with their number",
            )
        connect_group.set_defaults(func=lambda args: self.connect(vars(args)))

        disconnect_parser = subparsers.add_parser("disconnect", help="disconnect the currently active server")
        disconnect_parser.set_defaults(func=self.disconnect)

        list_parser = subparsers.add_parser("list", help="list all configured servers")
        if self.variant.use_predefined_servers:
            list_parser.add_argument("--all", action="store_true", help="list all available servers")
        list_parser.set_defaults(func=lambda args: self.list(vars(args)))

        remove_parser = subparsers.add_parser("remove", help="remove a configured server")
        remove_parser.add_argument(
            "-n",
            "--number",
            type=int,
            required=True,
            help="remove a configured server by number",
        )
        remove_parser.set_defaults(func=lambda args: self.remove(vars(args)))

        status_parser = subparsers.add_parser("status", help="see the current status of eduVPN")
        status_parser.set_defaults(func=self.status)

        parsed = parser.parse_args()

        if parsed.version:
            print(f"eduVPN CLI version: {__version__} with eduvpn-common version: {commonver}")
            return

        init_logger(parsed.debug, self.variant.logfile, CONFIG_DIR_MODE)

        # Skip yes/no prompts if given
        self.skip_yes = parsed.yes

        # Register the common library
        self.app.model.register(parsed.debug)

        # Update the state by asking NetworkManager
        self.update_state(True)

        # Run the command
        parsed.func(parsed)

        # Deregister the library
        self.common.deregister()


class CommandLineTransitions:
    def __init__(self, app, nm_manager):
        self.app = app
        self.nm_manager = nm_manager

    @cmd_transition(State.ASK_LOCATION, StateType.ENTER)
    def on_ask_location(self, old_state: State, data):
        print("This Secure Internet Server has multiple available locations. Please choose one to continue...")
        setter, locations = data
        ask_locations(setter, locations)

    @cmd_transition(State.ASK_PROFILE, StateType.ENTER)
    def on_ask_profile(self, old_state: State, data):
        print("This server has multiple profiles. Please choose one to continue...")
        setter, profiles = data
        ask_profiles(setter, profiles)

    @cmd_transition(State.OAUTH_STARTED, StateType.ENTER)
    def on_oauth_started(self, old_state: State, url: str):
        print(f"Authorization needed. Your browser has been opened with url: {url}")

    @cmd_transition(ONLINEDETECT_STATE, StateType.ENTER)  # type: ignore[arg-type]
    def on_online_detection(self, old_state: State, data: str):
        print("Connected, but we are testing your VPN connection...")

    @cmd_transition(FAILOVERED_STATE, StateType.ENTER)  # type: ignore[arg-type]
    def on_failovered(self, old_state: State, data: str):
        print("The connection has switched to a new VPN protocol...")


def eduvpn():
    _common = common.EduVPN(CLIENT_ID, __version__, str(CONFIG_PREFIX))
    cmd = CommandLine("eduVPN", EDUVPN, _common)
    cmd.start()


def letsconnect():
    _common = common.EduVPN(LETSCONNECT_CLIENT_ID, __version__, str(LETSCONNECT_CONFIG_PREFIX))
    cmd = CommandLine("Let's Connect!", LETS_CONNECT, _common)
    cmd.start()
