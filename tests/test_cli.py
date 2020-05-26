from unittest import TestCase, mock
from eduvpn.cli import interactive, start


class TestCli(TestCase):
    @mock.patch('eduvpn.cli.save_connection')
    @mock.patch('eduvpn.cli.set_api_url')
    @mock.patch('eduvpn.cli.set_auth_url')
    @mock.patch('eduvpn.cli.set_profile')
    @mock.patch('eduvpn.cli.create_keypair')
    @mock.patch('eduvpn.cli.get_config')
    @mock.patch('eduvpn.cli.list_profiles')
    @mock.patch('eduvpn.cli.get_oauth')
    @mock.patch('eduvpn.cli.get_info')
    @mock.patch('eduvpn.cli.write_config')
    @mock.patch('eduvpn.cli.write_to_nm_choice')
    def test_start(
            self,
            write_to_nm_choice: mock.MagicMock,
            write_config: mock.MagicMock,
            get_info: mock.MagicMock,
            get_oauth: mock.MagicMock,
            list_profiles: mock.MagicMock,
            get_config: mock.MagicMock,
            create_keypair: mock.MagicMock,
            set_profile: mock.MagicMock,
            set_auth_url: mock.MagicMock,
            set_api_url: mock.MagicMock,
            save_connection: mock.MagicMock,
    ):
        write_to_nm_choice.return_value = False
        create_keypair.return_value = ["cert", "key"]
        get_info.return_value = {"api_base_uri", "token_endpoint", "auth_endpoint"}
        list_profiles.return_value = [{'profile_id': 'internet'}]
        get_config.return_value = "a config file"

        args = mock.MagicMock()
        args.match = "https://test"
        start(args)

    @mock.patch('eduvpn.cli.start')
    def test_main_with_url(self, start: mock.MagicMock):
        args = mock.MagicMock()
        args.match = "https://test"
        interactive(args)
