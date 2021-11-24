from unittest import TestCase
from eduvpn.ovpn import InvalidOVPN, Ovpn, Field, Section, Comment, Empty


class OVPNTests(TestCase):
    def test_parse_and_write(self):
        ovpn_file = (
            '# hello world\n'
            'set a 1\n'
            '\n'
            '<ca>\n'
            'the\n'
            'certificate\n'
            'content\n'
            '</ca>\n'
        )
        ovpn = Ovpn.parse(ovpn_file)
        self.assertEqual(ovpn.content, [
            Comment(' hello world'),
            Field('set', ['a', '1']),
            Empty(),
            Section('ca', ['the', 'certificate', 'content']),
        ])
        self.assertEqual(ovpn.to_string(), ovpn_file)

    def test_force_tcp(self):
        ovpn = Ovpn.parse(
            'a\n'
            'remote vpn.example.com 1234 udp\n'
            'remote vpn.example.com 5678 udp\r\n'
            'remote vpn.example.com 1234 tcp\r'
            'remote vpn.example.com 5678 tcp\r\n'
            'b\r\n'
            'c\n'
        )
        expected_content = (
            'a \n'
            '# omitted to force tcp: remote vpn.example.com 1234 udp\n'
            '# omitted to force tcp: remote vpn.example.com 5678 udp\n'
            'remote vpn.example.com 1234 tcp\n'
            'remote vpn.example.com 5678 tcp\n'
            'b \n'
            'c \n'
        )
        ovpn.force_tcp()
        self.assertEqual(ovpn.to_string(), expected_content)

    def test_force_tcp_fail(self):
        ovpn = Ovpn.parse(
            'remote vpn.example.com 1234 udp\n'
        )
        with self.assertRaises(InvalidOVPN):
            ovpn.force_tcp()
