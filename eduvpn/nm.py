from enum import Flag
import dbus  # type:ignore
from dbus.mainloop.glib import DBusGMainLoop  # type:ignore
from logging import getLogger
from pathlib import Path
from shutil import rmtree
from sys import modules
from tempfile import mkdtemp
from typing import Optional, Tuple

logger = getLogger(__name__)

try:
    import gi

    gi.require_version('NM', '1.0')
    from gi.repository import NM, GLib  # type: ignore
except (ImportError, ValueError) as e:
    logger.warning("Network Manager not available")
    NM = None

from eduvpn.storage import set_uuid, get_uuid, write_config
from eduvpn.utils import get_logger


class ConnectionState(Flag):
    UNKNOWN = 0  # NM.VpnConnectionState.UNKNOWN
    PREPARE = 1  # NM.VpnConnectionState.PREPARE
    NEED_AUTH = 2  # NM.VpnConnectionState.NEED_AUTH
    CONNECT = 3  # NM.VpnConnectionState.CONNECT
    IP_CONFIG_GET = 4  # NM.VpnConnectionState.IP_CONFIG_GET
    ACTIVATED = 5  # NM.VpnConnectionState.ACTIVATED
    FAILED = 6  # NM.VpnConnectionState.FAILED
    DISCONNECTED = 7  # NM.VpnConnectionState.DISCONNECTED


class ConnectionStateReason(Flag):
    UNKNOWN = 0  # NM.VpnConnectionStateReason.UNKNOWN
    NONE = 1  # NM.VpnConnectionStateReason.NONE
    USER_DISCONNECTED = 2  # NM.VpnConnectionStateReason.USER_DISCONNECTED
    DEVICE_DISCONNECTED = 3  # NM.VpnConnectionStateReason.DEVICE_DISCONNECTED
    SERVICE_STOPPED = 4  # NM.VpnConnectionStateReason.SERVICE_STOPPED
    IP_CONFIG_INVALID = 5  # NM.VpnConnectionStateReason.IP_CONFIG_INVALID
    CONNECT_TIMEOUT = 6  # NM.VpnConnectionStateReason.CONNECT_TIMEOUT
    SERVICE_START_TIMEOUT = 7  # NM.VpnConnectionStateReason.SERVICE_START_TIMEOUT
    SERVICE_START_FAILED = 8  # NM.VpnConnectionStateReason.SERVICE_START_FAILED
    NO_SECRETS = 9  # NM.VpnConnectionStateReason.NO_SECRETS
    LOGIN_FAILED = 10  # NM.VpnConnectionStateReason.LOGIN_FAILED
    CONNECTION_REMOVED = 11  # NM.VpnConnectionStateReason.CONNECTION_REMOVED


logger = get_logger(__file__)


def get_client() -> 'NM.Client':
    """
    Create a new client object. We put this here so other modules don't need to import NM
    """
    return NM.Client.new(None)


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
    logger.debug("Connection added for uuid: {}".format(get_uuid()))
    if callback is not None:
        callback(new_con is not None)


def add_connection(client: 'NM.Client', connection: 'NM.Connection', callback=None):
    logger.info("Adding new connection")
    client.add_connection_async(connection=connection, save_to_disk=True, callback=add_callback, user_data=callback)


def update_connection_callback(client, result, callback=None):
    res = client.commit_changes_finish(result)
    logger.debug("Connection updated for uuid: {}, result: {}".format(get_uuid(), res))
    if callback is not None:
        callback(res)


def update_connection(old_con: 'NM.Connection', new_con: 'NM.Connection', callback=None):
    """
    Update an existing Network Manager connection with the settings from another Network Manager connection
    """
    logger.info("Updating existing connection with new configuration")

    old_con.replace_settings_from_connection(new_con)
    old_con.commit_changes_async(save_to_disk=True, cancellable=None, callback=update_connection_callback, user_data=callback)


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
    logger.debug("activate_connection uuid: {} connection: {}".format(uuid, con))

    client.activate_connection_async(connection=con)


def deactivate_connection(client: 'NM.Client', uuid: str):
    con = client.get_primary_connection()
    logger.debug("deactivate_connection uuid: {} connection: {}".format(uuid, con))
    if con:
        active_uuid = con.get_uuid()

        if uuid == active_uuid:
            client.deactivate_connection_async(active=con)
    else:
        logger.info("No active connection to deactivate")


def connection_status(client: 'NM.Client', uuid: str):
    con = client.get_primary_connection()
    active_uuid = con.get_uuid()

    if uuid == active_uuid:
        def callback(source_object, result):
            logger.debug(source_object.check_connectivity_finish(result))

        client.check_connectivity_async(callback=callback)


user_dbus_status_callback = None
vpn_state = ConnectionState.UNKNOWN


def register_status_callback(callback):
    global user_dbus_status_callback
    user_dbus_status_callback = callback
    global vpn_state
    dbus_status_callback(vpn_state, ConnectionStateReason.UNKNOWN)


def active_vpn_state() -> ConnectionState:
    global vpn_state
    return vpn_state


def dbus_status_callback(state_code=None, reason_code=None):
    global user_dbus_status_callback
    if user_dbus_status_callback is not None:
        user_dbus_status_callback(ConnectionState(state_code), ConnectionStateReason(reason_code))


def init_dbus_system_bus():
    """
    Create a new D-Bus system bus object. We put this here so other modules don't need to import D-Bus
    """
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    _ = bus.add_signal_receiver(handler_function=dbus_status_callback,
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
        global vpn_state
        if vpn:
            vpn_state = ConnectionState(a_props.Get("org.freedesktop.NetworkManager.VPN.Connection", "VpnState"))
            logger.debug('Id: {} VpnState: {}'.format(vpn_id, vpn_state))
            return
    vpn_state = ConnectionState.DISCONNECTED




