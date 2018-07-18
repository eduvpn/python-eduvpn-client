# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import gi
from gi.repository import GLib
from eduvpn.util import error_helper, thread_helper
from eduvpn.remote import list_profiles
from eduvpn.steps.parse_config import parse_config_step
from eduvpn.exceptions import EduvpnException

logger = logging.getLogger(__name__)


# ui thread
def fetch_profile_step(builder, meta, oauth):
    """background action step, fetches profiles and shows 'fetching' screen"""
    logger.info("fetching profile step")
    dialog = builder.get_object('fetch-dialog')
    window = builder.get_object('eduvpn-window')
    dialog.set_transient_for(window)
    dialog.show_all()
    thread_helper(lambda: _background(oauth, meta, builder, dialog))
    dialog.run()


# background thread
def _background(oauth, meta, builder, dialog):
    try:
        profiles = list_profiles(oauth, meta.api_base_uri)
        logger.info("There are {} profiles on {}".format(len(profiles), meta.api_base_uri))
        if len(profiles) > 1:
            GLib.idle_add(lambda: dialog.hide())
            GLib.idle_add(lambda: _select_profile_step(builder=builder, profiles=profiles, meta=meta, oauth=oauth))
        elif len(profiles) == 1:
            _parse_choice(builder, meta, oauth, profiles[0])
        else:
            raise EduvpnException("Either there are no VPN profiles defined, or this account does not have the "
                                  "required permissions to create a new VPN configurations for any of the "
                                  "available profiles.")

    except Exception as e:
        error = str(e)
        GLib.idle_add(lambda: error_helper(dialog, "Can't fetch profile list", error))
        GLib.idle_add(lambda: dialog.hide())
        raise


# ui thread
def _select_profile_step(builder, profiles, meta, oauth):
    """the profile selection step, doesn't do anything if only one profile"""
    logger.info("opening profile dialog")

    dialog = builder.get_object('profiles-dialog')
    window = builder.get_object('eduvpn-window')
    dialog.set_transient_for(window)
    model = builder.get_object('profiles-model')
    selection = builder.get_object('profiles-selection')
    dialog.show_all()
    model.clear()
    [model.append(p) for p in profiles]
    response = dialog.run()
    dialog.hide()

    if response == 0:  # cancel
        logger.info("cancel button pressed")
        return
    else:
        model, treeiter = selection.get_selected()
        if treeiter:
            _parse_choice(builder, meta, oauth, model[treeiter])
        else:
            logger.error("nothing selected")
            return


# ui thread
def _parse_choice(builder, meta, oauth, choice):
    meta.profile_display_name, meta.profile_id, meta.two_factor, two_factor_method = choice
    meta.two_factor_method = two_factor_method.split(",")
    parse_config_step(builder=builder, oauth=oauth, meta=meta)