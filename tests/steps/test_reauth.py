from unittest import TestCase
from mock import patch, MagicMock
from tests.util import MockBuilder, MockOAuth
from eduvpn.metadata import Metadata
from eduvpn.steps.reauth import reauth


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

    @patch('gi.repository.Gtk.MessageDialog')
    def test_reauth(self, _):
        reauth(builder=self.builder, meta=self.meta, verifier=self.verifier)


