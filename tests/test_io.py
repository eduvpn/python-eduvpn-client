# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import unittest

from eduvpn.io import open_file, write_and_open_ovpn, write_cert


class TestIo(unittest.TestCase):
    def test_write_and_open_ovpn(self):
        write_and_open_ovpn('/tmp/test')

    def test_open_file(self):
        open_file('/tmp/test')

    def test_write_cert(self):
        write_cert(content='test', type_='test', unique_name='test')
