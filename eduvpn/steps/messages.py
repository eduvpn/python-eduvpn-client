# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import gi
from gi.repository import GLib
from eduvpn.util import error_helper, thread_helper
from eduvpn.steps.reauth import reauth
from eduvpn.oauth2 import oauth_from_token
from eduvpn.remote import user_messages, system_messages, user_info
from eduvpn.exceptions import EduvpnAuthException

logger = logging.getLogger(__name__)


def _background(meta, builder, verifier):
    label = builder.get_object('messages-label')
    window = builder.get_object('eduvpn-window')
    try:
        oauth = oauth_from_token(meta=meta)
    except Exception as e:
        error = e
        GLib.idle_add(lambda: error_helper(window, "Can't reconstruct OAuth2 session", (str(error))))
        print(meta)
        raise

    text = ""

    try:
        messages_user = list(user_messages(oauth, meta.api_base_uri))
        messages_system = list(system_messages(oauth, meta.api_base_uri))
        info = user_info(oauth, meta.api_base_uri)
    except EduvpnAuthException:
        GLib.idle_add(lambda: reauth(meta=meta, verifier=verifier, builder=builder))
    except Exception as e:
        error = str(e)
        GLib.idle_add(lambda: error_helper(window, "Can't fetch user messages", error))
        raise
    else:
        if info['is_disabled']:
            GLib.idle_add(lambda: error_helper(window, "This account has been disabled", ""))
        for date_time, type_, message in messages_user:
            logger.info("user message at {}: {}".format(date_time, message))
            text += "<b><big>{}</big></b>\n".format(date_time)
            text += "<small><i>user, {}</i></small>\n".format(type_)
            text += "{}\n\n".format(message)
        for date_time, type_, message in messages_system:
            logger.info("system message at {}: {}".format(date_time, message))
            text += "<b><big>{}</big></b>\n".format(date_time)
            text += "<small><i>system, {}</i></small>\n".format(type_)
            text += "{}\n\n".format(message)
        GLib.idle_add(lambda: label.set_markup(text))


def fetch_messages(meta, builder, verifier):
    logger.info("fetching user and system messages from {} ({})".format(meta.display_name, meta.api_base_uri))
    thread_helper(lambda: _background(meta=meta, builder=builder, verifier=verifier))
