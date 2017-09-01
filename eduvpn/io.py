import errno
import json
import os
import subprocess
import sys
from os.path import expanduser
import logging

from eduvpn.config import config_path

logger = logging.getLogger(__name__)


def write_and_open_ovpn(ovpn_text, filename='eduvpn.ovpn'):
    """
    Write a OpenVPN config file and open it with the default OS assosiated file handler
    """
    with open(filename, 'w') as f:
        f.write(ovpn_text)
    open_file('eduvpn.ovpn')


def write_cert(content, type_, short_instance_name):
    """
    Write a certificate to the filesystem
    """
    home = expanduser("~")
    path = home + "/.cert/nm-openvpn/" + short_instance_name + "_" + type_ + ".pem"
    logger.info("writing {} file to {}".format(type_, path))
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, "w") as f:
        f.write(content)
    return path


def open_file(filepath):
    """
    Open file document with system associated program
    """
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filepath))
    elif os.name == 'nt':
        os.startfile(filepath)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', filepath))


def store_metadata(path, **metadata):
    logger.info("storing metadata in {}".format(path))
    serialized = json.dumps(metadata)
    mkdir_p(config_path)
    with open(path, 'w') as f:
        f.write(serialized)


def mkdir_p(path):
    logger.info("making sure config path {} exists".format(path))
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise