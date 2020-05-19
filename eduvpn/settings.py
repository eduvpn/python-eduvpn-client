from typing import Tuple
from pathlib import Path
from eduvpn.utils import get_prefix

prefix = get_prefix()

CONFIG_PREFIX = Path("~/.config/eduvpn/").expanduser().resolve()

DISCO_URI = 'https://disco.eduvpn.org/'
ORGANISATION_URI = DISCO_URI + "organization_list.json"
SECURE_INTERNET_URI = DISCO_URI + "server_list_secure_internet.json"

SERVER_URI = DISCO_URI + "server_list.json"


CLIENT_ID = "org.eduvpn.app.linux"
SCOPE = ["config"]
CODE_CHALLENGE_METHOD = "S256"
LANGUAGE = 'nl'
COUNTRY = "nl-NL"
VERIFY_KEY = 'E5On0JTtyUVZmcWd+I/FXRm32nSq8R2ioyW7dcu/U88='

# format: base64(<signature_algorithm> || <key_id> || <public_key>)
Ed25519_PUBLIC_KEY = "RWSC3Lwn4f9mhG3XIwRUTEIqf7Ucu9+7/Rq+scUMxrjg5/kjskXKOJY/"

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
