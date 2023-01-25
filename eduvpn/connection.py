from configparser import ConfigParser
from datetime import datetime, timedelta

from eduvpn.ovpn import Ovpn


def now() -> datetime:
    return datetime.now()


class Validity:
    def __init__(self, end: datetime) -> None:
        self.end = end

    @property
    def remaining(self) -> timedelta:
        """
        Return the duration from now until expiry.
        """
        return self.end - now()

    @property
    def is_expired(self) -> bool:
        """
        Return True if the validity has expired.
        """
        return now() >= self.end


class Connection:
    "Base class for connection configurations."

    @classmethod
    def parse(cls, config, protocol) -> "Connection":
        if protocol == "wireguard":
            connection_type = WireGuardConnection
        else:
            connection_type = OpenVPNConnection  # type: ignore
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

    def connect(self, manager, default_gateway, callback):
        manager.start_openvpn_connection(
            self.ovpn,
            default_gateway,
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

    def connect(self, manager, default_gateway, callback):
        manager.start_wireguard_connection(
            self.config,
            default_gateway,
            callback=callback,
        )
