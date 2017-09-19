import logging
import webbrowser

import gi
from gi.repository import GLib

from eduvpn.util import error_helper, thread_helper
from eduvpn.crypto import gen_code_verifier
from eduvpn.oauth2 import get_open_port, create_oauth_session, get_oauth_token_code
from eduvpn.remote import get_instance_info, get_auth_url
from eduvpn.steps.profile import fetch_profile_step

logger = logging.getLogger(__name__)


def browser_step(builder, meta, verifier):
    """The notorious browser step. starts webserver, wait for callback, show token dialog"""
    logger.info("opening token dialog")
    dialog = builder.get_object('token-dialog')
    thread_helper(lambda: _phase1_background(meta=meta, dialog=dialog, verifier=verifier, builder=builder))
    dialog.show_all()


def _phase1_background(meta, dialog, verifier, builder):
    try:
        logger.info("starting token obtaining in background")
        r = get_instance_info(meta.instance_base_uri, verifier)
        meta.api_base_uri, meta.authorization_endpoint, meta.token_endpoint = r
        code_verifier = gen_code_verifier()
        port = get_open_port()
        oauth = create_oauth_session(port)
        auth_url = get_auth_url(oauth, code_verifier, meta.authorization_endpoint)
    except Exception as e:
        GLib.idle_add(lambda: error_helper(dialog, "Can't create oauth session", "{}".format(str(e))))
        GLib.idle_add(lambda: dialog.hide())
    else:
        GLib.idle_add(lambda: _phase1_callback(meta, port, code_verifier, oauth, auth_url, dialog, builder))


def _phase1_callback(meta, port, code_verifier, oauth, auth_url, dialog, builder):
    thread_helper(lambda: _phase2_background(meta=meta, port=port, oauth=oauth, code_verifier=code_verifier,
                                             auth_url=auth_url, dialog=dialog, builder=builder))
    _show_dialog(dialog, auth_url, builder)


def _show_dialog(dialog, auth_url, builder):
    url_field = builder.get_object('redirect-url-entry')
    url_dialog = builder.get_object('redirecturl-dialog')
    while True:
        response = dialog.run()
        if response == 0:  # cancel
            logger.info("token dialog: cancel button pressed")
            dialog.hide()
            break
        elif response == 1:
            logger.info("token dialog: reopen browser button pressed, opening {} again".format(auth_url))
            webbrowser.open(auth_url)
        elif response == 2:
            logger.info("token dialog: show redirect URL button pressed")
            url_field.set_text(auth_url)
            url_dialog.run()
            logger.info("token dialog: url popup closed")
            url_dialog.hide()
        else:
            logger.info("token dialog: window closed")
            dialog.hide()
            break


def _phase2_background(meta, port, oauth, code_verifier, auth_url, dialog, builder):
    try:
        logger.info("opening browser with url {}".format(auth_url))
        webbrowser.open(auth_url)
        code = get_oauth_token_code(port)
        logger.info("control returned by browser")
        token = oauth.fetch_token(meta.token_endpoint, code=code, code_verifier=code_verifier)
    except Exception as e:
        GLib.idle_add(lambda: error_helper(dialog, "Can't obtain token", "{}".format(str(e))))
        GLib.idle_add(lambda: dialog.hide())
        raise
    else:
        token['token_endpoint'] = meta.token_endpoint
        logger.info("obtained oauth token")
        meta.token = token
        GLib.idle_add(lambda: _phase2_callback(meta=meta, oauth=oauth,  dialog=dialog, builder=builder))


def _phase2_callback(meta, oauth, dialog, builder):
    url_dialog = builder.get_object('redirecturl-dialog')
    logger.info("hiding url dialog")
    GLib.idle_add(lambda: url_dialog.hide())
    logger.info("hiding token dialog")
    GLib.idle_add(lambda: dialog.hide())
    fetch_profile_step(meta=meta, oauth=oauth, builder=builder)
