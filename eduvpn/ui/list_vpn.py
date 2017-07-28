from os import path
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from eduvpn.nm import list_vpn


def refresh(widget, event, name):
    print("refresh clicked for {}".format(name))


def make_connection_row(name):
    row = Gtk.ListBoxRow()
    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
    row.add(hbox)
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    hbox.pack_start(vbox, True, True, 0)

    label1 = Gtk.Label(name, xalign=0)
    vbox.pack_start(label1, True, True, 0)

    refresh_button = Gtk.Button(label="refresh", valign=Gtk.Align.CENTER)
    delete_button = Gtk.Button(label="delete", valign=Gtk.Align.CENTER)
    refresh_button.connect('button-press-event', refresh, name)
    hbox.pack_start(refresh_button, False, True, 0)
    hbox.pack_start(delete_button, False, True, 0)
    return row


class ListVpnWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="EduVPN client")
        self.set_border_width(10)
        box_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(box_outer)
        label = Gtk.Label("List of existing OpenVPN configurations")
        box_outer.pack_start(label, True, True, 0)

        self.config_listbox = Gtk.ListBox()
        box_outer.pack_start(self.config_listbox, True, True, 0)

        self.add_button = Gtk.Button(label='Add connection')
        box_outer.pack_start(self.add_button, True, True, 0)

    def update_list(self):
        for child in self.config_listbox.get_children():
            self.config_listbox.remove(child)

        for vpn in list_vpn():
            self.config_listbox.add(make_connection_row(vpn))
        self.config_listbox.show_all()



def main():
    window = ListVpnWindow()
    window.show_all()
    Gtk.main()


if __name__ == '__main__':
    main()