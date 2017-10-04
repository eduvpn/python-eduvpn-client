from unittest import TestCase
from eduvpn.test_util import MockBuilder, MockOAuth
from eduvpn.metadata import Metadata
from eduvpn.steps.finalize import finalizing_step


class TestFinalize(TestCase):
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

    def test_finalizing_step(self):
        finalizing_step(builder=self.builder, meta=self.meta, oauth=self.oauth)


