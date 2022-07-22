from typing import Union, Optional, Iterable, List, Dict
import logging
import os
import json
import enum
import eduvpn.nm as nm
import webbrowser
from eduvpn.i18n import extract_translation, retrieve_country_name
from eduvpn.settings import FLAG_PREFIX, IMAGE_PREFIX
from functools import partial
from eduvpn.connection import Connection
from .utils import (
    get_prefix, thread_helper, run_in_background_thread, run_in_main_gtk_thread, run_periodically)


logger = logging.getLogger(__name__)
TranslatedStr = Union[str, Dict[str, str]]

class StatusImage(enum.Enum):
    # The value is the image filename.
    DEFAULT = 'desktop-default.png'
    CONNECTING = 'desktop-connecting.png'
    CONNECTED = 'desktop-connected.png'
    NOT_CONNECTED = 'desktop-not-connected.png'

    @property
    def path(self):
        return IMAGE_PREFIX + self.value

class SecureInternetLocation:
    """
    A helper class for a secure internet location country code
    """

    def __init__(self,
                 country_code: str):
        self.country_code = country_code

    def __str__(self):
        return retrieve_country_name(self.country_code)

    def __repr__(self):
        return f"<SecureInternetLocation {str(self)!r}>"

    @property
    def flag_path(self) -> Optional[str]:
        path = f'{FLAG_PREFIX}{self.country_code}@1,5x.png'
        if os.path.exists(path):
            return path
        else:
            return None

class InstituteAccessServer:
    """
    A record from: https://disco.eduvpn.org/v2/server_list.json
    where: server_type == "institute_access"
    """

    def __init__(self,
                 base_url: str,
                 display_name: TranslatedStr,
                 support_contact: List[str] = [],
                 keyword_list: Optional[Union[str, List[str]]] = None):
        self.base_url = base_url
        self.display_name = display_name
        self.support_contact = support_contact
        if keyword_list is not None:
            if isinstance(keyword_list, str):
                keyword_list = [keyword_list]
            elif not isinstance(keyword_list, list):
                raise TypeError(keyword_list)
        self.keyword_list = keyword_list

    def __str__(self):
        return extract_translation(self.display_name)

    def __repr__(self):
        return f"<InstituteAccessServer {str(self)!r}>"

    @property
    def search_texts(self):
        texts = [str(self)]
        if self.keyword_list:
            texts.extend(self.keyword_list)
        return texts


class OrganisationServer:
    """
    A record from: https://disco.eduvpn.org/v2/organization_list.json
    """

    # TODO: Remove display name?
    def __init__(self,
                 display_name: TranslatedStr,
                 org_id: str,
                 keyword_list: Dict[str, str] = {},
                 **kwargs):
        self.display_name = display_name
        self.org_id = org_id
        self.keyword_list = keyword_list

    def __str__(self):
        return extract_translation(self.display_name)

    def __repr__(self):
        return f"<OrganisationServer {str(self)!r}>"

    @property
    def keyword(self) -> Optional[str]:
        if self.keyword_list:
            return extract_translation(self.keyword_list)
        return None

    @property
    def search_texts(self):
        texts = [str(self)]
        if self.keyword:
            texts.append(self.keyword)
        return texts


class CustomServer:
    """
    A server defined by the user.
    """

    def __init__(self, address: str):
        self.address = address

    def __str__(self):
        return self.address

    def __repr__(self):
        return f"<CustomServer {str(self)!r}>"


class Profile:
    def __init__(self,
                 profile_id: str,
                 display_name: TranslatedStr,
                 default_gateway: Optional[bool] = None,
                 vpn_proto_list: Iterable[str] = frozenset('openvpn'),
                 **kwargs
                 ):
        self.profile_id = profile_id
        self.display_name = display_name
        self.default_gateway = default_gateway
        self.vpn_proto_list = frozenset(vpn_proto_list)

    @property
    def id(self):
        return self.profile_id

    def __str__(self):
        return extract_translation(self.display_name)

    def __repr__(self):
        return f"<Profile id={self.id!r} {str(self)!r}>"

    @property
    def use_as_default_gateway(self) -> bool:
        if self.default_gateway is None:
            return False
        else:
            return self.default_gateway


# typing aliases
PredefinedServer = Union[
    InstituteAccessServer,
    OrganisationServer,
    CustomServer,
]
ConfiguredServer = Union[
    InstituteAccessServer,
    CustomServer,
]
AnyServer = Union[
    PredefinedServer,
    ConfiguredServer,
]


def is_search_match(server: PredefinedServer, query: str) -> bool:
    if hasattr(server, 'search_texts'):
        return any(query.lower() in search_text.lower()
                   for search_text
                   in server.search_texts)  # type: ignore
    else:
        return False


class ServerDatabase:
    def __init__(self):
        # TODO load the servers from a cache
        self.servers = []
        self.configured = []

    def disco_parse(self, disco_organizations, disco_servers):
        # TODO: Only parse on actual update
        # Reset organizations
        self.servers = []
        json_organizations = json.loads(disco_organizations)

        for organization in json_organizations['organization_list']:
            server = OrganisationServer(**organization)
            self.servers.append(server)

        json_servers = json.loads(disco_servers)

        for server_data in json_servers['server_list']:
            server_type = server_data.pop('server_type')
            if server_type == 'institute_access':
                server = InstituteAccessServer(**server_data)
                self.servers.append(server)

    def parse_servers(self, _str):
        #print("PARSE", _str)
        pass

    def all_configured(self) -> Iterable[ConfiguredServer]:
        "Return all configured servers."
        # TODO: replace with Go
        pass

    def get_single_configured(self) -> Optional[ConfiguredServer]:
        # TODO: replace with Go
        pass

    def all(self) -> Iterable[PredefinedServer]:
        "Return all servers."
        return self.servers

    def search_predefined(self, query: str) -> Iterable[PredefinedServer]:
        "Return all servers that match the search query."
        if query:
            for server in self.all():
                if is_search_match(server, query):
                    yield server
        else:
            yield from self.all()

    def search_custom(self, query: str) -> Iterable[CustomServer]:
        yield CustomServer(query)
