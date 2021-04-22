import logging
from typing import Tuple, List, Dict, Any
import json

import requests
from requests_oauthlib import OAuth2Session

from eduvpn.crypto import common_name_from_cert
from eduvpn.crypto import validate

logger = logging.getLogger(__name__)


class InvalidProfile(Exception):
    def __init__(self, message):
        self.message = message


def request(uri: str, verify: bool = False) -> dict:
    """
    Do a request and check the signature using our public key verifier.
    """
    logger.info(f"Requesting {uri}")
    try:
        response = requests.get(uri)
    except Exception as e:
        msg = f"Got exception {e} requesting {uri}"
        logger.debug(msg)
        raise
    if response.status_code != 200:
        msg = f"Got error code {response.status_code} requesting {uri}"
        logger.error(msg)
        raise IOError(msg)

    if verify:
        sig_uri = uri + '.minisig'
        logger.info(f"Retrieving signature {sig_uri}")
        sig_response = requests.get(sig_uri)
        if sig_response.status_code != 200:
            msg = f"Can't retrieve signature, requesting {sig_uri} gave error code {sig_response.status_code}"
            logger.error(msg)
            raise IOError(msg)

        logger.info(f"verifying signature of {uri}")
        signature = sig_response.content.decode('utf-8').split("\n")[1]
        _ = validate(content=response.content, signature=signature)
    return response.json()


def oauth_request(oauth: OAuth2Session, uri: str, method: str = 'get'):
    """
    Do an oauth request and check if there are no issues
    """
    call = getattr(oauth, method)
    response = call(uri)
    if response.status_code != 200:
        msg = f"Got error code {response.status_code} requesting {uri}"
        logger.error(msg)
        raise IOError(msg)
    return response


def list_organisations(uri: str) -> List[Dict[str, Any]]:
    try:
        result = request(uri, verify=True)['organization_list']
    except Exception as e:
        logger.error(f"Got exception {e} requesting {uri} for organization_list")
        raise
    return result


def list_servers(uri: str) -> List[Dict[str, Any]]:
    try:
        result = request(uri, verify=True)['server_list']
    except Exception as e:
        logger.error(f"Got exception {e} requesting {uri} for server_list")
        raise
    return result


def get_full_info(base_uri: str) -> Dict[str, Any]:
    if not base_uri.endswith('/'):
        base_uri += '/'
    uri = base_uri + 'info.json'
    return request(uri)['api']['http://eduvpn.org/api#2']


def get_info(base_uri: str):
    info = get_full_info(base_uri)
    api_base_uri = info['api_base_uri']
    token_endpoint = info['token_endpoint']
    auth_endpoint = info['authorization_endpoint']
    return api_base_uri, token_endpoint, auth_endpoint


def get_config(oauth: OAuth2Session, base_uri: str, profile_id: str) -> str:
    uri = base_uri + f'/profile_config?profile_id={profile_id}'
    text = oauth_request(oauth, uri).text
    try:
        data = json.loads(text)
    except json.decoder.JSONDecodeError:
        # On success, the response it *not* JSON but a valid ovpn file.
        pass
    else:
        # On errors, the server responds with JSON.
        if not data['profile_config']['ok']:
            logging.error(f"invalid profile_id: {profile_id} @ {base_uri}: {data}")
            raise InvalidProfile(data['profile_config']['error'])
        raise ValueError(data)
    return text


def list_profiles(oauth: OAuth2Session, api_base_uri: str):
    uri = api_base_uri + '/profile_list'
    return oauth_request(oauth, uri).json()['profile_list']['data']


def create_keypair(oauth: OAuth2Session, api_base_uri: str) -> Tuple[str, str]:
    uri = api_base_uri + '/create_keypair'
    keypair = oauth_request(oauth, uri, method='post').json()['create_keypair']['data']
    private_key = keypair['private_key']
    certificate = keypair['certificate']
    return private_key, certificate


def system_messages(oauth: OAuth2Session, api_base_uri: str):
    uri = api_base_uri + '/system_messages'
    return oauth_request(oauth, uri).json()['system_messages']['data']


def check_certificate(oauth: OAuth2Session, api_base_uri: str, certificate: str):
    common_name = common_name_from_cert(certificate.encode('ascii'))
    uri = api_base_uri + '/check_certificate?common_name=' + common_name
    return oauth_request(oauth, uri).json()['check_certificate']['data']['is_valid']
