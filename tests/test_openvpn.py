# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from os import path
import unittest
from eduvpn.openvpn import format_like_ovpn, parse_ovpn

from tests.mock_config import mock_config


class TestOpenvpn(unittest.TestCase):
    def test_format_like_ovpn(self):
        format_like_ovpn('test', 'test', 'test')

    def test_parse_ovpn(self):
        parse_ovpn(mock_config)
