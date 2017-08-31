import os
import logging
from eduvpn.io import open_file

from eduvpn.openvpn import format_like_ovpn

logger = logging.getLogger(__name__)

# only used if network manager is not available
config_store = os.path.expanduser('~/.config/eduvpn')


def list_providers():
    logger.info("generating list of profiles for non-Linux OS")
    if os.path.isdir(config_store):
        return [x[:-5] for x in os.listdir(config_store) if x.endswith('.ovpn')]
    else:
        return []


def store_provider(name, config, cert, key, token, profile_type, authorization_type, profile_display_name, profile_id, two_factor):
    logger.info("storing profile with name {} for non-Linux OS".format(name))
    ovpn_text = format_like_ovpn(config, cert, key)
    with open(os.path.join(config_store, name + '.ovpn'), 'w') as f:
        f.write(ovpn_text)


def delete_provider(name):
    logger.info("deleting profile with name {} for non-Linux OS".format(name))
    os.remove(os.path.join(config_store, name + '.ovpn'))


def connect_provider(name):
    logger.info("connecting profile with name {} for non-Linux OS".format(name))
    open_file(os.path.join(config_store, name + '.ovpn'))


def status_provider(name):
    logger.info("requesting status profile with name {} for non-Linux OS".format(name))
    raise NotImplementedError
