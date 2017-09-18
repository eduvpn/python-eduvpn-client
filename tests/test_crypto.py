# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import unittest

from eduvpn.crypto import gen_code_challenge, gen_code_verifier


class TestCrypto(unittest.TestCase):
    def test_gen_code_challenge(self):
        gen_code_challenge('bla')

    def test_gen_code_verifier(self):
        gen_code_verifier()
