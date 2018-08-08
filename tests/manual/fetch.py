from eduvpn.main import init
from gi.repository import Gtk

from eduvpn.steps.fetching import fetching_window

edu_vpn_app = init()
fetching_window(edu_vpn_app.builder, lets_connect=True)
dialog = edu_vpn_app.builder.get_object('fetch-dialog')
dialog.run()
dialog.hide()
Gtk.main()
