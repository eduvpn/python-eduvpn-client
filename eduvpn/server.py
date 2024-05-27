import enum
import json
import logging
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

from eduvpn_common.main import ServerType

from eduvpn.discovery import DiscoOrganization, DiscoServer, parse_disco_organizations, parse_disco_servers
from eduvpn.i18n import extract_translation
from eduvpn.settings import IMAGE_PREFIX

logger = logging.getLogger(__name__)
TranslatedStr = Union[str, Dict[str, str]]


class Profile:
    """The class that represents a server profile.
    :param: identifier: str: The identifier (id) of the profile
    :param: display_name: str: The display name of the profile
    :param: default_gateway: str: Whether or not this profile should have the default gateway set
    """

    def __init__(self, identifier: str, display_name: Dict[str, str], default_gateway: bool):
        self.identifier = identifier
        self.display_name = display_name
        self.default_gateway = default_gateway

    def __str__(self):
        return extract_translation(self.display_name)


class Profiles:
    """The class that represents a list of profiles
    :param: profiles: List[Profile]: A list of profiles
    :param: current: int: The current profile index
    """

    def __init__(self, profiles: Dict[str, Profile], current: str):
        self.profiles = profiles
        self.current_id = current

    @property
    def current(self) -> Optional[Profile]:
        """Get the current profile if there is any
        :return: The profile if there is a current one (meaning the index is valid)
        :rtype: Optional[Profile]
        """
        if self.current_id not in self.profiles:
            return None
        return self.profiles[self.current_id]


class Server:
    """The class that represents a server. Use this for a custom server
    :param: url: str: The base URL of the server. In case of secure internet (supertype) this is the organisation ID URL
    :param: display_name: str: The display name of the server
    :param: profiles: Optional[Profiles]: The profiles if there are any already obtained, defaults to None
    """

    def __init__(
        self,
        url: str,
        display_name: Dict[str, str],
        profiles: Optional[Profiles] = None,
    ):
        self.url = url
        self.display_name = display_name
        self.profiles = profiles

    def __str__(self) -> str:
        return extract_translation(self.display_name)

    @property
    def identifier(self) -> str:
        return self.url

    @property
    def category_id(self) -> ServerType:
        return ServerType.CUSTOM

    @property
    def category(self) -> str:
        """Return the category of the server as a string
        :return: The category string
        :rtype: str
        """
        return str(self.category_id)


class InstituteServer(Server):
    """The class that represents an Institute Access Server
    :param: url: str: The base URL of the Institute Access Server
    :param: display_name: str: The display name of the Institute Access Server
    :param: support_contact: List[str]: The list of support contacts
    :param: profiles: Profiles: The profiles of the server
    """

    def __init__(
        self,
        url: str,
        display_name: Dict[str, str],
        support_contact: List[str],
        profiles: Profiles,
    ):
        super().__init__(url, display_name, profiles)
        self.support_contact = support_contact

    @property
    def category_id(self) -> ServerType:
        return ServerType.INSTITUTE_ACCESS

    @property
    def category(self) -> str:
        """Return the category of the server as a string
        :return: The category string
        :rtype: str
        """
        return str(self.category_id)


class SecureInternetServer(Server):
    """The class that represents a Secure Internet Server
    :param: org_id: str: The organization ID of the Secure Internet Server as returned by Discovery
    :param: display_name: str: The display name of the server
    :param: support_contact: List[str]: The list of support contacts of the server
    :param: locations: List[str]: The list of secure internet locations
    :param: profiles: Profiles: The list of profiles that the server has
    :param: country_code: str: The country code of the server
    :param: locations: List[str]: The list of secure internet locations
    """

    def __init__(
        self,
        org_id: str,
        display_name: Dict[str, str],
        support_contact: List[str],
        profiles: Profiles,
        country_code: str,
        locations: List[str],
    ):
        super().__init__(org_id, display_name, profiles)
        self.org_id = org_id
        self.support_contact = support_contact
        self.country_code = country_code
        self.locations = locations

    @property
    def category_id(self) -> ServerType:
        return ServerType.SECURE_INTERNET

    @property
    def category(self) -> str:
        """Return the category of the server as a string
        :return: The category string
        :rtype: str
        """
        return str(self.category_id)


def parse_secure_internet(si: dict) -> Optional[SecureInternetServer]:
    profiles = parse_profiles(si["profiles"])
    locations = si.get("locations", [])
    # TODO: delisted
    return SecureInternetServer(
        si["identifier"],
        si["display_name"],
        si.get("support_contacts", []),
        profiles,
        si["country_code"],
        locations,
    )


def parse_current_server(server_json: str) -> Optional[Server]:
    d = json.loads(server_json)
    t = ServerType(d["server_type"])
    if t == ServerType.UNKNOWN:
        return None
    if t == ServerType.INSTITUTE_ACCESS:
        i = d["institute_access_server"]
        profiles = parse_profiles(i["profiles"])
        return InstituteServer(i["identifier"], i["display_name"], i["support_contacts"], profiles)
    if t == ServerType.SECURE_INTERNET:
        si = d["secure_internet_server"]
        return parse_secure_internet(si)
    if t == ServerType.CUSTOM:
        c = d["custom_server"]
        profiles = parse_profiles(c["profiles"])
        return Server(c["identifier"], c["display_name"], profiles)


def parse_profiles(profiles: dict) -> Profiles:
    returned = {}
    profile_map = profiles.get("map", {})
    for k, v in profile_map.items():
        # TODO: Default gateway
        returned[k] = Profile(k, v["display_name"], False)
    return Profiles(returned, profiles["current"])


def parse_required_transition(transition_json: str, get: Optional[Callable] = None) -> Tuple[int, Any]:
    transition = json.loads(transition_json)
    data_parsed = transition["data"]
    if get is not None:
        data_parsed = get(data_parsed)
    cookie = transition["cookie"]
    return cookie, data_parsed


def parse_servers(server_json: str) -> List[Server]:
    d = json.loads(server_json)

    institutes = d.get("institute_access_servers", [])
    servers: List[Server] = []
    for i in institutes:
        # TODO: delisted
        profiles = parse_profiles(i["profiles"])
        servers.append(
            InstituteServer(
                i["identifier"],
                i["display_name"],
                i.get("support_contacts", []),
                profiles,
            )
        )

    customs = d.get("custom_servers", [])
    for i in customs:
        profiles = parse_profiles(i["profiles"])
        servers.append(Server(i["identifier"], i["display_name"], profiles))

    si = d.get("secure_internet_server", None)
    if si is not None:
        # right now we only support one secure internet server
        si_parsed = parse_secure_internet(si)
        if si_parsed is not None:
            servers.append(si_parsed)
    return servers


class StatusImage(enum.Enum):
    # The value is the image filename.
    DEFAULT = "desktop-default.png"
    CONNECTING = "desktop-connecting.png"
    CONNECTED = "desktop-connected.png"
    NOT_CONNECTED = "desktop-not-connected.png"

    @property
    def path(self) -> str:
        return IMAGE_PREFIX + self.value


class ServerDatabase:
    def __init__(self, wrapper, enable_discovery=True) -> None:
        self.wrapper = wrapper
        self.enable_discovery = enable_discovery
        self.cached: List[Union[DiscoServer, DiscoOrganization]] = []

    @property
    def disco(self):
        if not self.enable_discovery:
            return []
        return self.cached

    def disco_update(self, search=""):
        if not self.enable_discovery:
            return
        disco_orgs = []
        if self.secure_internet is None:
            disco_orgs = parse_disco_organizations(self.wrapper.get_disco_organizations(search))
        disco_servers = parse_disco_servers(self.wrapper.get_disco_servers(search))
        ret_servers = disco_orgs
        ret_servers.extend(disco_servers)
        if search == "":
            self.cached = ret_servers
        return ret_servers

    def has(self, server) -> Optional[Server]:
        # The url attribute is always used as an identifier
        for s in self.configured:
            if server.identifier == s.identifier:
                return s
        return None

    @property
    def secure_internet(self) -> Optional[SecureInternetServer]:
        for server in self.configured:
            if isinstance(server, SecureInternetServer):
                return server
        return None

    @property
    def current(self):
        try:
            return parse_current_server(self.wrapper.get_current_server())
        except Exception as e:
            logger.debug(f"failed to get current server: {str(e)}")
            return None

    @property
    def configured(self):
        return parse_servers(self.wrapper.get_servers())

    def all(self):
        "Return all servers."
        return self.cached

    def search_predefined(self, query: str):
        "Return all servers that match the search query."
        return self.disco_update(query)

    def search_custom(self, query: str) -> Iterable[Server]:
        yield Server(query, query)  # type: ignore[arg-type]
