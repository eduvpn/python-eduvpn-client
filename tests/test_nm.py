from unittest import TestCase, skipIf

from eduvpn_base.nm import NMManager
from eduvpn_base.ovpn import Ovpn
from tests.mock_config import mock_config
from tests.variant import VARIANT


@skipIf(not NMManager(VARIANT).available, "Network manager not available")
class TestNm(TestCase):
    def test_nm_available(self):
        nm_manager = NMManager(VARIANT)
        nm_manager.available

    def test_import_ovpn(self):
        nm_manager = NMManager(VARIANT)
        ovpn = Ovpn.parse(mock_config)
        nm_manager.import_ovpn(ovpn)

    def test_get_add_connection(self):
        nm_manager = NMManager(VARIANT)
        ovpn = Ovpn.parse(mock_config)
        simple_connection = nm_manager.import_ovpn(ovpn)
        nm_manager.add_connection(simple_connection)

    def test_get_uuid(self):
        nm_manager = NMManager(VARIANT)
        nm_manager.uuid
