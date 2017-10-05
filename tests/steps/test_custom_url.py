from unittest import TestCase
from mock import MagicMock
from tests.util import MockBuilder
from eduvpn.metadata import Metadata
from eduvpn.steps.custom_url import custom_url


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

    def test_custom_url(self):
        custom_url(builder=self.builder, meta=self.meta, verifier=self.verifier)
