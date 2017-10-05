import unittest
from eduvpn.ui import EduVpnApp
from eduvpn.util import have_dbus


@unittest.skip("gives a segfault on travis")
class TestEduVpnApp(unittest.TestCase):
    def test_eduvpnapp(self):
        EduVpnApp()
