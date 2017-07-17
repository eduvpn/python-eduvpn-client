#!/usr/bin/env python2

from requests_oauthlib import OAuth2Session
import NetworkManager
import socket
import webbrowser
import requests
import base64
import random
import BaseHTTPServer
import base64
import hashlib
import json
import logging
import os
import random
import re
import socket
import subprocess
import sys
import urlparse
import uuid
import webbrowser
from os.path import expanduser

import nacl.signing
import requests
from requests_oauthlib import OAuth2Session


eduvpn_base_uri = 'https://static.eduvpn.nl/'
eduvpn_key = 'E5On0JTtyUVZmcWd+I/FXRm32nSq8R2ioyW7dcu/U88='

# we manually pick this one now
default_instance = 'https://demo.eduvpn.nl/'


landing_page = """<html>
<head>
<title>eduvpn</title>
</head>
<body>
<h1>You can now close this window</h1>
</body>
</html>
"""

logger = logging.getLogger(__name__)


def open_file(filepath):
    """
    Open file document with system associated program
    """
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filepath))
    elif os.name == 'nt':
        os.startfile(filepath)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', filepath))


def get_open_port():
        """find an unused port"""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("",0))
        s.listen(1)
        port = s.getsockname()[1]
        s.close()
        return port


def gen_code_verifier(length=128):
    """
    Generate a high entropy code verifier, used for PKCE
    """
    choices = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~'
    r = random.SystemRandom()
    return "".join(r.choice(choices) for _ in range(length))


def gen_code_challenge(code_verifier):
    """
    Transform the PKCE code verfier in a code challenge
    """
    return base64.urlsafe_b64encode(hashlib.sha256(code_verifier).digest()).rstrip('=')


def one_request(port):
    """
    Listen for one http request on port, then close and return request query
    """
    logger.info("listening for a request on port {}...".format(port))

    class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(landing_page)
            self.server.path = self.path

    httpd = BaseHTTPServer.HTTPServer(('', port), RequestHandler)
    httpd.handle_request()
    httpd.server_close()
    parsed = urlparse.urlparse(httpd.path)
    logger.info("received a request {}".format(httpd.path))
    return urlparse.parse_qs(parsed.query)


def get_instances(base_uri, verify_key):
    """
    retrieve a list of instances
    """
    logger.info("retrieving a list of instances from {}".format(base_uri))
    inst_doc_url = base_uri + '/instances.json'
    inst_doc_sig_url = base_uri + '/instances.json.sig'
    inst_doc = requests.get(inst_doc_url)
    inst_doc_sig = requests.get(inst_doc_sig_url)

    logger.info("verifying signature of {}".format(inst_doc_url))
    _ = verify_key.verify(smessage=inst_doc.content, signature=inst_doc_sig.content.decode('base64'))

    return inst_doc.json()


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


def create_oauth_session(port):
    logger.info("Creating an oauth session, temporarly starting webserver on port {} for auth callback".format(port))
    client_id = "org.eduvpn.app"
    redirect_uri = 'http://127.0.0.1:%s/callback' % port
    scope = "config"
    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=[scope])
    return oauth


def get_auth_url(oauth, code_verifier, auth_endpoint):
    logger.info("Geenrating authorisation URL using auth endport {}".format(auth_endpoint))
    code_challenge_method = "S256"
    code_challenge = gen_code_challenge(code_verifier)
    authorization_url, state = oauth.authorization_url(auth_endpoint,
                                                       code_challenge_method=code_challenge_method,
                                                       code_challenge=code_challenge)
    return authorization_url


def get_oauth_token_code(auth_url, port):
    logger.info("Opening default webbrowser with authorization URL and waiting for callback on port {}".format(port))
    webbrowser.open(auth_url)
    response = one_request(port)
    code = response['code'][0]
    return code


def create_keypair(oauth, api_base_uri):
    logger.info("Creating and retrieving key pair from {}".format(api_base_uri))
    create_keypair = oauth.post(api_base_uri + '/create_keypair', data={'display_name': 'notebook'})
    keypair = json.loads(create_keypair.content)['create_keypair']['data']
    cert = keypair['certificate']
    key = keypair['private_key']
    return cert, key


def _remote_calls(oauth, api_base_uri):
    """currently unused API endpoints"""
    profile_list = oauth.get(api_base_uri + '/profile_list').content
    user_info = oauth.get(api_base_uri + '/user_info').content
    user_messages = oauth.get(api_base_uri + '/user_messages').content
    system_messages = oauth.get(api_base_uri + '/system_messages').content
    create_config = oauth.post(api_base_uri + '/create_config',
                               data={'display_name': 'notebook', 'profile_id': 'internet'})


def get_profile_config(oauth, api_base_uri):
    logger.info("Retrieving profile config from {}".format(api_base_uri))
    return oauth.get(api_base_uri + '/profile_config?profile_id=internet').content


def format_like_ovpn(profile_config, cert, key):
    """create a OVPN format config text"""
    return profile_config + '\n<cert>\n{}\n</cert>\n<key>\n{}\n</key>\n'.format(cert, key)


def parse_ovpn(configtext):
    """Parse a ovpn like config file, return it in dict"""
    config = {}

    def configurator(text):
        for line in text.split('\n'):
            split = line.split('#')[0].strip().split()
            if len(split) == 0:
                continue
            if len(split) == 1:
                yield (split[0], None)
            elif len(split) == 2:
                yield split
            else:
                yield (split[0], split[1:])

    for tag in 'ca', 'tls-auth', 'cert', 'key':
        x = re.search('<{}>(.*)</{}>'.format(tag, tag), configtext, flags=re.S)
        if x:
            full_match = x.group(0)
            config[tag] = x.group(1).replace('\r\n', '\n')
            configtext = configtext.replace(full_match, '')
    config.update(dict(configurator(configtext)))
    return config


def write_cert(content, type_, short_instance_name):
    home = expanduser("~")
    path = home + "/.cert/nm-openvpn/" + short_instance_name + "_" + type_ + ".pem"
    logger.info("writing {} file to {}".format(type_, path))
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, "w") as f:
        f.write(content)
    return path


def gen_nm_settings(config, name):
    """
    Generate a NetworkManager style config dict from a parsed ovpn config dict
    """
    settings = {'connection': {'id': name,
                               'type': 'vpn',
                               'uuid': str(uuid.uuid4())},
                'ipv4': {
                    'method': 'auto',
                },
                'ipv6': {
                    'method': 'auto',
                },
                'vpn': {'data': {'auth': config.get('auth', 'SHA256'),
                                 'cipher': config.get('cipher', 'AES-256-CBC'),
                                 'comp-lzo': config.get('auth', 'adaptive'),
                                 'connection-type': config.get('connection-type', 'tls'),
                                 'dev': 'tun',
                                 'remote': ":".join(config['remote']),
                                 'remote-cert-tls': 'server',
                                 'ta-dir': config.get('key-direction', '1'),
                                 'tls-cipher': config.get('tls-cipher', 'TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384')},
                        'service-type': 'org.freedesktop.NetworkManager.openvpn'}
                }
    return settings


def write_and_open_ovpn(ovpn_text, filename='eduvpn.ovpn'):
    with open(filename, 'w') as f:
        f.write(filename)
    open_file('eduvpn.ovpn')


def add_nm_config(settings):
    name = settings['connection']['id']
    logger.info("generating or updating OpenVPN configuration with name {}".format(name))
    connection = NetworkManager.Settings.AddConnection(settings)
    return connection


def main():
    # used for verifying signatures
    verify_key = nacl.signing.VerifyKey(eduvpn_key, encoder=nacl.encoding.Base64Encoder)
    instances = get_instances(eduvpn_base_uri, verify_key)

    instance_urls = get_instance_info(default_instance, verify_key)

    short_instance_name = urlparse.urlparse(default_instance).hostname.replace(".", "")

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
    nm_config = gen_nm_settings(config_dict, name=short_instance_name)

    cert_path = write_cert(cert, 'cert', short_instance_name)
    key_path = write_cert(key, 'key', short_instance_name)
    ca_path = write_cert(config_dict.pop('ca'), 'ca', short_instance_name)
    ta_path = write_cert(config_dict.pop('tls-auth'), 'ta', short_instance_name)

    nm_config['vpn']['data'].update({'cert': cert_path, 'key': key_path, 'ca': ca_path, 'ta': ta_path})

    add_nm_config(nm_config)
