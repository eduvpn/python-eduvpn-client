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
import os
import sys

eduvpn_base_uri = 'https://static.eduvpn.nl/'
eduvpn_key = 'E5On0JTtyUVZmcWd+I/FXRm32nSq8R2ioyW7dcu/U88='


landing_page = """<html>
<head>
<title>eduvpn</title>
</head>
<body>
<h1>You can now close this window</h1>
</body>
</html>
"""


def open_file(filepath):
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
    choices = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~'
    r = random.SystemRandom()
    return "".join(r.choice(choices) for _ in range(length))


def gen_code_challenge(code_verifier):  
    return base64.urlsafe_b64encode(hashlib.sha256(code_verifier).digest()).rstrip('=')


def one_request(port):
    # listen for one request
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
    return urlparse.parse_qs(parsed.query)


# used for verifying signatures
verify_key = nacl.signing.VerifyKey(eduvpn_key, encoder=nacl.encoding.Base64Encoder)

# retrieve a list of instances
inst_doc_url = eduvpn_base_uri + '/instances.json'
inst_doc_sig_url = eduvpn_base_uri + '/instances.json.sig'
inst_doc = requests.get(inst_doc_url)
inst_doc_sig = requests.get(inst_doc_sig_url)

# verify signature
_ = verify_key.verify(smessage=inst_doc.content, signature=inst_doc_sig.content.decode('base64'))

instances = [i['base_uri'] for i in inst_doc.json()['instances']]

instance = 'https://demo.eduvpn.nl/'

# get info from server
info = requests.get(instance + '/info.json')
#info_sig = requests.get(instance + '/info.json.sig')
#_ = verify_key.verify(smessage=info.content, signature=info_sig.content.decode('base64'))


instance_urls = info.json()['api']['http://eduvpn.org/api#2']
authorization_endpoint = instance_urls['authorization_endpoint']
token_endpoint = instance_urls['token_endpoint']
api_base_uri = instance_urls['api_base_uri']


port = get_open_port()
client_id = "org.eduvpn.app"
redirect_uri = 'http://127.0.0.1:%s/callback' % port
auth_uri = 'https://demo.eduvpn.nl/portal/_oauth/authorize'
response_type = "code"
scope = "config"
code_challenge_method = "S256"
code_verifier = gen_code_verifier()
code_challenge = gen_code_challenge(code_verifier)

oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=[scope])
# we add extra arguments below for PKCE
authorization_url, state = oauth.authorization_url(authorization_endpoint, code_challenge_method=code_challenge_method,
                                                   code_challenge=code_challenge)

webbrowser.open(authorization_url)
response = one_request(port)

token = oauth.fetch_token(token_endpoint, code=response['code'][0], code_verifier=code_verifier)

profile_list = oauth.get(api_base_uri + '/profile_list').content
user_info = oauth.get(api_base_uri + '/user_info').content
user_messages = oauth.get(api_base_uri + '/user_messages').content
system_messages = oauth.get(api_base_uri + '/system_messages').content
create_config = oauth.post(api_base_uri + '/create_config', data={'display_name': 'notebook', 'profile_id': 'internet'})
create_keypair = oauth.post(api_base_uri + '/create_keypair', data={'display_name': 'notebook'})
keypair = json.loads(create_keypair.content)['create_keypair']['data']
cert = keypair['certificate']
key = keypair['private_key']
profile_config = oauth.get(api_base_uri + '/profile_config?profile_id=internet').content
final_config = profile_config + '\n<cert>\n{}\n</cert>\n<key>\n{}\n</key>\n'.format(cert, key)

with open('eduvpn.ovpn', 'w') as f:
    f.write(final_config)

open_file('eduvpn.ovpn')

