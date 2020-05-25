from unittest import TestCase, mock
from eduvpn.__main__ import letsconnect, parse_args, interactive


class TestMain(TestCase):
    def test_letsconnect(self):
        with self.assertRaises(NotImplementedError):
            letsconnect()

    def test_parse_args(self):
        with self.assertRaises(SystemExit):
            parse_args(["test"])

    @mock.patch('eduvpn.__main__.create_keypair')
    @mock.patch('eduvpn.__main__.get_config')
    @mock.patch('eduvpn.__main__.list_profiles')
    @mock.patch('eduvpn.__main__.get_oauth')
    @mock.patch('eduvpn.__main__.get_info')
    @mock.patch('eduvpn.__main__.write_config')
    @mock.patch('eduvpn.__main__.write_to_nm_choice')

    def test_main(
            self,
            write_to_nm_choice: mock.MagicMock,
            write_config: mock.MagicMock,
            get_info: mock.MagicMock,
            get_oauth: mock.MagicMock,
            list_profiles: mock.MagicMock,
            get_config: mock.MagicMock,
            create_keypair: mock.MagicMock,
    ):
        write_to_nm_choice.return_value = False
        create_keypair.return_value = ["cert", "key"]
        get_info.return_value = {"api_base_uri", "token_endpoint", "auth_endpoint"}
        list_profiles.return_value = [{'profile_id': 'internet'}]
        get_config.return_value = "a config file"

        args = mock.MagicMock()
        args.match = "https://test"
        interactive(args)
