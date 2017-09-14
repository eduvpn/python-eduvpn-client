# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import gi
gi.require_version('Notify', '0.7')
gi.require_version('Gtk', '3.0')
from gi.repository import Notify, GdkPixbuf


Notify.init("eduVPN client")

# http://www.devdungeon.com/content/desktop-notifications-python-libnotify
#image = GdkPixbuf.Pixbuf.new_from_file("/home/NanoDano/test.png")
#notification.set_icon_from_pixbuf(image)


def notify(msg):
    notification = Notify.Notification.new(msg)
    notification.show()
