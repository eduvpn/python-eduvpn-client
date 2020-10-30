from unittest import TestCase
from unittest.mock import patch, MagicMock
from argparse import Namespace
from eduvpn.actions import interactive, start, refresh, activate, configure, deactivate, match_term, search, \
    fetch_servers_orgs
from tests.mock_config import mock_server, mock_org
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError

class TestCli(TestCase):
    @patch('eduvpn.actions.save_connection')
    @patch('eduvpn.actions.set_api_url')
    @patch('eduvpn.actions.set_auth_url')
    @patch('eduvpn.actions.set_profile')
    @patch('eduvpn.actions.create_keypair')
    @patch('eduvpn.actions.get_config')
    @patch('eduvpn.actions.list_profiles')
    @patch('eduvpn.actions.get_oauth')
    @patch('eduvpn.actions.get_info')
    @patch('eduvpn.actions.write_config')
    @patch('eduvpn.actions.write_to_nm_choice')
    @patch('eduvpn.actions.get_client')
    def test_start(
            self,
            get_client: MagicMock,
            write_to_nm_choice: MagicMock,
            write_config: MagicMock,
            get_info: MagicMock,
            get_oauth: MagicMock,
            list_profiles: MagicMock,
            get_config: MagicMock,
            create_keypair: MagicMock,
            set_profile: MagicMock,
            set_auth_url: MagicMock,
            set_api_url: MagicMock,
            save_connection: MagicMock,
    ):
        write_to_nm_choice.return_value = False
        create_keypair.return_value = ["cert", "key"]
        get_info.return_value = {"api_base_uri", "token_endpoint", "auth_endpoint"}
        list_profiles.return_value = [{'profile_id': 'internet'}]
        get_config.return_value = "a config file"

        args = MagicMock()
        args.match = "https://test"
        start(args)

    @patch('eduvpn.actions.start')
    def test_main_with_url(self, start: MagicMock):
        args = MagicMock()
        args.match = "https://test"
        interactive(args)

    @patch('eduvpn.actions.OAuth2Session')
    @patch('eduvpn.actions.get_storage')
    @patch('eduvpn.actions.get_cert_key')
    @patch('eduvpn.actions.get_info')
    @patch('eduvpn.actions.check_certificate')
    @patch('eduvpn.actions.create_keypair')
    @patch('eduvpn.actions.get_config')
    @patch('eduvpn.actions.save_connection')
    def test_refresh(
            self,
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
        get_storage.return_value = "uuid", "auth_url", "api_url", "profile", ({}, "", "")
        get_info.return_value = "api_base_uri", "token_endpoint", "auth_endpoint"
        refresh(Namespace())

    @patch('eduvpn.actions.OAuth2Session')
    @patch('eduvpn.actions.get_storage')
    @patch('eduvpn.actions.get_cert_key')
    @patch('eduvpn.actions.get_info')
    @patch('eduvpn.actions.check_certificate')
    @patch('eduvpn.actions.create_keypair')
    @patch('eduvpn.actions.get_config')
    @patch('eduvpn.actions.save_connection')
    def test_refresh_invalid_signature(
            self,
            save_connection: MagicMock,
            get_config: MagicMock,
            create_keypair: MagicMock,
            check_certificate: MagicMock,
            get_info: MagicMock,
            get_cert_key: MagicMock,
            get_storage: MagicMock, oauth: MagicMock
    ):
        oauth.refresh_token = MagicMock(side_effect=InvalidGrantError("invalid signature")
)
        create_keypair.return_value = "key", "cert"
        check_certificate.return_value = False
        get_cert_key.return_value = "cert", "key"
        get_storage.return_value = "uuid", "auth_url", "api_url", "profile", ({}, "", "")
        get_info.return_value = "api_base_uri", "token_endpoint", "auth_endpoint"
        refresh(Namespace())

    @patch('eduvpn.actions.refresh')
    def test_activate(self, _):
        activate(Namespace())

    @patch('eduvpn.actions.fetch_servers_orgs')
    @patch('eduvpn.actions.start')
    def test_configure(self, _: MagicMock, fetch_servers_orgs_: MagicMock):
        fetch_servers_orgs_.return_value = [mock_server], [mock_org]
        configure(Namespace(match='bogus'))
        configure(Namespace(match=''))

    def test_deactivate(self):
        deactivate(Namespace())

    def test_match_term(self):
        match_term(servers=[], orgs=[], search_term="search")

    @patch('eduvpn.actions.fetch_servers_orgs')
    def test_search(self, fetch_servers_orgs_: MagicMock):
        fetch_servers_orgs_.return_value = [mock_server], [mock_org]
        search(Namespace(match='bogus'))

    @patch('eduvpn.actions.list_servers')
    @patch('eduvpn.actions.list_organisations')
    def test_fetch_servers_orgs(self, list_organisations, list_servers):
        fetch_servers_orgs()
