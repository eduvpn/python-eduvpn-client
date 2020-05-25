import requests
import logging
from typing import Tuple, Optional
from base64 import b64decode
from requests_oauthlib import OAuth2Session
from eduvpn.crypto import common_name_from_cert
from nacl.signing import VerifyKey

logger = logging.getLogger(__name__)


def request(uri: str, verifier: Optional[VerifyKey] = None) -> dict:
    """
    Do a request and check the signature using our public key verifier.
    """
    logger.info(u"Requesting{}".format(uri))
    response = requests.get(uri)
    if response.status_code != 200:
        msg = "Got error code {} requesting {}".format(response.status_code, uri)
        logger.error(msg)
        raise IOError(msg)

    if verifier:
        sig_uri = uri + '.minisig'
        logger.info(u"Retrieving signature {}".format(sig_uri))
        sig_response = requests.get(sig_uri)
        if sig_response.status_code != 200:
            msg = "Can't retrieve signature, requesting {} gave error code {}".format(sig_uri, sig_response.status_code)
            logger.error(msg)
            raise IOError(msg)

        logger.info(u"verifying signature of {}".format(uri))
        signature = sig_response.content.decode('utf-8').split("\n")[1]
        decoded = b64decode(signature)[10:]
        _ = verifier.verify(smessage=response.content, signature=decoded)
    return response.json()


def oauth_request(oauth: OAuth2Session, uri: str, method: str = 'get'):
    """
    Do an oauth request and check if there are no issues
    """
    call = getattr(oauth, method)
    response = call(uri)
    if response.status_code != 200:
        msg = "Got error code {} requesting {}".format(response.status_code, uri)
        logger.error(msg)
        raise IOError(msg)
    return response


def list_orgs(uri: str, verifier: VerifyKey):
    return request(uri, verifier)['organization_list']


def list_servers(uri: str, verifier: VerifyKey):
    return request(uri, verifier)['server_list']


def get_info(base_uri: str):
    uri = base_uri + 'info.json'
    info = request(uri)['api']['http://eduvpn.org/api#2']
    api_base_uri = info['api_base_uri']
    token_endpoint = info['token_endpoint']
    auth_endpoint = info['authorization_endpoint']
    return api_base_uri, token_endpoint, auth_endpoint


def get_config(oauth: OAuth2Session, base_uri: str, profile_id: int) -> str:
    uri = base_uri + f'/profile_config?profile_id={profile_id}'
    return oauth_request(oauth, uri).text


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
