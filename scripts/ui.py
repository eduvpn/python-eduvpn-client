import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject

here = os.path.dirname(__file__)


class EduVpnApp:
    def add_configuration(self, button):
        print("add configuration clicked")
        self.stack.set_visible_child_name('instance_page')

    def __init__(self):
        handlers = {
            "onDeleteWindow": Gtk.main_quit,
            "addConfiguration": self.add_configuration,
        }

        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(here, "../data/eduvpn.glade"))
        self.builder.connect_signals(handlers)

        self.window = self.builder.get_object('main_window')
        self.stack = self.builder.get_object('main_stack')
        self.config_list = self.builder.get_object('configlist')
        self.config_list.append((u'gijs',))
        self.window.show_all()


if __name__ == '__main__':
    eduVpnApp = EduVpnApp()
    Gtk.main()