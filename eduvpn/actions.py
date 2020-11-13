from logging import getLogger
from typing import Optional

from requests_oauthlib import OAuth2Session
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError

from eduvpn.menu import secure_internet_choice, profile_choice
from eduvpn.nm import activate_connection, deactivate_connection, get_cert_key, save_connection, get_client
from eduvpn.oauth2 import get_oauth
from eduvpn.remote import get_info, check_certificate, create_keypair, get_config, list_profiles
from eduvpn.settings import CLIENT_ID
from eduvpn.storage import get_storage, set_token, get_token, set_api_url, set_auth_url, set_profile
from eduvpn.storage import get_uuid

_logger = getLogger(__file__)


def refresh():
    """
    Refreshes an active configuration. The token is refreshed if expired, and a new token is obtained if the token
    is invalid.
    """
    uuid, auth_url, api_url, profile, token_full = get_storage(check=True)
    token, token_endpoint, auth_endpoint = token_full
    oauth = OAuth2Session(client_id=CLIENT_ID, token=token, auto_refresh_url=token_endpoint)

    try:
        token = oauth.refresh_token(token_url=token_endpoint)
    except InvalidGrantError as e:
        _logger.warning(f"token invalid: {e}")
        oauth = get_oauth(token_endpoint, auth_endpoint)

    set_token(auth_url, token, token_endpoint, auth_endpoint)

    client = get_client()
    cert, key = get_cert_key(client, uuid)
    api_base_uri, token_endpoint, auth_endpoint = get_info(auth_url)

    if not check_certificate(oauth, api_base_uri, cert):
        key, cert = create_keypair(oauth, api_base_uri)
        config = get_config(oauth, api_base_uri, profile)
        save_connection(client, config, key, cert)


def start(auth_url: str, secure_internet: Optional[list] = None, interactive: bool = False):
    """
    Starts the full enrollment procedure.

    Once completed, will store api_url, auth_url and profile in storage. Returns config, private key and certifcate,
    which you should use to compose a valid VPN configuration and store in NM or in a ovpn file.
    """
    # make sure our URL ends with a /
    if auth_url[-1] != '/':
        auth_url += '/'

    _logger.info(f"starting procedure with auth_url {auth_url}")
    exists = get_token(auth_url)

    if exists:
        _logger.info("token exists, restoring")
        token, token_endpoint, authorization_endpoint = exists
        oauth = OAuth2Session(client_id=CLIENT_ID, token=token, auto_refresh_url=token_endpoint)
        api_url, token_endpoint, auth_endpoint = get_info(auth_url)
    else:
        _logger.info("fetching token")
        api_url, token_endpoint, auth_endpoint = get_info(auth_url)
        oauth = get_oauth(token_endpoint, auth_endpoint)
        set_token(auth_url, oauth.token, token_endpoint, auth_endpoint)

    if secure_internet and interactive:
        base_uri = secure_internet_choice(secure_internet)
        if base_uri:
            api_url, _, _ = get_info(base_uri)

    _logger.info(f"using {api_url} as api_url")

    try:
        oauth.refresh_token(token_url=token_endpoint)
    except InvalidGrantError as e:
        _logger.warning(f"token invalid: {e}")
        oauth = get_oauth(token_endpoint, auth_endpoint)
        set_token(auth_url, oauth.token, token_endpoint, auth_endpoint)

    profiles = list_profiles(oauth, api_url)
    profile_id = profile_choice(profiles)
    config = get_config(oauth, api_url, profile_id)
    private_key, certificate = create_keypair(oauth, api_url)

    set_api_url(api_url)
    set_auth_url(auth_url)
    set_profile(profile_id)

    return config, private_key, certificate


def status():
    uuid, auth_url, api_url, profile, token_full = get_storage(check=False)

    _logger.info(f"uuid: {uuid}")
    _logger.info(f"auth_url: {auth_url}")
    _logger.info(f"api_url: {api_url}")
    _logger.info(f"profile: {profile}")

    if token_full:
        token, token_endpoint, authorization_endpoint = token_full
        oauth = OAuth2Session(client_id=CLIENT_ID, token=token, auto_refresh_url=token_endpoint)
        _logger.info(f"token.token_type: {token['token_type']}")
        _logger.info(f"token.expires_in: {token['expires_in']}")
        _logger.info(f"token.expires_at: {token['expires_at']}")
        _logger.info(f"token_endpoint: {token_endpoint}")
        _logger.info(f"authorization_endpoint: {authorization_endpoint}")
        _logger.info(f"oauth.authorized: {oauth.authorized}")
    else:
        _logger.info(f"token_full: {token_full}")


def activate():
    """
    Activates an existing configuration
    """
    client = get_client()
    refresh()
    activate_connection(client, get_uuid())


def deactivate():
    """
    Deactivates an existing configuration
    """
    client = get_client()
    deactivate_connection(client, get_uuid())
