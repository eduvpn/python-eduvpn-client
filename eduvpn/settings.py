from typing import Tuple
from pathlib import Path
from eduvpn.utils import get_prefix

prefix = get_prefix()

CONFIG_PREFIX = Path("~/.config/eduvpn/").expanduser().resolve()

DISCO_URI = 'https://disco.eduvpn.org/'
ORGANISATION_URI = DISCO_URI + "organization_list.json"
SERVER_URI = DISCO_URI + "server_list.json"
HELP_URL = 'https://www.eduvpn.org'

CLIENT_ID = "org.eduvpn.app.linux"
SCOPE = ["config"]
CODE_CHALLENGE_METHOD = "S256"
LANGUAGE = 'nl'
COUNTRY = "nl-NL"

COUNTRY_MAP = Path(prefix + "/share/eduvpn/country_codes.json")
FLAG_PREFIX = prefix + "/share/images/flags/png/"
IMAGE_PREFIX = prefix + "/share/images/"


# format: base64(<signature_algorithm> || <key_id> || <public_key>)
VERIFY_KEYS = [
    "RWSC3Lwn4f9mhG3XIwRUTEIqf7Ucu9+7/Rq+scUMxrjg5/kjskXKOJY/",
    "RWRtBSX1alxyGX+Xn3LuZnWUT0w//B6EmTJvgaAxBMYzlQeI+jdrO6KF",
]
eduvpn_main_logo = prefix + "/share/icons/hicolor/128x128/apps/eduvpn-client.png"
eduvpn_name = "eduVPN"
lets_connect_main_logo = prefix + "/share/icons/hicolor/128x128/apps/lets-connect-client.png"
lets_connect_name = "Let's Connect!"


def get_brand(lets_connect: bool) -> Tuple[str, str]:
    """
    args:
        lets_connect: Set true if we are let's connect, otherwise eduVPN
    returns:
        logo, name
    """
    if lets_connect:
        return lets_connect_main_logo, lets_connect_name
    else:
        return eduvpn_main_logo, eduvpn_name
