import os
import gi
import logging
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from eduvpn.nm import list_vpn

logger = logging.getLogger(__name__)
here = os.path.dirname(__file__)


class EduVpnApp:
    def add_config(self, button):
        logger.info("add configuration clicked")
        instances_dialog = self.builder.get_object('instances-dialog')
        instances_overlay = self.builder.get_object('instances-overlay')
        instances_overlay.show()
        instances_dialog.set_modal(True)
        instances_dialog.set_transient_for(self.window)
        response = instances_dialog.run()
        print(response)
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

        for vpn in list_vpn():
            self.config_list.append((vpn,))

        self.window.set_position(Gtk.WindowPosition.CENTER)

        self.window.show_all()


def main():
    logging.basicConfig(level=logging.INFO)
    eduVpnApp = EduVpnApp()
    Gtk.main()

if __name__ == '__main__':
    main()
