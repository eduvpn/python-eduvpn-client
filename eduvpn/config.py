# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from configparser import ConfigParser
from os import path, makedirs

config_path = path.expanduser('~/.config/eduvpn')

secure_internet_uri = 'https://static.eduvpn.nl/disco/secure_internet.json'
institute_access_uri = 'https://static.eduvpn.nl/disco/institute_access.json'
secure_internet_uri_dev = 'https://static.eduvpn.nl/disco/secure_internet_dev.json'
institute_access_uri_dev = 'https://static.eduvpn.nl/disco/institute_access_dev.json'
verify_key = 'E5On0JTtyUVZmcWd+I/FXRm32nSq8R2ioyW7dcu/U88='

# TODO: support multiple languages
locale = "en-US"

metadata = ("api_base_uri", "profile_id", "display_name", "token", "connection_type", "authorization_type",
            "profile_display_name", "two_factor", "cert", "key", "config", "uuid", "icon_data")


icon_size = {'width': 105, 'height': 45}