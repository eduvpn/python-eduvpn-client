# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import unittest

from eduvpn.managers.other import list_providers, store_provider, delete_provider, connect_provider, status_provider


class TestProviderOther(unittest.TestCase):
    def setUp(self):
        self.name = 'test'
        self.config = 'test'
        self.cert = 'test'
        self.key = 'test'

    def test_list_providers(self):
        list_providers()

    def test_store_provider(self):
        store_provider(api_base_uri='test', profile_id='test', display_name='test', token='test', connection_type='test',
                       authorization_type='test', profile_display_name='test',
                       two_factor='test', cert='test', key='test', config='test', icon_data=None)

    @unittest.skip("todo")
    def test_delete_provider(self):
        delete_provider(self.name)

    def test_connect_provider(self):
        connect_provider(self.name)

    @unittest.skip("todo not implemented yet")
    def test_status_provider(self):
        status_provider(self.name)