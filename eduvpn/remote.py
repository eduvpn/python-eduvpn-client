import json
import logging
from eduvpn.config import locale

import requests

from eduvpn.crypto import gen_code_challenge

logger = logging.getLogger(__name__)


def translate_display_name(display_name):
    """
    Translates a display_name in the current locale.

    args:
        display_name (str or dict):
    """
    if type(display_name) == dict:
        if locale in display_name:
            return display_name[locale]
        elif "us-US" in display_name:
            return display_name["us-US"]
        else:
            # otherwise just take the first
            return display_name.values()[0]
    else:
        return display_name


def get_instances(discovery_uri, verify_key=None):
    """
    retrieve a list of instances.

    args:
        discovery_uri (str): the URL to parse for instances discovery

    returns:
        generator: display_name, base_uri, logo_data
    """
    logger.info("Discovering instances at {}".format(discovery_uri))
    discovery_sig_uri = discovery_uri + '.sig'
    inst_doc = requests.get(discovery_uri)
    if inst_doc.status_code != 200:
        msg = "Got error code {} requesting {}".format(inst_doc.status_code, discovery_sig_uri)
        logger.error(msg)
        raise IOError(msg)

    if not verify_key:
        logger.warning("verification key not set, not verifying")
    else:
        logger.info("Retrieving signature {}".format(discovery_sig_uri))
        inst_doc_sig = requests.get(discovery_sig_uri)
        if inst_doc_sig.status_code != 200:
            msg = "Can't retrieve signature, requesting {} gave error code {}".format(discovery_sig_uri,
                                                                                    inst_doc_sig.status_code)
            logger.warning(msg)
        else:
            logger.info("verifying signature of {}".format(discovery_uri))
            logger.warning(inst_doc_sig.content)
            _ = verify_key.verify(smessage=inst_doc.content, signature=inst_doc_sig.content.decode('base64'))

    parsed = inst_doc.json()

    authorization_type = [parsed['authorization_type']]

    instances = []

    for instance in parsed['instances']:
        display_name = translate_display_name(instance['display_name'])
        base_uri = instance['base_uri']
        logo_uri = instance['logo']
        logo = requests.get(logo_uri)

        if logo.status_code != 200:
            logo_data = None
        else:
            logo_data = logo.content

            instances.append((display_name, base_uri, logo_data))

    return authorization_type, instances


def get_instance_info(instance_uri, verify_key):
    """
    Retrieve information from instance

    args:
        instance_uri (str): the base URI for the instance
        verify_key (nacl.signing.VerifyKey): the verifykey used to verify the key

    returns:
        tuple(str, str, str): api_base_uri, authorization_endpoint, token_endpoint
    """
    logger.info("Retrieving info from instance {}".format(instance_uri))
    info_uri = instance_uri + '/info.json'
    info = requests.get(info_uri)
    info_sig = requests.get(info_uri + '.sig')
    if info_sig.status_code == 404:
        logger.warning("can't verify signature for {} since there is no signature.".format(info_uri))
    else:
        _ = verify_key.verify(smessage=info.content, signature=info_sig.content.decode('base64'))
    urls = info.json()['api']['http://eduvpn.org/api#2']
    return urls["api_base_uri"], urls["authorization_endpoint"],urls["token_endpoint"]


def create_keypair(oauth, api_base_uri):
    """
    Create remote keypair and return results

    args:
        oauth (requests_oauthlib.OAuth2Session): oauth2 object
        api_base_uri (str): the instance base URI

    returns:
        tuple(str, str): certificate and key
    """
    logger.info("Creating and retrieving key pair from {}".format(api_base_uri))
    create_keypair = oauth.post(api_base_uri + '/create_keypair', data={'display_name': 'notebook'})
    keypair = json.loads(create_keypair.content)['create_keypair']['data']
    cert = keypair['certificate']
    key = keypair['private_key']
    return cert, key


def list_profiles(oauth, api_base_uri):
    """
    List profiles on instance

    args:
        oauth (requests_oauthlib.OAuth2Session): oauth2 object
        api_base_uri (str): the instance base URI

    returns:
        list: of available profiles on the instance (display_name, profile_id, two_factor)
    """
    logger.info("Retrieving profile list from {}".format(api_base_uri))
    data = oauth.get(api_base_uri + '/profile_list').json()['profile_list']['data']
    profiles = []
    for profile in data:
        display_name = translate_display_name(profile["display_name"])
        profile_id = profile["profile_id"]
        two_factor = profile["two_factor"]
        profiles.append((display_name, profile_id, two_factor))
    return profiles


def user_info(oauth, api_base_uri):
    """
    returns the user information

    args:
        oauth (requests_oauthlib.OAuth2Session): oauth2 object
        api_base_uri (str): the instance base URI
    """
    logger.info("Retrieving user info from {}".format(api_base_uri))
    return json.loads(oauth.get(api_base_uri + '/user_info').content)


def user_messages(oauth, api_base_uri):
    """
    Returns user messages

    args:
        oauth (requests_oauthlib.OAuth2Session): oauth2 object
        api_base_uri (str): the instance base URI
    """
    logger.info("Retrieving user messages from {}".format(api_base_uri))
    return json.loads(oauth.get(api_base_uri + '/user_messages').content)


def system_messages(oauth, api_base_uri):
    """
    Return all system messages

    args:
        oauth (requests_oauthlib.OAuth2Session): oauth2 object
        api_base_uri (str): the instance base URI
    """
    logger.info("Retrieving system messages from {}".format(api_base_uri))
    return json.loads(oauth.get(api_base_uri + '/system_messages').content)


def create_config(oauth, api_base_uri, display_name, profile_id):
    """
    Create a configuration for a given profile.

    args:
        oauth (requests_oauthlib.OAuth2Session): oauth2 object
        api_base_uri (str): the instance base URI
        display_name (str):
        profile_id (str):
    """
    logger.info("Creating config with name '{}' and profile '{}' at {}".format(display_name, profile_id, api_base_uri))
    return json.loads(oauth.post(api_base_uri + '/create_config', data={'display_name': display_name,
                                                                        'profile_id': profile_id}))


def get_profile_config(oauth, api_base_uri, profile_id):
    """
    Return a profile configuration

    args:
        oauth (requests_oauthlib.OAuth2Session): oauth2 object
        api_base_uri (str): the instance base URI
        profile_id (str):
    """
    logger.info("Retrieving profile config from {}".format(api_base_uri))
    return oauth.get(api_base_uri + '/profile_config?profile_id={}'.format(profile_id)).content


def get_auth_url(oauth, code_verifier, auth_endpoint):
    """"
    generate a authorization URL.

    args:
        oauth (requests_oauthlib.OAuth2Session): oauth2 object
        code_verifier (str):
        auth_endpoint (str):
        profile_id (str):
    """
    logger.info("Generating authorisation URL using auth endpoint {}".format(auth_endpoint))
    code_challenge_method = "S256"
    code_challenge = gen_code_challenge(code_verifier)
    authorization_url, state = oauth.authorization_url(auth_endpoint,
                                                       code_challenge_method=code_challenge_method,
                                                       code_challenge=code_challenge)
    return authorization_url


