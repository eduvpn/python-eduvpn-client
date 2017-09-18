# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import unittest

from eduvpn.io import write_cert, store_metadata, get_metadata, mkdir_p


class TestIo(unittest.TestCase):
    def test_write_cert(self):
        write_cert(content='test', type_='test', unique_name='test')

    def test_metadata(self):
        metadata = {'test': 'test'}
        uuid = 'test'
        store_metadata(uuid, metadata)
        metadata2 = get_metadata(uuid)
        self.assertEqual(metadata, metadata2)

    def test_mkdir_p(self):
        mkdir_p('/tmp/test/test/test')
