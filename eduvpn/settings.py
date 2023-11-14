from pathlib import Path

from eduvpn.utils import get_prefix

prefix = get_prefix()

CONFIG_DIR_MODE = 0o700  # Same as the Go library

LANGUAGE = "nl"
COUNTRY = "nl-NL"

COUNTRY_MAP = Path(prefix + "/share/eduvpn/country_codes.json")
IMAGE_PREFIX_COMMON = prefix + "/share/eduvpn/images/common/"
