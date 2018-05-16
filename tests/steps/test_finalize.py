from unittest import TestCase
from mock import patch
from tests.util import MockBuilder, MockOAuth, MockDialog
from eduvpn.metadata import Metadata
from eduvpn.steps.finalize import finalizing_step, _background


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
        cls.dialog = MockDialog()

    @patch('eduvpn.steps.finalize.thread_helper')
    def test_finalizing_step(self, *_):
        finalizing_step(builder=self.builder, meta=self.meta, oauth=self.oauth)

    @patch('eduvpn.steps.finalize.store_provider')
    def test_background(self, *_):
        _background(builder=self.builder, dialog=self.dialog, meta=self.meta, oauth=self.oauth)

