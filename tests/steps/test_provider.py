from unittest import TestCase
from mock import patch
from eduvpn.test_util import MockBuilder, MochResponse
from eduvpn.steps.provider import update_providers


class TestProvider(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = MockBuilder()

    @patch('requests.get', side_effect=lambda x: MochResponse())
    def test_update_providers(self, _):
        update_providers(builder=self.builder)