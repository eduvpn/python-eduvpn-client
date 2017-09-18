# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import threading
import uuid
from os import path

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, GdkPixbuf, GLib

from eduvpn.config import icon_size

logger = logging.getLogger(__name__)


def make_unique_id():
    return str(uuid.uuid4())


def error_helper(parent, msg_big, msg_small):
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


def thread_helper(func):
    """
    Runs a function in a thread

    args:
        func (lambda): a function to run in the background
    """
    thread = threading.Thread(target=func)
    thread.daemon = True
    thread.start()
    return thread


def bytes2pixbuf(data, width=icon_size['width'], height=icon_size['height'], display_name=None):
    """
    converts raw bytes into a GTK PixBug

    args:
        data (bytes): raw bytes
        width (int): width of image
        height (int): height of images

    returns:
        GtkPixbuf: a GTK Pixbuf

    """
    l = GdkPixbuf.PixbufLoader()
    l.set_size(width, height)
    try:
        l.write(data)
    except GLib.Error as e:
        logger.error("can't process icon for {}: {}".format(display_name, str(e)))
    else:
        return l.get_pixbuf()
    finally:
        l.close()


def get_prefix():
    """
    Returns the Python prefix where eduVPN is installed

    returns:
        str: path to Python installation prefix
    """
    local = path.dirname(path.dirname(path.abspath(__file__)))
    options = [local, '/usr/', '/usr/local']
    for option in options:
        if path.isfile(path.join(option, 'share/eduvpn/eduvpn.ui')):
            return option
    raise Exception("Can't find eduVPN installation")


def _have_dbus():
    try:
        import dbus
        dbus = dbus.SystemBus(private=True)
    except Exception as e:
        logger.error("WARNING: dbus daemons not running, eduVPN client functionality limited")
        return False
    else:
        dbus.close()
        return True

have_dbus = _have_dbus()