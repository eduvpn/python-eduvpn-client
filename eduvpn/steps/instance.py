# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import base64
import gi
from gi.repository import GLib, Gtk
from eduvpn.util import error_helper, thread_helper, bytes2pixbuf
from eduvpn.remote import get_instances
from eduvpn.steps.browser import browser_step
from eduvpn.steps.fetching import fetching_window
from eduvpn.metadata import Metadata

logger = logging.getLogger(__name__)


# ui thread
def fetch_instance_step(meta, builder, verifier, lets_connect):
    #type: (Metadata, Gtk.builder, str, bool) -> None
    """fetch list of instances"""
    logger.info("fetching instances step")
    fetching_window(builder=builder, lets_connect=lets_connect)
    dialog = builder.get_object('fetch-dialog')
    thread_helper(lambda: _fetch_background(meta=meta, verifier=verifier, builder=builder, lets_connect=lets_connect))
    dialog.run()


# background thread
def _fetch_background(meta, verifier, builder, lets_connect):
    #type: (Metadata, str, Gtk.builder, bool) -> None
    dialog = builder.get_object('fetch-dialog')
    window = builder.get_object('eduvpn-window')
    try:
        authorization_type, instances = get_instances(discovery_uri=meta.discovery_uri, verifier=verifier)
    except Exception as e:
        error = e
        GLib.idle_add(lambda: dialog.hide())
        GLib.idle_add(lambda: error_helper(window, "can't fetch instances", "{} {}".format(type(error), str(error))))
        raise
    else:
        GLib.idle_add(lambda: dialog.hide())
        meta.authorization_type = authorization_type
        GLib.idle_add(lambda: select_instance_step(meta, instances, builder=builder, verifier=verifier,
                                                   lets_connect=lets_connect))


# ui thread
def select_instance_step(meta, instances, builder, verifier, lets_connect):
    #type: (Metadata, dict, Gtk.builder, str, bool) -> None
    """prompt user with instance dialog"""
    logger.info("presenting instances to user")
    dialog = builder.get_object('instances-dialog')
    model = builder.get_object('instances-model')
    selection = builder.get_object('instances-selection')
    window = builder.get_object('eduvpn-window')
    dialog.set_transient_for(window)
    model.clear()
    dialog.show_all()

    for display_name, url, icon_data in instances:
        icon = bytes2pixbuf(icon_data)
        model.append((display_name, url, icon, base64.b64encode(icon_data).decode('ascii')))

    response = dialog.run()
    dialog.hide()

    if response == 0:  # cancel
        logger.info("cancel button pressed")
    else:
        model, treeiter = selection.get_selected()
        if treeiter:
            display_name, instance_base_uri, icon_pixbuf, icon_data = model[treeiter]
            meta.display_name = display_name
            meta.instance_base_uri = instance_base_uri
            meta.icon_data = icon_data
            browser_step(builder, meta, verifier, lets_connect=lets_connect)
        else:
            logger.info("nothing selected")
