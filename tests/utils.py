from shutil import rmtree
from eduvpn import settings
from eduvpn.app import Application


def remove_existing_config():
    rmtree(settings.CONFIG_PREFIX, ignore_errors=True)


def create_test_app() -> Application:
    app = Application(make_func_threadsafe=lambda x: x)
    app.initialize()
    return app
