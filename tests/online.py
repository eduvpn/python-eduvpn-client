from os import environ
import logging
from future.moves.urllib.parse import urlparse
from eduvpn.exceptions import EduvpnAuthException
from eduvpn.metadata import Metadata
from eduvpn.crypto import gen_code_verifier
from eduvpn.oauth2 import get_open_port, create_oauth_session, get_oauth_token_code
from eduvpn.remote import (get_instance_info, get_auth_url)


logger = logging.getLogger(__name__)


def check_online_tests():
    if "EDUVPN_TEST_ONLINE" in environ and environ["EDUVPN_TEST_ONLINE"].lower() == "true":
        user = environ["EDUVPN_TEST_USER"]
        password = environ["EDUVPN_TEST_PASSWORD"]
        return user, password
    else:
        return False


if check_online_tests():
    import mechanicalsoup
    from pyotp import TOTP
    from concurrent.futures import ThreadPoolExecutor


def disable_2fa(user, password, totp_secret, base_url):
    prefix = "/vpn-admin-portal"
    admin_url = base_url + prefix
    browser = mechanicalsoup.StatefulBrowser(raise_on_404=True)
    logger.info("opening auth_url")
    response = browser.open(admin_url)
    assert response.ok
    browser.select_form()
    browser["userName"] = user
    browser["userPass"] = password
    logger.info("logging in")
    response = browser.submit_selected()
    assert response.ok
    form = browser.select_form()
    if form.form.attrs['action'] != prefix + '/_two_factor/auth/verify/totp':
        logger.warning("2fa not enabled")
        return

    # redirected to totp screen
    totp = TOTP(totp_secret)
    browser['_two_factor_auth_totp_key'] = totp.now()
    logger.info("submitting totp key")
    response = browser.submit_selected()
    assert response.ok

    form = browser.select_form()
    if form.form.attrs['action'] == prefix + '/_two_factor/auth/verify/totp':
        error = browser.get_current_page().findAll("p", {"class": "error"})[0].contents[0].strip()
        raise EduvpnAuthException(error)

    response = browser.open("{}/user?user_id={}".format(admin_url, user))
    assert response.ok
    form = browser.select_form()
    button = form.form.select('button[value="deleteTotpSecret"]')
    if button:
        response = browser.submit_selected()
        assert(response.ok)
    else:
        logger.error(form.form)
        logger.error("2fa not enabled, but had to supply otp during login")


def authorize(auth_url, user, password):
    browser = mechanicalsoup.StatefulBrowser(raise_on_404=True)
    logger.info("opening auth_url")
    response = browser.open(auth_url)
    assert(response.ok)
    browser.select_form('form[action="/vpn-user-portal/_form/auth/verify"]')
    browser["userName"] = user
    browser["userPass"] = password
    logger.info("logging in")
    response = browser.submit_selected()
    assert(response.ok)
    form = browser.select_form()
    if 'action' in form.form.attrs and form.form.attrs['action'] == '/vpn-user-portal/_two_factor/auth/verify/totp':
        raise EduvpnAuthException("otp enabled")
    assert(urlparse(browser.get_url()).path == "/vpn-user-portal/_oauth/authorize")  # make sure is the right page
    form = browser.select_form()
    form.form.select('button[value="yes"]')
    logger.info("authorising app")
    response = browser.submit_selected()
    assert(response.ok)


def get_oauth_token(user, password, instance_uri):
    meta = Metadata()
    meta.api_base_uri, meta.authorization_endpoint, meta.token_endpoint = get_instance_info(instance_uri=instance_uri)
    meta.refresh_token()
    code_verifier = gen_code_verifier()
    port = get_open_port()
    oauth = create_oauth_session(port, auto_refresh_url=meta.token_endpoint)
    auth_url, state = get_auth_url(oauth, code_verifier, meta.authorization_endpoint)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(get_oauth_token_code, port, timeout=5)
        authorize(auth_url, user, password)
        code, other_state = future.result()

    assert(state == other_state)
    meta.token = oauth.fetch_token(meta.token_endpoint, code=code, code_verifier=code_verifier, client_id=oauth.client_id, include_client_id=True)
    return oauth, meta