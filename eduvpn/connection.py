from configparser import ConfigParser
from typing import Optional, List, Type
from . import nm
from .ovpn import Ovpn

# from .session import Validity


class Connection:
    "Base class for connection configurations."

    @classmethod
    def parse(cls, config, protocol) -> "Connection":
        if protocol == "wireguard":
            connection_type = WireGuardConnection
        else:
            connection_type = OpenVPNConnection
        return connection_type.parse(config, protocol)

    def force_tcp(self):
        raise NotImplementedError

    def connect(self, callback):
        """
        Start this connection.

        This method is always called from the main thread.
        """
        raise NotImplementedError


class OpenVPNConnection(Connection):
    def __init__(self, ovpn: Ovpn):
        self.ovpn = ovpn
        super().__init__()

    @classmethod
    def parse(cls, config, _) -> "OpenVPNConnection":
        ovpn = Ovpn.parse(config)
        return cls(ovpn=ovpn)

    def force_tcp(self):
        self.ovpn.force_tcp()

    def connect(self, callback):
        nm.start_openvpn_connection(
            self.ovpn,
            callback=callback,
        )


class WireGuardConnection(Connection):
    def __init__(self, config: ConfigParser):
        self.config = config
        super().__init__()

    @classmethod
    def parse(cls, config_str, _) -> "WireGuardConnection":
        # TODO: validity
        config = ConfigParser()
        config.read_string(config_str)
        return cls(config=config)

    def force_tcp(self):
        raise NotImplementedError("WireGuard cannot be forced over tcp")

    def connect(self, callback):
        nm.start_wireguard_connection(
            self.config,
            callback=callback,
        )
