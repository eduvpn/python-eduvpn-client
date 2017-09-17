# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+
from os import path

import gi
gi.require_version('Notify', '0.7')
gi.require_version('Gtk', '3.0')
from gi.repository import Notify, GdkPixbuf

from eduvpn.config import prefix

Notify.init("eduVPN client")

# http://www.devdungeon.com/content/desktop-notifications-python-libnotify
image_path = path.join(prefix, 'share/eduvpn/eduvpn.png')
image = GdkPixbuf.Pixbuf.new_from_file(image_path)

notification = Notify.Notification.new('test')
notification.set_icon_from_pixbuf(image)
notification.set_app_name("eduVPN")


def notify(msg, small_msg=None):
    notification.update(msg, small_msg)
    notification.show()
