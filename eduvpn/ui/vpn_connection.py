import os
import json
import uuid

from logging import getLogger
from typing import Any, List
from eduvpn.settings import CONFIG_PREFIX, CONFIG_JSON_PREFIX
from enum import Enum

logger = getLogger(__name__)


class VpnConnection:
    class ConnectionType(str, Enum):
        INSTITUTE = "INSTITUTE",
        SECURE = "SECURE",
        OTHER = "OTHER"

    def __init__(self):
        self.uuid: str = str(uuid.uuid4())
        self.type: str = VpnConnection.ConnectionType.OTHER
        self.api_url: str = ""
        self.auth_url: str = ""
        self.token_endpoint: str = ""
        self.authorization_endpoint: str = ""
        self.server_name: str = ""
        self.server_image = None
        self.profile_name: str = ""
        self.support_contact: List[str] = []

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    @staticmethod
    def from_uuid(filename: str, server_name: str = None) -> Any:
        vpn_connection_path = os.path.join(CONFIG_PREFIX, filename)
        vpn_connection = VpnConnection()
        try:
            with open(vpn_connection_path, 'r') as f:
                x = json.load(f)
                for key, value in x.items():
                    if value:
                        setattr(vpn_connection, key, value)
                return vpn_connection
        except (ValueError, IOError) as e:
            logger.error("can't open vpn connection data "
                         f"file for {filename}: {e}")
            if server_name:
                vpn_connection.server_name = server_name
            else:
                vpn_connection.server_name = vpn_connection.uuid
            return vpn_connection

    def write(self) -> None:
        fields = [f for f in dir(self) if not f.startswith('_') and not callable(getattr(self, f))]
        d = {field: getattr(self, field) for field in fields}
        p = os.path.join(CONFIG_PREFIX, CONFIG_JSON_PREFIX + self.uuid + '.json')
        logger.info(u"storing vpn connection data in {}".format(p))
        serialized = json.dumps(d)
        os.makedirs(CONFIG_PREFIX, mode=0o777, exist_ok=True)
        with open(p, 'w') as f:
            f.write(serialized)

        # if self.authorization_type == 'distributed':
        #     self.write_distributed_token()

    @staticmethod
    def read_all() -> List[Any]:
        if not os.access(CONFIG_PREFIX, os.X_OK):
            return []
        connections_list = [VpnConnection.from_uuid(i) for i in os.listdir(CONFIG_PREFIX) if i.startswith(CONFIG_JSON_PREFIX) and i.endswith('.json')]

        for i in connections_list:
            print(i)
        return connections_list
