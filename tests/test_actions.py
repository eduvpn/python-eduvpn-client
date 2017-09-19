import unittest
from mock import MagicMock, patch
from eduvpn.test_util import MockSelection
from eduvpn.util import have_dbus
from eduvpn.actions.activate import activate_connection
from eduvpn.actions.add import new_provider
from eduvpn.actions.delete import delete_profile
from eduvpn.actions.select import select_profile
from eduvpn.actions.switch import switched
from eduvpn.actions.vpn_status import vpn_change
from eduvpn.metadata import Metadata


class MockBuilder:
    def __init__(self):
        self.objects = {
            'provider-selection': MockSelection(4),
        }

    def get_object(self, o):
        return self.objects.get(o, MagicMock())


class TestActions(unittest.TestCase):
    uuid = 'test'

    @classmethod
    def setUpClass(cls):
        cls.meta = Metadata()
        cls.meta.uuid = cls.uuid

        cls.builder = MockBuilder()
        cls.verifier = MagicMock()

    @unittest.skipUnless(have_dbus(), "DBus daemon not running")
    @patch('gi.repository.Gtk.MessageDialog')
    @patch('eduvpn.other_nm.Settings.GetConnectionByUuid')
    @patch('eduvpn.other_nm.NetworkManager.ActivateConnection')
    def test_activate_connection(self, *args):
        activate_connection(builder=self.builder, meta=self.meta)

    @patch('gi.repository.Gtk.MessageDialog')
    def test_delete_profile(self, mock_dialog):
        delete_profile(builder=self.builder)

    def test_select_profile(self):
        select_profile(builder=self.builder, verifier=self.verifier)

    @unittest.skipUnless(have_dbus(), "DBus daemon not running")
    @patch('gi.repository.Gtk.MessageDialog')
    @patch('eduvpn.other_nm.NetworkManager', ActiveConnections=[MagicMock(Uuid=uuid)])
    def test_switched(self, mock_activecon, mock_dialog):
        switched(builder=self.builder, meta=self.meta)

    def test_new_provider(self):
        new_provider(builder=self.builder, verifier=self.verifier)

    def test_vpn_change(self):
        vpn_change(builder=self.builder)
