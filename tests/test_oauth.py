from unittest import mock, TestCase
from eduvpn.oauth2 import get_oauth, one_request, get_open_port, stringify_image, OAuth2Session


class TestOauth(TestCase):

    @mock.patch.object(OAuth2Session, 'fetch_token')
    @mock.patch.object(OAuth2Session, 'authorization_url')
    @mock.patch('eduvpn.oauth2.one_request')
    @mock.patch('eduvpn.oauth2.webbrowser.open')
    def test_get_oauth(
            self,
            webbrowser_open: mock.MagicMock,
            one_request: mock.MagicMock,
            authorization_url: mock.MagicMock,
            fetch_token: mock.MagicMock,
    ):
        authorization_url.return_value = ["authorization_url", "state"]
        one_request.return_value = {'code': ["test"], 'state': ['state']}
        fetch_token.return_value = "token"

        get_oauth(authorization_endpoint="https://test", token_endpoint="https://test")

    def test_one_request(self):
        with self.assertRaises(Exception):
            one_request(port=9999, lets_connect=True, timeout=1)

        # one_request(port=9999, lets_connect=False)

    def test_get_open_port(self):
        get_open_port()

    def test_stringify_image(self):
        with self.assertRaises(FileNotFoundError):
            stringify_image("path")
