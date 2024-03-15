import json
from typing import Dict, List

from eduvpn_common.main import ServerType

from eduvpn.i18n import extract_translation


class DiscoOrganization:
    """The class that represents an organization from discovery
    :param: display_name: Dict[str, str]: The display name of the organizations
    :param: org_id: str: The organization ID
    :param: secure_internet_home: str: Indicating which server is the secure internet home server
    :param: keywords: Dict[str, str]: The dictionary of strings that the users gets to search on to find the server
    """

    def __init__(
        self,
        display_name: Dict[str, str],
        org_id: str,
        secure_internet_home: str,
        keywords: Dict[str, str],
    ):
        self.display_name = display_name
        self.org_id = org_id
        self.secure_internet_home = secure_internet_home
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
    :param: authentication_url_template: str: The OAuth template to use to skip WAYF
    :param: base_url: str: The base URL of the server
    :param: country_code: str: The country code of the server
    :param: display_name: Dict[str, str]: The display name of the server
    :param: keywords: Dict[str, str]: The dictionary of keywords that the user can use to find the server
    :param: public_keys: List[str]: The list of public keys
    :param: server_type: str: The server type as a string
    :param: support_contacts: List[str]: The list of support contacts
    """

    def __init__(
        self,
        base_url: str,
        country_code: str,
        display_name: Dict[str, str],
        keywords: Dict[str, str],
        server_type: str,
        support_contacts: List[str],
    ):
        self.base_url = base_url
        self.country_code = country_code
        self.display_name = display_name
        self.keywords = keywords
        self.server_type = server_type
        self.support_contacts = support_contacts

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
    country_code = s.get("country_code", "")
    display_name = s.get("display_name", "")
    # display names are just space separated in server_list.json
    keywords = s.get("keyword_list", {"en": ""})
    # Mandatory
    server_type = s["server_type"]
    support_contacts = s.get("support_contact", None)
    return DiscoServer(b_url, country_code, display_name, keywords, server_type, support_contacts)


def parse_disco_organization(o: dict) -> DiscoOrganization:
    display_name = o.get("display_name", "")
    org_id = o["org_id"]
    secure_internet_home = o["secure_internet_home"]
    keywords = o.get("keyword_list", {"en": ""})
    return DiscoOrganization(display_name, org_id, secure_internet_home, keywords)


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
