from unittest import TestCase
from unittest.mock import patch
from tests.util import MockBuilder, MockResponse
from eduvpn.steps.start import refresh_start


class TestProvider(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = MockBuilder()

    @patch('requests.get', side_effect=lambda x: MockResponse())
    def test_update_providers(self, _):
        refresh_start(builder=self.builder, lets_connect=False)
