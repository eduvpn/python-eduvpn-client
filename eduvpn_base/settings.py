from eduvpn_base.utils import get_base_prefix

prefix = get_base_prefix()

CONFIG_DIR_MODE = 0o700  # Same as the Go library

LANGUAGE = "nl"
COUNTRY = "nl-NL"

IMAGE_PREFIX_COMMON = prefix + "/share/eduvpn-base/images/"
