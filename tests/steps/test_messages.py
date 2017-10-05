from unittest import TestCase
from mock import MagicMock, patch
from tests.util import MockBuilder
from eduvpn.metadata import Metadata
from eduvpn.steps.messages import fetch_messages, _background


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

    @patch('eduvpn.steps.messages.thread_helper')
    def test_fetch_messages(self, *_):
        fetch_messages(builder=self.builder, meta=self.meta, verifier=self.verifier)

    @patch('eduvpn.steps.messages.user_messages')
    @patch('eduvpn.steps.messages.system_messages')
    @patch('eduvpn.steps.messages.user_info')
    def test_background(self, *_):
        _background(builder=self.builder, meta=self.meta, verifier=self.verifier)



