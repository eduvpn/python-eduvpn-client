import logging
import os
import threading
import webbrowser

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')

from gi.repository import GObject, Gtk, GLib, GdkPixbuf, Notify, Gio

from eduvpn.config import secure_internet_uri, institute_access_uri, verify_key
from eduvpn.crypto import make_verifier, gen_code_verifier
from eduvpn.oauth2 import get_open_port, create_oauth_session, get_oauth_token_code, oauth_from_token
from eduvpn.managers import connect_provider, list_providers, store_provider, delete_provider, disconnect_provider, \
    is_provider_connected
from eduvpn.remote import get_instances, get_instance_info, get_auth_url, list_profiles, create_keypair, \
    get_profile_config, system_messages, user_messages
from eduvpn.notify import notify
from eduvpn.io import get_metadata

logger = logging.getLogger(__name__)


def error_helper(parent, msg_big, msg_small):
    logger.error("{}: {}".format(msg_big, msg_small))
    error_dialog = Gtk.MessageDialog(parent, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK, str(msg_big))
    error_dialog.format_secondary_text(str(msg_small))
    error_dialog.run()
    error_dialog.hide()


def thread_helper(func):
    thread = threading.Thread(target=func)
    thread.daemon = True
    thread.start()
    return thread


class EduVpnApp:
    def __init__(self, here):
        self.here = here

        # hack to make the reopen url button work
        self.auth_url = None

        handlers = {
            "delete_window": Gtk.main_quit,
            "add_config": self.selection_connection_step,
            "del_config": self.delete,
            "select_config": self.select_config,
            "connect_set": self.connect_set,
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
            uuid, display_name = model[treeiter]
            notify("Connecting to {}".format(display_name))
            connect_provider(uuid)

    def disconnect(self, selection):
        logger.info("disconnect pressed")
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            uuid, display_name = model[treeiter]
            notify("Disconnecting to {}".format(display_name))
            disconnect_provider(uuid)

    def update_providers(self):
        config_list = self.builder.get_object('configs-model')
        introduction = self.builder.get_object('introduction')
        config_list.clear()
        providers = list(list_providers())

        if len(providers) > 0:
            logger.info("hiding introduction")
            introduction.hide()
            for meta in providers:
                config_list.append((meta['uuid'], meta['display_name']))
        else:
            logger.info("showing introduction")
            introduction.show()

    def selection_connection_step(self, _):
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
            self.fetch_instance_step(discovery_uri=secure_internet_uri, connection_type='secure_internet')
        elif response == 2:
            logger.info("institute button pressed")
            self.fetch_instance_step(discovery_uri=institute_access_uri, connection_type='institute_access')

        elif response == 3:
            logger.info("custom button pressed")
            self.custom_url()

    def custom_url(self):
        dialog = self.builder.get_object('custom-url-dialog')
        entry = self.builder.get_object('custom-url-entry')
        dialog.show_all()
        while True:
            response = dialog.run()
            if response == 0:  # cancel
                logger.info("cancel button pressed")
                return
            else:
                custom_url = entry.get_text()
                logger.info("ok pressed, entry text: {}".format(custom_url))
                if not custom_url.startswith('https://'):
                    GLib.idle_add(error_helper, dialog, "Invalid URL", "URL should start with https://")
                else:
                    GLib.idle_add(dialog.hide)
                    display_name = custom_url[8:].split('/')[0]
                    logger.info("using {} for display name".format(display_name))
                    GLib.idle_add(self.browser_step, display_name, custom_url, 'custom', 'local', None)
                    break

    def fetch_instance_step(self, discovery_uri, connection_type):
        logger.info("fetching instances step")
        dialog = self.builder.get_object('fetch-dialog')
        dialog.show_all()

        def background():
            try:
                authorization_type, instances = get_instances(discovery_uri=discovery_uri, verify_key=self.verifier)
            except Exception as e:
                GLib.idle_add(error_helper, dialog, "can't fetch instances", "{} {}".format(type(e), str(e)))
                GLib.idle_add(dialog.hide)
            else:
                GLib.idle_add(dialog.hide)
                GLib.idle_add(self.select_instance_step, connection_type, authorization_type, instances)

        thread_helper(background())

    def select_instance_step(self, connection_type, authorization_type, instances):
        logger.info("presenting instances to user")
        dialog = self.builder.get_object('instances-dialog')
        model = self.builder.get_object('instances-model')
        selection = self.builder.get_object('instances-selection')
        model.clear()
        dialog.show_all()

        for instance in instances:
            display_name, url, icon_data = instance
            l = GdkPixbuf.PixbufLoader()
            l.set_size(width=100, height=50)
            l.write(icon_data)
            l.close()
            pixbuf = l.get_pixbuf()
            model.append((display_name, url, pixbuf))

        response = dialog.run()
        dialog.hide()

        if response == 0:  # cancel
            logging.info("cancel button pressed")
        else:
            model, treeiter = selection.get_selected()
            if treeiter:
                display_name, instance_base_uri, icon_pixbuf = model[treeiter]
                self.browser_step(display_name=display_name, instance_base_uri=instance_base_uri,
                                  connection_type=connection_type,
                                  authorization_type=authorization_type, icon_pixbuf=icon_pixbuf)
            else:
                logger.info("nothing selected")

    def browser_step(self, display_name, instance_base_uri, connection_type, authorization_type, icon_pixbuf):
        logger.info("opening token dialog")
        dialog = self.builder.get_object('token-dialog')
        dialog.show_all()

        def update(token, api_base_uri, oauth):
            dialog.hide()
            self.fetch_profile_step(token, api_base_uri, oauth, display_name, connection_type, authorization_type,
                                    icon_pixbuf)

        def background():
            try:
                api_base_uri, authorization_endpoint, token_endpoint = get_instance_info(instance_base_uri,
                                                                                         self.verifier)
                code_verifier = gen_code_verifier()
                port = get_open_port()
                oauth = create_oauth_session(port)
                self.auth_url = get_auth_url(oauth, code_verifier, authorization_endpoint)
                webbrowser.open(self.auth_url)
                code = get_oauth_token_code(port)
                token = oauth.fetch_token(token_endpoint, code=code, code_verifier=code_verifier)
            except Exception as e:
                GLib.idle_add(error_helper, dialog, "can't obtain token", "{} {}".format(type(e).__name__, str(e)))
                GLib.idle_add(dialog.hide)
                raise
            else:
                GLib.idle_add(update, token, api_base_uri, oauth)

        thread_helper(background)

        while True:
            response = dialog.run()
            if response == 0:  # cancel
                logger.info("token dialog: cancel button pressed")
                dialog.hide()
                break
            elif response == 1:
                logger.info("token dialog: reopen browser button pressed, opening {} again".format(self.auth_url))
                webbrowser.open(self.auth_url)
            else:
                logger.info("token dialog: received callback response")
                break

    def fetch_profile_step(self, token, api_base_uri, oauth, display_name, connection_type, authorization_type,
                           icon_pixbuf):
        logger.info("fetching profile step")
        dialog = self.builder.get_object('fetch-dialog')
        dialog.show_all()

        def background():
            try:
                profiles = list_profiles(oauth, api_base_uri)
                if len(profiles) > 1:
                    GLib.idle_add(dialog.hide)
                    GLib.idle_add(self.select_profile_step, token, profiles, api_base_uri, oauth, display_name,
                                  connection_type, authorization_type, icon_pixbuf)
                elif len(profiles) == 1:
                    profile_display_name, profile_id, two_factor = profiles[0]
                    self.finalizing_step(oauth, api_base_uri, profile_id, display_name, token, connection_type,
                                         authorization_type, profile_display_name, two_factor, icon_pixbuf)
                else:
                    raise Exception("Instance doesn't contain any profiles")
            except Exception as e:
                GLib.idle_add(error_helper, dialog, "can't fetch profile", "{} {}".format(type(e).__name__, str(e)))
                GLib.idle_add(dialog.hide)
                raise

        thread_helper(background)

    def select_profile_step(self, profiles, token, api_base_uri, oauth, display_name, connection_type,
                            authorization_type, icon_pixbuf):
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
                self.finalizing_step(oauth, api_base_uri, profile_id, display_name, token, connection_type,
                                     authorization_type, profile_display_name, two_factor, icon_pixbuf)
            else:
                logger.error("nothing selected")
                return

    def finalizing_step(self, oauth, api_base_uri, profile_id, display_name, token, connection_type, authorization_type,
                        profile_display_name, two_factor, icon_pixbuf):
        logger.info("finalizing step")
        dialog = self.builder.get_object('fetch-dialog')
        dialog.show_all()

        def background():
            try:
                cert, key = create_keypair(oauth, api_base_uri)
                config = get_profile_config(oauth, api_base_uri, profile_id)
            except Exception as e:
                GLib.idle_add(error_helper, dialog, "can't finalize configuration", "{} {}".format(type(e).__name__,
                                                                                                   str(e)))
                GLib.idle_add(dialog.hide)
            else:
                try:
                    store_provider(api_base_uri, profile_id, display_name, token, connection_type, authorization_type,
                                   profile_display_name, two_factor, cert, key, config, icon_pixbuf)
                    notify("Added eduVPN configuration {}".format(display_name))
                except Exception as e:
                    GLib.idle_add(error_helper, dialog, "can't store configuration", "{} {}".format(type(e).__name__,
                                                                                                    str(e)))
                    GLib.idle_add(dialog.hide)
                    raise
                else:
                    GLib.idle_add(dialog.hide)
                    GLib.idle_add(self.update_providers)

        thread_helper(background)

    def delete(self, selection):
        logger.info("delete provider clicked")
        model, treeiter = selection.get_selected()
        if not treeiter:
            logger.info("nothing selected")
            return

        uuid, display_name = model[treeiter]

        dialog = Gtk.MessageDialog(self.window, Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION,
                                   Gtk.ButtonsType.YES_NO, "Are you sure you want to remove '{}'?".format(display_name))
        dialog.format_secondary_text("This action can't be undone.")
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            logger.info("deleting provider config")
            try:
                delete_provider(uuid)
                notify("Deleted eduVPN configuration {}".format(display_name))
            except Exception as e:
                GLib.idle_add(error_helper, self.window, "can't delete profile", "{}: {}".format(type(e).__name__, str(e)))
            GLib.idle_add(self.update_providers)
        elif response == Gtk.ResponseType.NO:
            logger.info("not deleting provider config")
        dialog.destroy()
        
    def fetch_messages(self, uuid):
        buffer = self.builder.get_object('messages-buffer')
        text = ""
        metadata = get_metadata(uuid)
        api_base_uri = metadata['api_base_uri']
        oauth = oauth_from_token(metadata['token'])
        logger.error(user_messages(oauth, api_base_uri))
        for message in user_messages(oauth, api_base_uri):
            date_time = message['date_time']
            content = message['message']
            type = message['notification']
            text += content
        for message in system_messages(oauth, api_base_uri):
            date_time = message['date_time']
            content = message['message']
            type = message['type']
            text += content
        buffer.set_text(text)

    def select_config(self, list):
        notebook = self.builder.get_object('outer-notebook')
        switch = self.builder.get_object('connect-switch')
        model, treeiter = list.get_selected()
        if not treeiter:
            logger.info("no configuration selected, showing main logo")
            notebook.set_current_page(0)
            return
        else:
            uuid, display_name = model[treeiter]
            logger.info("{} ({}) configuration was selected".format(display_name, uuid))
            switch.set_state(is_provider_connected(uuid=uuid))
            notebook.show_all()
            notebook.set_current_page(1)
            GLib.idle_add(self.fetch_messages, uuid)


    def connect_set(self, selection, buttonevent):
        switch = self.builder.get_object('connect-switch')
        state = switch.get_active()
        logger.info("switch activated, state {}".format(state))
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            uuid, display_name = model[treeiter]
            if not state:
                notify("Connecting to {}".format(display_name))
                try:
                    connect_provider(uuid)
                except Exception as e:
                    error_helper(self.window, "can't enable connection", "{}: {}".format(type(e).__name__, str(e)))
            else:
                notify("Disconnecting from {}".format(display_name))
                try:
                    disconnect_provider(uuid)
                except Exception as e:
                    error_helper(self.window, "can't disconnect", "{}: {}".format(type(e).__name__, str(e)))


def main(here):
    GObject.threads_init()
    logging.basicConfig(level=logging.INFO)
    eduVpnApp = EduVpnApp(here)
    Gtk.main()
