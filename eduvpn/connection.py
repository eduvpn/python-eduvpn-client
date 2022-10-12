from configparser import ConfigParser

from eduvpn import nm
from eduvpn.ovpn import Ovpn


class Connection:
    "Base class for connection configurations."

    @classmethod
    def parse(cls, config, protocol) -> "Connection":
        if protocol == "wireguard":
            connection_type = WireGuardConnection
        else:
            connection_type = OpenVPNConnection
        return connection_type.parse(config, protocol)

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

    def connect(self, variant, callback):
        nm.start_openvpn_connection(
            self.ovpn,
            variant,
            callback=callback,
        )


class WireGuardConnection(Connection):
    def __init__(self, config: ConfigParser):
        self.config = config
        super().__init__()

    @classmethod
    def parse(cls, config_str, _) -> "WireGuardConnection":
        config = ConfigParser()
        config.read_string(config_str)
        return cls(config=config)

    def connect(self, variant, callback):
        nm.start_wireguard_connection(
            self.config,
            variant,
            callback=callback,
        )
