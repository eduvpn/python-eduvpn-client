from __future__ import print_function
import gi
import logging
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


logger = logging.getLogger(__name__)


class InstanceBoxRow(Gtk.ListBoxRow):
    def __init__(self, display_name, base_uri):
        super(Gtk.ListBoxRow, self).__init__()
        self.display_name = display_name
        self.base_uri = base_uri
        self.add(Gtk.Label(display_name))


class AddVpnWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="EduVPN client")
        self.set_border_width(10)

        box_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(box_outer)

        label = Gtk.Label("Please select an instance")

        box_outer.pack_start(label, True, True, 0)

        self.instances_listbox = Gtk.ListBox()

        box_outer.pack_start(self.instances_listbox, True, True, 0)
        self.instances_listbox.show_all()

    def update_instances(self, instances):
        for display_name, base_uri, logo in instances:
            row = InstanceBoxRow(display_name, base_uri)
            self.instances_listbox.add(row)


def main():
    logging.basicConfig(level=logging.INFO)
    win = AddVpnWindow()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == '__main__':
    main()