from unittest import TestCase

from mock import patch

from eduvpn.metadata import Metadata
from eduvpn.steps.profile import fetch_profile_step, select_profile_step, _background
from eduvpn.test_util import MockBuilder, MockOAuth, MochResponse
from eduvpn.exceptions import EduvpnException


class TestProfile(TestCase):
    uuid = 'test'

    @classmethod
    def setUpClass(cls):
        cls.meta = Metadata()
        cls.meta.uuid = cls.uuid
        cls.meta.api_base_uri = "test_url"
        cls.meta.token = {'token_endpoint': 'https://test'}
        cls.meta.api_base_uri = 'https://test'
        cls.builder = MockBuilder()
        cls.oauth = MockOAuth()

    @patch('eduvpn.steps.profile._background')
    def test_fetch_profile_step(self, _):
        fetch_profile_step(builder=self.builder, meta=self.meta, oauth=self.oauth)

    @patch('eduvpn.steps.profile._background')
    def test_select_profile_step(self, _):
        select_profile_step(builder=self.builder, meta=self.meta, oauth=self.oauth, profiles=[])

    def test_background_no_profile(self):
        response = MochResponse(content_json={"profile_list": {"data": []}})
        oauth = MockOAuth(response=response)
        with self.assertRaises(EduvpnException):
            _background(meta=self.meta, builder=self.builder, dialog=None, oauth=oauth)

    def test_background_one_profile(self):
        response = MochResponse(content_json={"profile_list": {"data": [
            {
                "display_name": "test 1",
                "profile_id": "internet",
                "two_factor": False
            },
        ]}})
        oauth = MockOAuth(response=response)
        _background(meta=self.meta, builder=self.builder, dialog=None, oauth=oauth)

    def test_background_two_profile(self):
        response = MochResponse(content_json={"profile_list": {"data": [
            {
                "display_name": "test 1",
                "profile_id": "internet",
                "two_factor": False
            },
            {
                "display_name": "test 2",
                "profile_id": "extranet",
                "two_factor": True
            },
        ]}})
        oauth = MockOAuth(response=response)
        _background(meta=self.meta, builder=self.builder, dialog=None, oauth=oauth)
