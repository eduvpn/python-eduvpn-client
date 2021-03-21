import json
import os
import locale
import re
from gettext import install
from inspect import currentframe
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
    install(domain, localedir=directory)

    return domain


def f(fstring: str) -> str:
    """
    Implements late f-string evaluation to make them translatable.
    Includes support for translating pluralizable placeholders like {number:singular|plural}.
    usage: f(_('Hey, {username}')) or
           f(_('Count {number:entry|entries}'))

    https://stackoverflow.com/questions/49797658/how-to-use-gettext-with-python-3-6-f-strings
    https://www.transifex.com/amebis/teams/83968/discussions/
    """
    frame = currentframe().f_back  # type: ignore
    if frame is None:
        return fstring
    while True:
        match = re.match(r'(.*)\{(?:(.*?):(.*?))\}(.*)', fstring)
        if match is None:
            break

        variant = match.group(3).split('|')

        n = 0
        if match.group(2) in frame.f_locals:
            n = int(frame.f_locals[match.group(2)])
        elif match.group(2) in frame.f_globals:
            n = int(frame.f_globals[match.group(2)])

        # Examples
        # English:   {seconds:second|seconds} (singular|plural)
        # German:    {seconds:Sekunde|Sekunden} (singular|plural)
        # Slovenian: {seconds:sekunda|sekundi|sekunde|sekund} (singular|dual|plural 3-4|plural >=5)

        unit = variant[0]
        if (n == 0 or n >= 2) and len(variant) > 1:
            unit = variant[1]
        if n >= 3 and n <= 4 and len(variant) > 2:
            unit = variant[2]
        if n >= 5 and len(variant) > 3:
            unit = variant[3]

        fstring = match.group(1) + "{" + match.group(2) + "} " + unit + match.group(4)

    return eval(f"f'{fstring}'", frame.f_locals, frame.f_globals)


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
