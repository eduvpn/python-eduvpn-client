from shutil import rmtree
import unittest
from eduvpn import settings
import eduvpn.nm
from eduvpn.app import Application


def remove_existing_config():
    rmtree(settings.CONFIG_PREFIX, ignore_errors=True)


def create_test_app() -> Application:
    app = Application(make_func_threadsafe=lambda x: x)
    app.initialize()
    return app


platform_supports_network_manager = eduvpn.nm.NM is not None

skip_if_network_manager_not_supported = unittest.skipUnless(
    platform_supports_network_manager,
    "Network Manager not supported",
)
