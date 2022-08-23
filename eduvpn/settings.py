from pathlib import Path

from eduvpn.utils import get_config_dir, get_prefix

prefix = get_prefix()

CONFIG_PREFIX = (Path(get_config_dir()).expanduser() / "eduvpn").resolve()
LETSCONNECT_CONFIG_PREFIX = (
    Path(get_config_dir()).expanduser() / "letsconnect"
).resolve()
CONFIG_DIR_MODE = 0o700  # Same as the Go library

HELP_URL = "https://www.eduvpn.org"

CLIENT_ID = "org.eduvpn.app.linux"
LETSCONNECT_CLIENT_ID = "org.letsconnect-vpn.app.linux"
SCOPE = ["config"]
CODE_CHALLENGE_METHOD = "S256"
LANGUAGE = "nl"
COUNTRY = "nl-NL"
REQUEST_TIMEOUT = 2

COUNTRY_MAP = Path(prefix + "/share/eduvpn/country_codes.json")
FLAG_PREFIX = prefix + "/share/eduvpn/images/flags/png/"
IMAGE_PREFIX = prefix + "/share/eduvpn/images/"
LC_IMAGE_PREFIX = prefix + "/share/letsconnect/images/"


EDUVPN_ICON = prefix + "/share/icons/hicolor/128x128/apps/org.eduvpn.client.png"
EDUVPN_NAME = "eduVPN"
LETS_CONNECT_LOGO = LC_IMAGE_PREFIX + "letsconnect.png"
SERVER_ILLUSTRATION = LC_IMAGE_PREFIX + "server-illustration.png"
LETS_CONNECT_ICON = (
    prefix + "/share/icons/hicolor/128x128/apps/org.letsconnect-vpn.client.png"
)
LETS_CONNECT_NAME = "Let's Connect!"
