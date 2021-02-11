from typing import Any, Union, Optional, Iterable, List, Dict, Type
from eduvpn.remote import list_servers, list_organisations
from eduvpn.i18n import extract_translation
from eduvpn.settings import SERVER_URI, ORGANISATION_URI


class InstituteAccessServer:
    """
    A record from: https://disco.eduvpn.org/v2/server_list.json
    where: server_type == "institute_access"
    """

    def __init__(self,
                 base_url: str,
                 display_name: Union[str, Dict[str, str]],
                 support_contact: List[str] = [],
                 keyword_list: Optional[str] = None):
        self.base_url = base_url
        self.display_name = display_name
        self.support_contact = support_contact
        self.keyword_list = keyword_list

    def __str__(self):
        return extract_translation(self.display_name)

    def __repr__(self):
        return f"<InstituteAccessServer {str(self)!r}>"

    @property
    def keyword(self) -> Optional[str]:
        return self.keyword_list

    @property
    def search_texts(self):
        texts = [str(self)]
        if self.keyword:
            texts.append(self.keyword)
        return texts

    @property
    def oauth_login_url(self):
        return self.base_url


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
        return self.base_url  # TODO

    def __repr__(self):
        return f"<SecureInternetServer {str(self)!r}>"

    @property
    def oauth_login_url(self):
        return self.base_url


class OrganisationServer:
    """
    A record from: https://disco.eduvpn.org/v2/organization_list.json
    """

    def __init__(self,
                 secure_internet_home: str,
                 display_name: Union[str, Dict[str, str]],
                 org_id: str,
                 keyword_list: List[str] = []):
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

    @property
    def oauth_login_url(self):
        return self.secure_internet_home


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


server_types = [
    InstituteAccessServer,
    OrganisationServer,
    CustomServer,
]


# typing aliases
ServerType = Any
Server = Union[tuple(server_types)]


def group_servers_by_type(servers: Iterable[Server]) -> Dict[Type, Server]:
    groups = {server_type: [] for server_type in server_types}
    for server in servers:
        groups[type(server)].append(server)
    return groups


def is_search_match(server: Server, query: str) -> bool:
    if hasattr(server, 'search_texts'):
        return any(query.lower() in search_text.lower()
                   for search_text in server.search_texts)
    else:
        return False


class ServerDatabase:
    def __init__(self):
        # TODO load the servers from a cache
        self.servers = []
        self.is_loaded = False

    def update(self):
        """
        Download the list of institute and secure internet servers,
        and update this database.

        This method must be thread-safe.
        """
        new_servers = []
        server_list = list_servers(SERVER_URI)
        organisation_list = list_organisations(ORGANISATION_URI)
        for server_data in server_list:
            server_type = server_data.pop('server_type')
            if server_type == 'institute_access':
                server = InstituteAccessServer(**server_data)
                new_servers.append(server)
            elif server_type == 'secure_internet':
                server = SecureInternetServer(**server_data)
                new_servers.append(server)
            else:
                raise ValueError(server_type, server_data)
        for organisation_data in organisation_list:
            server = OrganisationServer(**organisation_data)
            new_servers.append(server)
        # Atomic update of server map.
        # TODO keep custom other servers
        self.servers = new_servers
        self.is_loaded = True

    def all(self) -> Iterable[Server]:
        "Return all servers."
        return iter(self.servers)

    def search(self, query: str) -> Iterable[Server]:
        "Return all servers that match the search query."
        if query:
            for server in self.all():
                if is_search_match(server, query):
                    yield server
        else:
            yield from self.all()
