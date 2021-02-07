from argparse import Namespace
from unittest import TestCase, mock
from unittest.mock import patch, MagicMock
from tests.mock_config import mock_server, mock_org
from eduvpn.menu import menu, input_int, profile_choice, provider_choice, write_to_nm_choice
from eduvpn.menu import search, configure, interactive, match_term, fetch_servers_orgs


class TestMenu(TestCase):
    def test_menu(self):
        with mock.patch('builtins.input', lambda _: '0'):
            menu(institutes=[{'display_name': 'test', 'base_url': 'no url', 'support_contact': 'rutte@gov.nl'}], orgs=[], search_term="test")

    def test_input_int(self):
        with mock.patch('builtins.input', lambda _: '1'):
            input_int(max_=3)

    def test_profile_choice(self):
        profiles = [{'profile_id': 'internet'}]
        profile_choice(profiles=profiles)

    def test_provider_choice(self):
        base_uri = 'bla'
        institutes = [{'display_name': 'test', 'base_url': base_uri, 'support_contact': 'trump@whitehouse.gov'}]
        with mock.patch('builtins.input', lambda _: '0'):
            url, display_name, contact, secure_internet = provider_choice(institutes=institutes, orgs=[])
        self.assertEqual(secure_internet, False)
        self.assertEqual(base_uri, url)

    def test_write_to_nm_choice(self):
        with mock.patch('builtins.input', lambda _: '1'):
            write_to_nm_choice()

    @patch('eduvpn.menu.fetch_servers_orgs')
    @patch('eduvpn.actions.fetch_token')
    def test_configure(self, _: MagicMock, fetch_servers_orgs_: MagicMock):
        fetch_servers_orgs_.return_value = [mock_server], [mock_org]
        configure(Namespace(match='bogus'))
        configure(Namespace(match=''))

    def test_match_term(self):
        match_term(servers=[], orgs=[], search_term="search")

    @patch('eduvpn.menu.fetch_servers_orgs')
    def test_search(self, fetch_servers_orgs_: MagicMock):
        fetch_servers_orgs_.return_value = [mock_server], [mock_org]
        search(Namespace(match='bogus'))

    @patch('eduvpn.menu.list_servers')
    @patch('eduvpn.menu.list_organisations')
    def test_fetch_servers_orgs(self, list_organisations, list_servers):
        fetch_servers_orgs()

    def test_main_with_url(self):
        args = MagicMock()
        args.match = "https://test"
        interactive(args)
