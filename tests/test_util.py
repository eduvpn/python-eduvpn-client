import unittest
from mock import patch
from eduvpn.util import get_prefix, have_dbus, make_unique_id, thread_helper, error_helper, bytes2pixbuf, detect_distro


class TestUtil(unittest.TestCase):
    def test_get_prefix(self):
        get_prefix()

    def test_have_dbus(self):
        have_dbus()

    def test_make_unique_id(self):
        make_unique_id()

    def test_thread_helper(self):
        thread_helper(lambda: [])

    def test_bytes2pixbuf(self):
        bytes2pixbuf(bytes())

    def test_detect_distro(self):
        distro, version = detect_distro()

    @patch('eduvpn.util.Gtk.MessageDialog')
    def test_error_helper(self, *_):
        error_helper(None, None, None)
