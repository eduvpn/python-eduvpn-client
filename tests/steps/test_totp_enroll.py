from unittest import TestCase
from eduvpn.steps.totp_enroll import totp_enroll_window, _make_qr, _parse_user_input
from eduvpn.metadata import Metadata
from tests.util import MockBuilder, MockOAuth
from tests.mock_config import mock_config_dict


class TestTotpEnroll(TestCase):
    @classmethod
    def setUp(cls):
        cls.builder = MockBuilder()
        cls.meta = Metadata()
        cls.meta.api_base_uri = "https://bla.bla/bla"
        cls.oauth = MockOAuth()

    def test_totp_enroll_window(self):
        totp_enroll_window(builder=self.builder, config_dict=mock_config_dict,
                           meta=self.meta, oauth=self.oauth, lets_connect=False)

    def test_make(self):
        _make_qr(builder=self.builder, config_dict=mock_config_dict,
                 meta=self.meta, oauth=self.oauth, lets_connect=False)

    def test_parse_user_input(self):
        _parse_user_input(builder=self.builder, config_dict=mock_config_dict,
                          meta=self.meta, oauth=self.oauth, secret='bla', lets_connect=False)

