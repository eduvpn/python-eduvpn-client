from __future__ import print_function
import NetworkManager
import gi
import logging
from os import path

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

logger = logging.getLogger(__name__)


def list_vpn():
    all_connections = NetworkManager.Settings.ListConnections()
    vpn_connections = [c for c in all_connections if c.GetSettings()['connection']['type'] == 'vpn']
    return vpn_connections


class InstanceBoxRow(Gtk.ListBoxRow):
    def __init__(self, id):
        super(Gtk.ListBoxRow, self).__init__()
        self.id = id
        self.add(Gtk.Label(id))


class ListBoxWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="EduVPN client")
        self.set_border_width(10)

        box_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=60)
        self.add(box_outer)

        label = Gtk.Label("Please select an instance")

        box_outer.pack_start(label, True, True, 0)

        self.instances_listbox = Gtk.ListBox()

        image_path = path.join(path.dirname(path.realpath(__file__)), '../artwork/Schild2.png')
        image = Gtk.Image.new_from_file(image_path)

        self.set_default_icon_from_file(image_path)

        box_outer.pack_start(image, True, True, 0)

        self.instances_listbox.connect('row-activated', self.selected)

        box_outer.pack_start(self.instances_listbox, True, True, 0)
        self.instances_listbox.show_all()

        for vpn in list_vpn():
            id = vpn.GetSettings()['connection']['id']
            row = InstanceBoxRow(id)
            self.instances_listbox.add(row)

    def selected(self, widget, row):
        print(row)



logging.basicConfig(level=logging.INFO)
win = ListBoxWindow()
win.connect("delete-event", Gtk.main_quit)
win.show_all()
Gtk.main()
