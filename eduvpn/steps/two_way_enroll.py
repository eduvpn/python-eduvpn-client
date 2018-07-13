import logging
from future.moves.urllib.parse import urlparse
import qrcode
import gi
from gi.repository import GLib
from eduvpn.exceptions import EduvpnException
from eduvpn.util import pil2pixbuf
from eduvpn.remote import two_factor_enroll_totp
from eduvpn.crypto import gen_base32
from eduvpn.util import error_helper, thread_helper
from eduvpn.steps.finalize import finalizing_step

logger = logging.getLogger(__name__)


# ui thread
def two_fa_enroll_window(builder, oauth, meta, config_dict, secret=None):
    """finalise the add profile flow, add a configuration"""
    dialog = builder.get_object('2fa-enroll-dialog')
    window = builder.get_object('eduvpn-window')
    dialog.set_transient_for(window)
    dialog.show_all()
    thread_helper(lambda: _make_qr(meta=meta, oauth=oauth, builder=builder, config_dict=config_dict, secret=secret))


# background thread
def _make_qr(builder, oauth, meta, config_dict, secret=None):
    image = builder.get_object('qr-image')
    if not secret:
        secret = gen_base32()
    host = urlparse(meta.api_base_uri).netloc
    uri = "otpauth://totp/{host}?secret={secret}&issuer={host}".format(host=host, secret=secret)
    img = qrcode.make(uri)
    pixbuf = pil2pixbuf(img)
    image.set_from_pixbuf(pixbuf)
    thread_helper(lambda: _show_qr(builder, oauth, meta, config_dict=config_dict, secret=secret))


# ui thread
def _show_qr(builder, oauth, meta, config_dict, secret):
    dialog = builder.get_object('2fa-enroll-dialog')
    code_entry = builder.get_object('code-entry')

    while True:
        response = dialog.run()
        #dialog.hide()
        if response == 0:
            key = code_entry.get_text()
            thread_helper(lambda: _enroll(builder, oauth, meta, config_dict, secret, key))
        else:
            break


# background tread
def _enroll(builder, oauth, meta, config_dict, secret, key):
    error_label = builder.get_object('error-label')
    dialog = builder.get_object('2fa-enroll-dialog')
    try:
        two_factor_enroll_totp(oauth, meta.api_base_uri, secret=secret, key=key)
    except EduvpnException as e:
        GLib.idle_add(lambda: error_label.set_markup('<span color="red" size="large">{}</span>'.format(e)))
    except Exception as e:
        error = e
        GLib.idle_add(
            lambda: error_helper(dialog, "can't enroll", "{}: {}".format(type(error).__name__, str(error))))
    else:
        GLib.idle_add(lambda: finalizing_step(meta=meta, builder=builder, config_dict=config_dict))
        GLib.idle_add(lambda: dialog.hide())