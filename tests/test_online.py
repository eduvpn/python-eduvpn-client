"""
This test suite only runs when EDUVPN_TEST_ONLINE, EDUVPN_TEST_USER and EDUVPN_TEST_PASSWORD are set
"""
from os import environ
from unittest import TestCase, skipIf

ONLINE_TEST = False
if "EDUVPN_TEST_ONLINE" in environ and environ["EDUVPN_TEST_ONLINE"].lower() == "true":
    print("bla")
    ONLINE_TEST = True
    ONLINE_USER = environ["EDUVPN_TEST_USER"]
    ONLINE_PASSWORD = environ["EDUVPN_TEST_PASSWORD"]

    from eduvpn.metadata import Metadata
    from eduvpn.crypto import gen_code_verifier
    from eduvpn.oauth2 import get_open_port, create_oauth_session, get_oauth_token_code
    from eduvpn.remote import (get_instance_info, get_auth_url, list_profiles, user_info, get_profile_config,
                               create_keypair, two_factor_enroll_totp)
    from eduvpn.openvpn import format_like_ovpn, ovpn_to_nm, parse_ovpn
    from eduvpn.exceptions import EduvpnException

    import mechanicalsoup
    from concurrent.futures import ThreadPoolExecutor
    from pyotp import TOTP


REMOTE = "https://debian-vpn.tuxed.net"
TOTP_SECRET = "E5BIDDZR6TSDSKA3HW3L54S4UM5YGYUH"


def authorize(auth_url):
    browser = mechanicalsoup.StatefulBrowser(raise_on_404=True)
    browser.open(auth_url)
    browser.select_form('form[action="/vpn-user-portal/_form/auth/verify"]')
    browser["userName"] = ONLINE_USER
    browser["userPass"] = ONLINE_PASSWORD
    browser.submit_selected()
    form = browser.select_form()
    if form.form.attrs['action'] == '/vpn-user-portal/_two_factor/auth/verify/totp':
        totp = TOTP(TOTP_SECRET)
        browser['_two_factor_auth_totp_key'] = totp.now()
        browser.submit_selected()
    form = browser.select_form()
    form.form.select('button[value="yes"]')
    browser.submit_selected()


@skipIf(not ONLINE_TEST, "Skipping online tests")
class OnlineTest(TestCase):
    def test_2fa_enroll(self):
        meta = Metadata()
        meta.api_base_uri, meta.authorization_endpoint, meta.token_endpoint = get_instance_info(instance_uri=REMOTE)
        meta.refresh_token()
        code_verifier = gen_code_verifier()
        port = get_open_port()
        oauth = create_oauth_session(port, auto_refresh_url=meta.token_endpoint)
        auth_url, state = get_auth_url(oauth, code_verifier, meta.authorization_endpoint)

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(get_oauth_token_code, port)
            authorize(auth_url)
            code, other_state = future.result()

        self.assertEqual(state, other_state)
        meta.token = oauth.fetch_token(meta.token_endpoint, code=code, code_verifier=code_verifier)
        profiles = list_profiles(oauth, meta.api_base_uri)
        self.assertEqual(len(profiles), 1)
        meta.profile_display_name, meta.profile_id, meta.two_factor = profiles[0]
        info = user_info(oauth, meta.api_base_uri)
        self.assertFalse(info['is_disabled'])
        self.assertFalse(info['two_factor_enrolled'])
        cert, key = create_keypair(oauth, meta.api_base_uri)
        meta.cert = cert
        meta.key = key
        meta.config = get_profile_config(oauth, meta.api_base_uri, meta.profile_id)
        ovpn_text = format_like_ovpn(meta.config, meta.cert, meta.key)
        config_dict = parse_ovpn(ovpn_text)
        with self.assertRaises(EduvpnException):
            ovpn_to_nm(config_dict, meta=meta, display_name=meta.display_name, username=meta.username)

        with self.assertRaises(EduvpnException):
            # invalid totp key
            two_factor_enroll_totp(oauth, meta.api_base_uri, "bla", "bla")

        totp = TOTP(TOTP_SECRET)
        two_factor_enroll_totp(oauth, meta.api_base_uri, secret=TOTP_SECRET, key=totp.now())