#!/usr/bin/env python2

import logging
from future.moves.urllib.parse import urlparse

from eduvpn.crypto import gen_code_verifier, make_verifier
from eduvpn.local_oauth2 import get_open_port, create_oauth_session, get_oauth_token_code
from eduvpn.local_io import write_cert
#from eduvpn.nm import gen_nm_settings, add_nm_config
from eduvpn.config import read as read_config
from eduvpn.openvpn import format_like_ovpn, parse_ovpn
from eduvpn.remote import get_instances, get_instance_info, create_keypair, get_profile_config, get_auth_url



# we manually pick this one now
default_instance = 'https://demo.eduvpn.nl/'

logger = logging.getLogger(__name__)


def main():
    config = read_config()
    discovery_uri = config['eduvpn']['discovery_uri']
    key = config['eduvpn']['key']
    verifier = make_verifier(key)
    instances = get_instances(discovery_uri, verifier)

    instance_urls = get_instance_info(default_instance, verifier)

    short_instance_name = urlparse(default_instance).hostname.replace(".", "")

    auth_endpoint = instance_urls['authorization_endpoint']
    token_endpoint = instance_urls['token_endpoint']
    api_base_uri = instance_urls['api_base_uri']
    code_verifier = gen_code_verifier()
    port = get_open_port()
    oauth = create_oauth_session(port)
    auth_url = get_auth_url(oauth, code_verifier, auth_endpoint)
    code = get_oauth_token_code(auth_url, port)
    token = oauth.fetch_token(token_endpoint, code=code, code_verifier=code_verifier)
    cert, key = create_keypair(oauth, api_base_uri)
    profile_config = get_profile_config(oauth, api_base_uri)
    ovpn_text = format_like_ovpn(profile_config, cert, key)
    config_dict = parse_ovpn(ovpn_text)

    cert_path = write_cert(cert, 'cert', short_instance_name)
    key_path = write_cert(key, 'key', short_instance_name)
    ca_path = write_cert(config_dict.pop('ca'), 'ca', short_instance_name)
    ta_path = write_cert(config_dict.pop('tls-auth'), 'ta', short_instance_name)

    #nm_config = gen_nm_settings(config_dict, name=short_instance_name)
    #nm_config['vpn']['data'].update({'cert': cert_path, 'key': key_path, 'ca': ca_path, 'ta': ta_path})
    #add_nm_config(nm_config)
