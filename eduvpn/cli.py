import logging
from argparse import ArgumentParser, Namespace
from sys import argv
from typing import List
from logging import getLogger
from eduvpn.storage import set_auth_url, set_metadata, ConnectionType
from eduvpn.remote import get_info
from eduvpn import actions
from eduvpn import menu

from eduvpn.menu import store_configuration

_logger = getLogger(__file__)


def list_(args: Namespace):
    args.match = None
    menu.search(args)


def search(args):
    menu.search(args)


def refresh(_):
    actions.refresh()


def activate(_):
    actions.activate()


def deactivate(_):
    actions.deactivate()


def status(_):
    actions.status()


def enroll(auth_url, display_name, support_contact, secure_internets, interactive: bool):
    api_url, oauth, token_endpoint, auth_endpoint = actions.fetch_token(auth_url)

    country_code = None
    if secure_internets and interactive:
        choice = menu.secure_internet_choice(secure_internets)
        if choice:
            base_url, country_code = choice
            api_url, _, _ = get_info(base_url)

    if secure_internets:
        con_type = ConnectionType.SECURE
    else:
        con_type = ConnectionType.INSTITUTE

    _logger.info(f"using {api_url} as api_url")
    profile_id = actions.get_profile(oauth, api_url, interactive=interactive)
    config, private_key, certificate = actions.get_config_and_keycert(oauth, api_url, profile_id)
    set_metadata(auth_url, oauth.token, token_endpoint, auth_endpoint, api_url, display_name, support_contact,
                 profile_id, con_type, country_code)
    set_auth_url(auth_url)
    store_configuration(config, private_key, certificate, interactive=interactive)


def interactive(args):
    auth_url, display_name, support_contact, secure_internets = menu.interactive(args)
    enroll(auth_url, display_name, support_contact, secure_internets, interactive=True)


def configure(args):
    """
    Configure in a non-interactive way based on supplied arguments
    """
    auth_url, display_name, support_contact, secure_internets = menu.configure(args)
    enroll(auth_url, display_name, support_contact, secure_internets, interactive=False)


def parse_eduvpn(args: List[str]):
    parser = ArgumentParser(description='The eduVPN command line client')
    subparsers = parser.add_subparsers(title='subcommands',
                                       description='Valid subcommands',
                                       help='append -h to any subcommand to see potential additional parameters')

    interactive_parser = subparsers.add_parser('interactive')
    interactive_parser.add_argument('match', nargs='?')
    interactive_parser.set_defaults(func=interactive)

    search_parsers = subparsers.add_parser('search')
    search_parsers.add_argument('match')
    search_parsers.set_defaults(func=search)

    configure_parser = subparsers.add_parser('configure')
    configure_parser.add_argument('match')
    configure_parser.add_argument('secure_internet', nargs='?')
    configure_parser.set_defaults(func=configure)

    subparsers.add_parser('refresh').set_defaults(func=refresh)
    subparsers.add_parser('list').set_defaults(func=list_)
    subparsers.add_parser('activate').set_defaults(func=activate)
    subparsers.add_parser('deactivate').set_defaults(func=deactivate)
    subparsers.add_parser('status').set_defaults(func=status)

    parsed = parser.parse_args(args)
    if hasattr(parsed, 'func'):
        parsed.func(parsed)
    else:
        parser.print_help()


def letsconnect_start(args):
    auth_url = args.url
    enroll(auth_url, display_name=None, support_contact=None, secure_internets=None, interactive=False)


def parse_letsconnect(args: List[str]):
    parser = ArgumentParser(description="The Let's Connect! command line client")
    subparsers = parser.add_subparsers(title='subcommands',
                                       description='Valid subcommands',
                                       help='append -h to any subcommand to see potential additional parameters')

    configure_parser = subparsers.add_parser('configure')
    configure_parser.add_argument('url')
    configure_parser.set_defaults(func=letsconnect_start)

    subparsers.add_parser('refresh').set_defaults(func=refresh)
    subparsers.add_parser('activate').set_defaults(func=activate)
    subparsers.add_parser('deactivate').set_defaults(func=deactivate)
    subparsers.add_parser('status').set_defaults(func=status)

    parsed = parser.parse_args(args)
    if hasattr(parsed, 'func'):
        parsed.func(parsed)
    else:
        parser.print_help()


def eduvpn():
    logging.basicConfig(level=logging.INFO)
    parse_eduvpn(argv[1:])


def letsconnect():
    logging.basicConfig(level=logging.INFO)
    parse_letsconnect(argv[1:])
