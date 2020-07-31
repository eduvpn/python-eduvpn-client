from logging import getLogger
from eduvpn.remote import list_orgs, list_servers
from eduvpn.settings import SERVER_URI, ORGANISATION_URI
from eduvpn.nm import ConnectionState
logger = getLogger(__name__)


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
        self.connection_state = ConnectionState.UNKNOWN
        self.server_name = ""
        self.new_server_name = ""
        self.server_image = None
        self.new_server_image = None
        self.support_contact = []
        self.new_support_contact = []
