from unittest import TestCase
from mock import MagicMock
from eduvpn.test_util import MockBuilder
from eduvpn.metadata import Metadata
from eduvpn.steps.messages import fetch_messages


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

    def test_fetch_messages(self):
        fetch_messages(builder=self.builder, meta=self.meta, verifier=self.verifier)



