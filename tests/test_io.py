import unittest

from eduvpn.io import open_file, write_and_open_ovpn, write_cert


class TestIo(unittest.TestCase):
    def test_write_and_open_ovpn(self):
        write_and_open_ovpn('/tmp/test')

    def test_open_file(self):
        open_file('/tmp/test')

    def test_write_cert(self):
        write_cert(content='test', type_='test', short_instance_name='test')
