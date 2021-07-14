from logging import getLogger
from argparse import Namespace
from itertools import chain
from pathlib import Path
from sys import exit
from typing import List, Dict, Optional, Tuple, Any

import nacl.exceptions

from eduvpn.i18n import extract_translation
from eduvpn.nm import nm_available, save_connection_with_mainloop
from eduvpn.remote import list_servers, list_organisations
from eduvpn.settings import SERVER_URI, ORGANISATION_URI
from eduvpn.storage import write_config

_logger = getLogger()

ServerListType = List[Dict[str, Any]]


def fetch_servers_orgs() -> Tuple[ServerListType, ServerListType]:
    servers = list_servers(SERVER_URI)
    orgs = list_organisations(ORGANISATION_URI)
    return servers, orgs


def input_int(max_: int):
    """
    Request the user to enter a number.
    """
    while True:
        choice = input("\n> ")
        if choice.isdigit() and int(choice) < max_:
            break
        else:
            print("error: invalid choice")
    return int(choice)


def provider_choice(institutes: List[dict], orgs: List[dict]) -> Tuple[str, str, Optional[str], bool]:
    """
    Ask the user to make a choice from a list of institute and secure internet providers.

    returns:
        url, display_name, contact, bool. Bool indicates if it is secure_internet or not.
    """
    print("\nPlease choose server:\n")
    print("Institute access:")
    for i, row in enumerate(institutes):
        print(f"[{i}] {extract_translation(row['display_name'])}")

    print("Secure internet: \n")
    for i, row in enumerate(orgs, start=len(institutes)):
        print(f"[{i}] {extract_translation(row['display_name'])}")

    choice = input_int(max_=len(institutes) + len(orgs))

    if choice < len(institutes):
        institute = institutes[choice]
        return institute['base_url'], extract_translation(institute['display_name']), institute[
            'support_contact'], False
    else:
        org = orgs[choice - len(institutes)]
        return org['secure_internet_home'], extract_translation(org['display_name']), None, True


def menu(
        institutes: List[dict],
        orgs: List[dict],
        search_term: Optional[str] = None
) -> Tuple[str, str, Optional[str], bool]:
    """
    returns:
        url, bool. Bool indicates if it is secure_internet or not.
    """
    # todo: add initial search filtering
    return provider_choice(institutes, orgs)


def profile_choice(profiles: List[Dict]) -> str:
    """
    If multiple profiles are available, present user with choice which profile.
    """
    if len(profiles) > 1:
        print("\nplease choose a profile:\n")
        for i, profile in enumerate(profiles):
            print(f" * [{i}] {profile['display_name']}")
        choice = input_int(max_=len(profiles))
        return profiles[int(choice)]['profile_id']
    else:
        return profiles[0]['profile_id']


def write_to_nm_choice() -> bool:
    """
    When Network Manager is available, asks user to add VPN to Network Manager
    """
    print("\nWhat would you like to do with your VPN configuration:\n")
    print("* [0] Write .ovpn file to current directory")
    print("* [1] Add VPN configuration to Network Manager")
    return bool(input_int(max_=2))


def secure_internet_choice(secure_internets: List[dict]) -> Optional[Tuple[str, str]]:
    print("Do you want to select a secure internet location? If not we use the default.")
    while True:
        choice = input("\n[N/y] > ").strip().lower()
        if choice == 'n' or not choice:
            return None
        elif choice == 'y':
            print("\nplease choose a secure internet server:\n")
            for i, profile in enumerate(secure_internets):
                print(f" * [{i}] {extract_translation(profile['country_code'])}")
            choice = input_int(max_=len(secure_internets))
            base_url = secure_internets[int(choice)]['base_url']
            country_code = secure_internets[int(choice)]['country_code']
            return base_url, country_code
        else:
            print("error: invalid choice, please enter y, n or just leave empty")


def search(args: Namespace):
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


def configure(args: Namespace) -> Tuple[str, str, Optional[str], Optional[ServerListType]]:
    search_term = args.match
    servers, orgs = fetch_servers_orgs()
    secure_internets = [s for s in servers if s['server_type'] == 'secure_internet']
    institute_matches, org_matches = match_term(servers, orgs, search_term, exact=True)

    if isinstance(search_term, str) and search_term.lower().startswith('https://'):
        return search_term, search_term, None, None
    else:
        if len(institute_matches) == 0 and len(org_matches) == 0:
            print(f"The filter '{search_term}' had no matches")
            exit(1)
        elif len(institute_matches) == 1 and len(org_matches) == 0:
            index, institute = institute_matches[0]
            print(f"filter '{search_term}' matched with institute '{institute['display_name']}'")
            return institute['base_url'], extract_translation(institute['display_name']), institute[
                'support_contact'], None
        elif len(institute_matches) == 0 and len(org_matches) == 1:
            index, org = org_matches[0]
            print(f"filter '{search_term}' matched with organisation '{org['display_name']}'")
            return org['secure_internet_home'], extract_translation(org['display_name']), None, secure_internets
        else:
            matches = [i[1]['display_name'] for i in chain(institute_matches, org_matches)]
            print(
                f"filter '{search_term}' matched with {len(matches)} institutes and organisations, please be more specific.")
            print("Matches:")
            for m in matches:
                print(f" - {extract_translation(m)}")
            exit(1)


def interactive(args: Namespace) -> Tuple[str, str, Optional[str], Optional[ServerListType]]:
    """
    returns:
        auth_url, display_name, support_contact, secure_internets
    """
    search_term = args.match

    if isinstance(search_term, str) and search_term.lower().startswith('https://'):
        return search_term, search_term, None, None

    try:
        servers = list_servers(SERVER_URI)
    except nacl.exceptions.BadSignatureError:
        print(f"Received a bad signature from server {SERVER_URI}")
        exit(1)
    secure_internets = [s for s in servers if s['server_type'] == 'secure_internet']
    institute_access = [s for s in servers if s['server_type'] == 'institute_access']
    orgs = list_organisations(ORGANISATION_URI)
    choice = menu(institutes=institute_access, orgs=orgs, search_term=search_term)

    if not choice:
        exit(1)

    auth_url, display_name, support_contact, secure_internet = choice
    if not secure_internet:
        return auth_url, display_name, support_contact, None

    return auth_url, display_name, support_contact, secure_internets


def match_term(
        servers: ServerListType,
        orgs: ServerListType,
        search_term: Optional[str], exact=False
) -> Tuple[List[Tuple[int, Dict[str, Any]]], List[Tuple[int, Dict[str, Any]]]]:
    """
    Search the list of institutes and organisations for a string match.

    returns:
        None or (type ('base_url' or 'secure_internet_home'), url)
    """
    institute_access = [s for s in servers if s['server_type'] == 'institute_access']

    if not search_term:
        return list(enumerate(institute_access)), list(enumerate(orgs, len(institute_access)))

    institute_matches: List[Tuple[int, Dict[str, Any]]] = []
    for x, i in enumerate(institute_access):
        if not exact:
            if search_term.lower() in extract_translation(i['display_name']).lower():
                institute_matches.append((x, i))
        else:
            if search_term.lower() == extract_translation(i['display_name']).lower():
                institute_matches.append((x, i))

    org_matches: List[Tuple[int, Dict[str, Any]]] = []
    for x, i in enumerate(orgs, len(institute_access)):
        if not exact:
            if search_term.lower() in extract_translation(i['display_name']).lower() \
                    or 'keyword_list' in i and search_term in i['keyword_list']:
                org_matches.append((x, i))
        else:
            if search_term.lower() == extract_translation(i['display_name']).lower():
                org_matches.append((x, i))
    return institute_matches, org_matches


def store_configuration(config, private_key, certificate, interactive=False):
    target = Path('eduVPN.ovpn').resolve()
    if interactive and nm_available():
        if write_to_nm_choice():
            save_connection_with_mainloop(config, private_key, certificate)
        else:
            write_config(config, private_key, certificate, target)
    else:
        if nm_available():
            save_connection_with_mainloop(config, private_key, certificate)
        else:
            write_config(config, private_key, certificate, target)
