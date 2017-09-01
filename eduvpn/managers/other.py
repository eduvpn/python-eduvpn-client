import json
import logging
import os

from eduvpn.config import config_path, metadata
from eduvpn.io import open_file, store_metadata, mkdir_p
from eduvpn.openvpn import format_like_ovpn
from eduvpn.util import make_unique_id


logger = logging.getLogger(__name__)


def list_providers():
    logger.info("generating list of profiles for non-Linux OS")
    if os.path.isdir(config_path):
        for p in (i for i in os.listdir(config_path) if i.endswith('.json')):
            try:
                metadata = json.load(open(os.path.join(config_path, p), 'r'))
                # these are absolutely vital
                for keyword in "uuid", "display_name":
                    if keyword not in metadata:
                        raise Exception("{} keyword missing in config file {}".format(keyword, p))
            except Exception as e:
                logger.error("problem parsing provider: {}".format(str(e)))
            else:
                yield metadata
    else:
        raise StopIteration


def store_provider(api_base_uri, profile_id, display_name, token, connection_type, authorization_type,
                   profile_display_name, two_factor, cert, key, config):
    logger.info("storing profile with name {} for non-Linux OS".format(display_name))
    ovpn_text = format_like_ovpn(config, cert, key)
    uuid = make_unique_id()
    mkdir_p(config_path)
    l = locals()
    store = {i: l[i] for i in metadata}
    store_metadata(os.path.join(config_path, uuid + '.json'), **store)
    with open(os.path.join(config_path, uuid + '.ovpn'), 'w') as f:
        f.write(ovpn_text)


def delete_provider(name):
    logger.info("deleting profile with name {} for non-Linux OS".format(name))
    try:
        os.remove(os.path.join(config_path, name + '.ovpn'))
    except Exception as e:
        logger.error("can't remove ovpn file: {}".format(str(e)))
    try:
        os.remove(os.path.join(config_path, name + '.json'))
    except Exception as e:
        logger.error("can't remove ovpn file: {}".format(str(e)))


def connect_provider(name):
    logger.info("connecting profile with name {} for non-Linux OS".format(name))
    open_file(os.path.join(config_path, name + '.ovpn'))


def status_provider(name):
    logger.info("requesting status profile with name {} for non-Linux OS".format(name))
    raise NotImplementedError
