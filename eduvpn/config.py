from configparser import ConfigParser
from os import path, makedirs

config_file = path.expanduser('~/.config/eduvpn/settings')

defaults = {
    'discovery_uri': 'https://static.eduvpn.nl/',
    'key': 'E5On0JTtyUVZmcWd+I/FXRm32nSq8R2ioyW7dcu/U88=',
}


def read():
    """
    Read config from filesystem
    """
    config = ConfigParser()
    config['eduvpn'] = defaults
    config.read(config_file)
    return config


def write(config):
    """
    Write config to filesystem
    """
    makedirs(path.basename(config_file))
    with open(config_file, 'w') as f:
        config.write(f)


