# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from os import path
import unittest
from dbus.exceptions import DBusException

from eduvpn.util import have_dbus
from eduvpn.metadata import Metadata
from eduvpn.manager import update_token, list_providers, list_active, connect_provider, delete_provider,\
    disconnect_provider, insert_config, is_provider_connected, update_config_provider, store_provider,\
    update_keys_provider
from eduvpn.exceptions import EduvpnException
from eduvpn.util import make_unique_id


here = path.dirname(__file__)


#@unittest.skipUnless(have_dbus, "DBus daemon not running")
class TestNm(unittest.TestCase):
    def setUp(self):
        self.meta = Metadata()
        self.meta.uuid = make_unique_id()
        self.meta.cert = "testcert"
        self.meta.key = "testkey"
        with open(path.join(here, 'example.ovpn'), 'r') as f:
            self.meta.config = f.read()

    def test_list_providers(self):
        list_providers()

    def test_store_provider(self):
        uuid = store_provider(meta=self.meta)
        update_token(uuid=self.meta.uuid, token={})
        update_config_provider(self.meta)
        delete_provider(uuid)

    def test_connect_provider(self):
        with self.assertRaises(EduvpnException):
            connect_provider(self.meta.uuid)

    def test_list_active(self):
        list_active()

    def test_disconnect_provider(self):
        with self.assertRaises(EduvpnException):
            disconnect_provider(uuid=self.meta.uuid)

    def test_insert_config(self):
        settings = {'connection': {'id': 'insert_test', 'type': 'vpn'},
                    'vpn': {
                        'data': {},
                        'service-type': 'org.freedesktop.NetworkManager.openvpn'}
                    }
        insert_config(settings=settings)

    def test_is_provider_connected(self):
        is_provider_connected(uuid=self.meta.uuid)

    def test_update_keys_provider(self):
        update_keys_provider(uuid=self.meta.uuid, cert=self.meta.cert, key=self.meta.key)
