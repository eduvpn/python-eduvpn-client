# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import os
import sys
import unittest
from dbus.exceptions import DBusException


run = os.name == 'posix' and not sys.platform.startswith('darwin')

if run:
    from eduvpn.managers.nm import list_providers, store_provider, delete_provider, connect_provider, status_provider


@unittest.skipUnless(run, "requires NetworkManager (Linux)")
class TestNm(unittest.TestCase):
    def setUp(self):
        self.name = 'test'
        self.config = 'test'
        self.cert = 'test'
        self.key = 'test'

    def test_list_providers(self):
        list_providers()

    @unittest.skip("todo")
    def test_store_provider(self):
        store_provider(api_base_uri="test", profile_id="test", display_name="test", token="test",
                       connection_type="test", authorization_type="test", profile_display_name="test",
                       two_factor="test", cert="test", key="test", config="test", icon_data="test")

    def test_delete_provider(self):
        with self.assertRaises(Exception):
            delete_provider(self.name)

    def test_connect_provider(self):
        with self.assertRaises(DBusException):
            connect_provider(self.name)

    def test_status_provider(self):
        with self.assertRaises(DBusException):
            status_provider(self.name)
