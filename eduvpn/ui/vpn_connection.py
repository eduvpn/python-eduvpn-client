from logging import getLogger
from typing import List
from enum import Enum
from oauthlib.oauth2.rfc6749.tokens import OAuth2Token

logger = getLogger(__name__)


class VpnConnection:
    class ConnectionType(str, Enum):
        INSTITUTE = "INSTITUTE",
        SECURE = "SECURE",
        OTHER = "OTHER"

    def __init__(self):
        self.type: str = VpnConnection.ConnectionType.OTHER
        self.api_url: str = ""
        self.auth_url: str = ""
        self.token_endpoint: str = ""
        self.authorization_endpoint: str = ""
        self.server_name: str = ""
        self.server_image = None
        self.profile_id: str = ""
        self.support_contact: List[str] = []
        self.token: OAuth2Token

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)
