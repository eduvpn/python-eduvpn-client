import logging
import gi
from gi.repository import GLib
from eduvpn.util import error_helper, thread_helper
from eduvpn.remote import user_info
from eduvpn.steps.finalize import finalizing_step

logger = logging.getLogger(__name__)


def update(options, meta, oauth, builder):
    two_dialog = builder.get_object('2fa-dialog')

    for i, option in enumerate(options):
        two_dialog.add_button(option, i)
    two_dialog.show()
    index = int(two_dialog.run())
    if index >= 0:
        meta.username = options[index]
        logger.info("user selected '{}'".format(meta.username))
        finalizing_step(oauth=oauth, meta=meta, builder=builder)
    two_dialog.destroy()


def background(meta, oauth, builder):
    try:
        info = user_info(oauth, meta.api_base_uri)
    except Exception as e:
        GLib.idle_add(lambda: error_helper(window, "Can't fetch user info", str(e)))
        raise

    username = None
    if info['is_disabled']:
        window = builder.get_object('eduvpn-window')
        GLib.idle_add(lambda: error_helper(window, "This account has been disabled", ""))

    if 'two_factor_enrolled_with' in info:
        options = info['two_factor_enrolled_with']
        if len(options) > 1:
            GLib.idle_add(lambda: update(options=options, meta=meta, oauth=oauth, builder=builder))
            return
        elif len(options) == 1:
            meta.username = options[0]
            GLib.idle_add(lambda: error_helper(window, "two_factor_enrolled_with' doesn't contain any fields", ""))
        else:
            GLib.idle_add(lambda: error_helper(window, "This account has been disabled", ""))
        GLib.idle_add(lambda: finalizing_step(oauth=oauth, meta=meta, builder=builder))


def two_auth_step(builder, oauth, meta):
    """checks if 2auth is enabled. If more than 1 option presents user with choice"""
    thread_helper(lambda: background(meta, oauth, builder))
