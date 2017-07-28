import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class TokenWaitWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="EduVPN client")
        self.set_border_width(10)
        box_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(box_outer)
        label = Gtk.Label("Waiting for callback from browser")
        box_outer.pack_start(label, True, True, 0)

        self.button = Gtk.Button(label="open webbrower again")
        box_outer.pack_start(self.button, True, True, 0)


def main():
    window = TokenWaitWindow()
    window.show_all()
    Gtk.main()


if __name__ == '__main__':
    main()