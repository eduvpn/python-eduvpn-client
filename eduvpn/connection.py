import json
from configparser import ConfigParser
from datetime import datetime, timedelta
from enum import IntEnum
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from eduvpn.ovpn import Ovpn


class Token:
    """The class that represents oauth Tokens
    :param: access: str: The access token
    :param: refresh: str: The refresh token
    :param: expired: int: The expire unix time
    """

    def __init__(self, access: str, refresh: str, expired: int):
        self.access = access
        self.refresh = refresh
        self.expires = expired

    def dump(self) -> str:
        """Dumps the tokens as a JSON string"""
        d = {
            "access_token": self.access,
            "refresh_token": self.refresh,
            "expires": self.expires,
        }

        return json.dumps(d)


class Protocol(IntEnum):
    UNKNOWN = 0
    OPENVPN = 1
    WIREGUARD = 2
    WIREGUARDTCP = 3


class Proxy:
    """The class that represents a proxyguard instance
    :param: peer: str: The remote peer string
    :param: listen: str: The listen proxy string
    """

    def __init__(
        self,
        peer: str,
        source_port: int,
        listen: str,
    ):
        self.peer = peer
        self.source_port = source_port
        self.listen = listen

    @property
    def peer_scheme(self) -> str:
        try:
            parsed = urlparse(self.peer)
            return parsed.scheme
        except Exception:
            return ""

    @property
    def peer_port(self):
        if self.peer_scheme == "http":
            return 80
        return 443


class Config:
    """The class that represents an OpenVPN/WireGuard config
    :param: config: str: The config string
    :param: protocol: Protocol: The type of config, openvpn/wireguard
    :param: default_gateway: bool: If this configuration should be configured with default gateway
    """

    def __init__(
        self,
        config: str,
        protocol: Protocol,
        default_gateway: bool,
        dns_search_domains: List[str],
        proxy: Proxy,
        should_failover: bool,
    ):
        self.config = config
        self.protocol = protocol
        self.default_gateway = default_gateway
        self.dns_search_domains = dns_search_domains
        self.proxy = proxy
        self.should_failover = should_failover

    def __str__(self):
        return self.config


def parse_tokens(tokens_json: str) -> Token:
    jsonT = json.loads(tokens_json)
    return Token(jsonT["access_token"], jsonT["refresh_token"], jsonT["expires_at"])


def parse_config(config_json: str) -> Config:
    d = json.loads(config_json)
    proxy = d.get("proxy", None)
    if proxy:
        proxy = Proxy(proxy["peer"], proxy["source_port"], proxy["listen"])
    cfg = Config(
        d["config"],
        Protocol(d["protocol"]),
        d["default_gateway"],
        d.get("dns_search_domains", []),
        proxy,
        d["should_failover"],
    )
    return cfg


class Validity:
    def __init__(
        self,
        start: datetime,
        end: datetime,
        button: datetime,
        countdown: datetime,
        notifications: List[datetime],
    ):
        self.start = start
        self.end = end
        self.button = button
        self.countdown = countdown
        self.notifications = notifications

    @property
    def remaining(self) -> timedelta:
        """
        Return the duration from now until expiry.
        """
        return self.end - datetime.now()

    @property
    def is_expired(self) -> bool:
        """
        Return True if the validity has expired.
        """
        return datetime.now() >= self.end


def parse_date(d: Dict[str, Any], key: str) -> datetime:
    val = d.get(key, 0)
    return datetime.fromtimestamp(val)


def parse_expiry(exp_json: str) -> Optional[Validity]:
    d = json.loads(exp_json)
    start = parse_date(d, "start_time")
    end = parse_date(d, "end_time")
    button = parse_date(d, "button_time")
    countdown = parse_date(d, "countdown_time")
    notifs = d.get("notification_times", [])
    parsed_notifs = []
    for n in notifs:
        parsed_notifs.append(datetime.fromtimestamp(n))
    return Validity(start, end, button, countdown, parsed_notifs)


class Connection:
    "Base class for connection configurations."

    @classmethod
    def parse(cls, config: Config) -> "Connection":
        if (
            config.protocol == Protocol.WIREGUARD
            or config.protocol == Protocol.WIREGUARDTCP
        ):
            connection_type = WireGuardConnection
        else:
            connection_type = OpenVPNConnection  # type: ignore
        return connection_type.parse(config.config)

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
    def parse(cls, config_str: str) -> "OpenVPNConnection":  # type: ignore
        ovpn = Ovpn.parse(config_str)
        return cls(ovpn=ovpn)

    def connect(
        self,
        manager,
        default_gateway,
        allow_lan,
        dns_search_domains,
        proxy,
        proxy_peer_ips,
        callback,
    ):
        manager.start_openvpn_connection(
            self.ovpn,
            default_gateway,
            dns_search_domains,
            callback=callback,
        )


class WireGuardConnection(Connection):
    def __init__(self, config: ConfigParser):
        self.config = config
        super().__init__()

    @classmethod
    def parse(cls, config_str: str) -> "WireGuardConnection":  # type: ignore
        config = ConfigParser()
        config.read_string(config_str)
        return cls(config=config)

    def connect(
        self,
        manager,
        default_gateway,
        allow_lan,
        dns_search_domains,
        proxy,
        proxy_peer_ips,
        callback,
    ):
        manager.start_wireguard_connection(
            self.config,
            default_gateway,
            allow_wg_lan=allow_lan,
            callback=callback,
            proxy_peer_ips=proxy_peer_ips,
            proxy=proxy,
        )
