import enum
import logging
import os
from typing import Dict, Iterable, List, Optional, Union

from eduvpn_common.server import Server
from eduvpn.i18n import retrieve_country_name
from eduvpn.settings import FLAG_PREFIX, IMAGE_PREFIX

logger = logging.getLogger(__name__)
TranslatedStr = Union[str, Dict[str, str]]


class StatusImage(enum.Enum):
    # The value is the image filename.
    DEFAULT = "desktop-default.png"
    CONNECTING = "desktop-connecting.png"
    CONNECTED = "desktop-connected.png"
    NOT_CONNECTED = "desktop-not-connected.png"

    @property
    def path(self) -> str:
        return IMAGE_PREFIX + self.value


def get_search_text(server) -> List[str]:
    search_texts = [server.display_name]
    if hasattr(server, "keyword_list"):
        search_texts.extend(server.keyword_list.split(" "))
    return search_texts


def is_search_match(server, query: str) -> bool:
    search_texts = get_search_text(server)
    return any(query.lower() in search_text.lower() for search_text in search_texts)


class ServerDatabase:
    def __init__(self, common, enable_discovery=True) -> None:
        self.common = common
        self.enable_discovery = enable_discovery

    @property
    def disco(self):
        if not self.enable_discovery:
            return []
        disco_orgs = self.common.get_disco_organizations()
        disco_servers = self.common.get_disco_servers()
        all_servers = disco_orgs.organizations
        all_servers.extend(disco_servers.servers)
        return all_servers

    @property
    def configured(self):
        return self.common.get_saved_servers()

    def all(self):
        "Return all servers."
        return self.disco

    def search_predefined(self, query: str):
        "Return all servers that match the search query."
        if query:
            for server in self.all():
                if is_search_match(server, query):
                    yield server
        else:
            yield from self.all()

    def search_custom(self, query: str) -> Iterable[Server]:
        yield Server(query, query)
