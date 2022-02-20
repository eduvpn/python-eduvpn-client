from datetime import datetime, timezone
from typing import List, Type
from . import nm
from .ovpn import Ovpn
from .server import Protocol
from .session import Validity
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

    @classmethod
    def parse(cls, response) -> 'WireGuardConnection':
        raise NotImplementedError  # TODO


connection_types: List[Type[Connection]] = [
    OpenVPNConnection,
    WireGuardConnection,
]

protocol_to_connection_type = {
    connection_type.protocol: connection_type
    for connection_type in connection_types
}
