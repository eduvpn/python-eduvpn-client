import unittest
import mock
from http.server import BaseHTTPRequestHandler, HTTPServer

from eduvpn.local_oauth2 import create_oauth_session, get_oauth_token_code, get_open_port, one_request


class TestCrypto(unittest.TestCase):
    def test_create_oauth_session(self):
        create_oauth_session(port=1025)

    @mock.patch('eduvpn.local_oauth2.one_request')
    @mock.patch('webbrowser.open')
    def test_get_oauth_token_code(self, moch_open, moch_one_request):
        get_oauth_token_code(auth_url='bla', port=1025)

    def test_get_open_port(self):
        get_open_port()

    @mock.patch('http.server.HTTPServer.handle_request')
    @mock.patch('http.server.HTTPServer.path')
    def test_one_request(self, moch_path, mock_handle_request):
        one_request(1025)
