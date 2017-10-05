import unittest
from mock import MagicMock, patch
from tests.util import MockSelection
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


class MockSwitch:
    def __init__(self, state=False):
        self.state = state

    def get_active(self):
        return self.state


class TestActions(unittest.TestCase):
    uuid = 'test'

    @classmethod
    def setUpClass(cls):
        cls.meta = Metadata()
        cls.meta.uuid = cls.uuid

        cls.builder = MockBuilder()
        cls.verifier = MagicMock()

    @patch('gi.repository.Gtk.MessageDialog')
    @patch('eduvpn.actions.switch.activate_connection')
    @patch('eduvpn.actions.switch.disconnect_provider')
    def test_switched_on(self, *args):
        builder = MockBuilder()
        builder.objects['connect-switch'] = MockSwitch(state=True)
        switched(builder=self.builder, meta=self.meta)

    @patch('gi.repository.Gtk.MessageDialog')
    @patch('eduvpn.actions.switch.activate_connection')
    @patch('eduvpn.actions.switch.disconnect_provider')
    def test_switched_off(self, *args):
        builder = MockBuilder()
        builder.objects['connect-switch'] = MockSwitch(state=False)
        switched(builder=self.builder, meta=self.meta)
