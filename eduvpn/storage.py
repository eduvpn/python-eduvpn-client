"""
This module contains code to maintain a simple metadata storage in ~/.config/eduvpn/
"""
from typing import Optional, Tuple, List
from enum import Enum
from os import PathLike
from datetime import datetime
import json
from oauthlib.oauth2.rfc6749.tokens import OAuth2Token
import eduvpn
from eduvpn.settings import CONFIG_PREFIX, CONFIG_DIR_MODE
from eduvpn.ovpn import Ovpn
from eduvpn.utils import get_logger

logger = get_logger(__name__)

_metadata_path = CONFIG_PREFIX / "metadata.json"


class ConnectionType(str, Enum):
    INSTITUTE = "INSTITUTE",
    SECURE = "SECURE",
    OTHER = "OTHER"


def is_config_dir_permissions_correct() -> bool:
    return CONFIG_PREFIX.stat().st_mode & 0o777 == CONFIG_DIR_MODE


def check_config_dir_permissions():
    if not is_config_dir_permissions_correct():
        logger.warning(
            f"The permissions for the config dir ({CONFIG_PREFIX}) "
            f"are not as expected, it may be world readable!")


def ensure_config_dir_exists():
    """
    Ensure the config directory exists with the correct permissions.
    """
    CONFIG_PREFIX.mkdir(parents=True, exist_ok=True, mode=CONFIG_DIR_MODE)
    check_config_dir_permissions()


def get_all_metadatas() -> dict:
    """
    Read the metadata from disk, returns an empty dict in case of failure.
    """
    if _metadata_path.exists():
        try:
            with open(_metadata_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading metadatas {_metadata_path}: {e}")
    return {}


def _write_metadatas(storage: dict) -> None:
    """
    Write the storage to disk.
    """
    try:
        dump = json.dumps(storage)
        ensure_config_dir_exists()
        with open(_metadata_path, 'w') as f:
            f.write(dump)
    except Exception as e:
        logger.error(f"Error writing metadatas: {e}")


def _get_setting(what: str) -> Optional[str]:
    p = (CONFIG_PREFIX / what).expanduser()
    if p.exists():
        return open(p, 'r').read().strip()
    else:
        return None


def _set_setting(what: str, value: str):
    p = (CONFIG_PREFIX / what).expanduser()
    ensure_config_dir_exists()
    with open(p, 'w') as f:
        f.write(value)


Metadata = Tuple[OAuth2Token, str, str, str, str, str, str, str, str, Optional[datetime], Optional[datetime]]


def serialize_datetime(dt: datetime) -> str:
    return dt.isoformat()


def deserialize_datetime(value: str) -> datetime:
    if hasattr(datetime, 'fromisoformat'):
        return datetime.fromisoformat(value)
    else:
        # Python < 3.7.
        format = '%Y-%m-%dT%H:%M:%S'
        if '.' in value:
            format += '.%f'
        if '+' in value or value.count('-') > 2:
            format += '%z'
        return datetime.strptime(value, format)


def get_current_metadata(auth_url: str) -> Optional[Metadata]:
    """
    Return the metadata for current connection from storage.
    """
    storage = get_all_metadatas()
    if auth_url in storage:
        v = storage[auth_url]
        created = v.get('certificate_created')
        if created is not None:
            created = deserialize_datetime(created)
        expiry = v.get('certificate_expiry')
        if expiry is not None:
            expiry = deserialize_datetime(expiry)
        return (
            OAuth2Token(v['token']),
            v['token_endpoint'],
            v['authorization_endpoint'],
            v['api_url'],
            v['display_name'],
            v['support_contact'],
            v['profile_id'],
            v['con_type'],
            v['country_id'],
            created,
            expiry,
        )
    else:
        return None


def get_current_validity(auth_url: str) -> Optional['eduvpn.session.Validity']:
    metadata = get_current_metadata(auth_url)
    if metadata is None:
        return None
    *_, start, end = metadata
    if start is None or end is None:
        return None
    from .session import Validity
    return Validity(start, end)


def set_metadata(
        auth_url: str,
        token: OAuth2Token,
        token_endpoint: str,
        authorization_endpoint: str,
        api_url: str,
        display_name: str,
        support_contact: List[str],
        profile_id: str,
        con_type: str,
        country_id: Optional[str],
        certificate_created: Optional[datetime] = None,
        certificate_expiry: Optional[datetime] = None,
) -> None:
    """
    Set a configuration profile in storage
    """
    storage = get_all_metadatas()
    if certificate_created is None:
        created_str = None
    else:
        created_str = serialize_datetime(certificate_created)
    if certificate_expiry is None:
        expiry_str = None
    else:
        expiry_str = serialize_datetime(certificate_expiry)
    storage[auth_url] = {
        'token': token,
        'api_base_uri': auth_url,
        'token_endpoint': token_endpoint,
        'authorization_endpoint': authorization_endpoint,
        'api_url': api_url,
        'display_name': display_name,
        'support_contact': support_contact,
        'profile_id': profile_id,
        'con_type': con_type,
        'country_id': country_id,
        'certificate_created': created_str,
        'certificate_expiry': expiry_str,
    }
    _write_metadatas(storage)


def del_metadata(auth_url: str) -> None:
    """
    Remove a metadata from the metadata storage
    """
    storage = get_all_metadatas()
    if auth_url in storage:
        storage.pop(auth_url)
        _write_metadatas(storage)


def get_uuid() -> Optional[str]:
    """
    Read the UUID of the last generated eduVPN Network Manager connection.
    """
    return _get_setting("uuid")


def set_uuid(uuid: str):
    """
    Write the eduVPN network manager connection UUID to disk.
    """
    return _set_setting("uuid", uuid)


def get_auth_url() -> Optional[str]:
    """
    Read the auth_url of the current eduVPN Network Manager connection.
    """
    return _get_setting("auth_url")


def set_auth_url(auth_url: str):
    """
    Write the eduVPN network manager active auth_url to disk.
    """
    return _set_setting("auth_url", auth_url)


def write_config(config: str, private_key: str, certificate: str, target: PathLike):
    """
    Write the configuration to target.
    """
    ovpn = Ovpn.parse(config)
    write_ovpn(ovpn, private_key, certificate, target)


def write_ovpn(ovpn: Ovpn, private_key: str, certificate: str, target: PathLike):
    """
    Write the OVPN configuration file to target.
    """
    logger.info(f"Writing configuration to {target}")
    with open(target, mode='w+t') as f:
        ovpn.write(f)
        f.writelines(f"\n<key>\n{private_key}\n</key>\n")
        f.writelines(f"\n<cert>\n{certificate}\n</cert>\n")


def get_storage(check=False) -> Tuple[Optional[str], Optional[str], Optional[Metadata]]:
    """

    Args:
        check: fail if item not found

    Returns:
        uuid, auth_url, api_url, metadata, profile
    """
    uuid = get_uuid()
    if not uuid and check:
        raise Exception("no eduVPN uuid stored (yet)")

    auth_url = get_auth_url()
    if not auth_url and check:
        raise Exception("no eduVPN auth_url stored (yet)")

    if auth_url:
        metadata = get_current_metadata(auth_url)
        if not metadata and check:
            raise Exception(f"no eduVPN metadata for {auth_url} stored (yet)")
    else:
        metadata = None

    return uuid, auth_url, metadata


def update_token(token: OAuth2Token):
    """
    In case of a token refresh only the new token needs to be written to storage.
    """
    auth_url = get_auth_url()
    logger.info(f"updating token for {auth_url}")
    metadatas = get_all_metadatas()
    if 'auth_url' in metadatas:
        metadatas[auth_url]['token'] = token
        _write_metadatas(metadatas)
