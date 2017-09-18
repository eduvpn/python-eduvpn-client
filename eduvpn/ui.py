# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import gi
import logging
import os
import webbrowser
import base64

from datetime import datetime
import dbus.mainloop.glib

gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('Notify', '0.7')
from gi.repository import GObject, Gtk, GLib, GdkPixbuf

logging.basicConfig(level=logging.INFO)

from eduvpn.util import error_helper, thread_helper, get_prefix
from eduvpn.config import secure_internet_uri, institute_access_uri, verify_key, icon_size
from eduvpn.crypto import make_verifier, gen_code_verifier
from eduvpn.oauth2 import get_open_port, create_oauth_session, get_oauth_token_code, oauth_from_token
from eduvpn.manager import connect_provider, list_providers, store_provider, delete_provider, disconnect_provider, \
    is_provider_connected, update_config_provider, update_keys_provider, update_token, vpn_monitor, active_connections
from eduvpn.remote import get_instances, get_instance_info, get_auth_url, list_profiles, create_keypair, \
    get_profile_config, system_messages, user_messages, user_info
from eduvpn.notify import notify
from eduvpn.util import bytes2pixbuf
from eduvpn.exceptions import EduvpnAuthException
from eduvpn.metadata import Metadata


logger = logging.getLogger(__name__)


class EduVpnApp:
    def __init__(self):
        """setup UI thingies, don't do any fetching or DBus communication yet"""

        self.prefix = get_prefix()

        # minimal global state to pass around data between steps where otherwise difficult
        self.auth_url = None
        self.selected = None

        # the signals coming from the GTK ui
        handlers = {
            "delete_window": Gtk.main_quit,
            "add_config": self.selection_connection_step,
            "del_config": self.delete,
            "select_config": self.select_config,
            "connect_set": self.connect_set,
        }

        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(self.prefix, 'share/eduvpn/eduvpn.ui'))
        self.builder.connect_signals(handlers)

        self.window = self.builder.get_object('eduvpn-window')
        self.verifier = make_verifier(verify_key)

        self.window.set_position(Gtk.WindowPosition.CENTER)

        logo = os.path.join(self.prefix, 'share/eduvpn/eduvpn.png')
        self.icon_placeholder = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo, icon_size['width'],
                                                                        icon_size['height'], True)
        self.icon_placeholder_big = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo, icon_size['width']*2,
                                                                            icon_size['height']*2, True)

    def run(self):
        # attach a callback to VPN connection monitor
        vpn_monitor(self.vpn_status_change)
        self.window.show_all()
        self.update_providers()

    def connect(self, selection):
        logger.info("connect pressed")
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            uuid, display_name = model[treeiter]
            notify("eduVPN connecting...", "Connecting to {}".format(display_name))
            connect_provider(uuid)

    def disconnect(self, selection):
        logger.info("disconnect pressed")
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            uuid, display_name = model[treeiter]
            notify("eduVPN disconnecting...", "Disconnecting from '{}'".format(display_name))
            disconnect_provider(uuid)

    def update_providers(self):
        logger.info("composing list of current eduVPN configurations")
        config_list = self.builder.get_object('configs-model')
        introduction = self.builder.get_object('introduction')
        config_list.clear()
        providers = list(list_providers())

        if len(providers) > 0:
            logger.info("hiding introduction")
            introduction.hide()
            for meta in providers:
                connection_type = "{}\n{}".format(meta.display_name, meta.connection_type)
                if meta.icon_data:
                    icon = bytes2pixbuf(base64.b64decode(meta.icon_data.encode()))
                else:
                    icon = self.icon_placeholder
                config_list.append((meta.uuid, meta.display_name, icon, connection_type))
        else:
            logger.info("showing introduction")
            introduction.show()

    def selection_connection_step(self, _):
        """The connection type selection step"""
        logger.info("add configuration clicked")
        dialog = self.builder.get_object('connection-type-dialog')
        dialog.show_all()
        response = dialog.run()
        dialog.hide()

        meta = Metadata()

        if response == 0:  # cancel
            logger.info("cancel button pressed")
            return
        elif response == 1:
            logger.info("secure button pressed")
            meta.discovery_uri = secure_internet_uri
            meta.connection_type = 'Secure Internet'
            self.fetch_instance_step(meta)
        elif response == 2:
            logger.info("institute button pressed")
            meta.discovery_uri = institute_access_uri
            meta.connection_type = 'Institute Access'
            self.fetch_instance_step(meta)

        elif response == 3:
            logger.info("custom button pressed")
            self.custom_url(meta)

    def custom_url(self, meta):
        """the custom URL dialog where a user can enter a custom instance URL"""
        dialog = self.builder.get_object('custom-url-dialog')
        entry = self.builder.get_object('custom-url-entry')
        dialog.show_all()
        while True:
            response = dialog.run()
            if response == 1:
                custom_url = entry.get_text()
                logger.info("ok pressed, entry text: {}".format(custom_url))
                if not custom_url.startswith('https://'):
                    GLib.idle_add(error_helper, dialog, "Invalid URL", "URL should start with https://")
                else:
                    GLib.idle_add(dialog.hide)
                    meta.display_name = custom_url[8:].split('/')[0]
                    logger.info("using {} for display name".format(meta.display_name))
                    meta.instance_base_uri = custom_url
                    meta.connection_type = 'Custom Instance'
                    meta.authorization_type = 'local'
                    meta.icon_data = None
                    GLib.idle_add(self.browser_step, meta)
                    break
            else:  # cancel or close
                logger.info("cancel or close button pressed (response {})".format(response))
                dialog.hide()
                return

    def fetch_instance_step(self, meta):
        """fetch list of instances"""
        logger.info("fetching instances step")
        dialog = self.builder.get_object('fetch-dialog')
        dialog.show_all()

        def background():
            try:
                authorization_type, instances = get_instances(discovery_uri=meta.discovery_uri,
                                                              verify_key=self.verifier)
            except Exception as e:
                GLib.idle_add(error_helper, dialog, "can't fetch instances", "{} {}".format(type(e), str(e)))
                GLib.idle_add(dialog.hide)
                raise
            else:
                GLib.idle_add(dialog.hide)
                meta.authorization_type = authorization_type
                GLib.idle_add(self.select_instance_step, meta, instances)

        thread_helper(background())

    def select_instance_step(self, meta, instances):
        """prompt user with instance dialog"""
        logger.info("presenting instances to user")
        dialog = self.builder.get_object('instances-dialog')
        model = self.builder.get_object('instances-model')
        selection = self.builder.get_object('instances-selection')
        model.clear()
        dialog.show_all()

        for display_name, url, icon_data in instances:
            icon = bytes2pixbuf(icon_data)
            model.append((display_name, url, icon, base64.b64encode(icon_data).decode('ascii')))

        response = dialog.run()
        dialog.hide()

        if response == 0:  # cancel
            logging.info("cancel button pressed")
        else:
            model, treeiter = selection.get_selected()
            if treeiter:
                display_name, instance_base_uri, icon_pixbuf, icon_data = model[treeiter]
                meta.display_name = display_name
                meta.instance_base_uri = instance_base_uri
                meta.icon_pixbuf = icon_pixbuf
                meta.icon_data = icon_data
                self.browser_step(meta)
            else:
                logger.info("nothing selected")

    def browser_step(self, meta):
        """The notorious browser step. starts webserver, wait for callback, show token dialog"""
        logger.info("opening token dialog")
        dialog = self.builder.get_object('token-dialog')
        url_dialog = self.builder.get_object('redirecturl-dialog')
        dialog.show_all()

        def url_callback(meta, port, code_verifier, oauth):
            thread_helper(lambda: phase2(meta, port, oauth, code_verifier))

        def update2(meta, oauth):
            logger.info("hiding url dialog")
            GLib.idle_add(url_dialog.hide)
            logger.info("hiding token dialog")
            GLib.idle_add(dialog.hide)
            self.fetch_profile_step(meta, oauth)

        def auth_url_background(meta):
            try:
                logger.info("starting token obtaining in background")
                r = get_instance_info(meta.instance_base_uri, self.verifier)
                meta.api_base_uri, meta.authorization_endpoint, meta.token_endpoint = r
                code_verifier = gen_code_verifier()
                port = get_open_port()
                oauth = create_oauth_session(port)
                self.auth_url = get_auth_url(oauth, code_verifier, meta.authorization_endpoint)
            except Exception as e:
                GLib.idle_add(error_helper, dialog, "Can't create oauth session", "{}".format(str(e)))
                GLib.idle_add(dialog.hide)
            else:
                GLib.idle_add(url_callback, meta, port, code_verifier, oauth)

        def phase2(meta, port, oauth, code_verifier):
            try:
                logger.info("opening browser with url {}".format(self.auth_url))
                webbrowser.open(self.auth_url)
                code = get_oauth_token_code(port)
                logger.info("control returned by browser")
                token = oauth.fetch_token(meta.token_endpoint, code=code, code_verifier=code_verifier)
            except Exception as e:
                GLib.idle_add(error_helper, dialog, "Can't obtain token", "{}".format(str(e)))
                GLib.idle_add(dialog.hide)
                raise
            else:
                token['token_endpoint'] = meta.token_endpoint
                logger.info("obtained oauth token")
                meta.token = token
                GLib.idle_add(update2, meta, oauth)

        thread_helper(lambda: auth_url_background(meta))

        while True:
            response = dialog.run()
            if response == 0:  # cancel
                logger.info("token dialog: cancel button pressed")
                dialog.hide()
                break
            elif response == 1:
                logger.info("token dialog: reopen browser button pressed, opening {} again".format(self.auth_url))
                webbrowser.open(self.auth_url)
            elif response == 2:
                logger.info("token dialog: show redirect URL button pressed")
                url_field = self.builder.get_object('redirect-url-entry')
                url_field.set_text(self.auth_url)
                url_dialog.run()
                logger.info("token dialog: url popup closed")
                url_dialog.hide()
                break
            else:
                logger.info("token dialog: window closed")
                dialog.hide()
                break

    def fetch_profile_step(self, meta, oauth):
        """background action step, fetches profiles and shows 'fetching' screen"""
        logger.info("fetching profile step")
        dialog = self.builder.get_object('fetch-dialog')
        dialog.show_all()

        def background():
            try:
                profiles = list_profiles(oauth, meta.api_base_uri)
                if len(profiles) > 1:
                    GLib.idle_add(dialog.hide)
                    GLib.idle_add(self.select_profile_step, profiles, meta, oauth)
                elif len(profiles) == 1:
                    profile_display_name, profile_id, two_factor = profiles[0]
                    meta.profile_display_name = profile_display_name
                    meta.profile_id = profile_id
                    meta.two_factor = two_factor
                    self.two_auth_step(oauth, meta)
                else:
                    raise Exception("Either there are no VPN profiles defined, or this account does not have the "
                                    "required permissions to create a new VPN configurations for any of the "
                                    "available profiles.")

            except Exception as e:
                GLib.idle_add(error_helper, dialog, "Can't fetch profile list", str(e))
                GLib.idle_add(dialog.hide)
                raise

        thread_helper(background)

    def select_profile_step(self, profiles, meta, oauth):
        """the profile selection step, doesn't do anything if only one profile"""
        logger.info("opening profile dialog")

        dialog = self.builder.get_object('profiles-dialog')
        model = self.builder.get_object('profiles-model')
        selection = self.builder.get_object('profiles-selection')
        dialog.show_all()
        model.clear()
        [model.append(p) for p in profiles]
        response = dialog.run()
        dialog.hide()

        if response == 0:  # cancel
            logging.info("cancel button pressed")
            return
        else:
            model, treeiter = selection.get_selected()
            if treeiter:
                profile_display_name, profile_id, two_factor = model[treeiter]
                meta.profile_display_name = profile_display_name
                meta.profile_id = profile_id
                meta.two_factor = two_factor
                self.two_auth_step(oauth, meta)
            else:
                logger.error("nothing selected")
                return

    def two_auth_step(self, oauth, meta):
        """checks if 2auth is enabled. If more than 1 option presents user with choice"""
        dialog = self.builder.get_object('2fa-dialog')

        def update(options):
            two_dialog = self.builder.get_object('2fa-dialog')
            for i, option in enumerate(options):
                dialog.add_button(option, i)
            two_dialog.show()
            index = int(dialog.run())
            if index >= 0:
                meta.username = options[index]
                logger.info("user selected '{}'".format(meta.username))
                self.finalizing_step(oauth, meta)
            dialog.destroy()

        def background(meta):
            info = user_info(oauth, meta.api_base_uri)
            username = None
            if info['is_disabled']:
                GLib.idle_add(error_helper, self.window, "This account has been disabled", "")

            if 'two_factor_enrolled_with' in info:
                options = info['two_factor_enrolled_with']
                if len(options) > 1:
                    GLib.idle_add(update, options)
                    return
                elif len(options) == 1:
                    meta.username = options[0]
                    logger.info("auto selected username {} for 2 factor authentication".format(username))
                GLib.idle_add(self.finalizing_step, oauth, meta)

        thread_helper(lambda: background(meta))

    def finalizing_step(self, oauth, meta):
        """finalise the add profile flow, add a configuration"""
        logger.info("finalizing step")
        dialog = self.builder.get_object('fetch-dialog')
        dialog.show_all()

        def background(meta):
            try:
                cert, key = create_keypair(oauth, meta.api_base_uri)
                meta.cert = cert
                meta.key = key
                meta.config = get_profile_config(oauth, meta.api_base_uri, meta.profile_id)
            except Exception as e:
                GLib.idle_add(error_helper, dialog, "can't finalize configuration", "{}: {}".format(type(e).__name__,
                                                                                                    str(e)))
                GLib.idle_add(dialog.hide)
                raise
            else:
                try:
                    store_provider(meta)
                    GLib.idle_add(notify, "eduVPN provider added", "added provider '{}'".format(meta.display_name))
                except Exception as e:
                    GLib.idle_add(error_helper, dialog, "can't store configuration", "{} {}".format(type(e).__name__,
                                                                                                    str(e)))
                    GLib.idle_add(dialog.hide)
                    raise
                else:
                    GLib.idle_add(dialog.hide)
                    GLib.idle_add(self.update_providers)

        thread_helper(lambda: background(meta))

    def delete(self, selection):
        """called when the user presses the - button"""
        logger.info("delete provider clicked")
        model, treeiter = selection.get_selected()
        if not treeiter:
            logger.info("nothing selected")
            return

        uuid, display_name, _, _ = model[treeiter]

        dialog = Gtk.MessageDialog(self.window, Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION,
                                   Gtk.ButtonsType.YES_NO, "Are you sure you want to remove '{}'?".format(display_name))
        dialog.format_secondary_text("This action can't be undone.")
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            logger.info("deleting provider config")
            try:
                delete_provider(uuid)
                notify("eduVPN provider deleted", "Deleted '{}'".format(display_name))
            except Exception as e:
                error_helper(self.window, "can't delete profile", str(e))
                dialog.destroy()
                raise
            GLib.idle_add(self.update_providers)
        elif response == Gtk.ResponseType.NO:
            logger.info("not deleting provider config")
        dialog.destroy()

    def reauth(self, meta):
        """called when the authorization is expired"""
        logger.info("looks like authorization is expired or removed")
        dialog = Gtk.MessageDialog(self.window, Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION,
                                   Gtk.ButtonsType.YES_NO,
                                   "Authorization for {}is expired or removed.".format(meta.display_name))
        dialog.format_secondary_text("Do you want to re-authorize?")
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            self.browser_step(meta)
            delete_provider(meta.uuid)
        elif response == Gtk.ResponseType.NO:
            pass
        dialog.destroy()

    def fetch_messages(self, meta):
        logger.info("fetching user and system messages from {} ({})".format(meta.display_name, meta.api_base_uri))

        def background(label, token):
            oauth = oauth_from_token(token, update_token, meta.uuid)
            text = ""
            try:
                messages_user = list(user_messages(oauth, meta.api_base_uri))
                messages_system = list(system_messages(oauth, meta.api_base_uri))
                info = user_info(oauth, meta.api_base_uri)
                if info['is_disabled']:
                    GLib.idle_add(error_helper, self.window, "This account has been disabled", "")

            except EduvpnAuthException:
                GLib.idle_add(self.reauth, meta)
            except Exception as e:
                GLib.idle_add(error_helper, self.window, "Can't fetch user messages", str(e))
                raise
            else:
                for date_time, type_, message in messages_user:
                    logger.info("user message at {}: {}".format(date_time, message))
                    text += "<b><big>{}</big></b>\n".format(date_time)
                    text += "<small><i>user, {}</i></small>\n".format(type_)
                    text += "{}\n\n".format(message)
                for date_time, type_, message in messages_system:
                    logger.info("system message at {}: {}".format(date_time, message))
                    text += "<b><big>{}</big></b>\n".format(date_time)
                    text += "<small><i>system, {}</i></small>\n".format(type_)
                    text += "{}\n\n".format(message)
                GLib.idle_add(label.set_markup, text)

        label = self.builder.get_object('messages-label')
        thread_helper(lambda: background(label, meta.token))

    def select_config(self, list_):
        """called when a users selects a configuration"""
        notebook = self.builder.get_object('outer-notebook')
        switch = self.builder.get_object('connect-switch')
        ipv4_label = self.builder.get_object('ipv4-label')
        ipv6_label = self.builder.get_object('ipv6-label')
        twofa_label = self.builder.get_object('2fa-label')
        twofa_label_label = self.builder.get_object('2fa-label-label')
        name_label = self.builder.get_object('name-label')
        profile_label = self.builder.get_object('profile-label')
        profile_image = self.builder.get_object('profile-image')
        model, treeiter = list_.get_selected()
        if not treeiter:
            logger.info("no configuration selected, showing main logo")
            notebook.set_current_page(0)
            return
        else:
            uuid, display_name, icon, _ = model[treeiter]
            logger.info("configuration was selected {} ({})".format(display_name, uuid))
            self.selected = Metadata.from_uuid(uuid)
            name_label.set_text(display_name)
            if self.selected['icon_data']:
                icon = bytes2pixbuf(base64.b64decode(self.selected['icon_data'].encode()),
                                    width=icon_size['width']*2, height=icon_size['height']*2)
            else:
                icon = self.icon_placeholder_big
            profile_image.set_from_pixbuf(icon)
            profile_label.set_text(self.selected['connection_type'])
            connected = is_provider_connected(uuid=uuid)
            switch.set_state(bool(connected))
            if connected:
                ipv4, ipv6 = connected
                ipv4_label.set_text(ipv4)
                ipv6_label.set_text(ipv6)
            else:
                ipv4_label.set_text("")
                ipv6_label.set_text("")

            if self.selected.username:
                twofa_label.set_text(self.selected.username)
                twofa_label_label.set_text("2FA:")
            else:
                twofa_label.set_text("")
                twofa_label_label.set_text("")

            notebook.show_all()
            notebook.set_current_page(1)

            self.fetch_messages(self.selected)

    def vpn_status_change(self, *args, **kwargs):
        """called when the status of a VPN connection changes"""
        logger.info("VPN status change")
        switch = self.builder.get_object('connect-switch')
        ipv4_label = self.builder.get_object('ipv4-label')
        ipv6_label = self.builder.get_object('ipv6-label')

        selected_uuid_active = False
        for active in active_connections():
            try:
                if active.Uuid == self.selected['uuid']:
                    selected_uuid_active = True
                    if active.State == 2:  # activated
                        logger.info("setting ip for {}".format(self.selected['uuid']))
                        logger.info("setting switch ON")
                        switch.set_active(True)
                        GLib.idle_add(ipv4_label.set_text, active.Ip4Config.AddressData[0]['address'])
                        GLib.idle_add(ipv6_label.set_text, active.Ip6Config.AddressData[0]['address'])
                        notify("eduVPN connected", "Connected to '{}'".format(self.selected['display_name']))
                    elif active.State == 1:  # activating
                        logger.info("setting switch ON")
                        switch.set_active(True)
                        notify("eduVPN connecting...", "Activating '{}'".format(self.selected['display_name']))
                    else:
                        logger.info("clearing ip for '{}'".format(self.selected['uuid']))
                        logger.info("setting switch OFF")
                        switch.set_active(False)
                        GLib.idle_add(ipv4_label.set_text, "")
                        GLib.idle_add(ipv6_label.set_text, "")
                    break
            except Exception as e:
                logger.warning("probably race condition in network manager: {}".format(e))
                pass

        if not selected_uuid_active:
            logger.info("Our selected profile not active {}".format(self.selected['uuid']))
            notify("eduVPN Disconnected", "Disconnected from '{}'".format(self.selected['display_name']))
            logger.info("setting switch OFF")
            switch.set_active(False)
            GLib.idle_add(ipv4_label.set_text, "")
            GLib.idle_add(ipv6_label.set_text, "")

    def activate_connection(self, meta):
        """do the actual connecting action"""
        logger.info("Connecting to {}".format(meta.display_name))
        notify("eduVPN connecting...", "Connecting to '{}'".format(meta.display_name))
        try:
            oauth = oauth_from_token(meta.token, update_token, meta.uuid)
            config = get_profile_config(oauth, meta.api_base_uri, meta.profile_id)
            meta.config = config
            update_config_provider(meta)

            if datetime.now() > datetime.fromtimestamp(meta.token['expires_at']):
                logger.info("key pair is expired")
                cert, key = create_keypair(oauth, meta.api_base_uri)
                update_keys_provider(meta.uuid, cert, key)

            connect_provider(meta.uuid)

        except Exception as e:
            switch = self.builder.get_object('connect-switch')
            GLib.idle_add(switch.set_active, False)
            error_helper(self.window, "can't enable connection", "{}: {}".format(type(e).__name__, str(e)))
            raise

    def connect_set(self, selection, _):
        """called when the user releases the connection switch"""
        switch = self.builder.get_object('connect-switch')
        state = switch.get_active()
        logger.info("switch activated, state {}".format(state))
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            uuid, display_name, _, _ = model[treeiter]
            if not state:
                logger.info("setting switch ON")
                GLib.idle_add(switch.set_active, True)
                self.activate_connection(self.selected)
            else:
                notify("eduVPN disconnecting...", "Disconnecting from {}".format(display_name))
                logger.info("setting switch OFF")
                GLib.idle_add(switch.set_active, False)
                try:
                    disconnect_provider(uuid)
                except Exception as e:
                    error_helper(self.window, "can't disconnect", "{}: {}".format(type(e).__name__, str(e)))
                    GLib.idle_add(switch.set_active, True)
                    raise


def main():
    GObject.threads_init()
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    edu_vpn_app = EduVpnApp()
    edu_vpn_app.run()
    Gtk.main()

