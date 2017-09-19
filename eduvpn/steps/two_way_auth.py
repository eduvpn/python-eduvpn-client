import logging
import gi
from gi.repository import GLib
from eduvpn.util import error_helper, thread_helper
from eduvpn.remote import user_info
from eduvpn.steps.finalize import finalizing_step

logger = logging.getLogger(__name__)


def update(options, meta, dialog, oauth, two_dialog, builder):
    for i, option in enumerate(options):
        dialog.add_button(option, i)
    two_dialog.show()
    index = int(dialog.run())
    if index >= 0:
        meta.username = options[index]
        logger.info("user selected '{}'".format(meta.username))
        finalizing_step(oauth=oauth, meta=meta, builder=builder)
    dialog.destroy()


def background(meta, dialog, oauth, two_dialog, builder):
    info = user_info(oauth, meta.api_base_uri)
    username = None
    if info['is_disabled']:
        window = builder.get_object('eduvpn-window')
        GLib.idle_add(lambda: error_helper(window, "This account has been disabled", ""))

    if 'two_factor_enrolled_with' in info:
        options = info['two_factor_enrolled_with']
        if len(options) > 1:
            GLib.idle_add(lambda: update(options=options, meta=meta, dialog=dialog, oauth=oauth,
                                         two_dialog=two_dialog, builder=builder))
            return
        elif len(options) == 1:
            meta.username = options[0]
            logger.info("auto selected username {} for 2 factor authentication".format(username))
        GLib.idle_add(lambda: finalizing_step(oauth=oauth, meta=meta, builder=builder))


def two_auth_step(builder, oauth, meta):
    """checks if 2auth is enabled. If more than 1 option presents user with choice"""
    dialog = builder.get_object('2fa-dialog')
    two_dialog = builder.get_object('2fa-dialog')

    thread_helper(lambda: background(meta, dialog, oauth, two_dialog, builder))