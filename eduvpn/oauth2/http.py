import logging
from typing import Optional, Callable
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from gettext import gettext as _
import requests
from ..variants import ApplicationVariant
from ..utils import run_in_background_thread


logger = logging.getLogger(__name__)


HTTP_HOST = 'localhost'
CALLBACK_PATH = '/callback'
CANCEL_PATH = '/cancel'


landing_page = """
<!doctype html>
<html lang=en>
<head>
<meta charset=utf-8>
<title>{brand}</title>
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
<p>{message}</p>
</div>
</body>
</html>
"""


def stringify_image(logo: str) -> str:
    import base64
    with open(logo, 'rb') as logo_file:
        return base64.b64encode(logo_file.read()).decode('ascii')


def build_response_page(app_variant) -> bytes:
    logo = stringify_image(app_variant.icon)
    message = _("You can now close this window.")
    return landing_page.format(logo=logo, brand=app_variant.name, message=message).encode('utf-8')


class OAuthWebServer:
    scheme = 'http'

    def __init__(self, app_variant: ApplicationVariant):
        self.app_variant = app_variant
        handler = partial(RequestHandler, oauth_web_server=self)
        self.server = HTTPServer((HTTP_HOST, 0), handler)
        self._completed = False
        self._result = None

    @property
    def address(self):
        return f'{self.server.server_address[0]}:{self.server.server_port}'

    @property
    def success_url(self):
        return f'{self.scheme}://{self.address}{CALLBACK_PATH}'

    @property
    def cancel_url(self):
        return f'{self.scheme}://{self.address}{CANCEL_PATH}'

    def run(self) -> Optional[dict]:
        logger.info(f"listening for a request at {self.address}...")
        self.server.handle_request()
        self.server.server_close()
        if not self._completed:
            logger.error("invalid request received")
        return self._result

    @run_in_background_thread('oauth-http-server-run')
    def run_in_background(self, callback: Callable[[Optional[dict]], None]):
        session = self.run()
        callback(session)

    @run_in_background_thread('oauth-http-server-stop')
    def stop(self):
        requests.get(self.cancel_url)


class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, oauth_web_server: OAuthWebServer, **kwargs):
        self._oauth_web_server = oauth_web_server
        super().__init__(*args, **kwargs)

    def do_GET(self):
        logger.info(f"received a request {self.path}")
        # notify the auth webserver of the result
        self._oauth_web_server._completed = True
        if self.path == CANCEL_PATH:
            self._oauth_web_server._result = None
        else:
            url = urlparse(self.path)
            query = parse_qs(url.query)
            self._oauth_web_server._result = query
        # send back a response
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        page = build_response_page(self._oauth_web_server.app_variant)
        self.wfile.write(page)
