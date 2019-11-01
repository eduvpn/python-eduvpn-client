# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
from builtins import chr
from future.moves.urllib.parse import urlparse
import qrcode
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gdk, Gtk
from eduvpn.util import pil2pixbuf
from eduvpn.remote import two_factor_enroll_totp
from eduvpn.crypto import gen_base32
from eduvpn.util import thread_helper
from eduvpn.steps.finalize import finalizing_step
from eduvpn.metadata import Metadata
from typing import Any, Optional


logger = logging.getLogger(__name__)


# ui thread
def totp_enroll_window(builder, oauth, meta, config_dict, lets_connect, secret=None):
    # type: (Gtk.builder, str, Metadata, dict, bool, Any) -> None
    dialog = builder.get_object('totp-enroll-dialog')
    window = builder.get_object('eduvpn-window')
    dialog.set_transient_for(window)
    cancel_button = builder.get_object('totp-cancel-button')
    submit_button = builder.get_object('totp-submit-button')

    cancel_button.set_sensitive(False)
    submit_button.set_sensitive(False)

    dialog.show_all()
    GLib.idle_add(lambda: _make_qr(meta=meta, oauth=oauth, builder=builder, config_dict=config_dict, secret=secret,
                                   lets_connect=lets_connect))


# background thread
def _make_qr(builder, oauth, meta, config_dict, lets_connect, secret=None):
    # type: (Gtk.builder, str, Metadata, dict, bool, Any) -> None
    image = builder.get_object('totp-qr-image')
    if not secret:
        secret = gen_base32()
    host = urlparse(meta.api_base_uri).netloc
    uri = "otpauth://totp/{user_id}@{host}?secret={secret}&issuer={host}".format(user_id=meta.user_id, host=host,
                                                                                 secret=secret)
    qr = qrcode.QRCode(box_size=7, border=2)
    qr.add_data(uri)
    qr.make()
    img = qr.make_image()

    pixbuf = pil2pixbuf(img)
    image.set_from_pixbuf(pixbuf)
    GLib.idle_add(lambda: _parse_user_input(builder, oauth, meta, config_dict=config_dict,
                                            lets_connect=lets_connect, secret=secret))


# ui thread
def _parse_user_input(builder, oauth, meta, config_dict, lets_connect, secret=None):
    # type: (Gtk.builder, str, Metadata, dict, bool, str) -> None
    dialog = builder.get_object('totp-enroll-dialog')
    code_entry = builder.get_object('totp-code-entry')
    cancel_button = builder.get_object('totp-cancel-button')
    submit_button = builder.get_object('totp-submit-button')

    def callback(_, event):
        valid = chr(event.keyval).isdigit()
        logger.debug(u"user pressed {}, valid: {}".format(event.keyval, valid))
        if event.keyval in (Gdk.KEY_Left, Gdk.KEY_Right, Gdk.KEY_BackSpace, Gdk.KEY_End, Gdk.KEY_Home,
                            Gdk.KEY_Delete, Gdk.KEY_Return, Gdk.KEY_Escape):
            return False
        return not chr(event.keyval).isdigit()

    code_entry.connect("key-press-event", callback)
    code_entry.set_max_length(6)

    cancel_button.set_sensitive(True)
    submit_button.set_sensitive(True)
    while True:
        response = dialog.run()
        if response == 0:
            key = code_entry.get_text()
            cancel_button.set_sensitive(False)
            submit_button.set_sensitive(False)
            thread_helper(lambda: _enroll(builder, oauth, meta, config_dict, secret, key, lets_connect))
        else:
            dialog.hide()
            break


# background tread
def _enroll(builder, oauth, meta, config_dict, secret, key, lets_connect):
    # type: (Gtk.builder, str, Metadata, dict, Any, str, bool) -> None
    dialog = builder.get_object('totp-enroll-dialog')
    error_label = builder.get_object('totp-error-label')
    cancel_button = builder.get_object('totp-cancel-button')
    submit_button = builder.get_object('totp-submit-button')

    try:
        two_factor_enroll_totp(oauth, meta.api_base_uri, secret=secret, key=key)
    except Exception as e:
        error = e
        GLib.idle_add(lambda: error_label.set_markup('<span color="red" size="large">{}</span>'.format(error)))
        GLib.idle_add(lambda: submit_button.set_sensitive(True))
        GLib.idle_add(lambda: cancel_button.set_sensitive(True))
        raise
    else:
        GLib.idle_add(lambda: finalizing_step(meta=meta, builder=builder, config_dict=config_dict,
                                              lets_connect=lets_connect))
        GLib.idle_add(lambda: dialog.hide())
