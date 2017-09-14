import unittest
import mock

from eduvpn.oauth2 import create_oauth_session, get_oauth_token_code, get_open_port, one_request


class TestCrypto(unittest.TestCase):
    def test_create_oauth_session(self):
        create_oauth_session(port=1025)

    @mock.patch('eduvpn.oauth2.one_request')
    @mock.patch('webbrowser.open')
    def test_get_oauth_token_code(self, moch_open, moch_one_request):
        moch_one_request.return_value({"code": "blabla"})
        # todo
        with self.assertRaises(Exception):
            get_oauth_token_code(port=1025)

    def test_get_open_port(self):
        get_open_port()

    @unittest.skip("todo: need to mock the listener")
    @mock.patch('http.server.HTTPServer.handle_request')
    def test_one_request(self, mock_handle_request):
        one_request(1025)
