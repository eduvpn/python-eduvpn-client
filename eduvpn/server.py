from typing import Union, Optional, Iterable, List, Dict
from enum import Enum
import logging
import os
from urllib.parse import quote_plus
from requests_oauthlib import OAuth2Session
import nacl.exceptions
import eduvpn
from eduvpn import remote
from eduvpn import storage
from eduvpn import crypto
from eduvpn.i18n import extract_translation, retrieve_country_name
from eduvpn.settings import SERVER_URI, ORGANISATION_URI, FLAG_PREFIX, MAX_HTTP_RETRIES, MAX_HTTP_TIMEOUT
from eduvpn.utils import custom_server_oauth_url, add_retry_adapter


logger = logging.getLogger(__name__)
TranslatedStr = Union[str, Dict[str, str]]


class Protocol(Enum):
    OPENVPN = 'openvpn'
    WIREGUARD = 'wireguard'

    @property
    def is_supported(self) -> bool:
        if self.value == 'wireguard':
            from .nm import is_wireguard_supported
            return is_wireguard_supported()
        else:
            return True

    def supports_config(self, config: 'eduvpn.config.Configuration') -> bool:
        if config.force_tcp:
            if self is Protocol.WIREGUARD:
                # WireGuard cannot be forced over TCP.
                return False
        return True

    @property
    def config_type(self) -> str:
        return protocol_connection_config_mime_type[self]

    @classmethod
    def get_by_config_type(cls, config_type: str) -> 'Protocol':
        return connection_config_mime_type_protocol[config_type]


protocol_connection_config_mime_type = {
    # NOTE: Each protocol must have a unique type
    #       because the server ultimately decides on
    #       the protocol and the client uses the type
    #       to determine which one was actually chosen.
    Protocol.OPENVPN: 'application/x-openvpn-profile',
    Protocol.WIREGUARD: 'application/x-wireguard-profile',
}

connection_config_mime_type_protocol = dict(
    (proto, config_type)
    for (config_type, proto)
    in protocol_connection_config_mime_type.items()
)


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

    @property
    def oauth_login_url(self):
        return self.base_url

    def authentication_url(self, oauth_url: str) -> str:
        return oauth_url


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

    @property
    def oauth_login_url(self):
        return self.base_url

    def authentication_url(
        self,
        organisation: 'OrganisationServer',
        oauth_url: str,
    ) -> str:
        if self.authentication_url_template is None:
            return oauth_url
        return (self.authentication_url_template
                .replace('@ORG_ID@', quote_plus(organisation.org_id))
                .replace('@RETURN_TO@', quote_plus(oauth_url)))


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

    @property
    def oauth_login_url(self):
        return custom_server_oauth_url(self.address)

    def authentication_url(self, oauth_url: str) -> str:
        return oauth_url


class ServerInfo:
    def __init__(self, api_endpoint, token_endpoint, authorization_endpoint):
        self.api_endpoint = api_endpoint
        self.token_endpoint = token_endpoint
        self.authorization_endpoint = authorization_endpoint

    def api_call_endpoint(self, call: str) -> str:
        return self.api_endpoint + '/' + call

    def list_profiles(self, session: OAuth2Session) -> Iterable['Profile']:
        # https://github.com/eduvpn/documentation/blob/v3/API.md#info
        response = session.get(self.api_call_endpoint('info'))
        remote.check_response(response)
        profiles = response.json()['info']['profile_list']
        return [Profile(**data) for data in profiles]

    def get_profile(self, session: OAuth2Session, id: str) -> Optional['Profile']:
        profiles = [profile for profile in self.list_profiles(session)
                    if profile.id == id]
        if len(profiles) == 1:
            return profiles[0]
        else:
            return None

    def connect(self, app, profile: 'Profile', session: OAuth2Session) -> 'eduvpn.connection.Connection':
        # https://github.com/eduvpn/documentation/blob/v3/API.md#connect
        accept_types = ', '.join(
            proto.config_type
            for proto in profile.vpn_proto_list
            if proto.is_supported and proto.supports_config(app.config)
        )
        data = dict(profile_id=profile.id)

        keypair = None
        if Protocol.WIREGUARD in profile.vpn_proto_list:
            keypair = crypto.generate_wireguard_keys()
            data['public_key'] = keypair.public

        session = add_retry_adapter(session, MAX_HTTP_RETRIES)
        endpoint = self.api_call_endpoint('connect')
        try:
            response = session.post(
                endpoint,
                data=data,
                headers={'Accept': accept_types},
                timeout=MAX_HTTP_TIMEOUT)
        except Exception as e:
            msg = f"Got exception {e} requesting {endpoint}"
            logger.debug(msg)
            raise
        remote.check_response(response)
        from .connection import Connection
        connection = Connection.parse(response)
        if keypair:
            connection.set_secret_key(keypair.secret)
        return connection

    def disconnect(self, session: OAuth2Session):
        # https://github.com/eduvpn/documentation/blob/v3/API.md#disconnect
        # We allow a timeout for 1 second here
        try:
            session.post(self.api_call_endpoint('disconnect'), timeout=1)
        except:  # NOQA: ignore
            # NOTE: No need to check the response as,
            #       according to the API specification,
            #       this is a "best-effort" call.
            pass


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
        self.vpn_proto_list = frozenset(map(Protocol, vpn_proto_list))

    @property
    def id(self):
        return self.profile_id

    def __str__(self):
        return extract_translation(self.display_name)

    def __repr__(self):
        return f"<Profile id={self.id!r} {str(self)!r}>"

    @property
    def has_supported_protocol(self) -> bool:
        return any(proto.is_supported for proto in self.vpn_proto_list)

    def supports_config(self, config: 'eduvpn.config.Configuration') -> bool:
        return any(proto.supports_config(config) for proto in self.vpn_proto_list)

    @property
    def use_as_default_gateway(self) -> bool:
        if self.default_gateway is None:
            return False
        else:
            return self.default_gateway


class SecureInternetLocation:
    def __init__(self,
                 server: OrganisationServer,
                 location: SecureInternetServer):
        self.server = server
        self.location = location

    def __str__(self):
        return self.location.country_name

    def __repr__(self):
        return f"<SecureInternetLocation {self.server!r} {self.location!r}>"

    @property
    def image_path(self) -> Optional[str]:
        return self.location.flag_path

    @property
    def support_contact(self) -> List[str]:
        return self.location.support_contact

    @property
    def oauth_login_url(self):
        assert self.server.oauth_login_url == self.location.oauth_login_url
        return self.server.oauth_login_url

    def authentication_url(self, oauth_url: str) -> str:
        return self.location.authentication_url(self.server, oauth_url)


# typing aliases
PredefinedServer = Union[
    InstituteAccessServer,
    OrganisationServer,
    CustomServer,
]
ConfiguredServer = Union[
    InstituteAccessServer,
    SecureInternetLocation,
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


class ServerSignatureError(Exception):
    def __init__(self, uri: str):
        self.uri = uri


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
        try:
            server_list = remote.list_servers(SERVER_URI)
        except nacl.exceptions.BadSignatureError:
            raise ServerSignatureError(SERVER_URI)
        try:
            organisation_list = remote.list_organisations(ORGANISATION_URI)
        except nacl.exceptions.BadSignatureError:
            raise ServerSignatureError(ORGANISATION_URI)
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

    def all_configured(self) -> Iterable[ConfiguredServer]:
        "Return all configured servers."
        for key, data in storage.get_all_metadatas().items():
            if data['con_type'] == storage.ConnectionType.INSTITUTE:
                yield InstituteAccessServer(
                    base_url=data['api_base_uri'],
                    display_name=data['display_name'],
                    support_contact=data['support_contact'],
                    keyword_list=None,  # TODO
                )
            elif data['con_type'] == storage.ConnectionType.SECURE:
                secure_internet = SecureInternetServer(
                    base_url=data['api_base_uri'],
                    public_key_list=[],  # TODO
                    country_code=data['country_id'],
                    support_contact=data['support_contact'],
                    authentication_url_template=None,  # TODO
                )
                organisation = OrganisationServer(
                    secure_internet_home=data['api_base_uri'],
                    display_name=data['display_name'],
                    org_id='',  # TODO
                    keyword_list={},
                )
                yield SecureInternetLocation(organisation, secure_internet)
            elif data['con_type'] == storage.ConnectionType.OTHER:
                yield CustomServer(data['api_base_uri'])
            else:
                raise ValueError(data)

    def get_single_configured(self) -> Optional[ConfiguredServer]:
        auth_url = storage.get_auth_url()
        if auth_url is not None:
            for server in self.all_configured():
                if server.oauth_login_url == auth_url:
                    return server
        return None

    def all(self) -> Iterable[PredefinedServer]:
        "Return all servers."
        return iter(self.servers)

    def get_secure_internet_server(self, base_url: str) -> Optional[SecureInternetServer]:
        for server in self.all():
            if isinstance(server, SecureInternetServer) and server.base_url == base_url:
                return server
        return None

    def search(self, query: str) -> Iterable[PredefinedServer]:
        "Return all servers that match the search query."
        if query:
            for server in self.all():
                if is_search_match(server, query):
                    yield server
        else:
            yield from self.all()

    def get_server_info(self, server) -> ServerInfo:
        base_uri = server.oauth_login_url
        if not base_uri.endswith('/'):
            base_uri += '/'
        uri = base_uri + '.well-known/vpn-user-portal'
        json_data = remote.request(uri)
        info = json_data['api']['http://eduvpn.org/api#3']
        return ServerInfo(**info)
