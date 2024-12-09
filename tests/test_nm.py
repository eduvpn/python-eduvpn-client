from unittest import TestCase, skipIf

from eduvpn.nm import NMManager
from eduvpn.variants import EDUVPN
from tests.mock_config import mock_config


@skipIf(not NMManager(EDUVPN).available, "Network manager not available")
class TestNm(TestCase):
    def test_nm_available(self):
        nm_manager = NMManager(EDUVPN, None)
        nm_manager.available

    def test_import_ovpn(self):
        nm_manager = NMManager(EDUVPN, None)
        nm_manager.import_ovpn(mock_config)

    def test_get_add_connection(self):
        nm_manager = NMManager(EDUVPN, None)
        simple_connection = nm_manager.import_ovpn(mock_config)
        nm_manager.add_connection(simple_connection)

    def test_get_uuid(self):
        nm_manager = NMManager(EDUVPN, None)
        nm_manager.uuid
