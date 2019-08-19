# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
# noinspection PyCompatibility
from http.server import BaseHTTPRequestHandler, HTTPServer
import socket
from future.moves.urllib.parse import urlparse, parse_qs
from requests_oauthlib import OAuth2Session
from eduvpn.brand import get_brand
from typing import Any, Optional, Tuple
from eduvpn.metadata import Metadata

logger = logging.getLogger(__name__)

landing_page = """
<!doctype html>
<html lang=en>
<head>
<meta charset=utf-8>
<title>{brand} - bye</title>
<style>
.center {{
    font-family: arial;
    font-size: 30px;
    position: absolute;
    text-align: center;
    width: 800px;
    height: 50px;
    top: 50%;
    left: 50%;
    margin-left: -400px; /* margin is -0.5 * dimension */
    margin-top: -25px;
}}
</style>
</head>
<body>

<div class="center">
<img src="data:image/png;base64,{logo}" width="150">
<p>You can now close this window.</p>
</div>
</body>
</html>
"""  # type: str

client_id_lets_connect = "org.letsconnect-vpn.app.linux"  # type: str
client_id_eduvpn = "org.eduvpn.app.linux"  # type: str

scope = ["config"]  # type: Any


def get_open_port():  # type: () -> int
    """Find an unused local port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


def one_request(port, lets_connect, timeout=None):  # type: (int, bool, Optional[int]) -> str
    """Listen for one http request on port, then close and return request query."""
    logger.info("listening for a request on port {}...".format(port))

    class RequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            logo, name = get_brand(lets_connect)
            logo = stringify_image(logo)
            content = landing_page.format(logo=logo, brand=name).encode('utf-8')
            self.wfile.write(content)
            self.server.path = self.path

    httpd = HTTPServer(('', port), RequestHandler)
    if timeout:
        httpd.socket.settimeout(timeout)
    httpd.handle_request()
    httpd.server_close()

    if not hasattr(httpd, "path"):
        raise Exception("Invalid response received")

    parsed = urlparse(httpd.path)
    logger.info("received a request {}".format(httpd.path))
    return parse_qs(parsed.query)


def stringify_image(logo):
	# type: (str) -> str
    import base64
    return base64.b64encode(open(logo, 'rb').read()).decode('ascii')


def create_oauth_session(port, lets_connect, auto_refresh_url):  # type: (int, bool, str) -> OAuth2Session
    """Create a oauth2 callback webserver."""
    logger.info("Creating an oauth session, temporarily starting webserver on port {} for auth callback".format(port))
    redirect_uri = 'http://127.0.0.1:%s/callback' % port

    if lets_connect:
        client_id = client_id_lets_connect
    else:
        client_id = client_id_eduvpn

    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, auto_refresh_url=auto_refresh_url, scope=scope)
    return oauth


def get_oauth_token_code(port, lets_connect, timeout=None):  # type: (int, bool, int) -> Tuple[str, str]
    """Start webserver, open browser, wait for callback response. """
    logger.info("waiting for callback on port {}".format(port))
    response = one_request(port, lets_connect, timeout)  # type: str
    if 'code' in response and 'state' in response:
        code = response['code'][0]
        state = response['state'][0]
        return code, state
    elif 'error' in response:
        raise Exception("Can't authenticate: {}".format(response['error']))
    else:
        raise Exception("Unknown error during authentication: {}".format(response))


def oauth_from_token(meta, lets_connect):  # type: (Metadata, bool) -> OAuth2Session
    """Recreate a oauth2 object from a token."""
    def inner(new_token):
        meta.update_token(new_token)

    if lets_connect:
        client_id = client_id_lets_connect
    else:
        client_id = client_id_eduvpn

    return OAuth2Session(token=meta.token, auto_refresh_url=meta.token_endpoint, scope=scope, token_updater=inner,
                         client_id=client_id)
