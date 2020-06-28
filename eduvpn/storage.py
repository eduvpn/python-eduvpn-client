"""
This module contains code to maintain a simple token storage in ~/.config/eduvpn/
"""
from typing import Optional, Tuple, List, Callable
from os import PathLike
import json
from oauthlib.oauth2.rfc6749.tokens import OAuth2Token
from eduvpn.settings import CONFIG_PREFIX
from eduvpn.type import url
from eduvpn.utils import get_logger

logger = get_logger(__name__)

_tokens_path = CONFIG_PREFIX / "tokens"

def _read_tokens() -> dict:
    """
    Read the storage from disk, returns an empty dict in case of failure.
    """
    if _tokens_path.exists():
        try:
            with open(_tokens_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading tokens: {e}")
    return {}


def _write_tokens(storage: dict) -> None:
    """
    Write the storage to disk.
    """
    try:
        _tokens_path.parent.mkdir(parents=True, exist_ok=True)
        with open(_tokens_path, 'w') as f:
            return json.dump(storage, fp=f)
    except Exception as e:
        logger.error(f"Error writing tokens: {e}")


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


def get_token(auth_url: str) -> Optional[Tuple[OAuth2Token, str, str]]:
    """
    Return the metadata from storage
    """
    storage = _read_tokens()
    if auth_url in storage:
        v = storage[auth_url]
        return OAuth2Token(v['token']), v['token_endpoint'], v['authorization_endpoint']
    else:
        return None


def set_token(
        auth_url: str,
        token: OAuth2Token,
        token_endpoint: str,
        authorization_endpoint: str,
) -> None:
    """
    Set a configuration profile in storage
    """
    storage = _read_tokens()
    storage[auth_url] = {
        'token': token,
        'api_base_uri': auth_url,
        'token_endpoint': token_endpoint,
        'authorization_endpoint': authorization_endpoint,
    }
    _write_tokens(storage)


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


def get_api_url() -> Optional[str]:
    """
    Read the api_url of the current eduVPN Network Manager connection.
    """
    return _get_setting("api_url")


def set_api_url(api_url: str):
    """
    Write the eduVPN network manager active api_url to disk.
    """
    return _set_setting("api_url", api_url)


def get_profile() -> Optional[str]:
    """
    Read the profile of the current eduVPN Network Manager connection.
    """
    return _get_setting("profile")


def set_profile(profile: str):
    """
    Write the eduVPN network manager active profile to disk.
    """
    return _set_setting("profile", profile)


def write_config(config: str, private_key: str, certificate: str, target: PathLike):
    """
    Write the configuration to target.
    """
    print(f"Writing configuration to {target}")
    with open(target, mode='w+t') as f:
        f.writelines(config)
        f.writelines(f"\n<key>\n{private_key}\n</key>\n")
        f.writelines(f"\n<cert>\n{certificate}\n</cert>\n")


def get_storage(check=False) -> Tuple[str,
                                      str,
                                      str,
                                      str,
                                      Tuple[OAuth2Token, str, str]]:
    """

    Args:
        check: fail if item not found

    Returns:
        uuid, auth_url, api_url, token, profile
    """
    uuid = get_uuid()
    if not uuid and check:
        raise Exception("no eduVPN uuid stored (yet)")

    auth_url = get_auth_url()
    if not auth_url and check:
        raise Exception("no eduVPN auth_url stored (yet)")

    api_url = get_api_url()
    if not api_url and check:
        raise Exception("no eduVPN api_url stored (yet)")

    profile = get_profile()
    if not profile and check:
        raise Exception("no eduVPN profile stored (yet)")

    if auth_url:
        token = get_token(auth_url)
        if not token and check:
            raise Exception(f"no eduVPN token for {auth_url} stored (yet)")
    else:
        token = None

    return uuid, auth_url, api_url, profile, token  # type: ignore
