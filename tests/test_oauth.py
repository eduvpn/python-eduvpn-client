from unittest import mock, TestCase
from eduvpn.variants import EDUVPN
from eduvpn.oauth2.challenge import run_challenge, OAuth2Session, OAuthWebServer
from eduvpn.oauth2.http import stringify_image


class TestOauth(TestCase):

    @mock.patch.object(OAuth2Session, 'fetch_token')
    @mock.patch.object(OAuth2Session, 'authorization_url')
    @mock.patch.object(OAuthWebServer, 'run')
    @mock.patch('eduvpn.oauth2.challenge.webbrowser.open')
    def test_run_challenge(
            self,
            webbrowser_open: mock.MagicMock,
            webserver_run: mock.MagicMock,
            authorization_url: mock.MagicMock,
            fetch_token: mock.MagicMock,
    ):
        authorization_url.return_value = ["authorization_url", "state"]
        webserver_run.return_value = {'code': ["test"], 'state': ['state']}
        fetch_token.return_value = "token"

        run_challenge(authorization_endpoint="https://test", token_endpoint="https://test", app_variant=EDUVPN)

    def test_stringify_image(self):
        with self.assertRaises(FileNotFoundError):
            stringify_image("path")
