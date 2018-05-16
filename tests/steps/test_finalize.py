from unittest import TestCase
from mock import patch
from tests.util import MockBuilder, MockOAuth, MockDialog
from eduvpn.metadata import Metadata
from eduvpn.steps.finalize import finalizing_step, _background
from eduvpn.util import have_dbus

if have_dbus():
    from dbus.exceptions import DBusException


class TestFinalize(TestCase):
    uuid = 'test'

    @classmethod
    def setUpClass(cls):
        cls.meta = Metadata()
        cls.meta.uuid = cls.uuid
        cls.meta.api_base_uri = "test_url"
        cls.meta.token = {'token_endpoint': 'https://test'}
        cls.meta.api_base_uri = 'https://test'
        cls.builder = MockBuilder()
        cls.oauth = MockOAuth()
        cls.dialog = MockDialog()

    @patch('eduvpn.steps.finalize.thread_helper')
    def test_finalizing_step(self, *_):
        finalizing_step(builder=self.builder, meta=self.meta, oauth=self.oauth)

    @patch('eduvpn.manager.monitor_vpn')
    @patch('eduvpn.steps.finalize.store_provider')
    def test_background(self, store_provider, y):
        store_provider.method.return_value = "blabla"
        store_provider.return_value = "blabla"
        try:
            _background(builder=self.builder, dialog=self.dialog, meta=self.meta, oauth=self.oauth)
        except DBusException as e:
            pass


