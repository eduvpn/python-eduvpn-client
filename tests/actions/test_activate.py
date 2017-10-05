import unittest
from mock import MagicMock, patch
from eduvpn.test_util import MockBuilder
from eduvpn.util import have_dbus
from eduvpn.actions.activate import activate_connection
from eduvpn.metadata import Metadata


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