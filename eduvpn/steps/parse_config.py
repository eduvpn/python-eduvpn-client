import logging
import gi
from gi.repository import GLib
from eduvpn.util import error_helper, thread_helper
from eduvpn.remote import create_keypair, get_profile_config
from eduvpn.openvpn import format_like_ovpn, parse_ovpn
from eduvpn.steps.two_way_auth import two_auth_step
from eduvpn.steps.finalize import finalizing_step

logger = logging.getLogger(__name__)


def parse_config_step(builder, oauth, meta):
    """parse the config and see if action is still required, otherwise finalize"""
    logger.info("parse config step")
    dialog = builder.get_object('fetch-dialog')
    dialog.show_all()
    thread_helper(lambda: _background(meta=meta, oauth=oauth, dialog=dialog, builder=builder))


def _background(meta, oauth, dialog, builder):
    try:
        cert, key = create_keypair(oauth, meta.api_base_uri)
        meta.cert = cert
        meta.key = key
        meta.config = get_profile_config(oauth, meta.api_base_uri, meta.profile_id)
        ovpn_text = format_like_ovpn(meta.config, meta.cert, meta.key)
        config_dict = parse_ovpn(ovpn_text)
        if 'auth-user-pass' in config_dict and not meta.username:
            # TODO: unset secret
            GLib.idle_add(lambda: two_auth_step(builder, oauth, meta, config_dict=config_dict))
        else:
            GLib.idle_add(lambda: finalizing_step(meta=meta, builder=builder, config_dict=config_dict))
        GLib.idle_add(lambda: dialog.hide())

    except Exception as e:
        error = e
        GLib.idle_add(lambda: error_helper(dialog, "can't finalize configuration", "{}: {}".format(type(error).__name__,
                                                                                                   str(error))))
        GLib.idle_add(lambda: dialog.hide())
        raise
