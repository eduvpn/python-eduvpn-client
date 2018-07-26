from eduvpn.main import init
from eduvpn.steps.browser import _show_dialog
from gi.repository import Gtk

edu_vpn_app = init()
dialog = edu_vpn_app.builder.get_object('token-dialog')
_show_dialog(dialog, auth_url="", builder=edu_vpn_app.builder)
Gtk.main()
