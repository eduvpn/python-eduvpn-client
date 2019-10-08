# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import gi
gi.require_version('Gtk', '3.0')
from eduvpn.brand import get_brand
from gi.repository import Gtk


logger = logging.getLogger(__name__)



def fetching_window(builder, lets_connect):  # type: (Gtk.builder, bool) -> None
    """
    Don't forget to call dialog.run() after creating the fetch window!
    """
    logger.info("fetching instances step")
    dialog = builder.get_object('fetch-dialog')
    image = builder.get_object('fetch-image')
    window = builder.get_object('eduvpn-window')
    dialog.set_transient_for(window)
    icon, _ = get_brand(lets_connect)
    image.set_from_file(icon)
    dialog.show_all()
