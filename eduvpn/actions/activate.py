# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
from datetime import datetime
import gi
from gi.repository import GLib
from eduvpn.util import error_helper
from eduvpn.oauth2 import oauth_from_token
from eduvpn.manager import update_config_provider, update_keys_provider, connect_provider
from eduvpn.remote import get_profile_config, create_keypair
from eduvpn.notify import notify


logger = logging.getLogger(__name__)


def activate_connection(meta, builder):
    """do the actual connecting action"""
    logger.info("Connecting to {}".format(meta.display_name))
    notify("eduVPN connecting...", "Connecting to '{}'".format(meta.display_name))
    try:
        if not meta.token:
            logger.error("metadata for {} doesn't contain oauth2 token".format(meta.uuid))
        else:
            oauth = oauth_from_token(meta=meta)
            config = get_profile_config(oauth, meta.api_base_uri, meta.profile_id)
            meta.config = config
            update_config_provider(meta)

            if datetime.now() > datetime.fromtimestamp(meta.token['expires_at']):
                logger.info("key pair is expired")
                cert, key = create_keypair(oauth, meta.api_base_uri)
                update_keys_provider(meta.uuid, cert, key)

        connect_provider(meta.uuid)

    except Exception as e:
        switch = builder.get_object('connect-switch')
        GLib.idle_add(switch.set_active, False)
        window = builder.get_object('eduvpn-window')
        error_helper(window, "can't enable connection", "{}: {}".format(type(e).__name__, str(e)))
        raise
