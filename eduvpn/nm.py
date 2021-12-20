import logging
import time
from functools import lru_cache
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Any, Optional, Tuple, Callable

from .config import Configuration
from .ovpn import Ovpn
from .storage import set_uuid, get_uuid, write_ovpn

_logger = logging.getLogger(__name__)

try:
    import gi

    gi.require_version('NM', '1.0')
    from gi.repository import NM, GLib  # type: ignore
except (ImportError, ValueError):
    _logger.warning("Network Manager not available")
    NM = None

try:
    import dbus
except ImportError:
    dbus = None


@lru_cache()
def get_client() -> 'NM.Client':
    """
    Create a new client object. We put this here so other modules don't need to import NM
    """
    return NM.Client.new(None)


@lru_cache()
def get_mainloop():
    """
    Create a new client object. We put this here so other modules don't need to import Glib
    """
    return GLib.MainLoop()


def nm_available() -> bool:
    """
    check if Network Manager is available
    """
    if NM is None:
        return False
    try:
        get_client()
    except Exception:
        return False
    else:
        return True


def get_existing_configuration_uuid() -> Optional[str]:
    uuid = get_uuid()
    if uuid is None:
        return None
    client = get_client()
    connection = client.get_connection_by_uuid(uuid)
    if connection is None:
        return None
    else:
        return uuid


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


def import_ovpn(ovpn: Ovpn, private_key: str, certificate: str) -> 'NM.SimpleConnection':
    """
    Import the OVPN string into Network Manager.
    """
    target_parent = Path(mkdtemp())
    target = target_parent / "eduVPN.ovpn"
    write_ovpn(ovpn, private_key, certificate, target)
    connection = nm_ovpn_import(target)
    rmtree(target_parent)
    return connection


def add_connection_callback(client, result, callback=None):
    new_con = client.add_connection_finish(result)
    set_uuid(uuid=new_con.get_uuid())
    _logger.info(f"Connection added for uuid: {get_uuid()}")
    if callback is not None:
        callback(new_con is not None)


def add_connection(client: 'NM.Client', connection: 'NM.Connection', callback=None):
    _logger.info("Adding new connection")
    client.add_connection_async(connection=connection, save_to_disk=True, callback=add_connection_callback,
                                user_data=callback)


def update_connection_callback(remote_connection, result, callback=None):
    res = remote_connection.commit_changes_finish(result)
    _logger.debug(f"Connection updated for uuid: {get_uuid()}, result: {res}, remote_con: {remote_connection}")
    if callback is not None:
        callback(result)


def update_connection(old_con: 'NM.Connection', new_con: 'NM.Connection', callback=None):
    """
    Update an existing Network Manager connection with the settings from another Network Manager connection
    """
    _logger.info("Updating existing connection with new configuration")

    # Don't attempt to overwrite the uuid,
    # but reuse the one from the previous connection.
    # Refer to issue #269.
    for setting in new_con.get_settings():
        if setting.get_name() == 'connection':
            setting.props.uuid = old_con.get_uuid()
    old_con.replace_settings_from_connection(new_con)
    old_con.commit_changes_async(save_to_disk=True, cancellable=None, callback=update_connection_callback,
                                 user_data=callback)


def save_connection(client: 'NM.Client', ovpn: Ovpn, private_key, certificate, callback=None):
    _logger.info("writing configuration to Network Manager")
    new_con = import_ovpn(ovpn, private_key, certificate)
    uuid = get_uuid()
    if uuid:
        old_con = client.get_connection_by_uuid(uuid)
        if old_con:
            update_connection(old_con, new_con, callback)
            return
    add_connection(client=client, connection=new_con, callback=callback)


def save_connection_with_config(client: 'NM.Client',
                                config,
                                private_key,
                                certificate,
                                callback=None,
                                ):
    ovpn = Ovpn(config)
    settings = Configuration.load()
    if settings.force_tcp:
        ovpn.force_tcp()
    return save_connection(client, ovpn, private_key, certificate, callback)


def get_cert_key(client: 'NM.Client', uuid: str) -> Tuple[str, str]:
    try:
        connection = client.get_connection_by_uuid(uuid)
        cert_path = connection.get_setting_vpn().get_data_item('cert')
    except Exception:
        _logger.error(f"Can't fetch stored VPN connecton with uuid {uuid}")
        raise IOError("Can't fetch eduVPN profile")

    key_path = connection.get_setting_vpn().get_data_item('key')
    cert = open(cert_path).read()
    key = open(key_path).read()
    return cert, key


def activate_connection(client: 'NM.Client', uuid: str, callback=None):
    con = client.get_connection_by_uuid(uuid)
    _logger.info(f"activate_connection uuid: {uuid} connection: {con}")
    if con is None:
        # Temporary workaround, connection is sometimes created too
        # late while according to the logging the connection is already
        # created. Need to find the correct event to sync on.
        time.sleep(.1)
        GLib.idle_add(lambda: activate_connection(client, uuid, callback))
        return

    def activate_connection_callback(a_client, res, callback=None):
        try:
            result = a_client.activate_connection_finish(res)
        except Exception as e:
            _logger.error(e)
        else:
            _logger.info(F"activate_connection_async result: {result}")
        finally:
            if callback:
                callback()

    client.activate_connection_async(connection=con, callback=activate_connection_callback, user_data=callback)


def deactivate_connection(client: 'NM.Client', uuid: str, callback=None):
    con = client.get_primary_connection()
    _logger.debug(f"deactivate_connection uuid: {uuid} connection: {con}")
    if con:
        active_uuid = con.get_uuid()

        if uuid == active_uuid:
            def on_deactivate_connection(a_client: 'NM.Client', res, callback=None):
                try:
                    result = a_client.deactivate_connection_finish(res)
                except Exception as e:
                    _logger.error(e)
                else:
                    _logger.info(F"deactivate_connection_async result: {result}")
                finally:
                    if callback:
                        callback()

            client.deactivate_connection_async(active=con, callback=on_deactivate_connection, user_data=callback)
    else:
        _logger.info("No active connection to deactivate")


def connection_status(client: 'NM.Client') -> Tuple[Optional[str], Optional['NM.ActiveConnectionState']]:
    con = client.get_primary_connection()
    if type(con) != NM.VpnConnection:
        return None, None
    uuid = con.get_uuid()
    status = con.get_state()
    return uuid, status


def get_vpn_status(client: 'NM.Client') -> Tuple['NM.VpnConnectionState', 'NM.VpnConnectionStateReason']:
    vpns = [a for a in NM.Client.new(None).get_active_connections() if type(a) == NM.VpnConnection]
    if len(vpns) > 1:
        _logger.warning("more than one VPN connection active")
        return NM.VpnConnectionState.UNKNOWN, NM.VpnConnectionStateReason.UNKNOWN
    elif len(vpns) == 0:
        return NM.VpnConnectionState.UNKNOWN, NM.VpnConnectionStateReason.UNKNOWN
    else:
        return vpns[0].get_state(), vpns[0].get_state_reason()


def set_default_gateway(enable: bool):
    "If True, make the VPN connection the default gateway."
    _logger.info(f"setting default gateway: {enable}")
    client = get_client()
    uuid = get_uuid()
    connection = client.get_connection_by_uuid(uuid)
    ipv4_setting = connection.get_setting_ip4_config()
    ipv6_setting = connection.get_setting_ip6_config()
    ipv4_setting.set_property('never-default', not enable)
    ipv6_setting.set_property('never-default', not enable)
    connection.commit_changes(
        save_to_disk=True,
        cancellable=None,
    )


@lru_cache(maxsize=1)
def get_dbus() -> Optional['dbus.SystemBus']:
    """
    Get the DBus system bus.

    None is returned on failure.
    """
    if dbus is None:
        logging.debug("DBus module could not be imported")
        return None
    try:
        from dbus.mainloop.glib import DBusGMainLoop
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus(private=True)
    except Exception:
        logging.debug("Unable to access dbus", exc_info=True)
        return None
    else:
        return bus


def subscribe_to_status_changes(
    callback: Callable[['NM.VpnConnectionState', 'NM.VpnConnectionStateReason'], Any],
) -> bool:
    """
    Subscribe to all network status changes via DBus.

    The callback argument is called with the connection state and reason
    whenever they change.

    False is returned on failure.
    """
    bus = get_dbus()
    if bus is None:
        return False

    def wrapped_callback(state_code: 'dbus.UInt32', reason_code: 'dbus.UInt32'):
        state = NM.VpnConnectionState(state_code)
        reason = NM.VpnConnectionStateReason(reason_code)
        callback(state, reason)

    bus.add_signal_receiver(
        handler_function=wrapped_callback,
        dbus_interface='org.freedesktop.NetworkManager.VPN.Connection',
        signal_name='VpnStateChanged',
    )
    return True


def action_with_mainloop(action: Callable):
    _logger.info("calling action with CLI mainloop")
    main_loop = get_mainloop()

    def quit_loop(*args, **kwargs):
        _logger.info("Quiting main loop, thanks!")
        main_loop.quit()

    action(callback=quit_loop)
    main_loop.run()


def save_connection_with_mainloop(config, private_key, certificate):
    action_with_mainloop(
        action=lambda callback: save_connection_with_config(get_client(), config, private_key, certificate, callback))


def activate_connection_with_mainloop(uuid):
    action_with_mainloop(action=lambda callback: activate_connection(get_client(), uuid, callback))


def deactivate_connection_with_mainloop(uuid):
    action_with_mainloop(action=lambda callback: deactivate_connection(get_client(), uuid, callback))
