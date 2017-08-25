from configparser import ConfigParser
from os import path, makedirs

config_file = path.expanduser('~/.config/eduvpn/settings')

defaults = {
    'discovery_uri': 'https://static.eduvpn.nl/',
    'verify_key': 'E5On0JTtyUVZmcWd+I/FXRm32nSq8R2ioyW7dcu/U88=',
}


secure_internet_uri = 'https://static.eduvpn.nl/disco/secure_internet.json'
institute_access_uri = 'https://static.eduvpn.nl/disco/institute_access.json'
secure_internet_uri_dev = 'https://static.eduvpn.nl/disco/secure_internet_dev.json'
institute_access_uri_dev = 'https://static.eduvpn.nl/disco/institute_access_dev.json'
verify_key = 'E5On0JTtyUVZmcWd+I/FXRm32nSq8R2ioyW7dcu/U88='

# TODO: support multiple languages
locale = "us-US"


def read():
    """
    Read config from filesystem
    """
    config = ConfigParser()
    config['eduvpn'] = defaults
    config.read(config_file)
    return config['eduvpn']


def write(config):
    """
    Write config to filesystem
    """
    makedirs(path.basename(config_file))
    with open(config_file, 'w') as f:
        config.write(f)


