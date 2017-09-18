# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from os import path
import unittest
from eduvpn.openvpn import format_like_ovpn, parse_ovpn

here = path.dirname(__file__)
example = open(path.join(here, 'example.ovpn'), 'r').read()


class TestOpenvpn(unittest.TestCase):
    def test_format_like_ovpn(self):
        format_like_ovpn('test', 'test', 'test')

    def parse_ovpn(self):
        config = parse_ovpn(example)
