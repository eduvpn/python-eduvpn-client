from typing import Union, Optional, Iterable, List, Dict
import logging
import os
import json
import eduvpn.nm as nm
from eduvpn.i18n import extract_translation, retrieve_country_name
from eduvpn.settings import FLAG_PREFIX
from functools import partial
from eduvpn.connection import Connection
from .utils import (
    get_prefix, thread_helper, run_in_background_thread, run_in_main_gtk_thread, run_periodically, cancel_at_context_end)


logger = logging.getLogger(__name__)
TranslatedStr = Union[str, Dict[str, str]]


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


class SecureInternetServer:
    """
    A record from: https://disco.eduvpn.org/v2/server_list.json
    where: server_type == "secure_internet"
    """

    def __init__(self,
                 base_url: str,
                 public_key_list: List[str],
                 country_code: str,
                 support_contact: List[str] = [],
                 authentication_url_template: Optional[str] = None):
        self.base_url = base_url
        self.public_key_list = public_key_list
        self.support_contact = support_contact
        self.country_code = country_code
        self.authentication_url_template = authentication_url_template

    def __str__(self):
        return f"{self.country_name} @ {self.base_url}"

    def __repr__(self):
        return f"<SecureInternetServer {str(self)!r}>"

    @property
    def country_name(self) -> str:
        return retrieve_country_name(self.country_code)

    @property
    def flag_path(self) -> Optional[str]:
        path = f'{FLAG_PREFIX}{self.country_code}@1,5x.png'
        if os.path.exists(path):
            return path
        else:
            return None


class OrganisationServer:
    """
    A record from: https://disco.eduvpn.org/v2/organization_list.json
    """

    def __init__(self,
                 secure_internet_home: str,
                 display_name: TranslatedStr,
                 org_id: str,
                 keyword_list: Dict[str, str] = {}):
        self.secure_internet_home = secure_internet_home
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
    SecureInternetServer,
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

    @run_in_background_thread('connect')
    def connect(self, eduvpn, server: AnyServer):
        is_institute = True
        if isinstance(server, InstituteAccessServer):
            url = server.base_url
        elif isinstance(server, OrganisationServer):
            url = server.secure_internet_home
            is_institute = False
        elif isinstance(server, CustomServer):
            url = server.address
        if is_institute:
            config, config_type = eduvpn.get_config_institute_access(url)
        else:
            config, config_type = eduvpn.get_config_secure_internet(url)

        def on_connected():
            eduvpn.set_connected()

        def on_connect(arg):
            client = nm.get_client()
            uuid = nm.get_uuid(eduvpn)
            nm.activate_connection(client, uuid, on_connected)

        @run_in_main_gtk_thread
        def connect(common, config, config_type):
            connection = Connection.parse(common, config, config_type)
            connection.connect(on_connect)

        connect(eduvpn, config, config_type)

        

    def disco_parse_organizations(self, _str):
        # TODO: Only parse on actual update
        # Reset organizations
        self.organizations = []
        json_organizations = json.loads(_str)

        for organization in json_organizations['organization_list']:
            server = OrganisationServer(**organization)
            self.servers.append(server)

    def disco_parse_servers(self, _str):
        # TODO: Only parse on actual update
        # Reset servers
        self.servers = []
        json_servers = json.loads(_str)

        for server_data in json_servers['server_list']:
            server_type = server_data.pop('server_type')
            if server_type == 'institute_access':
                server = InstituteAccessServer(**server_data)
                self.servers.append(server)
            elif server_type == 'secure_internet':
                server = SecureInternetServer(**server_data)
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
