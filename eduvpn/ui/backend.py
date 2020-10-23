from logging import getLogger
from typing import List
from requests_oauthlib import OAuth2Session
import gi
gi.require_version('NM', '1.0')
from gi.repository import NM  # type: ignore

from eduvpn.remote import list_orgs, list_servers
from eduvpn.settings import SERVER_URI, ORGANISATION_URI
logger = getLogger(__name__)


class BackendData:
    def __init__(self, lets_connect: bool = False):
        if lets_connect:
            self.servers = []
        else:
            self.servers = list_servers(SERVER_URI)
        self.secure_internet = [s for s in self.servers if s['server_type'] == 'secure_internet']
        self.institute_access = [s for s in self.servers if s['server_type'] == 'institute_access']

        if lets_connect:
            self.orgs: dict = {}
        else:
            self.orgs = list_orgs(ORGANISATION_URI)

        self.profiles: dict = {}
        self.locations: list = []
        self.secure_internet_home: str = ""
        self.oauth: OAuth2Session
        self.api_url: str = ""
        self.auth_url: str = ""
        self.token_endpoint: str = ""
        self.authorization_endpoint: str = ""
        self.connection_state = NM.VpnConnectionState.UNKNOWN
        self.server_name: str = ""
        self.new_server_name: str = ""
        self.server_image = None
        self.new_server_image = None
        self.support_contact: List[str] = []
        self.new_support_contact: List[str] = []
