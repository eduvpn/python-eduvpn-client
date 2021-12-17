from pathlib import Path
from eduvpn.utils import get_prefix, get_config_dir

prefix = get_prefix()

CONFIG_PREFIX = (Path(get_config_dir()).expanduser() / "eduvpn").resolve()
CONFIG_DIR_MODE = 0o700
CONFIG_JSON_PREFIX = "2.0_"

DISCO_URI = 'https://disco.eduvpn.org/v2/'
ORGANISATION_URI = DISCO_URI + "organization_list.json"
SERVER_URI = DISCO_URI + "server_list.json"
HELP_URL = 'https://www.eduvpn.org'

CLIENT_ID = "org.eduvpn.app.linux"
SCOPE = ["config"]
CODE_CHALLENGE_METHOD = "S256"
LANGUAGE = 'nl'
COUNTRY = "nl-NL"

COUNTRY_MAP = Path(prefix + "/share/eduvpn/country_codes.json")
FLAG_PREFIX = prefix + "/share/eduvpn/images/flags/png/"
IMAGE_PREFIX = prefix + "/share/eduvpn/images/"
LC_IMAGE_PREFIX = prefix + "/share/letsconnect/images/"


# format: base64(<signature_algorithm> || <key_id> || <public_key>)
VERIFY_KEYS = [
    "RWRtBSX1alxyGX+Xn3LuZnWUT0w//B6EmTJvgaAxBMYzlQeI+jdrO6KF",
    "RWQKqtqvd0R7rUDp0rWzbtYPA3towPWcLDCl7eY9pBMMI/ohCmrS0WiM"
]
EDUVPN_ICON = prefix + "/share/icons/hicolor/128x128/apps/org.eduvpn.client.png"
EDUVPN_NAME = "eduVPN"
LETS_CONNECT_LOGO = LC_IMAGE_PREFIX + "letsconnect.png"
SERVER_ILLUSTRATION = LC_IMAGE_PREFIX + "server-illustration.png"
LETS_CONNECT_ICON = prefix + "/share/icons/hicolor/128x128/apps/org.letsconnect-vpn.client.png"
LETS_CONNECT_NAME = "Let's Connect!"

SESSION_PENDING_EXPIRY_MINUTES = 15
SESSION_PENDING_EXPIRY_FRACTION = 0.8
