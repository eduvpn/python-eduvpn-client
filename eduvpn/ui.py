import logging
import os
import threading
import webbrowser

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, Gtk, GLib, GdkPixbuf

from eduvpn.config import secure_internet_uri, institute_access_uri, verify_key
from eduvpn.crypto import make_verifier, gen_code_verifier
from eduvpn.oauth2 import get_open_port, create_oauth_session, get_oauth_token_code
from eduvpn.managers import connect_provider, list_providers, store_provider, delete_provider
from eduvpn.remote import get_instances, get_instance_info, get_auth_url, list_profiles, create_keypair, \
    get_profile_config

logger = logging.getLogger(__name__)


class EduVpnApp:
    def __init__(self, here):
        self.here = here

        handlers = {
            "delete_window": Gtk.main_quit,
            "add_config": self.selection_connection,
            "del_config": self.delete,
            "connect": self.connect,
            "disconnect": self.disconnect,
            "select_config": self.select_config,
        }

        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(self.here, "../share/eduvpn/eduvpn.ui"))
        self.builder.connect_signals(handlers)

        self.window = self.builder.get_object('eduvpn-window')
        self.verifier = make_verifier(verify_key)

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
        config_list = self.builder.get_object('configs-model')
        config_list.clear()
        for provider in list_providers():
            config_list.append((provider,))

    def selection_connection(self, _):
        logger.info("add configuration clicked")
        dialog = self.builder.get_object('connection-type-dialog')
        dialog.show_all()

        response = dialog.run()
        dialog.hide()

        if response == 0:  # cancel
            logger.info("cancel button pressed")
            return
        elif response == 1:
            logger.info("secure button pressed")
            self.select_instance(discovery_uri=secure_internet_uri, connection_type='secure_internet')
        elif response == 2:
            logger.info("institute button pressed")
            self.select_instance(discovery_uri=institute_access_uri, connection_type='institute_access')

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
            self.select_instance(discovery_uri=custom_url, connection_type='custom_url')

    def select_instance(self, discovery_uri, connection_type):
        logger.info("add configuration clicked")
        instances_dialog = self.builder.get_object('instances-dialog')
        instances_overlay = self.builder.get_object('instances-overlay')
        instances_model = self.builder.get_object('instances-model')
        instances_selection = self.builder.get_object('instances-selection')
        instances_model.clear()
        instances_dialog.show_all()

        # allow this to be overriden by background()
        authorization_type = None

        def update(instance):
            name, url, icon = instance
            pixbuf = GdkPixbuf.Pixbuf.new_for_string(icon)
            instances_model.append((name, url, pixbuf))
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
                authorization_type, instances = get_instances(discovery_uri=discovery_uri, verify_key=self.verifier)
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
                self.browser_step(name, base_uri, connection_type, authorization_type)
            else:
                logger.info("nothing selected")

    def error(self, exception, parent, msg):
        error_dialog = Gtk.MessageDialog(parent, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK, msg)
        error_dialog.format_secondary_text(str(exception))
        error_dialog.run()
        error_dialog.hide()
        parent.hide()

    def browser_step(self, name, instance_base_uri, connection_type, authorization_type):
        logger.info("opening token dialog")
        dialog = self.builder.get_object('token-dialog')
        dialog.show_all()

        # put this here so it can be overridden by background()
        auth_url = None

        def update(token, api_base_uri, oauth):
            dialog.hide()
            self.fetch_profile(token, api_base_uri, oauth, name, connection_type, authorization_type)

        def background():
            try:
                api_base_uri, authorization_endpoint, token_endpoint = get_instance_info(instance_base_uri,
                                                                                         self.verifier)
                code_verifier = gen_code_verifier()
                port = get_open_port()
                oauth = create_oauth_session(port)
                auth_url = get_auth_url(oauth, code_verifier, authorization_endpoint)
                webbrowser.open(auth_url)
                code = get_oauth_token_code(port)
                token = oauth.fetch_token(token_endpoint, code=code, code_verifier=code_verifier)

            except Exception as e:
                GLib.idle_add(self.error, e, dialog, e)
            else:
                GLib.idle_add(update, token, api_base_uri, oauth)

        thread = threading.Thread(target=background)
        thread.daemon = True
        thread.start()

        while True:
            response = dialog.run()
            if response == 0:  # cancel
                logger.info("token dialog: cancel button pressed")
                dialog.hide()
                break
            elif response == 1:
                logger.info("token dialog: reopen browser button pressed")
                webbrowser.open(auth_url)
            else:
                logger.info("token dialog: received callback response")
                break

    def fetch_profile(self, token, api_base_uri, oauth, name, connection_type, authorization_type):
        dialog = self.builder.get_object('fetch-profile-dialog')
        dialog.show_all()

        def update(profiles):
            dialog.hide()
            if len(profiles) > 1:
                self.select_profile_step(token, profiles, api_base_uri, oauth, name, connection_type,
                                         authorization_type)
            else:
                profile_display_name, profile_id, two_factor = profiles[0]
                cert, key = create_keypair(oauth, api_base_uri)
                config = get_profile_config(oauth, api_base_uri, profile_id)
                store_provider(name, config, cert, key, token, connection_type, authorization_type,
                               profile_display_name,
                               profile_id, two_factor)
                self.update_providers()

        def background():
            try:
                profiles = list_profiles(oauth, api_base_uri)
            except Exception as e:
                GLib.idle_add(self.error, e, dialog, e)
            else:
                GLib.idle_add(update, profiles)

    def select_profile_step(self, profiles, token, api_base_uri, oauth, name, connection_type, authorization_type):
        logger.info("opening profile dialog")

        dialog = self.builder.get_object('profiles-dialog')
        model = self.builder.get_object('profiles-model')
        selection = self.builder.get_object('profiles-selection')
        dialog.show_all()

        model.append(profiles)

        response = dialog.run()
        dialog.hide()

        if response == 0:  # cancel
            logging.info("cancel button pressed")
            return
        else:
            model, treeiter = selection.get_selected()
            if treeiter:
                profile_display_name, profile_id, two_factor = model[treeiter]
                cert, key = create_keypair(oauth, api_base_uri)
                config = get_profile_config(oauth, api_base_uri, profile_id)
                store_provider(name, config, cert, key, token, connection_type, authorization_type, profile_display_name,
                               profile_id, two_factor)
                self.update_providers()
            else:
                logger.error("nothing selected")
                return

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


def main(here):
    GObject.threads_init()
    logging.basicConfig(level=logging.INFO)
    eduVpnApp = EduVpnApp(here)
    Gtk.main()