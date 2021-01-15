import os

from typing import Optional

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf

from eduvpn.utils import logger
from eduvpn.settings import FLAG_PREFIX


# ui thread
def error_helper(parent: Gtk.Widget, msg_big: str, msg_small: str) -> None:  # type: ignore
    """
    Shows a GTK error message dialog.
    args:
        parent (GObject): A GTK Window
        msg_big (str): the big string
        msg_small (str): the small string
    """
    logger.error(f"{msg_big}: {msg_small}")
    error_dialog = Gtk.MessageDialog(parent, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, str(msg_big))  # type: ignore
    error_dialog.format_secondary_text(str(msg_small))  # type: ignore
    error_dialog.run()  # type: ignore
    error_dialog.hide()  # type: ignore


def get_flag_image_file(country_code: str) -> Optional[str]:
    logger.debug(f"get_flag_image: {country_code}")

    if country_code:
        flag_location = FLAG_PREFIX + country_code + "@1,5x.png"
        if os.path.exists(flag_location):
            return flag_location
    return None
