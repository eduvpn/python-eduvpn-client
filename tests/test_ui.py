import unittest
from eduvpn.ui import EduVpnApp
from eduvpn.util import have_dbus


class TestEduVpnApp(unittest.TestCase):
    def test_eduvpnapp(self):
        EduVpnApp()
