from unittest import TestCase
from mock import MagicMock
from eduvpn.test_util import MockBuilder
from eduvpn.metadata import Metadata
from eduvpn.steps.instance import fetch_instance_step


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

    def test_fetch_instance_step(self):
        fetch_instance_step(builder=self.builder, meta=self.meta, verifier=self.verifier)




