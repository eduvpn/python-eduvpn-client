# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import unittest
from eduvpn.openvpn import format_like_ovpn, parse_ovpn, ovpn_to_nm

from tests.mock_config import mock_config


class TestOpenvpn(unittest.TestCase):
    def test_format_like_ovpn(self):
        format_like_ovpn('test', 'test', 'test')

    def test_parse_ovpn(self):
        _ = parse_ovpn(mock_config)

    def test_ovpn_to_nm(self):
        config = parse_ovpn(mock_config)
        _ = ovpn_to_nm(config=config, uuid='test_uuid', display_name='test name')

    def test_ovpn_to_nm_2fa(self):
        config = parse_ovpn(mock_config)
        config['auth-user-pass'] = True
        username = 'test_user'
        nm_dict = ovpn_to_nm(config=config, uuid='test_uuid', display_name='test name', username=username)
        self.assertEqual(username, nm_dict['vpn']['data']['username'], username)