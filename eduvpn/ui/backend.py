from enum import Flag, auto

from logging import getLogger
from eduvpn.remote import list_orgs, list_servers
from eduvpn.settings import CLIENT_ID, SERVER_URI, ORGANISATION_URI

logger = getLogger(__name__)


class ConnectionStatus(Flag):
    INITIALIZING = auto()
    NOT_CONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    CONNECTION_ERROR = auto()


class BackendData:
    def __init__(self):
        self.servers = list_servers(SERVER_URI)
        self.secure_internet = [s for s in self.servers if s['server_type'] == 'secure_internet']
        self.institute_access = [s for s in self.servers if s['server_type'] == 'institute_access']
        self.orgs = list_orgs(ORGANISATION_URI)
        self.profiles = []
        self.locations = []
        self.secure_internet_home = None
        self.oauth = None
        self.api_url = None
        self.auth_url = None
        self.token_endpoint = None
        self.connection_status = ConnectionStatus.INITIALIZING
        self.server_name = None
        self.server_image = None
        self.support_contact = []


