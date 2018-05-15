# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import gi
from gi.repository import GLib
from eduvpn.util import error_helper
from eduvpn.steps.browser import browser_step


logger = logging.getLogger(__name__)


def custom_url(builder, meta, verifier):
    """the custom URL dialog where a user can enter a custom instance URL"""
    dialog = builder.get_object('custom-url-dialog')
    entry = builder.get_object('custom-url-entry')
    dialog.show_all()
    while True:
        response = dialog.run()
        if response == 1:
            url = entry.get_text().strip()
            logger.info("ok pressed, entry text: {}".format(url))
            if not url.startswith('https://'):
                GLib.idle_add(lambda: error_helper(dialog, "Invalid URL", "URL should start with https://"))
            else:
                GLib.idle_add(lambda: dialog.hide())
                meta.display_name = url[8:].split('/')[0]
                logger.info("using {} for display name".format(meta.display_name))
                meta.instance_base_uri = url
                meta.connection_type = 'Custom Instance'
                meta.authorization_type = 'local'
                meta.icon_data = None
                GLib.idle_add(lambda: browser_step(builder=builder, meta=meta, verifier=verifier))
                break
        else:  # cancel or close
            logger.info("cancel or close button pressed (response {})".format(response))
            dialog.hide()
            return
