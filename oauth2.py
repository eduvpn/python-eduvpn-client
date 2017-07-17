from requests_oauthlib import OAuth2Session
import socket
import webbrowser
import requests
import base64
import random
import BaseHTTPServer
import hashlib
import json
import nacl.signing
import urlparse
import subprocess
import logging
import os
import sys

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


def main():
    # used for verifying signatures
    verify_key = nacl.signing.VerifyKey(eduvpn_key, encoder=nacl.encoding.Base64Encoder)
    instances = get_instances(eduvpn_base_uri, verify_key)
    instance_urls = get_instance_info(default_instance, verify_key)
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

    with open('eduvpn.ovpn', 'w') as f:
        f.write(ovpn_text)

    open_file('eduvpn.ovpn')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()