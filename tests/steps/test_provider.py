from unittest import TestCase
from mock import patch
from tests.util import MockBuilder, MockResponse
from eduvpn.steps.provider import update_providers


class TestProvider(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = MockBuilder()

    @patch('requests.get', side_effect=lambda x: MockResponse())
    def test_update_providers(self, _):
        update_providers(builder=self.builder)