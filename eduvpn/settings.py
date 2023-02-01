from pathlib import Path

from eduvpn.utils import get_config_dir, get_prefix

prefix = get_prefix()

CONFIG_PREFIX = (Path(get_config_dir()).expanduser() / "eduvpn").resolve()
LETSCONNECT_CONFIG_PREFIX = (
    Path(get_config_dir()).expanduser() / "letsconnect"
).resolve()
CONFIG_DIR_MODE = 0o700  # Same as the Go library

CLIENT_ID = "org.eduvpn.app.linux"
LETSCONNECT_CLIENT_ID = "org.letsconnect-vpn.app.linux"
LANGUAGE = "nl"
COUNTRY = "nl-NL"

COUNTRY_MAP = Path(prefix + "/share/eduvpn/country_codes.json")
FLAG_PREFIX = prefix + "/share/eduvpn/images/flags/png/"
IMAGE_PREFIX = prefix + "/share/eduvpn/images/"
LC_IMAGE_PREFIX = prefix + "/share/letsconnect/images/"


EDUVPN_ICON = prefix + "/share/icons/hicolor/128x128/apps/org.eduvpn.client.png"
EDUVPN_NAME = "eduVPN"
EDUVPN_LOGO = IMAGE_PREFIX + "edu-vpn-logo.png"
EDUVPN_LOGO_DARK = IMAGE_PREFIX + "edu-vpn-logo-dark.png"
LETS_CONNECT_LOGO = LC_IMAGE_PREFIX + "letsconnect.png"
SERVER_ILLUSTRATION = LC_IMAGE_PREFIX + "server-illustration.png"
LETS_CONNECT_ICON = (
    prefix + "/share/icons/hicolor/128x128/apps/org.letsconnect-vpn.client.png"
)
LETS_CONNECT_NAME = "Let's Connect!"
