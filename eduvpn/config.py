# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from os.path import expanduser

config_path = expanduser('~/.config/eduvpn')

secure_internet_uri = 'https://static.eduvpn.nl/disco/secure_internet.json'
institute_access_uri = 'https://static.eduvpn.nl/disco/institute_access.json'
secure_internet_uri_dev = 'https://static.eduvpn.nl/disco/secure_internet_dev.json'
institute_access_uri_dev = 'https://static.eduvpn.nl/disco/institute_access_dev.json'

verify_key = 'E5On0JTtyUVZmcWd+I/FXRm32nSq8R2ioyW7dcu/U88='

locale = "en-US"

icon_size = {'width': 105, 'height': 45}
