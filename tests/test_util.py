import unittest
from eduvpn.util import get_prefix, _have_dbus


class TestUtil(unittest.TestCase):
    def test_get_prefix(self):
        get_prefix()

    def test_have_dbus(self):
        _have_dbus()