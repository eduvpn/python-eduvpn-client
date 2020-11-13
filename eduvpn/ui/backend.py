from logging import getLogger
from requests_oauthlib import OAuth2Session
from typing import List, Optional

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('NM', '1.0')
from gi.repository import NM  # type: ignore

from eduvpn.remote import list_organisations, list_servers
from eduvpn.settings import SERVER_URI, ORGANISATION_URI
from eduvpn.ui.vpn_connection import VpnConnection

logger = getLogger(__name__)


class BackendData:
    def __init__(self, lets_connect: bool = False):
        self.uuid: Optional[str] = ""
        if lets_connect:
            self.servers = []
        else:
            self.servers = list_servers(SERVER_URI)
        self.secure_internet = [s for s in self.servers if s['server_type'] == 'secure_internet']
        self.institute_access = [s for s in self.servers if s['server_type'] == 'institute_access']

        if lets_connect:
            self.organisations = []
        else:
            self.organisations = list_organisations(ORGANISATION_URI)

        self.profiles: dict = {}
        self.locations: list = []
        self.secure_internet_home: str = ""
        self.oauth: OAuth2Session
        self.new_server_name: str = ""
        self.new_server_image = None
        self.new_support_contact: List[str] = []
        self.connection_state = NM.VpnConnectionState.UNKNOWN
        self.vpn_connection: VpnConnection = VpnConnection()
