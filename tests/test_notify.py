import unittest
from eduvpn.notify import notify
from eduvpn.util import have_dbus


@unittest.skipUnless(have_dbus, "DBus daemon not running")
class TestNotify(unittest.TestCase):
    def test_notify(self):
        notify('test')
