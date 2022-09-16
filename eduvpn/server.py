import enum
import json
import logging
import os
from typing import Dict, Iterable, List, Optional, Union

from eduvpn_common.server import Server
from eduvpn.i18n import extract_translation, retrieve_country_name
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
    def __init__(self) -> None:
        # TODO load the servers from a cache
        self.servers = []
        self.configured = []

    #def parse_servers(self, _str):
    #    # print("PARSE", _str)
    #    pass

    #def all_configured(self) -> Iterable[ConfiguredServer]:
    #    "Return all configured servers."
    #    # TODO: replace with Go
    #    pass

    #def get_single_configured(self) -> Optional[ConfiguredServer]:
    #    # TODO: replace with Go
    #    pass

    def all(self):
        "Return all servers."
        return self.servers

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
