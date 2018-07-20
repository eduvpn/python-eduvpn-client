from unittest import TestCase
from mock import patch, MagicMock
from tests.util import MockResponse, MockOAuth, MockBuilder
from tests.mock_config import mock_config_dict
from eduvpn.metadata import Metadata
from eduvpn.steps.two_way_auth import two_auth_step, _background, _choice_window


class TestTwoWayAuth(TestCase):
    uuid = 'test'

    @classmethod
    def setUpClass(cls):
        cls.meta = Metadata()
        cls.meta.uuid = cls.uuid
        cls.meta.api_base_uri = "test_url"
        cls.meta.token = {'token_endpoint': 'https://test'}
        cls.meta.api_base_uri = 'https://test'

        cls.builder = MockBuilder()
        cls.verifier = MagicMock()
        cls.oauth = MockOAuth()

    @patch('eduvpn.steps.two_way_auth.thread_helper')
    def test_two_auth_step(self, *_):
        response_2fa = MockResponse()
        response_2fa.content_json['user_info']['data']['two_factor_enrolled'] = True
        oauth_2fa = MockOAuth(response_2fa)
        two_auth_step(builder=self.builder, meta=self.meta, oauth=oauth_2fa, config_dict=mock_config_dict)

    def test_two_auth_background_step_no_2fa(self):
        oauth_no_2fa = MockOAuth()
        _background(builder=self.builder, meta=self.meta, oauth=oauth_no_2fa, config_dict=mock_config_dict)

    def test_two_auth_background_step_2fa(self):
        response_2fa = MockResponse()
        response_2fa.content_json['user_info']['data']['two_factor_enrolled'] = True
        oauth_2fa = MockOAuth(response_2fa)
        _background(builder=self.builder, meta=self.meta, oauth=oauth_2fa, config_dict=mock_config_dict)

    def test_two_auth_background_step_2fa_multiple(self):
        # multiple 2fa metods available
        response_2fa = MockResponse()
        response_2fa.content_json['user_info']['data']['two_factor_enrolled'] = True
        response_2fa.content_json['user_info']['data']['two_factor_enrolled_with'] = ['yubikey', 'totp']
        oauth_2fa = MockOAuth(response_2fa)
        _background(builder=self.builder, meta=self.meta, oauth=oauth_2fa, config_dict=mock_config_dict)

    @patch('eduvpn.steps.two_way_auth.finalizing_step')
    @patch('eduvpn.steps.two_way_auth.Gtk.Dialog')
    @patch('eduvpn.steps.two_way_auth.Gtk.Label')
    def test_choice_window(self, *_):
        _choice_window(builder=self.builder, meta=self.meta, oauth=self.oauth, options=['bla1', 'bla2'],
                       config_dict=mock_config_dict)



