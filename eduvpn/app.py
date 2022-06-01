from typing import Optional
import logging
from gettext import gettext as _
from .server import ServerDatabase
from . import nm
from .variants import ApplicationVariant
from .config import Configuration
from .utils import run_periodically


logger = logging.getLogger(__name__)

CHECK_NETWORK_INTERVAL = 1  # seconds


class Application:
    def __init__(self, variant: ApplicationVariant, make_func_threadsafe):
        self.variant = variant
        self.make_func_threadsafe = make_func_threadsafe
        self.server_db = ServerDatabase()
        self.current_network_uuid: Optional[str] = None

    def initialize(self):
        self.initialize_network()
        if self.variant.use_predefined_servers:
            # TODO: Go initialize server db?
            pass
        self.config = Configuration.load()

    def initialize_network(self):
        """
        Determine the current network state.
        """
        # Check if a previous network configuration exists.
        uuid = nm.get_existing_configuration_uuid()
        if uuid:
            self.current_network_uuid = uuid
            # Check what server corresponds to the configuration.
            server = self.server_db.get_single_configured()
            if server is None:
                # There is a network configuration,
                # but no record of what server corresponds to it.
                # TODO: Implement with Go
                pass
            else:
                # TODO: Implement with Go
                pass
        else:
            # TODO: Implement with Go
            pass

        def on_network_update_callback(state):
            network.on_state_update_callback(self, state)

        from . import network
        nm.subscribe_to_status_changes(on_network_update_callback)
