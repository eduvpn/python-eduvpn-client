import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
import socket
import webbrowser
from future.moves.urllib.parse import urlparse, parse_qs
from requests_oauthlib import OAuth2Session

logger = logging.getLogger(__name__)

landing_page = """
<!doctype html>
<html lang=en>
<title>eduVPN - you can close this screen</title>
<style>
.center {
    font-family: arial;
    font-size: 50px;
    position: absolute;
    text-align: center;
    width: 800px;
    height: 50px;
    top: 50%;
    left: 50%;
    margin-left: -400px; /* margin is -0.5 * dimension */
    margin-top: -25px;
}
</style>
<head>
<meta charset=utf-8>
<title>blah</title>
</head>
<body>
<div class="center">You can now close this window</div>
</body>
</html>
"""




def get_open_port():
    """find an unused port"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


def one_request(port):
    """
    Listen for one http request on port, then close and return request query
    """
    logger.info("listening for a request on port {}...".format(port))

    class RequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(landing_page)
            self.server.path = self.path

    httpd = HTTPServer(('', port), RequestHandler)
    httpd.handle_request()
    httpd.server_close()
    parsed = urlparse(httpd.path)
    logger.info("received a request {}".format(httpd.path))
    return parse_qs(parsed.query)


def create_oauth_session(port):
    """
    Create a callback oauth2 session object
    """
    logger.info("Creating an oauth session, temporarly starting webserver on port {} for auth callback".format(port))
    client_id = "org.eduvpn.app"
    redirect_uri = 'http://127.0.0.1:%s/callback' % port
    scope = "config"
    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=[scope])
    return oauth


def get_oauth_token_code(port):
    """
    Start webserver, open browser, wait for callback response.
    """
    logger.info("waiting for callback on port {}".format(port))
    response = one_request(port)
    code = response['code'][0]
    return code
