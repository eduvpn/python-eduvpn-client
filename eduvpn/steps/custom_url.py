# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import gi
from eduvpn.util import error_helper
from eduvpn.steps.browser import browser_step


logger = logging.getLogger(__name__)


# ui thread
def custom_url(builder, meta, verifier, lets_connect):
    """the custom URL dialog where a user can enter a custom instance URL"""
    dialog = builder.get_object('custom-url-dialog')
    window = builder.get_object('eduvpn-window')
    dialog.set_transient_for(window)
    entry = builder.get_object('custom-url-entry')
    # entry.set_text('https://debian-vpn.tuxed.net')
    entry.set_position(len(entry.get_text()))
    dialog.show_all()
    while True:
        response = dialog.run()
        if response == 1:
            url = entry.get_text().strip()
            logger.info("ok pressed, entry text: {}".format(url))
            if not url.startswith('https://'):
                error_helper(dialog, "Invalid URL", "URL should start with https://")
            elif url == 'https://':
                error_helper(dialog, "Invalid URL", "Please enter a URL")
            else:
                dialog.hide()
                meta.display_name = url[8:].split('/')[0]
                logger.info("using {} for display name".format(meta.display_name))
                meta.instance_base_uri = url
                meta.connection_type = 'Custom Instance'
                meta.authorization_type = 'local'
                meta.icon_data = None
                browser_step(builder=builder, meta=meta, verifier=verifier, lets_connect=lets_connect)
                break
        else:  # cancel or close
            logger.info("cancel or close button pressed (response {})".format(response))
            dialog.hide()
            return
