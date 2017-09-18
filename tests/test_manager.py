# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from os import path
import unittest
from dbus.exceptions import DBusException

from eduvpn.util import have_dbus
from eduvpn.manager import update_token, list_providers, list_active, connect_provider, delete_provider,\
    disconnect_provider, insert_config, is_provider_connected, update_config_provider, store_provider,\
    update_keys_provider
from eduvpn.exceptions import EduvpnException


here = path.dirname(__file__)


@unittest.skipUnless(have_dbus(), "DBus daemon not running")
class TestNm(unittest.TestCase):
    def setUp(self):
        self.name = 'test'
        self.config = 'test'
        self.cert = 'test'
        self.key = 'test'

    def test_list_providers(self):
        list_providers()

    def test_store_provider(self):
        with open(path.join(here, 'example.ovpn'), 'r') as f:
            config = f.read()
            uuid = store_provider(api_base_uri="test", profile_id="test", display_name="test", token="test",
                                  connection_type="test", authorization_type="test", profile_display_name="test",
                                  two_factor="test", cert="test", key="test", config=config, icon_data=None,
                                  instance_base_uri="test")
            update_config_provider(uuid=uuid, display_name='test', config=config)
            delete_provider(uuid)

    def test_connect_provider(self):
        with self.assertRaises(DBusException):
            connect_provider(self.name)

    def test_update_token(self):
        update_token(uuid='test', token={})

    def test_list_active(self):
        list_active()

    def test_disconnect_provider(self):
        with self.assertRaises(EduvpnException):
            disconnect_provider(uuid='test')

    def test_insert_config(self):
        settings = {'connection': {'id': 'insert_test', 'type': 'vpn'},
                    'vpn': {
                        'data': {},
                        'service-type': 'org.freedesktop.NetworkManager.openvpn'}
                    }
        insert_config(settings=settings)

    def test_is_provider_connected(self):
        is_provider_connected(uuid='test')

    def test_update_keys_provider(self):
        update_keys_provider(uuid="test", cert="cert", key="key")