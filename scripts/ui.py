import os
import gi
import logging
import time
import threading
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GObject
from eduvpn.nm import list_vpn
from eduvpn.remote import get_instances
from eduvpn.config import read as read_config

logger = logging.getLogger(__name__)
here = os.path.dirname(__file__)


class EduVpnApp:
    def add_config(self, button):
        logger.info("add configuration clicked")
        instances_dialog = self.builder.get_object('instances-dialog')
        instances_overlay = self.builder.get_object('instances-overlay')
        instances_model = self.builder.get_object('instances-model')
        instances_selection = self.builder.get_object('instances-selection')
        instances_model.clear()
        instances_dialog.show_all()

        def update_instances(instance):
            instances_model.append(instance)
            return False  # needs to return False to be removed from update queue

        def example_target():
            for instance in list(get_instances(discovery_uri=self.config['discovery_uri'],
                                               verify_key=self.config['verify_key'])):
                GLib.idle_add(update_instances, instance)

        thread = threading.Thread(target=example_target)
        thread.daemon = True
        thread.start()

        instances_overlay.show_all()

        response = instances_dialog.run()
        if response == 0:  # cancel
            logging.info("cancel button pressed")
        else:
            model, treeiter = instances_selection.get_selected()
            if treeiter != None:
                print(model[treeiter])
        instances_dialog.hide()

    def del_config(self, button):
        logger.info("del configuration clicked")
        dialog = Gtk.MessageDialog(self.window, Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION,
                                   Gtk.ButtonsType.YES_NO, "Are you sure you want to remove this configuration?")
        dialog.format_secondary_text("This action can't be undone.")
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            logger.info("QUESTION dialog closed by clicking YES button")
        elif response == Gtk.ResponseType.NO:
            logger.info("QUESTION dialog closed by clicking NO button")
        dialog.destroy()

    def select_config(self, something):
        logger.info("a configuration was selected")

    def __init__(self):
        handlers = {
            "delete_window": Gtk.main_quit,
            "add_config": self.add_config,
            "del_config": self.del_config,
            "select_config": self.select_config,
        }

        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(here, "../data/eduvpn.ui"))
        self.builder.connect_signals(handlers)

        self.window = self.builder.get_object('eduvpn-window')
        self.config_list = self.builder.get_object('configs-model')

        self.config = read_config()

        for vpn in list_vpn():
            self.config_list.append((vpn,))

        self.window.set_position(Gtk.WindowPosition.CENTER)

        self.window.show_all()


def main():
    GObject.threads_init()
    logging.basicConfig(level=logging.INFO)
    eduVpnApp = EduVpnApp()
    Gtk.main()

if __name__ == '__main__':
    main()
