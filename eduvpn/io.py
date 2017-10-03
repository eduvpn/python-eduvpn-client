# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+
"""
Helper functions related to local IO
"""

import errno
import os
from os.path import expanduser
import logging

logger = logging.getLogger(__name__)


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
