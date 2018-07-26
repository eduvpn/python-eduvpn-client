from eduvpn.main import init
from gi.repository import Gtk

edu_vpn_app = init()
dialog = edu_vpn_app.builder.get_object('fetch-dialog')
window = edu_vpn_app.builder.get_object('eduvpn-window')
dialog.set_transient_for(window)
dialog.run()
dialog.hide()
Gtk.main()


