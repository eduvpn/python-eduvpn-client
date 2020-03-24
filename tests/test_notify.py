import unittest
from eduvpn.notify import notify, init_notify
from eduvpn.util import have_dbus_notification_service


@unittest.skipUnless(have_dbus_notification_service(), "DBus notification service not available")
class TestNotify(unittest.TestCase):
    def test_notify(self):
        notifier = init_notify(False)
        notify(notifier, 'test')
