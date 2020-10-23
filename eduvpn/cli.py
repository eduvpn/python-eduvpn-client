import argparse
from itertools import chain
from pathlib import Path
from sys import exit
from typing import Optional, Tuple, List

from requests_oauthlib import OAuth2Session

from eduvpn.i18n import extract_translation
from eduvpn.menu import menu, secure_internet_choice, profile_choice, write_to_nm_choice
from eduvpn.nm import activate_connection, deactivate_connection, get_cert_key, save_connection, nm_available, get_client
from eduvpn.oauth2 import get_oauth
from eduvpn.remote import get_info, check_certificate, create_keypair, get_config, list_servers, list_orgs, \
    list_profiles
from eduvpn.settings import CLIENT_ID, SERVER_URI, ORGANISATION_URI
from eduvpn.storage import get_storage, set_token, get_token, set_api_url, set_auth_url, set_profile, write_config
from eduvpn.storage import get_uuid


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
    servers, orgs = fetch_servers_orgs()
    institute_matches, org_matches = match_term(servers, orgs, search_term, exact=True)

    if isinstance(search_term, str) and search_term.lower().startswith('https://'):
        base_url = search_term
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
        else:
            matches = [i[1]['display_name'] for i in chain(institute_matches, org_matches)]
            print(
                f"filter '{search_term}' matched with {len(matches)} institutes and organisations, please be more specific.")
            print("Matches:")
            for m in matches:
                print(f" - {extract_translation(m)}")
            exit(1)

    start(base_url)


def refresh(_: argparse.Namespace):
    uuid, auth_url, api_url, profile, token_full = get_storage(check=True)
    token, token_endpoint, authorization_endpoint = token_full
    oauth = OAuth2Session(client_id=CLIENT_ID, token=token, auto_refresh_url=token_endpoint)
    token = oauth.refresh_token(token_url=token_endpoint)
    set_token(auth_url, token, token_endpoint, authorization_endpoint)

    client = get_client()
    cert, key = get_cert_key(client, uuid)
    api_base_uri, token_endpoint, auth_endpoint = get_info(auth_url)

    if not check_certificate(oauth, api_base_uri, cert):
        key, cert = create_keypair(oauth, api_base_uri)
        config = get_config(oauth, api_base_uri, profile)
        save_connection(client, config, key, cert)


def interactive(args: argparse.Namespace):
    search_term = args.match

    if isinstance(search_term, str) and search_term.lower().startswith('https://'):
        auth_url = search_term
        start(auth_url)
        secure_internets = None
    else:
        servers = list_servers(SERVER_URI)
        secure_internets = [s for s in servers if s['server_type'] == 'secure_internet']
        institute_access = [s for s in servers if s['server_type'] == 'institute_access']
        orgs = list_orgs(ORGANISATION_URI)
        choice = menu(institutes=institute_access, orgs=orgs, search_term=search_term)

        if not choice:
            exit(1)

        auth_url, secure_internet = choice
        if not secure_internet:
            secure_internets = None

    start(auth_url, secure_internet=secure_internets, interactive=True)


def fetch_servers_orgs():
    servers = list_servers(SERVER_URI)
    orgs = list_orgs(ORGANISATION_URI)
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


def start(auth_url, secure_internet: Optional[list] = None, interactive: bool = False):
    print(f"starting procedure with auth_url {auth_url}")
    exists = get_token(auth_url)

    if exists:
        print("token exists, restoring")
        token, token_endpoint, authorization_endpoint = exists
        oauth = OAuth2Session(client_id=CLIENT_ID, token=token, auto_refresh_url=token_endpoint)
        api_url, _, _ = get_info(auth_url)
    else:
        print("fetching token")
        api_url, token_endpoint, auth_endpoint = get_info(auth_url)
        oauth = get_oauth(token_endpoint, auth_endpoint)
        set_token(auth_url, oauth.token, token_endpoint, auth_endpoint)

    if secure_internet and interactive:
        choice = secure_internet_choice(secure_internet)
        if choice:
            api_url, _, _ = get_info(choice)

    print(f"using {api_url} as api_url")

    oauth.refresh_token(token_url=token_endpoint)
    profiles = list_profiles(oauth, api_url)
    profile_id = profile_choice(profiles)
    config = get_config(oauth, api_url, profile_id)
    private_key, certificate = create_keypair(oauth, api_url)

    set_api_url(api_url)
    set_auth_url(auth_url)
    set_profile(profile_id)

    target = Path('eduVPN.ovpn').resolve()
    if interactive and nm_available():
        if write_to_nm_choice():
            client = get_client()
            save_connection(client, config, private_key, certificate)
        else:
            write_config(config, private_key, certificate, target)
    else:
        if nm_available():
            client = get_client()
            save_connection(client, config, private_key, certificate)
        else:
            write_config(config, private_key, certificate, target)


def activate(_):
    client = get_client()
    activate_connection(client, get_uuid())


def deactivate(_):
    client = get_client()
    deactivate_connection(client, get_uuid())
