import json
import os
import locale
from gettext import install
from typing import Union, Dict
from eduvpn.settings import COUNTRY, LANGUAGE, COUNTRY_MAP
from eduvpn.utils import get_logger

logger = get_logger(__name__)

country_mapping = None


def init(lets_connect: bool, prefix: str):
    """
    Init locale and gettext, returns text domain
    """
    domain = 'LetConnect' if lets_connect else 'eduVPN'
    directory = os.path.join(prefix, 'share/locale')

    locale.setlocale(locale.LC_ALL, '')
    locale.bindtextdomain(domain, directory)  # type: ignore
    locale.textdomain(domain)  # type: ignore
    install(domain, names=('gettext', 'ngettext'), localedir=directory)

    return domain


def country() -> str:
    try:
        return locale.getlocale()[0].replace('_', '-')
    except Exception:
        return COUNTRY


def language() -> str:
    try:
        return locale.getlocale()[0].split('_')[0]
    except Exception:
        return LANGUAGE


def extract_translation(d: Union[str, Dict[str, str]]):
    if isinstance(d, dict):
        for m in [country(), language(), 'en-US', 'en']:
            try:
                return d[m]
            except KeyError:
                continue
        return list(d.values())[0]  # otherwise just return first in list
    else:
        return d


def retrieve_country_name(country_code: str) -> str:
    country_map = _read_country_map()
    loc = locale.getlocale()
    if loc[0] is None:
        prefix = 'en'
    else:
        prefix = loc[0][:2]
    if country_code in country_map:
        code = country_map[country_code]
        if prefix in code:
            return code[prefix]
    return country_code

# def get_token(auth_url: str) -> Optional[Tuple[OAuth2Token, str, str]]:
#     """
#     Return the metadata from storage
#     """
#     storage = _read_tokens()
#     if auth_url in storage:
#         v = storage[auth_url]
#         return OAuth2Token(v['token']), v['token_endpoint'], v['authorization_endpoint']
#     else:
#         return None


def _read_country_map() -> dict:
    """
    Read the storage from disk, returns an empty dict in case of failure.
    """
    global country_mapping

    if country_mapping is not None:
        return country_mapping

    if COUNTRY_MAP.exists():
        try:
            with open(COUNTRY_MAP, 'r') as f:
                country_mapping = json.load(f)
                return country_mapping
        except Exception as e:
            logger.error(f"Error reading country map: {e}")
    return {}
