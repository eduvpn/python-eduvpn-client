from eduvpn.main import init
from eduvpn.steps.two_way_auth import _choice_window
from tests.online import get_oauth_token, check_online_tests, disable_2fa
from gi.repository import Gtk
from pyotp import TOTP

INSTANCE_URI = "https://debian-vpn.tuxed.net"
TOTP_SECRET = "QXU5GXJ3Y3Z7TCZG"
user, password = check_online_tests()
disable_2fa(user, password, TOTP_SECRET, INSTANCE_URI)
oauth, meta = get_oauth_token(user, password, INSTANCE_URI)
config_dict = {}
totp = TOTP(TOTP_SECRET)

edu_vpn_app = init()
_choice_window(builder=edu_vpn_app.builder, oauth=oauth, meta=meta, config_dict=config_dict, options=['yubi', 'totp'])
Gtk.main()
