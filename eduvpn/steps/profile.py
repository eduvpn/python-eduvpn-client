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
from eduvpn.steps.fetching import fetching_window
from eduvpn.metadata import Metadata
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from typing import Any

logger = logging.getLogger(__name__)


# ui thread
def fetch_profile_step(builder, meta, oauth, lets_connect):  # type: (Gtk.builder, Metadata, str, bool) -> None
    """background action step, fetches profiles and shows 'fetching' screen"""
    logger.info("fetching profile step")

    if meta.profile_id:
        logger.info("we already selected the profile in the past, not presenting user with choice again")
        parse_config_step(builder=builder, oauth=oauth, meta=meta, lets_connect=lets_connect)
        return

    fetching_window(builder=builder, lets_connect=lets_connect)
    dialog = builder.get_object('fetch-dialog')
    thread_helper(lambda: _background(oauth, meta, builder, dialog, lets_connect=lets_connect))
    dialog.run()


# background thread
def _background(oauth, meta, builder, dialog, lets_connect):
    #type: (str, Metadata, Gtk.builder, Any, bool) -> None
    try:
        profiles = list_profiles(oauth, meta.api_base_uri)
        logger.info("There are {} profiles on {}".format(len(profiles), meta.api_base_uri))
        if len(profiles) > 1:
            GLib.idle_add(lambda: dialog.hide())
            GLib.idle_add(lambda: _select_profile_step(builder=builder, profiles=profiles, meta=meta, oauth=oauth,
                                                       lets_connect=lets_connect))
        elif len(profiles) == 1:
            _parse_choice(builder, meta, oauth, profiles[0], lets_connect=lets_connect)
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
def _select_profile_step(builder, profiles, meta, oauth, lets_connect):  # type: (Gtk.builder, dict, Metadata, str, bool) -> None
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
            _parse_choice(builder, meta, oauth, model[treeiter], lets_connect=lets_connect)
        else:
            logger.error("nothing selected")
            return


# ui thread
def _parse_choice(builder, meta, oauth, choice, lets_connect):
    #type: (Gtk.builder, Metadata, str, dict, bool) -> None
    meta.profile_display_name, meta.profile_id, meta.two_factor, two_factor_method = choice
    meta.two_factor_method = two_factor_method.split(",")
    parse_config_step(builder=builder, oauth=oauth, meta=meta, lets_connect=lets_connect)