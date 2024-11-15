from typing import List
from urllib.parse import urlparse

from eduvpn.utils import handle_exception


class Proxy:
    """The class that represents a proxyguard instance
    :param: common: The common library
    :param: peer: str: The remote peer string
    :param: listen: str: The listen proxy string
    """

    def __init__(
        self,
        common,
        config,
        wrapper,
    ):
        self.common = common
        self.config = config
        self.wrapper = wrapper

    def forward_exception(self, error):
        handle_exception(self.common, error)

    def tunnel(self, wgport):
        self.wrapper.tunnel(wgport)

    def restart(self):
        self.wrapper.restart()

    @property
    def peer(self) -> str:
        return self.config.peer

    @property
    def source_port(self) -> int:
        return self.config.source_port

    @property
    def listen_port(self) -> int:
        return self.config.listen_port

    @property
    def peer_ips(self) -> List[str]:
        return self.wrapper.peer_ips

    @property
    def peer_scheme(self) -> str:
        try:
            parsed = urlparse(self.config.peer)
            return parsed.scheme
        except Exception:
            return ""

    @property
    def peer_port(self):
        if self.peer_scheme == "http":
            return 80
        return 443
