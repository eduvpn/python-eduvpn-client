import os
import subprocess
import sys
from os.path import expanduser
import logging

logger = logging.getLogger(__name__)


def write_and_open_ovpn(ovpn_text, filename='eduvpn.ovpn'):
    with open(filename, 'w') as f:
        f.write(ovpn_text)
    open_file('eduvpn.ovpn')


def write_cert(content, type_, short_instance_name):
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