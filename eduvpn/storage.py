"""
This module contains code to maintain a simple token storage in ~/.config/eduvpn/
"""
from typing import Optional, Tuple
import json
from pathlib import Path
from oauthlib.oauth2.rfc6749.tokens import OAuth2Token
from eduvpn.settings import CONFIG_PREFIX
from eduvpn.type import url
from eduvpn.utils import get_logger

logger = get_logger(__name__)
metadata_path = CONFIG_PREFIX / "metadata"


def read_storage() -> dict:
    """
    Read the storage from disk, returns an empty dict in case of failure.
    """
    if metadata_path.exists():
        try:
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(e)
    return {}


def write_storage(storage: dict) -> None:
    """
    Write the storage to disk.
    """
    try:
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with open(metadata_path, 'w') as f:
            return json.dump(storage, fp=f)
    except Exception as e:
        logger.error(e)


def get_entry(base_url: str) -> Optional[Tuple[OAuth2Token, url, url, url]]:
    """
    Return the metadata from storage
    """
    storage = read_storage()
    if base_url in storage:
        v = storage[base_url]
        return OAuth2Token(v['token']), v['api_base_uri'], v['token_endpoint'], v['authorization_endpoint']


def set_entry(
        base_url: str,
        token: OAuth2Token,
        api_base_uri: url,
        token_endpoint: url,
        authorization_endpoint: url,
) -> None:
    """
    Set a configuration profile in storage
    """
    storage = read_storage()
    storage[base_url] = {
        'token': token,
        'api_base_uri': api_base_uri,
        'token_endpoint': token_endpoint,
        'authorization_endpoint': authorization_endpoint,
    }
    write_storage(storage)


def get_eduvpn_uuid() -> Optional[str]:
    """
    Read the UUID of the last generated eduVPN Network Manager connection.
    """
    p = Path("~/.config/eduvpn/uuid").expanduser()
    if p.exists():
        return open(p, 'r').read()
    else:
        return None


def set_eduvpn_uuid(uuid: str):
    """
    Write the eduVPN network manager connection UUID to disk.
    """
    p = Path("~/.config/eduvpn/uuid").expanduser()
    with open(p, 'w') as f:
        f.write(uuid)


def clear_eduvpn_uuid():
    """
    Clear the eduVPN network manager connection UUID.
    """
    p = Path("~/.config/eduvpn/uuid").expanduser()
    p.unlink(missing_ok=True)


def write_config(config: str, private_key: str, certificate: str, target: Path):
    """
    Write the configuration to target.
    """
    with open(target, mode='w+t') as f:
        f.writelines(config)
        f.writelines(f"\n<key>\n{private_key}\n</key>\n")
        f.writelines(f"\n<cert>\n{certificate}\n</cert>\n")