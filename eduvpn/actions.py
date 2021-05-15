from logging import getLogger
from typing import Tuple

from requests_oauthlib import OAuth2Session
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError

from eduvpn.menu import profile_choice
from eduvpn.nm import activate_connection_with_mainloop, get_cert_key, get_client,\
    nm_available, connection_status, save_connection_with_mainloop, deactivate_connection_with_mainloop
from eduvpn import oauth2
from eduvpn.remote import get_info, check_certificate, create_keypair, get_config, list_profiles
from eduvpn.settings import CLIENT_ID
from eduvpn.variants import EDUVPN
from eduvpn.storage import get_storage, get_current_metadata, update_token, get_uuid, get_all_metadatas

_logger = getLogger(__file__)


def refresh():
    """
    Refreshes an active configuration. The token is refreshed if expired, and a new token is obtained if the token
    is invalid.
    """
    uuid, auth_url, metadata = get_storage(check=True)
    token, token_endpoint, auth_endpoint, api_url, display_name, support_contact, profile_id, con_type, country_id, _, _ = metadata
    oauth = OAuth2Session(client_id=CLIENT_ID, token=token, auto_refresh_url=token_endpoint)

    try:
        token = oauth.refresh_token(token_url=token_endpoint)
    except InvalidGrantError as e:
        _logger.warning(f"token invalid: {e}")
        oauth = oauth2.run_challenge(token_endpoint, auth_endpoint, EDUVPN)

    api_base_uri, token_endpoint, auth_endpoint = get_info(auth_url)
    client = get_client()
    try:
        cert, key = get_cert_key(client, uuid)
    except IOError:
        # probably the NM connection was deleted
        cert = None

    if not cert or not check_certificate(oauth, api_base_uri, cert):
        key, cert = create_keypair(oauth, api_base_uri)
        config = get_config(oauth, api_base_uri, profile_id)
        save_connection_with_mainloop(config, key, cert)

    update_token(token)


def fetch_token(auth_url: str) -> Tuple[str, OAuth2Session, str, str]:
    """
    Starts the full enrollment procedure.

    Once completed, will store api_url, auth_url and profile in storage. Returns config, private key and certifcate,
    which you should use to compose a valid VPN configuration and store in NM or in a ovpn file.
    """
    # make sure our URL ends with a /
    if auth_url[-1] != '/':
        auth_url += '/'

    _logger.info(f"starting procedure with auth_url {auth_url}")
    exists = get_current_metadata(auth_url)

    if exists:
        _logger.info("token exists, restoring")
        token, token_endpoint, auth_endpoint, api_url, display_name, support_contact, profile_id, con_type, country_id, _, _ = exists
        oauth = OAuth2Session(client_id=CLIENT_ID, token=token, auto_refresh_url=token_endpoint)
        api_url, token_endpoint, auth_endpoint = get_info(auth_url)
    else:
        _logger.info("fetching token")
        api_url, token_endpoint, auth_endpoint = get_info(auth_url)
        oauth = oauth2.run_challenge(token_endpoint, auth_endpoint, EDUVPN)

    try:
        oauth.refresh_token(token_url=token_endpoint)
    except InvalidGrantError as e:
        _logger.warning(f"token invalid: {e}")
        oauth = oauth2.run_challenge(token_endpoint, auth_endpoint, EDUVPN)

    return api_url, oauth, token_endpoint, auth_endpoint


def get_profile(oauth: OAuth2Session, api_url: str, interactive: bool = False):
    profiles = list_profiles(oauth, api_url)
    if interactive:
        return profile_choice(profiles)
    else:
        return profile_choice(profiles[:1])


def get_config_and_keycert(oauth: OAuth2Session, api_url: str, profile_id: str) -> Tuple[str, str, str]:
    config = get_config(oauth, api_url, profile_id)
    private_key, certificate = create_keypair(oauth, api_url)
    return config, private_key, certificate


def status():
    uuid, current_auth_url, metadata = get_storage(check=False)

    print("\n\n# Global configuration\n")
    print(f"uuid: {uuid}")
    print(f"auth_url: {current_auth_url}")

    if nm_available():
        active_uuid, status = connection_status(get_client())
        print(f"VPN connection active: {bool(active_uuid)}")
        print(f"VPN NM status is: {status}")
        print(f"Active VPN connection is EduVPN: {bool(uuid == active_uuid)}")

    print("\n\n## Previous connection properties\n")

    for auth_url, props in get_all_metadatas().items():
        if auth_url == current_auth_url:
            print(" ** CURRENT ACTIVE CONFIGURATION **")
        print(f"auth_url {auth_url}")
        for t in ['api_url', 'display_name', 'support_contact', 'profile_id',
                  'token_endpoint', 'authorization_endpoint', 'con_type', 'country_id']:
            print(f"{t}: {props[t]}")
        print(f"token.token_type: {props['token']['token_type']}")
        print(f"token.expires_in: {props['token']['expires_in']}")
        print(f"token.expires_at: {props['token']['expires_at']}")
        print("\n\n")


def activate():
    """
    Activates an existing configuration
    """
    refresh()
    activate_connection_with_mainloop(get_uuid())


def deactivate():
    """
    Deactivates an existing configuration
    """
    deactivate_connection_with_mainloop(get_uuid())
