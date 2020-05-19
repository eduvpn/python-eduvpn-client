from unittest import TestCase, mock
from eduvpn.__main__ import letsconnect, parse_args, main


class TestMain(TestCase):
    def test_letsconnect(self):
        with self.assertRaises(NotImplementedError):
            letsconnect()

    def test_parse_args(self):
        parse_args(["test"])

    @mock.patch('eduvpn.__main__.create_keypair')
    @mock.patch('eduvpn.__main__.get_config')
    @mock.patch('eduvpn.__main__.list_profiles')
    @mock.patch('eduvpn.__main__.get_oauth')
    @mock.patch('eduvpn.__main__.get_info')
    def test_main(
            self,
            get_info: mock.MagicMock,
            get_oauth: mock.MagicMock,
            list_profiles: mock.MagicMock,
            get_config: mock.MagicMock,
            create_keypair: mock.MagicMock,
    ):
        create_keypair.return_value = ["cert", "key"]
        get_info.return_value = {"api_base_uri", "token_endpoint", "auth_endpoint"}
        list_profiles.return_value = [{'profile_id': 'internet'}]
        get_config.return_value = "a config file"

        main(["https://test"])
