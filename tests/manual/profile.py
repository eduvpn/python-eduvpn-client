from eduvpn.main import init
from eduvpn.steps.profile import _select_profile_step
from tests.online import get_oauth_token, check_online_tests, disable_2fa
from gi.repository import Gtk
from pyotp import TOTP


INSTANCE_URI = "https://vpn.tuxed.net"
user, password = check_online_tests()
oauth, meta = get_oauth_token(user, password, INSTANCE_URI)
config_dict = {}

edu_vpn_app = init()
profiles = [['profile_1', 'profile_id_1', False, ''], ['profile_2', 'profile_id_2', True, 'totp,yubi']]
_select_profile_step(edu_vpn_app.builder, oauth=oauth, meta=meta, profiles=profiles)
Gtk.main()
