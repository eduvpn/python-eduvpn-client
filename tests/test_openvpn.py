import unittest
from eduvpn.openvpn import format_like_ovpn, parse_ovpn


class TestOpenvpn(unittest.TestCase):
    def test_format_like_ovpn(self):
        format_like_ovpn('test', 'test', 'test')

    def parse_ovpn(self):
        parse_ovpn('test')