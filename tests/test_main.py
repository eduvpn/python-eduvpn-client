from unittest import TestCase, mock
from eduvpn.__main__ import letsconnect, parse_args
from eduvpn.cli import interactive


class TestMain(TestCase):
    def test_letsconnect(self):
        with self.assertRaises(NotImplementedError):
            letsconnect()

    def test_parse_args(self):
        with self.assertRaises(SystemExit):
            parse_args(["test"])
