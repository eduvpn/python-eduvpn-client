import logging
from future.moves.urllib.parse import urlparse
import qrcode
from eduvpn.exceptions import EduvpnException
from eduvpn.util import pil2pixbuf
from eduvpn.remote import two_factor_enroll_totp
from eduvpn.crypto import gen_base32


logger = logging.getLogger(__name__)


def two_fa_enroll_window(builder, oauth, meta, secret=None):
    dialog = builder.get_object('2fa-enroll-dialog')
    window = builder.get_object('eduvpn-window')
    dialog.set_transient_for(window)
    code_entry = builder.get_object('code-entry')
    error_label = builder.get_object('error-label')
    image = builder.get_object('qr-image')

    if not secret:
        secret = gen_base32()
    host = urlparse(meta.api_base_uri).netloc
    uri = "otpauth://totp/{host}?secret={secret}&issuer={host}".format(host=host, secret=secret)
    img = qrcode.make(uri)
    pixbuf = pil2pixbuf(img)
    image.set_from_pixbuf(pixbuf)

    while True:
        dialog.show_all()
        response = dialog.run()
        dialog.hide()
        if response == 0:
            key = code_entry.get_text()
            try:
                two_factor_enroll_totp(oauth, meta.api_base_uri, secret=secret, key=key)
            except EduvpnException as e:
                error_label.set_markup('<span color="red" size="large">{}</span>'.format(e))
            else:
                break
        else:
            break
