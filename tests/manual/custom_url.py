from eduvpn.main import init
from eduvpn.steps.custom_url import custom_url
from eduvpn.metadata import Metadata
from gi.repository import Gtk


edu_vpn_app = init()
custom_url(builder=edu_vpn_app.builder, meta=Metadata(), verifier=edu_vpn_app.verifier)
Gtk.main()
