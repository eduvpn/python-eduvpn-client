# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

"""
Helper functions related to local IO
"""
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
    Write a OpenVPN config file and open it with the default OS associated file handler

    args:
        ovpn_text (str): content of OpenVPN config file
        filename (str): filename for OpenVPN config file
    """
    with open(filename, 'w') as f:
        f.write(ovpn_text)
    open_file('eduvpn.ovpn')


def write_cert(content, type_, unique_name):
    """
    Write a certificate to the filesystem

    args:
        content (str): content of certificate file
        type (str): type of certificate file
        unique_name (str): description of file

    returns:
        str: full path to certificate file
    """
    home = expanduser("~")
    path = home + "/.cert/nm-openvpn/" + unique_name + "_" + type_ + ".pem"
    logger.info("writing {} file to {}".format(type_, path))
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, "w") as f:
        f.write(content)
    os.chmod(path, 0o600)
    return path


def open_file(filepath):
    """
    Open file document with system associated program

    args:
        filepath (str): path to file to open
    """
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filepath))
    elif os.name == 'nt':
        os.startfile(filepath)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', filepath))


def store_metadata(path, **metadata):
    """
    Store dictionary as JSON encoded string in a file

    args:
        path (str): path of file
        metadata (dict): metadata to store
    """
    logger.info("storing metadata in {}".format(path))
    serialized = json.dumps(metadata)
    mkdir_p(config_path)
    with open(path, 'w') as f:
        f.write(serialized)


def get_metadata(uuid):
    try:
        metadata_path = os.path.join(config_path, uuid + '.json')
        return json.load(open(metadata_path, 'r'))
    except IOError as e:
        logger.error("can't open metdata file for {}: {}".format(uuid, str(e)))
        return {'uuid': uuid, 'display_name': uuid, 'icon_data': None, 'connection_type': 'unknown'}


def mkdir_p(path):
    """
    Create a folder with all its parents, like mkdir -p

    args:
        path (str): path of directory to create
    """
    logger.info("making sure config path {} exists".format(path))
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise