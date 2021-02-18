import logging
import webbrowser
from typing import Optional, Callable, Dict, List
from http.server import BaseHTTPRequestHandler, HTTPServer
import socket
from urllib.parse import urlparse, parse_qs
import requests
from requests_oauthlib import OAuth2Session
from eduvpn.settings import get_brand
from eduvpn.settings import CLIENT_ID, SCOPE, CODE_CHALLENGE_METHOD
from eduvpn.utils import run_in_background_thread

from eduvpn.crypto import gen_code_verifier, gen_code_challenge

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
"""


def stringify_image(logo: str) -> str:
    import base64
    return base64.b64encode(open(logo, 'rb').read()).decode('ascii')


def get_open_port() -> int:
    """
    Find an unused local port.

    returns:
        int: an unused port number
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


def one_request(port: int, lets_connect: bool, timeout: Optional[int] = None) -> Optional[Dict[str, List[str]]]:
    """
    Listen for one http request on port, then close and return request query

    args:
        port (int): the port to listen for the request
    returns:
        str: the request
    """
    logger.info(f"listening for a request on port {port}...")

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

    path = httpd.path  # type: ignore
    if path == '/cancel':
        return None
    else:
        parsed = urlparse(path)
        logger.info(f"received a request {path}")  # type: ignore
        return parse_qs(parsed.query)


def get_oauth(token_endpoint: str, authorization_endpoint: str) -> Optional[OAuth2Session]:
    port = get_open_port()
    return get_oauth_at_port(port, token_endpoint, authorization_endpoint)


def get_oauth_at_port(port: int, token_endpoint: str, authorization_endpoint: str) -> Optional[OAuth2Session]:
    redirect_uri = f'http://127.0.0.1:{port}/callback'
    oauth = OAuth2Session(CLIENT_ID, redirect_uri=redirect_uri, auto_refresh_url=token_endpoint, scope=SCOPE)

    code_verifier = gen_code_verifier()
    code_challenge = gen_code_challenge(code_verifier)
    authorization_url, state = oauth.authorization_url(url=authorization_endpoint,
                                                       code_challenge_method=CODE_CHALLENGE_METHOD,
                                                       code_challenge=code_challenge)

    logger.info(f"opening browser with {authorization_url}")
    webbrowser.open(authorization_url)
    response = one_request(port, lets_connect=False)
    if response is None:
        return None
    code = response['code'][0]
    assert (state == response['state'][0])
    token = oauth.fetch_token(token_url=token_endpoint, code=code,
                              code_verifier=code_verifier,
                              client_id=oauth.client_id, include_client_id=True)
    return token


def send_cancel_request(port):
    requests.get(f'http://127.0.0.1:{port}/cancel')


class OAuthWebServer:
    def __init__(self, port: int):
        self.port = port

    @classmethod
    def start(cls,
              token_endpoint: str,
              authorization_endpoint: str,
              callback: Callable[[Optional[OAuth2Session]], None]) -> 'OAuthWebServer':
        port = get_open_port()

        @run_in_background_thread('oauth-http-server')
        def run_webserver():
            token = get_oauth_at_port(port, token_endpoint, authorization_endpoint)
            callback(token)

        run_webserver()
        return cls(port)

    @run_in_background_thread('oauth-http-server-stop')
    def stop(self):
        send_cancel_request(self.port)
