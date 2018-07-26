import logging
from builtins import chr
import gi
from gi.repository import GLib, Gdk
from eduvpn.remote import two_factor_enroll_yubi
from eduvpn.util import thread_helper
from eduvpn.steps.finalize import finalizing_step


logger = logging.getLogger(__name__)


# ui thread
def yubi_enroll_window(builder, oauth, meta, config_dict):
    """finalise the add profile flow, add a configuration"""
    dialog = builder.get_object('yubi-enroll-dialog')
    window = builder.get_object('eduvpn-window')
    dialog.set_transient_for(window)
    cancel_button = builder.get_object('yubi-cancel-button')
    submit_button = builder.get_object('yubi-submit-button')

    cancel_button.set_sensitive(False)
    submit_button.set_sensitive(False)

    dialog.show_all()
    _parse_user_input(builder, oauth, meta, config_dict)


# ui thread
def _parse_user_input(builder, oauth, meta, config_dict):
    dialog = builder.get_object('yubi-enroll-dialog')
    code_entry = builder.get_object('yubi-code-entry')
    cancel_button = builder.get_object('yubi-cancel-button')
    submit_button = builder.get_object('yubi-submit-button')

    def callback(_, event):
        valid = chr(event.keyval).isdigit()
        logger.debug("user pressed {}, valid: {}".format(event.keyval, valid))
        if event.keyval in (Gdk.KEY_Left, Gdk.KEY_Right, Gdk.KEY_BackSpace, Gdk.KEY_End, Gdk.KEY_Home,
                            Gdk.KEY_Delete, Gdk.KEY_Return, Gdk.KEY_Escape):
            return False
        return event.keyval not in range(0x20, 0x7e)

    code_entry.connect("key-press-event", callback)
    cancel_button.set_sensitive(True)
    submit_button.set_sensitive(True)
    while True:
        response = dialog.run()
        if response == 0:
            key = code_entry.get_text()
            cancel_button.set_sensitive(False)
            submit_button.set_sensitive(False)
            thread_helper(lambda: _enroll(builder, oauth, meta, config_dict, key))
        else:
            dialog.hide()
            break


# background tread
def _enroll(builder, oauth, meta, config_dict, key):
    error_label = builder.get_object('yubi-error-label')
    dialog = builder.get_object('yubi-enroll-dialog')
    cancel_button = builder.get_object('yubi-cancel-button')
    submit_button = builder.get_object('yubi-submit-button')

    try:
        two_factor_enroll_yubi(oauth, meta.api_base_uri, yubi_key_otp=key)
    except Exception as e:
        error = e
        GLib.idle_add(lambda: error_label.set_markup('<span color="red" size="large">{}</span>'.format(error)))
        GLib.idle_add(lambda: submit_button.set_sensitive(True))
        GLib.idle_add(lambda: cancel_button.set_sensitive(True))
        raise
    else:
        GLib.idle_add(lambda: finalizing_step(meta=meta, builder=builder, config_dict=config_dict))
        GLib.idle_add(lambda: dialog.hide())
