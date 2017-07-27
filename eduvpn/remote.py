import json
import logging

import requests

from eduvpn.crypto import gen_code_challenge

logger = logging.getLogger(__name__)


def get_instances(base_uri, verify_key):
    """
    retrieve a list of instances

    generates (display_name, base_uri, logo)
    """
    logger.info("retrieving a list of instances from {}".format(base_uri))
    inst_doc_url = base_uri + '/instances.json'
    inst_doc_sig_url = base_uri + '/instances.json.sig'
    inst_doc = requests.get(inst_doc_url)
    inst_doc_sig = requests.get(inst_doc_sig_url)

    logger.info("verifying signature of {}".format(inst_doc_url))
    _ = verify_key.verify(smessage=inst_doc.content, signature=inst_doc_sig.content.decode('base64'))

    parsed = inst_doc.json()

    for instance in parsed['instances']:
        display_name = instance['display_name']
        base_uri = instance['base_uri']
        logo_uri = instance['logo_uri']
        logo = requests.get(logo_uri)
        yield display_name, base_uri, logo.content



def get_instance_info(instance_uri, verify_key):
    logger.info("Retrieving info from instance {}".format(instance_uri))
    info_uri = instance_uri + '/info.json'
    info = requests.get(info_uri)
    info_sig = requests.get(info_uri + '.sig')
    if info_sig.status_code == 404:
        logger.warning("can't verify signature for {} since there is no signature.".format(info_uri))
    else:
        _ = verify_key.verify(smessage=info.content, signature=info_sig.content.decode('base64'))
    instance_urls = info.json()['api']['http://eduvpn.org/api#2']
    return instance_urls


def create_keypair(oauth, api_base_uri):
    logger.info("Creating and retrieving key pair from {}".format(api_base_uri))
    create_keypair = oauth.post(api_base_uri + '/create_keypair', data={'display_name': 'notebook'})
    keypair = json.loads(create_keypair.content)['create_keypair']['data']
    cert = keypair['certificate']
    key = keypair['private_key']
    return cert, key


def profile_list(oauth, api_base_uri):
    logger.info("Retrieving profile list from {}".format(api_base_uri))
    return json.loads(oauth.get(api_base_uri + '/profile_list').content)


def user_info(oauth, api_base_uri):
    logger.info("Retrieving user info from {}".format(api_base_uri))
    return json.loads(oauth.get(api_base_uri + '/user_info').content)


def user_messages(oauth, api_base_uri):
    logger.info("Retrieving user messages from {}".format(api_base_uri))
    return json.loads(oauth.get(api_base_uri + '/user_messages').content)


def system_messages(oauth, api_base_uri):
    logger.info("Retrieving system messages from {}".format(api_base_uri))
    return json.loads(oauth.get(api_base_uri + '/system_messages').content)


def create_config(oauth, api_base_uri, display_name, profile_id):
    logger.info("Creating config with name '{}' and profile '{}' at {}".format(display_name, profile_id, api_base_uri))
    return json.loads(oauth.post(api_base_uri + '/create_config', data={'display_name': display_name,
                                                                        'profile_id': profile_id}))


def get_profile_config(oauth, api_base_uri, profile_id):
    logger.info("Retrieving profile config from {}".format(api_base_uri))
    return oauth.get(api_base_uri + '/profile_config?profile_id={}'.format(profile_id)).content


def get_auth_url(oauth, code_verifier, auth_endpoint):
    logger.info("Generating authorisation URL using auth endpoint {}".format(auth_endpoint))
    code_challenge_method = "S256"
    code_challenge = gen_code_challenge(code_verifier)
    authorization_url, state = oauth.authorization_url(auth_endpoint,
                                                       code_challenge_method=code_challenge_method,
                                                       code_challenge=code_challenge)
    return authorization_url


