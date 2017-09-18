# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import unittest

from eduvpn.io import write_cert, mkdir_p


class TestIo(unittest.TestCase):
    def test_write_cert(self):
        write_cert(content='test', type_='test', unique_name='test')

    def test_mkdir_p(self):
        mkdir_p('/tmp/test/test/test')
