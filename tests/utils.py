from contextlib import contextmanager
import threading
from shutil import rmtree
import unittest
from eduvpn import settings
import eduvpn.nm
from eduvpn.variants import EDUVPN
from eduvpn.utils import run_in_main_gtk_thread
from eduvpn.app import Application


def remove_existing_config():
    rmtree(settings.CONFIG_PREFIX, ignore_errors=True)


@contextmanager
def create_test_app():
    from gi.repository import GLib
    event_loop = GLib.MainLoop()
    thread = threading.Thread(target=event_loop.run)
    thread.start()
    variant = EDUVPN
    app = Application(variant, make_func_threadsafe=run_in_main_gtk_thread)
    app.initialize()
    try:
        yield app
    finally:
        event_loop.quit()


platform_supports_network_manager = eduvpn.nm.NM is not None

skip_if_network_manager_not_supported = unittest.skipUnless(
    platform_supports_network_manager,
    "Network Manager not supported",
)
