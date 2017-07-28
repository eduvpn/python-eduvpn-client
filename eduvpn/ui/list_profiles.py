import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class ProfileListWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="EduVPN client")
        self.set_border_width(10)
        box_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(box_outer)
        label = Gtk.Label("Please select a profile")
        box_outer.pack_start(label, True, True, 0)

        self.listbox = Gtk.ListBox()
        box_outer.pack_start(self.listbox, True, True, 0)

    def update_list(self, profiles):
        for profile in profiles:
            row = Gtk.ListBoxRow()
            row.profile_id = profile['profile_id']
            row.add(Gtk.Label(profile['display_name']))
            self.listbox.add(row)
        self.listbox.show_all()


def main():
    window = ProfileListWindow()
    window.show_all()
    Gtk.main()


if __name__ == '__main__':
    main()