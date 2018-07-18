# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
from datetime import datetime
import gi
from gi.repository import GLib
from eduvpn.util import error_helper, thread_helper
from eduvpn.oauth2 import oauth_from_token
from eduvpn.manager import update_config_provider, update_keys_provider, connect_provider
from eduvpn.remote import get_profile_config, create_keypair, user_info
from eduvpn.steps.reauth import reauth
from eduvpn.notify import notify
from eduvpn.openvpn import parse_ovpn
from eduvpn.exceptions import EduvpnAuthException

logger = logging.getLogger(__name__)


# ui thread
def activate_connection(meta, builder, verifier):
    """do the actual connecting action"""
    logger.info("Connecting to {}".format(meta.display_name))
    notify("eduVPN connecting...", "Connecting to '{}'".format(meta.display_name))
    try:
        if not meta.token:
            logger.error("metadata for {} doesn't contain oauth2 token".format(meta.uuid))
            connect_provider(meta.uuid)

        else:
            oauth = oauth_from_token(meta=meta)
            thread_helper(lambda: _quick_check(oauth, meta, verifier, builder))

    except Exception as e:
        switch = builder.get_object('connect-switch')
        GLib.idle_add(switch.set_active, False)
        window = builder.get_object('eduvpn-window')
        error_helper(window, "can't enable connection", "{}: {}".format(type(e).__name__, str(e)))
        raise


def _quick_check(oauth, meta, verifier, builder):
    """quickly see if the can fetch messages, otherwise reauth"""
    try:
        user_info(oauth, meta.api_base_uri)
        _connect(oauth, meta)
    except EduvpnAuthException:
        GLib.idle_add(lambda: reauth(meta=meta, verifier=verifier, builder=builder))


def _connect(oauth, meta):
    config = get_profile_config(oauth, meta.api_base_uri, meta.profile_id)
    meta.config = config
    config_dict = parse_ovpn(meta.config)
    update_config_provider(meta, config_dict)

    if datetime.now() > datetime.fromtimestamp(meta.token['expires_at']):
        logger.info("key pair is expired")
        cert, key = create_keypair(oauth, meta.api_base_uri)
        update_keys_provider(meta.uuid, cert, key)

    connect_provider(meta.uuid)
