# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import gi
from gi.repository import GLib
from eduvpn.util import error_helper, thread_helper
from eduvpn.remote import user_info
from eduvpn.steps.two_way_enroll import two_fa_enroll_window

logger = logging.getLogger(__name__)


def _choice_window(options, meta, oauth, builder, config_dict):
    logger.info("presenting user with two-factor auth method dialog")
    two_dialog = builder.get_object('2fa-dialog')

    for i, option in enumerate(options):
        two_dialog.add_button(option, i)
    two_dialog.show()
    index = int(two_dialog.run())
    if index >= 0:
        meta.username = options[index]
        logger.info("user selected '{}'".format(meta.username))
        two_fa_enroll_window(oauth=oauth, meta=meta, builder=builder, config_dict=config_dict)
    two_dialog.destroy()


def _background(meta, oauth, builder, config_dict):
    window = builder.get_object('eduvpn-window')

    try:
        info = user_info(oauth, meta.api_base_uri)
    except Exception as e:
        error = e
        GLib.idle_add(lambda: error_helper(window, "Can't fetch user info", str(error)))
        raise

    if info['is_disabled']:
        GLib.idle_add(lambda: error_helper(window, "This account has been disabled", ""))

    if not info['two_factor_enrolled']:
        logger.info("no two factor auth enabled")
        GLib.idle_add(lambda: two_fa_enroll_window(oauth=oauth, meta=meta, builder=builder, config_dict=config_dict))

    elif 'two_factor_enrolled_with' in info:
        options = info['two_factor_enrolled_with']
        if len(options) > 1:
            GLib.idle_add(lambda: _choice_window(options=options, meta=meta, oauth=oauth, builder=builder,
                                                 config_dict=config_dict))
            return
        elif len(options) == 1:
            logger.info("selection only one two-factor auth methods available ({})".format(options[0]))
            meta.username = options[0]
        else:
            GLib.idle_add(lambda: error_helper(window, "two_factor_enrolled_with' doesn't contain any fields", ""))
        GLib.idle_add(lambda: two_fa_enroll_window(oauth=oauth, meta=meta, builder=builder, config_dict=config_dict))


def two_auth_step(builder, oauth, meta, config_dict):
    """checks if 2auth is enabled. If more than 1 option presents user with choice"""
    thread_helper(lambda: _background(meta, oauth, builder, config_dict=config_dict))
