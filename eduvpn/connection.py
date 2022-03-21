from datetime import datetime, timezone
from configparser import ConfigParser
from typing import Optional, List, Type
from . import nm
from .ovpn import Ovpn
from .server import Protocol
from .session import Validity
from .crypto import SecretKey
from .utils import parse_http_date_header, parse_http_expires_header


def get_response_date(response) -> datetime:
    try:
        return parse_http_date_header(response.headers['Date'])
    except (KeyError, ValueError):
        return datetime.now(timezone.utc)


class Connection:
    "Base class for connection configurations."

    protocol: Protocol
    validity: Validity

    def __init__(self, validity: Validity):
        self.validity = validity

    @classmethod
    def parse(cls, response) -> 'Connection':
        protocol = Protocol.get_by_config_type(response.headers['Content-Type'])
        connection_type = protocol_to_connection_type[protocol]
        return connection_type.parse(response)

    def set_secret_key(self, secret_key: SecretKey):
        pass

    def force_tcp(self):
        raise NotImplementedError

    def connect(self, callback):
        """
        Start this connection.

        This method is always called from the main thread.
        """
        raise NotImplementedError


class OpenVPNConnection(Connection):
    protocol = Protocol.OPENVPN

    def __init__(self, validity: Validity, ovpn: Ovpn):
        self.ovpn = ovpn
        super().__init__(validity)

    @classmethod
    def parse(cls, response) -> 'OpenVPNConnection':
        expiry = parse_http_expires_header(response.headers['Expires'])
        created = get_response_date(response)
        validity = Validity(created, expiry)
        ovpn = Ovpn.parse(response.text)
        return cls(validity=validity, ovpn=ovpn)

    def force_tcp(self):
        self.ovpn.force_tcp()

    def connect(self, callback):
        nm.start_openvpn_connection(
            self.ovpn,
            callback=callback,
        )


class WireGuardConnection(Connection):
    protocol = Protocol.WIREGUARD

    def __init__(self, validity: Validity, config: ConfigParser):
        self.config = config
        self.secret_key: Optional[SecretKey] = None
        super().__init__(validity)

    @classmethod
    def parse(cls, response) -> 'WireGuardConnection':
        expiry = parse_http_expires_header(response.headers['Expires'])
        created = get_response_date(response)
        validity = Validity(created, expiry)
        config = ConfigParser()
        config.read_string(response.text)
        return cls(validity=validity, config=config)

    def set_secret_key(self, secret_key: SecretKey):
        assert self.secret_key is None
        self.secret_key = secret_key

    def force_tcp(self):
        raise NotImplementedError("WireGuard cannot be forced over tcp")

    def connect(self, callback):
        assert self.secret_key is not None
        nm.start_wireguard_connection(
            self.config,
            secret_key=self.secret_key,
            callback=callback,
        )


connection_types: List[Type[Connection]] = [
    OpenVPNConnection,
    WireGuardConnection,
]

protocol_to_connection_type = {
    connection_type.protocol: connection_type
    for connection_type in connection_types
}
