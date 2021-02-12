# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import unittest

from eduvpn.crypto import gen_code_challenge, gen_code_verifier, common_name_from_cert, make_verifier
from tests.mock_config import mock_config_dict


class TestCrypto(unittest.TestCase):
    def test_gen_code_challenge(self):
        gen_code_challenge('bla')

    def test_gen_code_verifier(self):
        gen_code_verifier()

    def test_common_name_from_cert(self):
        result = common_name_from_cert(mock_config_dict['cert'].encode('ascii'))
        self.assertEqual(result, '9f43953f6371212130d2f8d65bad8694')

    def test_make_verifier(self):
        make_verifier("RWSC3Lwn4f9mhG3XIwRUTEIqf7Ucu9+7/Rq+scUMxrjg5/kjskXKOJY/")
