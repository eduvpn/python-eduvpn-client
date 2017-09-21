from unittest import TestCase
from mock import patch, MagicMock
from eduvpn.test_util import MockSelection, MochResponse, MockOAuth
from eduvpn.metadata import Metadata
from eduvpn.steps.browser import browser_step
from eduvpn.steps.custom_url import custom_url
from eduvpn.steps.finalize import finalizing_step
from eduvpn.steps.instance import fetch_instance_step
from eduvpn.steps.messages import fetch_messages
from eduvpn.steps.profile import fetch_profile_step, select_profile_step
from eduvpn.steps.provider import update_providers
from eduvpn.steps.reauth import reauth
from eduvpn.steps.two_way_auth import two_auth_step, background as two_auth_step_background


class MockBuilder:
    def __init__(self):
        self.objects = {
            'profiles-selection': MockSelection(3),
        }

    def get_object(self, o):
        return self.objects.get(o, MagicMock())


class TestSteps(TestCase):
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

    def test_browser_step(self):
        browser_step(builder=self.builder, meta=self.meta, verifier=self.verifier)

    def test_custom_url(self):
        custom_url(builder=self.builder, meta=self.meta, verifier=self.verifier)

    def test_finalizing_step(self):
        finalizing_step(builder=self.builder, meta=self.meta, oauth=self.oauth)

    def test_fetch_instance_step(self):
        fetch_instance_step(builder=self.builder, meta=self.meta, verifier=self.verifier, discovery_uri='test')

    def test_fetch_messages(self):
        fetch_messages(builder=self.builder, meta=self.meta, verifier=self.verifier)

    def test_fetch_profile_step(self):
        fetch_profile_step(builder=self.builder, meta=self.meta, oauth=self.oauth)

    def test_select_profile_step(self):
        select_profile_step(builder=self.builder, meta=self.meta, oauth=self.oauth, profiles=[])

    @patch('requests.get', side_effect=lambda x: MochResponse())
    def test_update_providers(self, _):
        update_providers(builder=self.builder)

    @patch('gi.repository.Gtk.MessageDialog')
    def test_reauth(self, mock_dialog):
        reauth(builder=self.builder, meta=self.meta, verifier=self.verifier)

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




