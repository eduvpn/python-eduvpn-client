import logging
from future.moves.urllib.parse import urlparse
import qrcode
import gi
from gi.repository import GLib
from eduvpn.util import pil2pixbuf
from eduvpn.remote import two_factor_enroll_totp
from eduvpn.crypto import gen_base32
from eduvpn.util import thread_helper
from eduvpn.steps.finalize import finalizing_step

logger = logging.getLogger(__name__)


# ui thread
def totp_enroll_window(builder, oauth, meta, config_dict, secret=None):
    dialog = builder.get_object('totp-enroll-dialog')
    window = builder.get_object('eduvpn-window')
    dialog.set_transient_for(window)
    cancel_button = builder.get_object('totp-cancel-button')
    submit_button = builder.get_object('totp-submit-button')

    cancel_button.set_sensitive(False)
    submit_button.set_sensitive(False)

    dialog.show_all()
    GLib.idle_add(lambda: _make_qr(meta=meta, oauth=oauth, builder=builder, config_dict=config_dict, secret=secret))


# background thread
def _make_qr(builder, oauth, meta, config_dict, secret=None):
    image = builder.get_object('totp-qr-image')
    if not secret:
        secret = gen_base32()
    host = urlparse(meta.api_base_uri).netloc
    uri = "otpauth://totp/{host}?secret={secret}&issuer={host}".format(host=host, secret=secret)
    img = qrcode.make(uri)
    pixbuf = pil2pixbuf(img)
    image.set_from_pixbuf(pixbuf)
    GLib.idle_add(lambda: _parse_user_input(builder, oauth, meta, config_dict=config_dict, secret=secret))


# ui thread
def _parse_user_input(builder, oauth, meta, config_dict, secret=None):
    dialog = builder.get_object('totp-enroll-dialog')
    code_entry = builder.get_object('totp-code-entry')
    cancel_button = builder.get_object('totp-cancel-button')
    submit_button = builder.get_object('totp-submit-button')

    cancel_button.set_sensitive(True)
    submit_button.set_sensitive(True)
    while True:
        response = dialog.run()
        if response == 0:
            key = code_entry.get_text()
            cancel_button.set_sensitive(False)
            submit_button.set_sensitive(False)
            thread_helper(lambda: _enroll(builder, oauth, meta, config_dict, secret, key))
        else:
            dialog.hide()
            break


# background tread
def _enroll(builder, oauth, meta, config_dict, secret, key):
    dialog = builder.get_object('totp-enroll-dialog')
    error_label = builder.get_object('totp-error-label')
    cancel_button = builder.get_object('totp-cancel-button')
    submit_button = builder.get_object('totp-submit-button')

    try:
        two_factor_enroll_totp(oauth, meta.api_base_uri, secret=secret, key=key)
    except Exception as e:
        GLib.idle_add(lambda: error_label.set_markup('<span color="red" size="large">{}</span>'.format(e)))
        GLib.idle_add(lambda: submit_button.set_sensitive(True))
        GLib.idle_add(lambda: cancel_button.set_sensitive(True))
        raise
    else:
        GLib.idle_add(lambda: finalizing_step(meta=meta, builder=builder, config_dict=config_dict))
        GLib.idle_add(lambda: dialog.hide())
