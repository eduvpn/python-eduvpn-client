import logging
import time
from pathlib import Path
from shutil import rmtree
from sys import modules
from tempfile import mkdtemp
from typing import Optional, Tuple
from eduvpn.storage import set_uuid, get_uuid, write_config

logger = logging.getLogger(__name__)

try:
    import gi
    gi.require_version('NM', '1.0')
    from gi.repository import NM, GLib  # type: ignore
except (ImportError, ValueError):
    logger.warning("Network Manager not available")
    NM = None

try:
    import dbus  # type:ignore
    from dbus.mainloop.glib import DBusGMainLoop  # type:ignore
except (ImportError, ValueError):
    logger.warning("Dbus not available")
    dbus = None


def get_client() -> Optional['NM.Client']:
    """
    Create a new client object. We put this here so other modules don't need to import NM
    """
    if NM:
        return NM.Client.new(None)
    else:
        return None


def get_mainloop():
    """
    Create a new client object. We put this here so other modules don't need to import Glib
    """
    return GLib.MainLoop()


def nm_available() -> bool:
    """
    check if Network Manager is available
    """
    return bool('gi.repository.NM' in modules)


def nm_ovpn_import(target: Path) -> Optional['NM.Connection']:
    """
    Use the Network Manager VPN config importer to import an OpenVPN configuration file.
    """
    vpn_infos = [i for i in NM.VpnPluginInfo.list_load() if i.get_name() == 'openvpn']

    if len(vpn_infos) != 1:
        raise Exception(f"Expected one openvpn VPN plugins, got: {len(vpn_infos)}")

    conn = vpn_infos[0].load_editor_plugin().import_(str(target))
    conn.normalize()
    return conn


def import_ovpn(config: str, private_key: str, certificate: str) -> 'NM.SimpleConnection':
    """
    Import the OVPN string into Network Manager.
    """
    target_parent = Path(mkdtemp())
    target = target_parent / "eduVPN.ovpn"
    write_config(config, private_key, certificate, target)
    connection = nm_ovpn_import(target)
    rmtree(target_parent)
    return connection


def add_callback(client, result, callback=None):
    new_con = client.add_connection_finish(result)
    set_uuid(uuid=new_con.get_uuid())
    logger.debug(f"Connection added for uuid: {get_uuid()}")
    if callback is not None:
        callback(new_con is not None)


def add_connection(client: 'NM.Client', connection: 'NM.Connection', callback=None):
    logger.info("Adding new connection")
    client.add_connection_async(connection=connection, save_to_disk=True, callback=add_callback, user_data=callback)


def update_connection_callback(remote_connection, result, callback=None):
    res = remote_connection.commit_changes_finish(result)
    logger.debug(f"Connection updated for uuid: {get_uuid()}, result: {res}, remote_con: {remote_connection}")
    if callback is not None:
        callback(res)


def update_connection(old_con: 'NM.Connection', new_con: 'NM.Connection', callback=None):
    """
    Update an existing Network Manager connection with the settings from another Network Manager connection
    """
    logger.info("Updating existing connection with new configuration")

    old_con.replace_settings_from_connection(new_con)
    old_con.commit_changes_async(save_to_disk=True, cancellable=None, callback=update_connection_callback,
                                 user_data=callback)


def save_connection(client: 'NM.Client', config, private_key, certificate, callback=None):
    logger.info("writing configuration to Network Manager")
    new_con = import_ovpn(config, private_key, certificate)
    uuid = get_uuid()
    if uuid:
        old_con = client.get_connection_by_uuid(uuid)
        if old_con:
            update_connection(old_con, new_con, callback)
        else:
            add_connection(client=client, connection=new_con, callback=callback)
    else:
        add_connection(client=client, connection=new_con, callback=callback)


def get_cert_key(client: 'NM.Client', uuid: str) -> Tuple[str, str]:
    connection = client.get_connection_by_uuid(uuid)
    cert_path = connection.get_setting_vpn().get_data_item('cert')
    key_path = connection.get_setting_vpn().get_data_item('key')
    cert = open(cert_path).read()
    key = open(key_path).read()
    return cert, key


def activate_connection(client: 'NM.Client', uuid: str):
    con = client.get_connection_by_uuid(uuid)
    logger.debug(f"activate_connection uuid: {uuid} connection: {con}")
    if con is None:
        # Temporary workaround, connection is sometimes created too
        # late while according to the logging the connection is already
        # created. Need to find the correct event to sync on.
        time.sleep(.1)
        GLib.idle_add(lambda: activate_connection(client, uuid))
        return

    def on_activate_connection(a_client, res):
        result = a_client.activate_connection_finish(res)
        logger.debug(F"activate_connection_async result: {result}")

    client.activate_connection_async(connection=con, callback=on_activate_connection)


def deactivate_connection(client: 'NM.Client', uuid: str):
    con = client.get_primary_connection()
    logger.debug(f"deactivate_connection uuid: {uuid} connection: {con}")
    if con:
        active_uuid = con.get_uuid()

        if uuid == active_uuid:
            def on_deactivate_connection(a_client, res):
                result = a_client.deactivate_connection_finish(res)
                logger.debug(F"deactivate_connection_async result: {result}")

            client.deactivate_connection_async(active=con, callback=on_deactivate_connection)
    else:
        logger.info("No active connection to deactivate")


def connection_status(client: 'NM.Client', uuid: str):
    con = client.get_primary_connection()
    active_uuid = con.get_uuid()

    if uuid == active_uuid:
        def callback(source_object, result):
            logger.debug(source_object.check_connectivity_finish(result))

        client.check_connectivity_async(callback=callback)


def init_dbus_system_bus(callback):
    """
    Create a new D-Bus system bus object. We put this here so other modules don't need to import D-Bus
    """
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    _ = bus.add_signal_receiver(handler_function=callback,
                                dbus_interface='org.freedesktop.NetworkManager.VPN.Connection',
                                signal_name='VpnStateChanged')
    m_proxy = bus.get_object("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager")
    mgr_props = dbus.Interface(m_proxy, "org.freedesktop.DBus.Properties")
    active = mgr_props.Get("org.freedesktop.NetworkManager", "ActiveConnections")
    for a in active:
        a_proxy = bus.get_object("org.freedesktop.NetworkManager", a)
        a_props = dbus.Interface(a_proxy, "org.freedesktop.DBus.Properties")
        vpn_id = a_props.Get("org.freedesktop.NetworkManager.Connection.Active", "Id")
        vpn = a_props.Get("org.freedesktop.NetworkManager.Connection.Active", "Vpn")
        if vpn:
            vpn_state = NM.VpnConnectionState(a_props.Get("org.freedesktop.NetworkManager.VPN.Connection", "VpnState"))
            logger.debug(f'Id: {vpn_id} VpnState: {vpn_state}')
            callback(vpn_state, NM.VpnConnectionStateReason.NONE)
            return
    callback(NM.VpnConnectionState.DISCONNECTED, NM.VpnConnectionStateReason.NONE)
