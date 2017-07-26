import unittest

from eduvpn.crypto import gen_code_challenge, gen_code_verifier


class TestCrypto(unittest.TestCase):
    def test_gen_code_challenge(self):
        gen_code_challenge('bla')

    def test_gen_code_verifier(self):
        gen_code_verifier()