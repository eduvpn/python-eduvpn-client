import logging
from argparse import ArgumentParser, Namespace
from sys import argv
from typing import List

from eduvpn import actions
from eduvpn import menu


def list_(args: Namespace):
    args.match = None
    menu.search(args)


def search(args):
    menu.search(args)


def configure(args):
    url = menu.configure(args)
    actions.start(url)


def refresh(_):
    actions.refresh()


def activate(_):
    actions.activate()


def deactivate(_):
    actions.deactivate()


def status(_):
    actions.status()


def interactive(args):
    auth_url, secure_internet = menu.interactive(args)
    actions.start(auth_url=auth_url, secure_internet=secure_internet, interactive=True)


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
    actions.start(args.url)


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
