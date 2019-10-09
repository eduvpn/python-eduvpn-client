# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import gi
from gi.repository import GLib, Gtk
from eduvpn.util import error_helper, thread_helper
from eduvpn.remote import user_info
from eduvpn.steps.totp_enroll import totp_enroll_window
from eduvpn.steps.yubi_enroll import yubi_enroll_window
from eduvpn.steps.finalize import finalizing_step
from eduvpn.metadata import Metadata
from typing import List

logger = logging.getLogger(__name__)


# ui thread
def two_auth_step(builder,
                  oauth, meta,
                  config_dict,
                  lets_connect):  # type: (Gtk.builder, str, Metadata, dict, bool) -> None
    """checks if 2auth is enabled. If more than 1 option presents user with choice"""
    thread_helper(lambda: _background(meta, oauth, builder, config_dict=config_dict, lets_connect=lets_connect))


# background thread
def _background(meta, oauth, builder, config_dict, lets_connect):
    # type: (Metadata, str, Gtk.builder, dict, bool) -> None
    window = builder.get_object('eduvpn-window')

    try:
        info = user_info(oauth, meta.api_base_uri)
        meta.user_id = info['user_id']
    except Exception as e:
        error = e
        GLib.idle_add(lambda: error_helper(window, "Can't fetch user info", str(error)))
        raise

    if info['is_disabled']:
        GLib.idle_add(lambda: error_helper(window, "This account has been disabled", ""))

    if info['two_factor_enrolled']:
        # Multiple 2fa can be enrolled, but we only support one.
        meta.username = info['two_factor_enrolled_with'][0]
        GLib.idle_add(lambda: finalizing_step(meta=meta, builder=builder, config_dict=config_dict,
                                              lets_connect=lets_connect))
    else:
        if len(meta.two_factor_method) == 0:
            logger.info("no two factor auth enabled on server")
            GLib.idle_add(lambda: finalizing_step(meta=meta, builder=builder, config_dict=config_dict,
                                                  lets_connect=lets_connect))
        elif len(meta.two_factor_method) > 1:
            logger.info("Multi two factor methods available")
            GLib.idle_add(lambda: _choice_window(options=meta.two_factor_method, meta=meta, oauth=oauth,
                                                 builder=builder, config_dict=config_dict, lets_connect=lets_connect))
        else:
            GLib.idle_add(lambda: _enroll(oauth=oauth, meta=meta, builder=builder, config_dict=config_dict,
                                          lets_connect=lets_connect))


# ui thread
def _choice_window(options, meta, oauth, builder, config_dict, lets_connect):
    # type: (List[str], Metadata, str, Gtk.builder, dict, bool) -> None
    logger.info("presenting user with two-factor auth method dialog")
    window = builder.get_object('eduvpn-window')

    # since we can't delete buttons from a dialog we have to create it manually
    # dialog = builder.get_object('2fa-dialog')
    dialog = Gtk.Dialog()
    dialog.set_transient_for(window)
    dialog.set_title("Two factor authentication")
    header = Gtk.Label()
    header.set_markup('<big><b>Two factor authentication</b></big>')
    label = Gtk.Label("Which 2-way authentication method would you like to use?")
    box = dialog.get_content_area()
    box.set_margin_top(8)
    box.set_margin_left(8)
    box.set_margin_right(8)
    box.set_margin_bottom(8)
    box.set_spacing(8)
    box.add(header)
    box.add(label)

    for i, option in enumerate(options):
        dialog.add_button(option, i)

    dialog.show_all()
    index = int(dialog.run())
    dialog.hide()
    if index >= 0:
        meta.username = options[index]
        logger.info("user selected '{}'".format(meta.username))
        _enroll(oauth=oauth, meta=meta, builder=builder, config_dict=config_dict, lets_connect=lets_connect)


def _enroll(oauth, meta, builder, config_dict, lets_connect):
    # type: (str, Metadata, Gtk.builder, dict, bool) -> None
    if meta.username == 'totp':
        GLib.idle_add(lambda: totp_enroll_window(oauth=oauth, meta=meta, builder=builder, config_dict=config_dict,
                                                 lets_connect=lets_connect))
    elif meta.username == 'yubi':
        GLib.idle_add(lambda: yubi_enroll_window(oauth=oauth, meta=meta, builder=builder, config_dict=config_dict,
                                                 lets_connect=lets_connect))
