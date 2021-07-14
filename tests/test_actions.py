from unittest import TestCase
from unittest.mock import patch, MagicMock
from eduvpn.actions import fetch_token, refresh, activate, deactivate
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError


class TestCli(TestCase):
    @patch('eduvpn.actions.save_connection_with_mainloop')
    @patch('eduvpn.actions.create_keypair')
    @patch('eduvpn.actions.get_config')
    @patch('eduvpn.actions.list_profiles')
    @patch('eduvpn.actions.oauth2.run_challenge')
    @patch('eduvpn.actions.get_info')
    @patch('eduvpn.actions.get_client')
    def test_start(
            self,
            get_client: MagicMock,
            get_info: MagicMock,
            run_challenge: MagicMock,
            list_profiles: MagicMock,
            get_config: MagicMock,
            create_keypair: MagicMock,
            save_connection: MagicMock,
    ):
        create_keypair.return_value = ["cert", "key"]
        get_info.return_value = {"api_base_uri", "token_endpoint", "auth_endpoint"}
        list_profiles.return_value = [{'profile_id': 'internet'}]
        get_config.return_value = "a config file"

        args = MagicMock()
        args.match = "https://test"
        fetch_token(args)

    @patch('eduvpn.actions.OAuth2Session')
    @patch('eduvpn.actions.get_storage')
    @patch('eduvpn.actions.get_cert_key')
    @patch('eduvpn.actions.get_info')
    @patch('eduvpn.actions.check_certificate')
    @patch('eduvpn.actions.create_keypair')
    @patch('eduvpn.actions.get_config')
    @patch('eduvpn.actions.save_connection_with_mainloop')
    @patch('eduvpn.actions.get_client')
    def test_refresh(
            self,
            get_client: MagicMock,
            save_connection: MagicMock,
            get_config: MagicMock,
            create_keypair: MagicMock,
            check_certificate: MagicMock,
            get_info: MagicMock,
            get_cert_key: MagicMock,
            get_storage: MagicMock, _: MagicMock
    ):
        create_keypair.return_value = "key", "cert"
        check_certificate.return_value = False
        get_cert_key.return_value = "cert", "key"
        get_storage.return_value = "uuid", "auth_url", ({}, "", "", "", "", "", "", "", "", None, None)
        get_info.return_value = "api_base_uri", "token_endpoint", "auth_endpoint"
        refresh()

    @patch('eduvpn.actions.OAuth2Session')
    @patch('eduvpn.actions.get_storage')
    @patch('eduvpn.actions.get_cert_key')
    @patch('eduvpn.actions.get_info')
    @patch('eduvpn.actions.check_certificate')
    @patch('eduvpn.actions.create_keypair')
    @patch('eduvpn.actions.get_config')
    @patch('eduvpn.actions.save_connection_with_mainloop')
    @patch('eduvpn.actions.get_client')
    def test_refresh_invalid_signature(
            self,
            get_client: MagicMock,
            save_connection: MagicMock,
            get_config: MagicMock,
            create_keypair: MagicMock,
            check_certificate: MagicMock,
            get_info: MagicMock,
            get_cert_key: MagicMock,
            get_storage: MagicMock, oauth: MagicMock
    ):
        oauth.refresh_token = MagicMock(side_effect=InvalidGrantError("invalid signature"))

        create_keypair.return_value = "key", "cert"
        check_certificate.return_value = False
        get_cert_key.return_value = "cert", "key"
        get_storage.return_value = "uuid", "auth_url", ({}, "", "", "", "", "", "", "", "", None, None)
        get_info.return_value = "api_base_uri", "token_endpoint", "auth_endpoint"
        refresh()

    @patch('eduvpn.actions.refresh')
    @patch('eduvpn.actions.activate_connection_with_mainloop')
    @patch('eduvpn.actions.get_client')
    def test_activate(self, get_client, activate_connection, refresh):
        activate()

    @patch('eduvpn.actions.get_client')
    @patch('eduvpn.actions.deactivate_connection_with_mainloop')
    def test_deactivate(self, get_client, deactivate_connection_with_mainloop):
        deactivate()
