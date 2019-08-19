# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from os import path
import gi
gi.require_version('Notify', '0.7')
gi.require_version('Gtk', '3.0')
from gi.repository import Notify, GdkPixbuf
from repoze.lru import lru_cache
from eduvpn.util import have_dbus
from eduvpn.brand import get_brand
from typing import Any, Optional
from gi.repository import Notify


@lru_cache(maxsize=1)
def init_notify(lets_connect):
    # type: (bool) -> Notify
    icon, name = get_brand(lets_connect)
    Notify.init(name + " client")
    image_path = path.join(icon)
    image = GdkPixbuf.Pixbuf.new_from_file(image_path)
    notification = Notify.Notification.new(name)
    notification.set_icon_from_pixbuf(image)
    notification.set_app_name(name)
    return notification


def notify(notification, msg, small_msg=None):
    # type: (Notify, str, Optional[Any]) -> None
    notification.update(msg, small_msg)
    if have_dbus():
        notification.show()