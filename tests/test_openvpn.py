# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import unittest
from eduvpn.openvpn import format_like_ovpn, parse_ovpn, ovpn_to_nm
from eduvpn.metadata import Metadata

from tests.mock_config import mock_config


class TestOpenvpn(unittest.TestCase):
    @classmethod
    def setUp(cls):
        cls.meta = Metadata()
        cls.meta.uuid = 'test'

    def test_format_like_ovpn(self):
        format_like_ovpn('test', 'test', 'test')

    def test_parse_ovpn(self):
        _ = parse_ovpn(mock_config)

    def test_ovpn_to_nm(self):
        config = parse_ovpn(mock_config)
        _ = ovpn_to_nm(config=config, meta=self.meta, display_name='test name')

    def test_ovpn_to_nm_2fa(self):
        config = parse_ovpn(mock_config)
        config['auth-user-pass'] = True
        username = 'test_user'
        nm_dict = ovpn_to_nm(config=config, meta=self.meta, display_name='test name', username=username)
        self.assertEqual(username, nm_dict['vpn']['data']['username'], username)

    def test_ovpn_to_nm_tls_auth(self):
        config = parse_ovpn(mock_config)
        config['tls-auth'] = "bla"
        _ = ovpn_to_nm(config=config, meta=self.meta, display_name='test name')

    def test_ovpn_to_nm_tls_crypt(self):
        config = parse_ovpn(mock_config)
        config['tls-crypt'] = "bla"
        _ = ovpn_to_nm(config=config, meta=self.meta, display_name='test name')

    def test_multiple_remote(self):
        configtext = """
remote internet.demo.eduvpn.nl 1194 udp
remote internet.demo.eduvpn.nl 1194 tcp
"""
        config = parse_ovpn(configtext)
        settings = ovpn_to_nm(config, meta=self.meta, display_name='test name')
        self.assertEqual(settings['vpn']['data']['remote'],
                         'internet.demo.eduvpn.nl:1194:udp,internet.demo.eduvpn.nl:1194:tcp')

    def test_single_remote(self):
        configtext = """
remote internet.demo.eduvpn.nl 1194 udp
"""
        config = parse_ovpn(configtext)
        settings = ovpn_to_nm(config, meta=self.meta, display_name='test name')
        self.assertEqual(settings['vpn']['data']['remote'],
                         'internet.demo.eduvpn.nl:1194:udp')