import json
from typing import Dict, List

from eduvpn_common.main import ServerType

from eduvpn.i18n import extract_translation


class DiscoOrganization:
    """The class that represents an organization from discovery
    :param: display_name: Dict[str, str]: The display name of the organizations
    :param: org_id: str: The organization ID
    :param: keywords: Dict[str, str]: The dictionary of strings that the users gets to search on to find the server
    """

    def __init__(
        self,
        display_name: Dict[str, str],
        org_id: str,
        keywords: Dict[str, str],
    ):
        self.display_name = display_name
        self.org_id = org_id
        self.keywords = keywords

    @property
    def identifier(self):
        return self.org_id

    @property
    def category_id(self) -> ServerType:
        return ServerType.SECURE_INTERNET

    def __str__(self):
        return extract_translation(self.display_name)


class DiscoServer:
    """The class that represents a discovery server, this can be an institute access or secure internet server
    :param: base_url: str: The base URL of the server
    :param: display_name: Dict[str, str]: The display name of the server
    :param: keywords: Dict[str, str]: The dictionary of keywords that the user can use to find the server
    :param: server_type: str: The server type as a string
    """

    def __init__(
        self,
        base_url: str,
        display_name: Dict[str, str],
        keywords: Dict[str, str],
        server_type: str,
    ):
        self.base_url = base_url
        self.display_name = display_name
        self.keywords = keywords
        self.server_type = server_type

    @property
    def identifier(self):
        return self.base_url

    @property
    def category_id(self) -> ServerType:
        return ServerType.INSTITUTE_ACCESS

    def __str__(self):
        return extract_translation(self.display_name)


def parse_disco_server(s: dict) -> DiscoServer:
    b_url = s["base_url"]
    display_name = s.get("display_name", "")
    # display names are just space separated in server_list.json
    keywords = s.get("keyword_list", {"en": ""})
    # Mandatory
    server_type = s["server_type"]
    return DiscoServer(b_url, display_name, keywords, server_type)


def parse_disco_organization(o: dict) -> DiscoOrganization:
    display_name = o.get("display_name", "")
    org_id = o["org_id"]
    keywords = o.get("keyword_list", {"en": ""})
    return DiscoOrganization(display_name, org_id, keywords)


def parse_disco_servers(json_str: str) -> List[DiscoServer]:
    d = json.loads(json_str)
    servers = d.get("server_list", [])
    disco_servers = []
    for s in servers:
        disco_server = parse_disco_server(s)
        disco_servers.append(disco_server)
    return disco_servers


def parse_disco_organizations(json_str: str) -> List[DiscoOrganization]:
    d = json.loads(json_str)
    organizations = d.get("organization_list", [])
    disco_orgs = []
    for o in organizations:
        disco_org = parse_disco_organization(o)
        disco_orgs.append(disco_org)
    return disco_orgs
