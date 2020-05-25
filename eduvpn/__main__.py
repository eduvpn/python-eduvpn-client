import logging
from sys import exit, argv
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from itertools import chain
from requests_oauthlib import OAuth2Session
from eduvpn.menu import menu, profile_choice, write_to_nm_choice, secure_internet_choice
from eduvpn.nm import save_connection
from eduvpn.oauth2 import get_oauth
from eduvpn.remote import get_info, list_profiles, get_config, create_keypair, list_orgs, list_servers
from eduvpn.settings import CLIENT_ID, ORGANISATION_URI, Ed25519_PUBLIC_KEY, SERVER_URI
from eduvpn.storage import get_entry, set_entry, write_config
from eduvpn.crypto import make_verifier
from eduvpn.i18n import extract_translation
import argparse


def fetch_servers_orgs():
    verifier = make_verifier(Ed25519_PUBLIC_KEY)
    servers = list_servers(SERVER_URI, verifier=verifier)
    orgs = list_orgs(ORGANISATION_URI, verifier=verifier)
    return servers, orgs


def match_term(servers, orgs, search_term: Optional[str], exact=False) -> Tuple[List[Tuple[int, dict]],
                                                                                List[Tuple[int, dict]]]:
    """
    Search the list of institutes and organisations for a string match.

    returns:
        None or (type ('base_url' or 'secure_internet_home'), url)
    """
    institute_access = [s for s in servers if s['server_type'] == 'institute_access']

    if not search_term:
        return list(enumerate(institute_access)), list(enumerate(orgs, len(institute_access)))

    institute_matches: List[Tuple[int, dict]] = []
    for x, i in enumerate(institute_access):
        if not exact:
            if search_term.lower() in extract_translation(i['display_name']).lower():
                institute_matches.append((x, i))
        if exact:
            if search_term.lower() == extract_translation(i['display_name']).lower():
                institute_matches.append((x, i))

    org_matches: List[Tuple[int, dict]] = []
    for x, i in enumerate(orgs, len(institute_access)):
        if not exact:
            if search_term.lower() in extract_translation(i['display_name']).lower() \
                    or 'keyword_list' in i and search_term in i['keyword_list']:
                org_matches.append((x, i))
        if exact:
            if search_term.lower() == extract_translation(i['display_name']).lower():
                org_matches.append((x, i))
    return institute_matches, org_matches


def search(args: argparse.Namespace):
    search_term = args.match
    servers, orgs = fetch_servers_orgs()
    institute_matches, org_matches = match_term(servers, orgs, search_term)
    print(f"Your search term '{search_term}'  matched with the following institutes/organisations:\n")

    if len(institute_matches):
        print("Institute access:")
        for i, row in institute_matches:
            print(f"[{i}] {extract_translation(row['display_name'])}")

    if len(org_matches):
        print("\nSecure internet: \n")
        for i, row in org_matches:
            print(f"[{i}] {extract_translation(row['display_name'])}")


def list_(args: argparse.Namespace):
    args.match = None
    search(args)


def configure(args: argparse.Namespace):
    search_term = args.match
    secure_internet_term = args.secure_internet
    servers, orgs = fetch_servers_orgs()
    institute_matches, org_matches = match_term(servers, orgs, search_term, exact=True)

    if isinstance(search_term, str) and search_term.lower().startswith('https://'):
        base_url = search_term
        info_url = base_url
    else:
        if len(institute_matches) == 0 and len(org_matches) == 0:
            print(f"The filter '{search_term}' had no matches")
            exit(1)
        elif len(institute_matches) == 1 and len(org_matches) == 0:
            index, institute = institute_matches[0]
            print(f"filter '{search_term}' matched with institute '{institute['display_name']}'")
            base_url = institute['base_url']
        elif len(institute_matches) == 0 and len(org_matches) == 1:
            index, org = org_matches[0]
            print(f"filter '{search_term}' matched with organisation '{org['display_name']}'")
            base_url = org['secure_internet_home']
            info_url = base_url
            secure_internet = [s for s in servers if
                               s['server_type'] == 'secure_internet' and s['base_url'] == base_url]
            if len(secure_internet) == 0:
                raise Exception("No secure internet entries for selected organisation.")
            elif len(secure_internet) == 1:
                info_url = secure_internet[0]['base_url']
            else:
                matches = [i for i in secure_internet if secure_internet_term.lower() in i.lower()]
                if len(matches) != 1:
                    print(f"Your secure internet string {secure_internet_term} didn't match "
                          f"any available secure internet servers.")
                    print("\nthe available secure internet servers for this profile are:")
                    for i, profile in enumerate(secure_internet):
                        print(f" * [{i}] {extract_translation(profile['display_name'])}")
                    exit(1)
        else:
            matches = [i[1]['display_name'] for i in chain(institute_matches, org_matches)]
            print(
                f"filter '{search_term}' matched with {len(matches)} institutes and organisations, please be more specific.")
            print("Matches:")
            for m in matches:
                print(f" - {extract_translation(m)}")
            exit(1)

    start(base_url, info_url)


def refresh(args: argparse.Namespace):
    raise NotImplementedError


def parse_args(args: List[str]):
    parser = argparse.ArgumentParser(description='The eduVPN command line client')
    subparsers = parser.add_subparsers()

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

    parsed = parser.parse_args(args)
    parsed.func(parsed)


def interactive(args: argparse.Namespace):
    search_term = args.match
    verifier = make_verifier(Ed25519_PUBLIC_KEY)

    if isinstance(search_term, str) and search_term.lower().startswith('https://'):
        base_url = search_term
        info_url = base_url
    else:
        servers = list_servers(SERVER_URI, verifier=verifier)
        secure_internet = [s for s in servers if s['server_type'] == 'secure_internet']
        institute_access = [s for s in servers if s['server_type'] == 'institute_access']
        orgs = list_orgs(ORGANISATION_URI, verifier=verifier)
        choice = menu(institutes=institute_access, orgs=orgs, search_term=search_term)

        if not choice:
            exit(1)

        type_, base_url = choice

        if type_ == 'secure_internet_home':
            secure_internets = [s for s in secure_internet if s['base_url'] == base_url]
            info_url = secure_internet_choice(secure_internets)
        else:
            info_url = base_url
    start(base_url, info_url)


def start(base_url, info_url):
    exists = get_entry(base_url)

    if exists:
        token, api_base_uri, token_endpoint, authorization_endpoint = exists
        oauth = OAuth2Session(client_id=CLIENT_ID, token=token, auto_refresh_url=token_endpoint)
    else:
        api_base_uri, token_endpoint, auth_endpoint = get_info(info_url)
        oauth = get_oauth(token_endpoint, auth_endpoint)
        set_entry(base_url, oauth.token, api_base_uri, token_endpoint, auth_endpoint)

    oauth.refresh_token(token_url=token_endpoint)
    profiles = list_profiles(oauth, api_base_uri)
    profile_id = profile_choice(profiles)
    config = get_config(oauth, api_base_uri, profile_id)
    private_key, certificate = create_keypair(oauth, api_base_uri)

    if write_to_nm_choice():
        save_connection(config, private_key, certificate)
    else:
        target = Path('eduVPN.ovpn').resolve()
        print(f"Writing configuration to {target}")
        write_config(config, private_key, certificate, target)


def letsconnect():
    raise NotImplementedError("todo :)")


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    parse_args(args=argv[1:])
