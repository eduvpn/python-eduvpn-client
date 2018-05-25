# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
import base64
import gi
from gi.repository import GLib
from eduvpn.util import error_helper, thread_helper, bytes2pixbuf
from eduvpn.remote import get_instances
from eduvpn.steps.browser import browser_step


logger = logging.getLogger(__name__)


def _fetch_background(dialog, meta, verifier, builder):
    try:
        authorization_type, instances = get_instances(discovery_uri=meta.discovery_uri, verifier=verifier)
    except Exception as e:
        error = e
        GLib.idle_add(lambda: error_helper(dialog, "can't fetch instances", "{} {}".format(type(error), str(error))))
        GLib.idle_add(lambda: dialog.hide())
        raise
    else:
        GLib.idle_add(lambda: dialog.hide())
        meta.authorization_type = authorization_type
        GLib.idle_add(lambda: select_instance_step(meta, instances, builder=builder, verifier=verifier))


def fetch_instance_step(meta, builder, verifier):
    """fetch list of instances"""
    logger.info("fetching instances step")
    dialog = builder.get_object('fetch-dialog')
    dialog.show_all()

    thread_helper(lambda: _fetch_background(dialog=dialog, meta=meta, verifier=verifier, builder=builder))


def select_instance_step(meta, instances, builder, verifier):
    """prompt user with instance dialog"""
    logger.info("presenting instances to user")
    dialog = builder.get_object('instances-dialog')
    model = builder.get_object('instances-model')
    selection = builder.get_object('instances-selection')
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
            browser_step(builder, meta, verifier)
        else:
            logger.info("nothing selected")
