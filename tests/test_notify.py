import unittest
from eduvpn.notify import notify


class TestNotify(unittest.TestCase):
    def test_notify(self):
        notify('test')