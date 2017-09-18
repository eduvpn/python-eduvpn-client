# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import threading
import uuid

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, GdkPixbuf

from eduvpn.config import icon_size

logger = logging.getLogger(__name__)


def make_unique_id():
    return str(uuid.uuid4())


def error_helper(parent, msg_big, msg_small):
    logger.error("{}: {}".format(msg_big, msg_small))
    error_dialog = Gtk.MessageDialog(parent, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, str(msg_big))
    error_dialog.format_secondary_text(str(msg_small))
    error_dialog.run()
    error_dialog.hide()


def thread_helper(func):
    thread = threading.Thread(target=func)
    thread.daemon = True
    thread.start()
    return thread


def bytes2pixbuf(data, width=icon_size['width'], height=icon_size['height']):
    l = GdkPixbuf.PixbufLoader()
    l.set_size(width, height)
    l.write(data)
    l.close()
    return l.get_pixbuf()
