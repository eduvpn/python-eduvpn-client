import logging
import os
import threading
import webbrowser

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, Gtk, GLib

from eduvpn.config import read as read_config, secure_internet_uri, institute_access_uri, verify_key
from eduvpn.crypto import make_verifier, gen_code_verifier
from eduvpn.oauth2 import get_open_port, create_oauth_session, get_oauth_token_code
from eduvpn.managers import connect_provider, list_providers, store_provider, delete_provider
from eduvpn.remote import get_instances, get_instance_info, get_auth_url, list_profiles, create_keypair, \
    get_profile_config

logger = logging.getLogger(__name__)
here = os.path.dirname(__file__)


class EduVpnApp:
    def __init__(self):
        # intermediate placeholder
        self.api_base_uri = None
        self.oauth = None
        self.auth_url = None
        self.instance_name = None

        handlers = {
            "delete_window": Gtk.main_quit,
            "add_config": self.select_profile,
            "del_config": self.delete,
            "connect": self.connect,
            "disconnect": self.disconnect,
            "select_config": self.select_config,
        }

        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(here, "../share/eduvpn/eduvpn.ui"))
        self.builder.connect_signals(handlers)

        self.window = self.builder.get_object('eduvpn-window')
        self.config_list = self.builder.get_object('configs-model')

        self.config = read_config()
        self.verifier = make_verifier(self.config['verify_key'])

        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.show_all()
        self.update_providers()

    def connect(self, selection):
        logger.info("connect pressed")
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            name = model[treeiter][0]
            connect_provider(name)

    def disconnect(self, selection):
        logger.info("disconnect pressed")
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            name = model[treeiter][0]

    def update_providers(self):
        self.config_list.clear()
        for provider in list_providers():
            self.config_list.append((provider,))

    def select_profile(self, _):
        logger.info("add configuration clicked")
        profile_dialog = self.builder.get_object('profile-dialog')
        profile_dialog.show_all()

        response = profile_dialog.run()
        profile_dialog.hide()

        if response == 0:  # cancel
            logger.info("cancel button pressed")
            return
        elif response == 1:
            logger.info("secure button pressed")
            self.select_instance(discovery_uri=secure_internet_uri)
        elif response == 2:
            logger.info("institute button pressed")
            self.select_instance(discovery_uri=institute_access_uri)

        elif response == 3:
            logger.info("custom button pressed")
            self.custom_url()

    def custom_url(self):
        dialog = self.builder.get_object('custom-url-dialog')
        entry = self.builder.get_object('custom-url-entry')
        dialog.show_all()
        response = dialog.run()
        dialog.hide()
        if response == 0:  # cancel
            logger.info("cancel button pressed")
            return
        else:
            custom_url = entry.get_text()
            logger.info("ok pressed, entry text: {}".format(custom_url))
            self.select_instance(discovery_uri=custom_url)

    def select_instance(self, discovery_uri):
        logger.info("add configuration clicked")
        instances_dialog = self.builder.get_object('instances-dialog')
        instances_overlay = self.builder.get_object('instances-overlay')
        instances_model = self.builder.get_object('instances-model')
        instances_selection = self.builder.get_object('instances-selection')
        instances_model.clear()
        instances_dialog.show_all()

        def update(instance):
            instances_model.append(instance)
            return False  # needs to return False to be removed from update queue

        def error(exception):
            dialog = Gtk.MessageDialog(instances_dialog, 0, Gtk.MessageType.INFO,
                                       Gtk.ButtonsType.OK, "Can't retrieve list of instances")
            dialog.format_secondary_text(str(exception))
            dialog.run()
            dialog.hide()
            instances_dialog.hide()

        def background():
            try:
                instances = list(get_instances(discovery_uri=discovery_uri, verify_key=self.verifier))
            except Exception as e:
                GLib.idle_add(error, e)
            else:
                for instance in instances:
                    GLib.idle_add(update, instance)

        thread = threading.Thread(target=background)
        thread.daemon = True
        thread.start()

        instances_overlay.show_all()

        response = instances_dialog.run()
        instances_dialog.hide()

        if response == 0:  # cancel
            logging.info("cancel button pressed")
        else:
            model, treeiter = instances_selection.get_selected()
            if treeiter:
                name, base_uri, _ = model[treeiter]
                self.token_step(name, base_uri)
            else:
                logger.info("nothing selected")

    def token_step(self, name, instance_base_uri):
        logger.info("opening token dialog")
        token_dialog = self.builder.get_object('token-dialog')
        token_dialog.show_all()

        def update():
            token_dialog.hide()
            self.profile_step()

        def background():
            self.instance_name = name
            instance_info = get_instance_info(instance_base_uri, self.verifier)
            auth_endpoint = instance_info['authorization_endpoint']
            token_endpoint = instance_info['token_endpoint']
            self.api_base_uri = instance_info['api_base_uri']
            code_verifier = gen_code_verifier()
            port = get_open_port()
            self.oauth = create_oauth_session(port)
            self.auth_url = get_auth_url(self.oauth, code_verifier, auth_endpoint)
            webbrowser.open(self.auth_url)
            code = get_oauth_token_code(port)
            token = self.oauth.fetch_token(token_endpoint, code=code, code_verifier=code_verifier)
            GLib.idle_add(update)

        thread = threading.Thread(target=background)
        thread.daemon = True
        thread.start()

        while True:
            response = token_dialog.run()
            if response == 0:  # cancel
                logger.info("token dialog: cancel button pressed")
                token_dialog.hide()
                break
            elif response == 1:
                logger.info("token dialog: reopen browser button pressed")
                webbrowser.open(self.auth_url)
            else:
                logger.info("token dialog: received callback response")
                break

    def profile_step(self):
        logger.info("opening profile dialog")
        profiles = list_profiles(self.oauth, self.api_base_uri)
        profile = profiles[0]
        cert, key = create_keypair(self.oauth, self.api_base_uri)
        profile_config = get_profile_config(self.oauth, self.api_base_uri, profile['profile_id'])
        store_provider(self.instance_name, profile_config, cert, key)
        self.update_providers()

    def delete(self, selection):
        logger.info("delete provider clicked")
        model, treeiter = selection.get_selected()
        if not treeiter:
            logger.info("nothing selected")
            return

        name = model[treeiter][0]

        dialog = Gtk.MessageDialog(self.window, Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION,
                                   Gtk.ButtonsType.YES_NO, "Are you sure you want to remove '{}'?".format(name))
        dialog.format_secondary_text("This action can't be undone.")
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            logger.info("deleting provider config")
            delete_provider(name)
            self.update_providers()
        elif response == Gtk.ResponseType.NO:
            logger.info("not deleting provider config")
        dialog.destroy()

    def select_config(self, something):
        logger.info("a configuration was selected")


def main():
    GObject.threads_init()
    logging.basicConfig(level=logging.INFO)
    eduVpnApp = EduVpnApp()
    Gtk.main()