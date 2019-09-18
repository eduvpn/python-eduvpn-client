# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+
import logging
import threading
import uuid
import sys
import os
from os import path
from future.standard_library import install_aliases
from repoze.lru import lru_cache
import gi
from gi.repository import Gtk, GdkPixbuf, GLib
from eduvpn.config import icon_size
from eduvpn.metadata import Metadata
from eduvpn.exceptions import EduvpnException
from typing import Any, Optional, Tuple

install_aliases()
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
logger = logging.getLogger(__name__)


def make_unique_id():
    # type: () -> str
    return str(uuid.uuid4())


# ui thread
def error_helper(parent, msg_big, msg_small):  # type: (Gtk.GObject, str, str) -> None
    """
    Shows a GTK error message dialog.

    args:
        parent (GObject): A GTK Window
        msg_big (str): the big string
        msg_small (str): the small string
    """
    logger.error("{}: {}".format(msg_big, msg_small))
    error_dialog = Gtk.MessageDialog(parent, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, str(msg_big))
    error_dialog.format_secondary_text(str(msg_small))
    error_dialog.run()
    error_dialog.hide()


def thread_helper(func):  # type: (Any) -> threading.Thread
    """
    Runs a function in a thread

    args:
        func (lambda): a function to run in the background
    """
    thread = threading.Thread(target=func)
    thread.daemon = True
    thread.start()
    return thread


def pil2pixbuf(img):  # type: (Any) -> GdkPixbuf.Pixbuf
    """
    Convert a pillow (pil) object to a pixbuf

    args:
        img: (pil.Image): A pillow image

    returns:
        GtkPixbuf: a GTK Pixbuf
    """
    width, height = img.size
    if img.mode != "RGB":  # gtk only supports RGB
        img = img.convert(mode='RGB')
    bytes = GLib.Bytes(img.tobytes())
    pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(bytes, GdkPixbuf.Colorspace.RGB, False, 8, width, height, width * 3)
    return pixbuf


def bytes2pixbuf(data,
                 width=icon_size['width'],
                 height=icon_size['height'],
                 display_name=None):  # type: (bytes, int, int, Optional[str]) -> GdkPixbuf.Pixbuf
    """
    converts raw bytes into a GTK PixBug

    args:
        data (bytes): raw bytes
        width (int): width of image
        height (int): height of images

    returns:
        GtkPixbuf: a GTK Pixbuf

    """
    loader = GdkPixbuf.PixbufLoader()
    loader.set_size(width, height)
    try:
        loader.write(data)
        loader.close()
    except (GLib.Error, TypeError) as e:
        logger.error("can't process icon for {}: {}".format(display_name, str(e)))
    else:
        return loader.get_pixbuf()


@lru_cache(maxsize=1)
def get_prefix():  # type: () -> str
    """
    Returns the Python prefix where eduVPN is installed

    returns:
        str: path to Python installation prefix
    """
    target = 'share/eduvpn/builder/window.ui'
    local = path.dirname(path.dirname(path.abspath(__file__)))
    options = [local, path.expanduser('~/.local'), '/usr/local', sys.prefix]
    for option in options:
        logger.debug("looking for '{}' in '{}'".format(target, option))
        if path.isfile(path.join(option, target)):
            return option
    raise Exception("Can't find eduVPN installation")


@lru_cache(maxsize=1)
def have_dbus():
    # type: () -> bool
    try:
        import dbus
        dbus = dbus.SystemBus(private=True)
    except Exception as e:
        logger.error("WARNING: dbus daemons not running, eduVPN client functionality limited")
        return False
    else:
        dbus.close()
        return True


@lru_cache(maxsize=1)
def get_pixbuf(logo=None):
    # type: (Optional[str]) -> Tuple[GdkPixbuf.Pixbuf, GdkPixbuf.Pixbuf]
    if not logo:
        logo = path.join(get_prefix(), 'share/eduvpn/eduvpn.png')

    small = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo, icon_size['width'], icon_size['height'], True)
    big = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo, icon_size['width'] * 2, icon_size['height'] * 2, True)
    return small, big


def metadata_of_selected(builder):
    # type: (Gtk.builder) -> Any
    selection = builder.get_object('provider-selection')
    model, treeiter = selection.get_selected()
    if treeiter is None:
        return
    else:
        uuid_, _, _, _ = model[treeiter]
        return Metadata.from_uuid(uuid_)


def detect_distro(release_file='/etc/os-release'):
    # type: (str) -> Tuple[str, str]
    params = {}
    if not os.access(release_file, os.R_OK):
        raise EduvpnException("Can't detect distribution version, '/etc/os-release' doesn't exist.")

    with open(release_file, 'r') as f:
        for line in f.readlines():
            splitted = line.strip().split('=')
            if len(splitted) == 2:
                key, value = splitted
                params[key] = value.strip('""')

    if 'ID' not in params and 'VERSION_ID' not in params:
        raise EduvpnException("Can't detect distribution version, '/etc/os-release' doesn't "
                              "contain ID and VERSION_ID fields")

    return params['ID'], params['VERSION_ID']


def are_we_running_ubuntu1804():
    # type: () -> bool
    try:
        distro, version = detect_distro()
    except EduvpnException as e:
        logger.error("can't determine distribution and version: {}".format(e))
        return False
    else:
        if distro == 'ubuntu' and version == '18.04':
            logger.critical("You are running Ubuntu 18.04, which leaks DNS information")
            return True
        else:
            return False
