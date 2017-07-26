import unittest
from eduvpn.nm import add_nm_config, gen_nm_settings


class TestNm(unittest.TestCase):
    def test_add_nm_config(self):
        add_nm_config({})

    def test_gen_nm_settings(self):
        gen_nm_settings('test', 'test')