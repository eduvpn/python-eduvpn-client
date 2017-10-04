from unittest import TestCase
from mock import patch, MagicMock
from eduvpn.test_util import MochResponse, MockOAuth, MockBuilder
from eduvpn.metadata import Metadata
from eduvpn.steps.two_way_auth import two_auth_step, background as two_auth_step_background


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

    def test_two_auth_step(self):
        two_auth_step(builder=self.builder, meta=self.meta, oauth=self.oauth)

    def test_two_auth_background_step_no_2fa(self):
        oauth_no_2fa = MockOAuth()
        two_auth_step_background(builder=self.builder, meta=self.meta, oauth=oauth_no_2fa)

    def test_two_auth_background_step_2fa(self):
        response_2fa = MochResponse()
        response_2fa.content_json['user_info']['data']['two_factor_enrolled'] = True
        oauth_2fa = MockOAuth(response_2fa)
        two_auth_step_background(builder=self.builder, meta=self.meta, oauth=oauth_2fa)

    def test_two_auth_background_step_2fa_multiple(self):
        # multiple 2fa metods available
        response_2fa = MochResponse()
        response_2fa.content_json['user_info']['data']['two_factor_enrolled'] = True
        response_2fa.content_json['user_info']['data']['two_factor_enrolled_with'] = ['yubikey', 'totp']
        oauth_2fa = MockOAuth(response_2fa)
        two_auth_step_background(builder=self.builder, meta=self.meta, oauth=oauth_2fa)



