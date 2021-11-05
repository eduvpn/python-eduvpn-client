from unittest import TestCase
from eduvpn.ovpn import Ovpn


class OVPNTests(TestCase):
    def test_force_tcp(self):
        ovpn = Ovpn(
            'a\n'
            'remote vpn.example.com 1234 udp\n'
            'remote vpn.example.com 5678 udp\r\n'
            'remote vpn.example.com 1234 tcp\r'
            'remote vpn.example.com 5678 tcp\rn'
            'b\r\n'
            'c\n'
        )
        expected_content = (
            'a\n'
            '# omitted to force tcp: remote vpn.example.com 1234 udp\n'
            '# omitted to force tcp: remote vpn.example.com 5678 udp\r\n'
            'remote vpn.example.com 1234 tcp\r'
            'remote vpn.example.com 5678 tcp\rn'
            'b\r\n'
            'c\n'
        )
        ovpn.force_tcp()
        self.assertEqual(ovpn.content, expected_content)
