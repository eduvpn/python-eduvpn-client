# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
from eduvpn.images import letsconnect_main_logo
logger = logging.getLogger(__name__)


def fetching_window(builder, lets_connect):
    """
    Don't forget to call dialog.run() after creating the fetch window!
    """
    logger.info("fetching instances step")
    dialog = builder.get_object('fetch-dialog')
    image = builder.get_object('fetch-image')
    window = builder.get_object('eduvpn-window')
    dialog.set_transient_for(window)

    if lets_connect:
        image.set_from_file(letsconnect_main_logo)

    dialog.show_all()
