from __future__ import print_function
import gi
import logging
import threading

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from eduvpn.config import read as read_config
from eduvpn.crypto import gen_code_verifier, make_verifier
from eduvpn.local_oauth2 import get_open_port, create_oauth_session, get_oauth_token_code
from eduvpn.openvpn import format_like_ovpn
from eduvpn.remote import get_instances, get_instance_info, create_keypair, get_profile_config, get_auth_url, profile_list

logger = logging.getLogger(__name__)


class InstanceBoxRow(Gtk.ListBoxRow):
    def __init__(self, display_name, base_uri):
        super(Gtk.ListBoxRow, self).__init__()
        self.display_name = display_name
        self.base_uri = base_uri
        self.add(Gtk.Label(display_name))


class ListBoxWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="EduVPN client")
        self.set_border_width(10)

        box_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(box_outer)

        label = Gtk.Label("Please select an instance")

        box_outer.pack_start(label, True, True, 0)

        self.instances_listbox = Gtk.ListBox()

        config = read_config()
        self.discovery_uri = config['eduvpn']['discovery_uri']
        key = config['eduvpn']['key']
        self.verifier = make_verifier(key)

        self.instances_listbox.connect('row-activated', self.instance_selected)

        box_outer.pack_start(self.instances_listbox, True, True, 0)
        self.instances_listbox.show_all()

        self.update_instances()

    def get_oauth_token_code_in_thread(self, auth_url, port):
        def inner(auth_url, port):
            code = get_oauth_token_code(auth_url, port)
            logger.info("calling callback")
            self.we_have_oauth_token(code)
        thread = threading.Thread(target=inner, args=(auth_url, port))
        thread.start()
        logger.info("thread running in background")


    def update_instances(self):
        for display_name, base_uri, logo in get_instances(self.discovery_uri, self.verifier):
            row = InstanceBoxRow(display_name, base_uri)
            self.instances_listbox.add(row)

    def instance_selected(self, widget, row):
        self.instance_info = get_instance_info(row.base_uri, self.verifier)
        auth_endpoint = self.instance_info['authorization_endpoint']
        self.code_verifier = gen_code_verifier()
        port = get_open_port()
        self.oauth = create_oauth_session(port)
        auth_url = get_auth_url(self.oauth, self.code_verifier, auth_endpoint)
        self.get_oauth_token_code_in_thread(auth_url=auth_url, port=port)

    def we_have_oauth_token(self, code):
        token_endpoint = self.instance_info['token_endpoint']
        api_base_uri = self.instance_info['api_base_uri']
        token = self.oauth.fetch_token(token_endpoint, code=code, code_verifier=self.code_verifier)
        cert, key = create_keypair(self.oauth, api_base_uri)
        profile_config = get_profile_config(self.oauth, api_base_uri, profile_id)


logging.basicConfig(level=logging.INFO)
win = ListBoxWindow()
win.connect("delete-event", Gtk.main_quit)
win.show_all()
Gtk.main()
