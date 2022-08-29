import eduvpn_common.main as common
from eduvpn_common.state import State, StateType

from ..app import ApplicationModel
from ..settings import (CLIENT_ID, CONFIG_PREFIX, LETSCONNECT_CLIENT_ID,
                        LETSCONNECT_CONFIG_PREFIX)
from ..utils  import cmd_transition
from .search import group_servers, ServerGroup
from ..nm import action_with_mainloop

from argparse import ArgumentParser
import time

class CommandLine:
    def __init__(self, common):
        self.common = common
        self.model = ApplicationModel(self.common)
        self.common.register_class_callbacks(self)
        self.grouped_servers = None

    @cmd_transition(State.NO_SERVER, StateType.Enter)
    def on_saved_servers(self, old_state: State, servers):
        self.grouped_servers = group_servers(servers)

    def connect_secure(self, _):
        if len(self.grouped_servers[ServerGroup.SECURE_INTERNET]) == 0:
            print("No Secure Internet server found, please add one first")

        print("Connect secure command")

        def connect(callback=None):
            self.model.connect(self.grouped_servers[ServerGroup.SECURE_INTERNET][0], callback)
            
        action_with_mainloop(connect)

    def disconnect(self, _):
        def disconnect(callback=None):
            try:
                self.model.deactivate_connection(callback)
            except:
                pass
                print("An error occurred while trying to disconnect. Are you connected?")
                if callback:
                    callback()

        action_with_mainloop(disconnect)

    def list(self, _):
        print("Saved Servers:")

        print("- [Institute Access Servers]")
        for index, institute in enumerate(self.grouped_servers[ServerGroup.INSTITUTE_ACCESS]):
            print(f"\t* [{index+1}]: {str(institute)}")

        print("- [Secure Internet Server]")
        for secure in self.grouped_servers[ServerGroup.SECURE_INTERNET]:
            print(f"\t* {str(secure)}")

        print("- [Custom Servers]")
        for index, custom in enumerate(self.grouped_servers[ServerGroup.OTHER]):
            print(f"\t* [{index+1}]: {str(custom)}")
    def initialize(self):
        uuid = nm.get_existing_configuration_uuid()
        if uuid:
            state = nm.get_connection_state()

            if state == nm.ConnectionState.CONNECTED:
                self.common.set_connected()

    def start(self):
        self.common.register(debug=True)
        self.initialize()
        parser = ArgumentParser(description='The eduVPN command line client')
        subparsers = parser.add_subparsers(title='subcommands',
                                           description='Valid subcommands',
                                           help='append -h to any subcommand to see potential additional parameters')

        connect_parser = subparsers.add_parser('connect')
        connect_subparsers = connect_parser.add_subparsers(title='subcommands',
                                      description='valid subcommands',
                                      help='append -h to any subcommand to see potential additional parameters')
        connect_secure_parser = connect_subparsers.add_parser('secure_internet')
        connect_secure_parser.set_defaults(func=self.connect_secure)

        disconnect_parser = subparsers.add_parser('disconnect')
        disconnect_parser.set_defaults(func=self.disconnect)


        list_parser = subparsers.add_parser('list')
        list_parser.set_defaults(func=self.list)
        #interactive_parser = subparsers.add_parser('interactive')
        #interactive_parser.add_argument('match', nargs='?')
        #interactive_parser.set_defaults(func=self.interactive)

        #search_parsers = subparsers.add_parser('search')
        #search_parsers.add_argument('match')
        #search_parsers.set_defaults(func=self.search)

        #configure_parser = subparsers.add_parser('configure')
        #configure_parser.add_argument('match')
        #configure_parser.add_argument('secure_internet', nargs='?')
        #configure_parser.set_defaults(func=self.configure)

        #subparsers.add_parser('refresh').set_defaults(func=refresh)
        #subparsers.add_parser('list').set_defaults(func=list_)
        #subparsers.add_parser('activate').set_defaults(func=activate)
        #subparsers.add_parser('deactivate').set_defaults(func=deactivate)
        #subparsers.add_parser('status').set_defaults(func=status)

        parsed = parser.parse_args()

        if hasattr(parsed, 'func'):
            parsed.func(parsed)
        else:
            parser.print_help()

        #print("COMMAND LINE HERE")


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
