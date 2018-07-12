"""
This test suite only runs when EDUVPN_TEST_ONLINE, EDUVPN_TEST_USER and EDUVPN_TEST_PASSWORD are set
"""
from unittest import TestCase, skipIf
from pyotp import TOTP
from eduvpn.remote import two_factor_enroll_totp
from tests.online import get_oauth_token, check_online_tests, disable_2fa

online_tests = check_online_tests()

INSTANCE_URI = "https://debian-vpn.tuxed.net"
TOTP_SECRET = "QXU5GXJ3Y3Z7TCZG"


@skipIf(not online_tests, "Skipping online tests")
class OnlineTest(TestCase):
    def test_2fa_enroll(self):
        username, password = online_tests
        disable_2fa(username, password, totp_secret=TOTP_SECRET, base_url=INSTANCE_URI)
        oauth, meta = get_oauth_token(username, password, instance_uri=INSTANCE_URI)
        two_factor_enroll_totp(oauth, meta.api_base_uri, secret=TOTP_SECRET, key=TOTP(TOTP_SECRET).now())
        disable_2fa(username, password, totp_secret=TOTP_SECRET, base_url=INSTANCE_URI)
