"""
This module contains code to maintain a simple metadata storage in ~/.config/eduvpn/
"""
from typing import Optional, Tuple
from os import PathLike
import json
from oauthlib.oauth2.rfc6749.tokens import OAuth2Token
from eduvpn.settings import CONFIG_PREFIX
from eduvpn.utils import get_logger

logger = get_logger(__name__)

_metadata_path = CONFIG_PREFIX / "metadata.json"


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
        _metadata_path.parent.mkdir(parents=True, exist_ok=True)
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
    with open(p, 'w') as f:
        f.write(value)


Metadata = Tuple[OAuth2Token, str, str, str, str, str, str]


def get_current_metadata(auth_url: str) -> Optional[Metadata]:
    """
    Return the metadata for current connection from storage.
    """
    storage = get_all_metadatas()
    if auth_url in storage:
        v = storage[auth_url]
        return (
            OAuth2Token(v['token']),
            v['token_endpoint'],
            v['authorization_endpoint'],
            v['api_url'],
            v['display_name'],
            v['support_contact'],
            v['profile_id'],
        )
    else:
        return None


def set_metadata(
        auth_url: str,
        token: OAuth2Token,
        token_endpoint: str,
        authorization_endpoint: str,
        api_url: str,
        display_name: str,
        support_contact: str,
        profile_id: str,
) -> None:
    """
    Set a configuration profile in storage
    """
    storage = get_all_metadatas()
    storage[auth_url] = {
        'token': token,
        'api_base_uri': auth_url,
        'token_endpoint': token_endpoint,
        'authorization_endpoint': authorization_endpoint,
        'api_url': api_url,
        'display_name': display_name,
        'support_contact': support_contact,
        'profile_id': profile_id,

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
    logger.info(f"Writing configuration to {target}")
    with open(target, mode='w+t') as f:
        f.writelines(config)
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
