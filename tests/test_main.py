from unittest import TestCase
from eduvpn.__main__ import parse_eduvpn


class TestMain(TestCase):
    def test_parse_args(self):
        with self.assertRaises(SystemExit):
            parse_eduvpn(["test"])
