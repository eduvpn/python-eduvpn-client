from unittest import TestCase
from mock import MagicMock, patch
from tests.util import MockBuilder, MockDialog
from eduvpn.metadata import Metadata
from eduvpn.steps.instance import fetch_instance_step, _fetch_background, select_instance_step


class TestSteps(TestCase):
    uuid = 'test'

    @classmethod
    def setUpClass(cls):
        cls.meta = Metadata()
        cls.meta.uuid = cls.uuid
        cls.meta.api_base_uri = "test_url"
        cls.meta.token = {'token_endpoint': 'https://test'}
        cls.meta.api_base_uri = 'https://test'
        cls.meta.discovery_uri = 'https://test'
        cls.builder = MockBuilder()
        cls.verifier = MagicMock()
        cls.dialog = MockDialog()

    @patch('eduvpn.steps.instance.thread_helper')
    def test_fetch_instance_step(self, *_):
        fetch_instance_step(builder=self.builder, meta=self.meta, verifier=self.verifier)

    @patch('eduvpn.steps.instance.get_instances', side_effect=lambda *_, **__: ('bla', 'bla'))
    def test_fetch_background(self, *_):
        _fetch_background(dialog=self.dialog, meta=self.meta, verifier=self.verifier, builder=self.builder)

    def test_select_instance_step(self):
        select_instance_step(meta=self.meta, instances=[], builder=self.builder, verifier=self.verifier)
