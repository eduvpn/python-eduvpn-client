import unittest
import mock

from eduvpn.local_io import open_file, write_and_open_ovpn, write_cert


class TestCrypto(unittest.TestCase):
    def test_write_and_open_ovpn(self):
        write_and_open_ovpn('test')

    def test_open_file(self):
        open_file('test')

    def test_write_cert(self):
        write_cert('test', 'test', 'test')