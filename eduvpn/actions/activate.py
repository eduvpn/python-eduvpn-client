# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk
from eduvpn.util import error_helper, thread_helper
from eduvpn.oauth2 import oauth_from_token
from eduvpn.manager import update_config_provider, update_keys_provider, connect_provider, disconnect_all
from eduvpn.remote import get_profile_config, create_keypair, user_info, check_certificate
from eduvpn.steps.reauth import reauth
from eduvpn.steps.two_way_auth import two_auth_step
from eduvpn.notify import notify, init_notify
from eduvpn.openvpn import parse_ovpn
from eduvpn.exceptions import EduvpnAuthException, EduvpnException
from eduvpn.crypto import common_name_from_cert
from eduvpn.brand import get_brand
from eduvpn.metadata import Metadata
from typing import Any, Union, List

logger = logging.getLogger(__name__)


# ui thread
def activate_connection(meta, builder, verifier, lets_connect):  # type: (Metadata, Gtk.builder, str, bool) -> None
    """do the actual connecting action"""
    logger.info(u"Connecting to {}".format(meta.display_name))
    disconnect_all()
    _, name = get_brand(lets_connect)
    notification = init_notify(lets_connect)
    notify(notification, u"{} connecting...".format(name), u"Connecting to '{}'".format(meta.display_name))
    try:
        if not meta.token:
            logger.error(u"metadata for {} doesn't contain oauth2 token".format(meta.uuid))
            connect_provider(meta.uuid)

        else:
            oauth = oauth_from_token(meta=meta, lets_connect=lets_connect)
            thread_helper(lambda: _auth_check(oauth, meta, verifier, builder, lets_connect=lets_connect))

    except Exception as e:
        switch = builder.get_object('connect-switch')
        GLib.idle_add(switch.set_active, False)
        window = builder.get_object('eduvpn-window')
        error_helper(window, u"can't enable connection", "{}: {}".format(type(e).__name__, str(e)))
        raise


# background thread
def _auth_check(oauth, meta, verifier, builder, lets_connect):  # type: (str, Metadata, str, Gtk.builder, bool) -> None
    """quickly see if the can fetch messages, otherwise reauth"""
    try:
        info = user_info(oauth, meta.api_base_uri)
        _cert_check(meta, oauth, builder, info, lets_connect)
    except EduvpnAuthException:
        GLib.idle_add(lambda: reauth(meta=meta, verifier=verifier, builder=builder, lets_connect=lets_connect))
    except Exception as e:
        error = e
        window = builder.get_object('eduvpn-window')
        GLib.idle_add(lambda: error_helper(window, u"Can't check account status", "{}".format(str(error))))
        raise


# background thread
def _cert_check(meta, oauth, builder, info, lets_connect):
    # type: (Metadata, str, Gtk.builder, dict, bool) -> None
    common_name = common_name_from_cert(meta.cert.encode('ascii'))
    cert_valid = check_certificate(oauth, meta.api_base_uri, common_name)

    if not cert_valid['is_valid']:
        logger.warning(u'client certificate not valid, reason: {}'.format(cert_valid['reason']))
        if cert_valid['reason'] in ('certificate_missing', 'certificate_not_yet_valid', 'certificate_expired'):
            logger.info(u'Going to try to fetch new keypair')
            cert, key = create_keypair(oauth, meta.api_base_uri)
            update_keys_provider(meta.uuid, cert, key)
        elif cert_valid['reason'] == 'user_disabled':
            raise EduvpnException(u'Your account has been disabled.')
        else:
            raise EduvpnException(u'Your client certificate is invalid ({})'.format(cert_valid['reason']))

    _fetch_updated_config(oauth, meta, builder, info, lets_connect)


# background thread
def _fetch_updated_config(oauth, meta, builder, info, lets_connect):
    # type: (str, Metadata, Gtk.builder, dict, bool) -> None
    config = get_profile_config(oauth, meta.api_base_uri, meta.profile_id)
    meta.config = config
    config_dict = parse_ovpn(meta.config)
    update_config_provider(meta, config_dict)

    _2fa_check(meta, builder, oauth, config_dict, info, lets_connect)


# background thread
def _2fa_check(meta, builder, oauth, config_dict, info, lets_connect):
    # type: (Metadata, Gtk.builder, str, dict, dict, bool) -> None
    if meta.two_factor and not info['two_factor_enrolled']:
        # 2fa is required, but the user is not enroled anymore
        two_auth_step(builder, oauth, meta, config_dict, lets_connect)
    else:
        connect_provider(meta.uuid)
