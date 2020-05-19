from eduvpn.menu import menu, input_int, profile_choice, search, provider_choice, write_to_nm_choice
from unittest import TestCase, mock


class TestMenu(TestCase):
    def test_menu(self):
        menu(institutes=[], orgs=[], search_term="test")

    def test_input_int(self):
        with mock.patch('builtins.input', lambda _: '1'):
            input_int(max_=3)

    def test_profile_choice(self):
        profiles = [{'profile_id': 'internet'}]
        profile_choice(profiles=profiles)

    def test_search(self):
        search(institutes=[], orgs=[], search_term="test")

    def test_provider_choice(self):
        base_uri = 'bla'
        institutes = [{'display_name': 'test', 'base_url': base_uri}]
        with mock.patch('builtins.input', lambda _: '0'):
            type_, url = provider_choice(institutes=institutes, orgs=[])
        self.assertEqual(type_, 'base_url')
        self.assertEqual(base_uri, url)

    def test_write_to_nm_choice(self):
        with mock.patch('builtins.input', lambda _: '1'):
            write_to_nm_choice()
