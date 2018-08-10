import unittest
from eduvpn.notify import notify, init_notify
from eduvpn.util import have_dbus


@unittest.skipUnless(have_dbus, "DBus daemon not running")
class TestNotify(unittest.TestCase):
    def test_notify(self):
        notifier = init_notify(False)
        notify(notifier, 'test')
