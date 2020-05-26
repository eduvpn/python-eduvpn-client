import logging
from sys import argv
from typing import List
from argparse import ArgumentParser
from eduvpn.cli import search, list_, configure, refresh, interactive, activate, deactivate, start


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

    refresh_parser = subparsers.add_parser('refresh')
    refresh_parser.set_defaults(func=refresh)

    refresh_parser = subparsers.add_parser('list')
    refresh_parser.set_defaults(func=list_)

    refresh_parser = subparsers.add_parser('activate')
    refresh_parser.set_defaults(func=activate)

    refresh_parser = subparsers.add_parser('deactivate')
    refresh_parser.set_defaults(func=deactivate)

    parsed = parser.parse_args(args)
    if hasattr(parsed, 'func'):
        parsed.func(parsed)
    else:
        parser.print_help()


def letsconnect_start(args):
    start(args.url)


def parse_letsconnect(args: List[str]):
    parser = ArgumentParser(description="The Let's Connect! command line client")
    subparsers = parser.add_subparsers(title='subcommands',
                                       description='Valid subcommands',
                                       help='append -h to any subcommand to see potential additional parameters')

    configure_parser = subparsers.add_parser('configure')
    configure_parser.add_argument('url')
    configure_parser.set_defaults(func=letsconnect_start)

    refresh_parser = subparsers.add_parser('refresh')
    refresh_parser.set_defaults(func=refresh)

    refresh_parser = subparsers.add_parser('activate')
    refresh_parser.set_defaults(func=activate)

    refresh_parser = subparsers.add_parser('deactivate')
    refresh_parser.set_defaults(func=deactivate)

    parsed = parser.parse_args(args)
    if hasattr(parsed, 'func'):
        parsed.func(parsed)
    else:
        parser.print_help()


def eduvpn():
    logging.basicConfig(level=logging.WARNING)
    parse_eduvpn(argv[1:])


def letsconnect():
    logging.basicConfig(level=logging.WARNING)
    parse_letsconnect(argv[1:])


if __name__ == '__main__':
    eduvpn()
