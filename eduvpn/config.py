# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from os import path

config_path = path.expanduser('~/.config/eduvpn')  # type : str
providers_path = config_path  # type : str
others_path = path.join(config_path, 'other')  # type : str

secure_internet_uri = 'https://static.eduvpn.nl/disco/secure_internet.json'  # type : str
institute_access_uri = 'https://static.eduvpn.nl/disco/institute_access.json'  # type : str
verify_key = 'E5On0JTtyUVZmcWd+I/FXRm32nSq8R2ioyW7dcu/U88='  # type : str

secure_internet_uri_dev = 'https://static.eduvpn.nl/disco/secure_internet_dev.json'  # type : str
institute_access_uri_dev = 'https://static.eduvpn.nl/disco/institute_access_dev.json'  # type : str
verify_key_dev = ' zzls4TZTXHEyV3yxaxag1DZw3tSpIdBoaaOjUGH/Rwg=.'  # type : str


locale = "en-US"  # type : str

icon_size = {'width': 105, 'height': 45}  # type : Any
