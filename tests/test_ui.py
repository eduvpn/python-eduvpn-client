import unittest
from eduvpn.ui import EduVpnApp
from eduvpn.util import have_dbus


@unittest.skipUnless(have_dbus(), "DBus daemon not running")
class TestEduVpnApp(unittest.TestCase):
    def test_eduvpnapp(self):
        EduVpnApp()
