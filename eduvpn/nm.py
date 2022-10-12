import enum
import logging
import time
import uuid
from configparser import ConfigParser
from functools import lru_cache
from ipaddress import ip_address, ip_interface
from pathlib import Path
from shutil import rmtree
from socket import AF_INET, AF_INET6
from tempfile import mkdtemp
from typing import Any, Callable, Optional, Tuple

from eduvpn.config import Configuration
from eduvpn.ovpn import Ovpn
from eduvpn.storage import get_uuid, set_uuid, write_ovpn
from eduvpn.utils import cache
from eduvpn.variants import get_variant_config, get_variant_vpn_name
import gi
gi.require_version("NM", "1.0")  # noqa: E402
from gi.repository.Gio import Task
from gi.repository.NM import Client, SimpleConnection

_logger = logging.getLogger(__name__)

try:
    import gi

    gi.require_version("NM", "1.0")
    from gi.repository import NM, GLib  # type: ignore
except (ImportError, ValueError):
    _logger.warning("Network Manager not available")
    NM = None

try:
    import dbus
except ImportError:
    dbus = None


@lru_cache()
def get_client() -> "NM.Client":
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


def get_active_connection() -> Optional["NM.ActiveConnection"]:
    """
    Gets the active connection for the current uuid
    """
    client = get_client()
    uuid = get_uuid()
    for connection in client.get_active_connections():
        if connection.get_uuid() == uuid:
            return connection
    return None


def get_iface() -> Optional[str]:
    """
    Get the interface as a string for an openvpn or wireguard connection if there is one
    """
    active_con = get_active_connection()
    if not active_con:
        return None

    devices = active_con.get_devices()
    if not devices:
        return None

    # Not always a master device is configured
    # So get the interface for the first device we have
    return devices[0].get_iface()


def get_ipv4() -> Optional[str]:
    """
    Get the ipv4 address for an openvpn or wireguard connection as a string if there is one
    """
    active_con = get_active_connection()
    if not active_con:
        return None

    ip4_config = active_con.get_ip4_config()
    if not ip4_config:
        return None

    addresses = ip4_config.get_addresses()
    if not addresses:
        return None

    return addresses[0].get_address()


def get_ipv6() -> Optional[str]:
    """
    Get the ipv6 address for an openvpn or wireguard connection as a string if there is one
    """
    active_con = get_active_connection()

    if not active_con:
        return None

    ip6_config = active_con.get_ip6_config()

    if not ip6_config:
        return None

    addresses = ip6_config.get_addresses()
    if not addresses:
        return None
    return addresses[0].get_address()


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


def nm_managed() -> bool:
    """
    check if any device of the primary connection is managed by Network Manager
    """
    client = get_client()
    active_connection = client.get_primary_connection()
    if active_connection is None:
        return False

    master_devices = active_connection.get_devices()
    if master_devices is None:
        return False

    return any(d.get_managed() for d in master_devices)


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


def nm_ovpn_import(target: Path) -> Optional["NM.Connection"]:
    """
    Use the Network Manager VPN config importer to import an OpenVPN configuration file.
    """
    vpn_infos = [i for i in NM.VpnPluginInfo.list_load() if i.get_name() == "openvpn"]

    if len(vpn_infos) != 1:
        raise Exception(f"Expected one openvpn VPN plugins, got: {len(vpn_infos)}")

    conn = vpn_infos[0].load_editor_plugin().import_(str(target))
    conn.normalize()
    return conn


def import_ovpn_and_certificate(
    ovpn: Ovpn, variant, private_key: str, certificate: str
) -> "NM.SimpleConnection":
    """
    Import the OVPN string into Network Manager.
    """
    target_parent = Path(mkdtemp())
    vpn_name = get_variant_vpn_name(variant)
    target = target_parent / f"{vpn_name}.ovpn"
    write_ovpn(ovpn, private_key, certificate, target)
    connection = nm_ovpn_import(target)
    rmtree(target_parent)
    return connection


def import_ovpn(ovpn: Ovpn, variant) -> "NM.SimpleConnection":
    """
    Import the OVPN string into Network Manager.
    """
    target_parent = Path(mkdtemp())
    vpn_name = get_variant_vpn_name(variant)
    target = target_parent / f"{vpn_name}.ovpn"
    _logger.info(f"Writing configuration to {target}")
    with open(target, mode="w+t") as f:
        ovpn.write(f)
    connection = nm_ovpn_import(target)
    rmtree(target_parent)
    return connection


def add_connection_callback(client: Client, result: Task, callback: Optional[Callable]=None) -> None:
    new_con = client.add_connection_finish(result)
    set_uuid(uuid=new_con.get_uuid())
    _logger.info(f"Connection added for uuid: {get_uuid()}")
    if callback is not None:
        callback(new_con is not None)


def add_connection(client: "NM.Client", connection: "NM.Connection", callback: Optional[Callable]=None) -> None:
    _logger.info("Adding new connection")
    client.add_connection_async(
        connection=connection,
        save_to_disk=True,
        callback=add_connection_callback,
        user_data=callback,
    )


def update_connection_callback(remote_connection, result, callback=None):
    res = remote_connection.commit_changes_finish(result)
    _logger.debug(
        f"Connection updated for uuid: {get_uuid()}, result: {res}, remote_con: {remote_connection}"
    )
    if callback is not None:
        callback(result)


def update_connection(
    old_con: "NM.Connection", new_con: "NM.Connection", callback=None
):
    """
    Update an existing Network Manager connection with the settings from another Network Manager connection
    """
    _logger.info("Updating existing connection with new configuration")

    # Don't attempt to overwrite the uuid,
    # but reuse the one from the previous connection.
    # Refer to issue #269.
    for setting in new_con.get_settings():
        if setting.get_name() == "connection":
            setting.props.uuid = old_con.get_uuid()
    old_con.replace_settings_from_connection(new_con)
    old_con.commit_changes_async(
        save_to_disk=True,
        cancellable=None,
        callback=update_connection_callback,
        user_data=callback,
    )


def set_connection(client: Client, new_connection: SimpleConnection, callback: Callable, system_wide: bool=False):
    uuid = get_uuid()
    new_connection = set_setting_ensure_permissions(new_connection, not system_wide)
    if uuid:
        old_con = client.get_connection_by_uuid(uuid)
        if old_con:
            update_connection(old_con, new_connection, callback)
            return
    add_connection(client=client, connection=new_connection, callback=callback)


def set_setting_ensure_permissions(
    con: "NM.SimpleConnection", enable: bool
) -> "NM.SimpleConnection":
    if enable:
        s_con = con.get_setting_connection()
        s_con.add_permission("user", GLib.get_user_name(), None)
        con.add_setting(s_con)
    return con


def save_connection(
    client: "NM.Client",
    variant,
    ovpn: Ovpn,
    private_key,
    certificate,
    callback=None,
    system_wide=False,
):
    _logger.info("writing configuration to Network Manager")
    new_con = import_ovpn_and_certificate(ovpn, variant, private_key, certificate)
    set_connection(client, new_con, callback, system_wide)


def save_connection_with_config(
    client: "NM.Client",
    variant,
    config,
    private_key,
    certificate,
    callback=None,
):
    ovpn = Ovpn.parse(config)
    settings = get_variant_config(variant)
    return save_connection(
        client, variant, ovpn, private_key, certificate, callback, settings.nm_system_wide
    )


def start_openvpn_connection(ovpn: Ovpn, variant, *, callback=None) -> None:
    client = get_client()
    _logger.info("writing ovpn configuration to Network Manager")
    new_con = import_ovpn(ovpn, variant)
    settings = get_variant_config(variant)
    set_connection(client, new_con, callback, settings.nm_system_wide)


def start_wireguard_connection(
    config: ConfigParser,
    variant,
    *,
    callback=None,
) -> None:
    client = get_client()
    _logger.info("writing wireguard configuration to Network Manager")

    ipv4s = []
    ipv6s = []
    for ip in config["Interface"]["Address"].split(","):
        addr = ip_interface(ip.strip())
        if addr.version == 4:
            ipv4s.append(NM.IPAddress(AF_INET, str(addr.ip), addr.network.prefixlen))
        elif addr.version == 6:
            ipv6s.append(NM.IPAddress(AF_INET6, str(addr.ip), addr.network.prefixlen))

    dns4 = []
    dns6 = []
    dns_hostnames = []

    # DNS entries are not required
    dns_entries = config['Interface'].get('DNS')
    if dns_entries:
        for dns_entry in dns_entries.split(','):
            stripped_entry = dns_entry.strip()
            try:
                address = ip_address(stripped_entry)
            # The entry is not an ip but a hostname
            # They need to be added to dns search domains
            except ValueError:
                dns_hostnames.append(stripped_entry)
            else:
                if address.version == 4:
                    dns4.append(str(address))
                elif address.version == 6:
                    dns6.append(str(address))

    profile = NM.SimpleConnection.new()
    s_con = NM.SettingConnection.new()
    s_con.set_property(NM.DEVICE_AUTOCONNECT, False)
    vpn_name = get_variant_vpn_name(variant)
    s_con.set_property(NM.SETTING_CONNECTION_ID, f"{vpn_name}-wireguard")
    s_con.set_property(NM.SETTING_CONNECTION_TYPE, "wireguard")
    s_con.set_property(NM.SETTING_CONNECTION_UUID, str(uuid.uuid4()))
    s_con.set_property(NM.SETTING_CONNECTION_INTERFACE_NAME, "EduVPN-WG")

    # https://lazka.github.io/pgi-docs/NM-1.0/classes/WireGuardPeer.html#NM.WireGuardPeer
    peer = NM.WireGuardPeer.new()
    peer.set_endpoint(config["Peer"]["Endpoint"], allow_invalid=False)
    peer.set_public_key(config["Peer"]["PublicKey"], accept_invalid=False)
    for ip in config["Peer"]["AllowedIPs"].split(","):
        peer.append_allowed_ip(ip.strip(), accept_invalid=False)

    s_ip4 = NM.SettingIP4Config.new()
    s_ip6 = NM.SettingIP6Config.new()

    for i in dns4:
        s_ip4.add_dns(i)
    for i in dns6:
        s_ip6.add_dns(i)
    for i in dns_hostnames:
        s_ip4.add_dns_search(i)
        s_ip6.add_dns_search(i)

    s_ip4.set_property(NM.SETTING_IP_CONFIG_METHOD, "manual")
    s_ip6.set_property(NM.SETTING_IP_CONFIG_METHOD, "manual")

    for i in ipv4s:
        s_ip4.add_address(i)
    for i in ipv6s:
        s_ip6.add_address(i)

    # https://lazka.github.io/pgi-docs/NM-1.0/classes/SettingWireGuard.html
    w_con = NM.SettingWireGuard.new()
    w_con.append_peer(peer)
    private_key = config["Interface"]["PrivateKey"]
    w_con.set_property(NM.SETTING_WIREGUARD_PRIVATE_KEY, private_key)

    profile.add_setting(s_ip4)
    profile.add_setting(s_ip6)
    profile.add_setting(s_con)
    profile.add_setting(w_con)

    settings = get_variant_config(variant)
    set_connection(client, profile, callback, settings.nm_system_wide)


def activate_connection(client: "NM.Client", uuid: str, callback: Optional[Callable]=None) -> None:
    con = client.get_connection_by_uuid(uuid)
    _logger.info(f"activate_connection uuid: {uuid} connection: {con}")
    if con is None:
        # Temporary workaround, connection is sometimes created too
        # late while according to the logging the connection is already
        # created. Need to find the correct event to sync on.
        time.sleep(0.1)
        GLib.idle_add(lambda: activate_connection(client, uuid, callback))
        return

    def activate_connection_callback(a_client, res, callback=None):
        try:
            result = a_client.activate_connection_finish(res)
        except Exception as e:
            _logger.error(e)
        else:
            _logger.info(f"activate_connection_async result: {result}")
        finally:
            if callback:
                callback()

    client.activate_connection_async(
        connection=con, callback=activate_connection_callback, user_data=callback
    )


def deactivate_connection(client: "NM.Client", uuid: str, callback: Optional[Callable]=None) -> None:
    connection = client.get_connection_by_uuid(uuid)
    if connection is None:
        _logger.warning(f"no connection to deactivate of uuid {uuid}")
        return
    type = connection.get_connection_type()
    if type == "vpn":
        deactivate_connection_vpn(client, uuid, callback)
    elif type == "wireguard":
        deactivate_connection_wg(client, uuid, callback)
    else:
        _logger.warning(f"unexpected connection type {type} of {uuid}")


def deactivate_connection_vpn(client: "NM.Client", uuid: str, callback: Optional[Callable]=None) -> None:
    con = get_active_connection()
    _logger.debug(f"deactivate_connection uuid: {uuid} connection: {con}")
    if con:

        def on_deactivate_connection(a_client: "NM.Client", res, callback=None):
            try:
                result = a_client.deactivate_connection_finish(res)
            except Exception as e:
                _logger.error(e)
            else:
                _logger.info(f"deactivate_connection_async result: {result}")
            finally:
                if callback:
                    delete_connection(callback)

        client.deactivate_connection_async(
            active=con, callback=on_deactivate_connection, user_data=callback
        )
    else:
        _logger.info("No active connection to deactivate")


def delete_connection(callback: Callable) -> None:
    client = get_client()
    uuid = get_uuid()

    # We run the disconnected callback early if a delete fail happens
    if uuid is None:
        callback()
        _logger.warning("No uuid found for deleting the connection")
        return

    con = client.get_connection_by_uuid(uuid)
    if con is None:
        callback()
        _logger.warning(f"No uuid connection found to delete with uuid {uuid}")
        return

    # Delete the connection and after that do the callback
    def on_deleted(a_con: "NM.RemoteConnection", res, callback=None):
        try:
            result = a_con.delete_finish(res)
        except Exception as e:
            _logger.error(e)
        else:
            _logger.info(f"delete_async result: {result}")
        finally:
            if callback:
                callback()

    con.delete_async(callback=on_deleted, user_data=callback)


def deactivate_connection_wg(client: "NM.Client", uuid: str, callback: Optional[Callable]=None) -> None:
    devices = [
        device
        for device in client.get_all_devices()
        if device.get_type_description() == "wireguard"
        and uuid in {conn.get_uuid() for conn in device.get_available_connections()}
    ]
    if not devices:
        _logger.warning("No WireGuard device to disconnect")
        return

    assert len(devices) == 1
    device = devices[0]

    def on_disconnect(a_device: "NM.DeviceWireGuard", res, callback=None):
        try:
            result = a_device.disconnect_finish(res)
        except Exception as e:
            _logger.error(e)
        else:
            _logger.info(f"disconnect_async result: {result}")
        finally:
            if callback:
                delete_connection(callback)

    _logger.debug(f"disconnect uuid: {uuid}")
    device.disconnect_async(callback=on_disconnect, user_data=callback)


class ConnectionState(enum.Enum):
    CONNECTING = enum.auto()
    CONNECTED = enum.auto()
    DISCONNECTED = enum.auto()
    FAILED = enum.auto()
    UNKNOWN = enum.auto()

    @classmethod
    def from_vpn_state(cls, state: "NM.VpnConnectionState") -> "ConnectionState":
        if state in [
            NM.VpnConnectionState.CONNECT,
            NM.VpnConnectionState.IP_CONFIG_GET,
            NM.VpnConnectionState.PREPARE,
        ]:
            return cls.CONNECTING
        elif state is NM.VpnConnectionState.ACTIVATED:
            return cls.CONNECTED
        elif state is NM.VpnConnectionState.DISCONNECTED:
            return cls.DISCONNECTED
        elif state is NM.VpnConnectionState.FAILED:
            return cls.FAILED
        elif state is NM.VpnConnectionState.NEED_AUTH:
            return cls.FAILED
        elif state is NM.VpnConnectionState.UNKNOWN:
            return cls.UNKNOWN
        else:
            raise ValueError(state)

    @classmethod
    def from_active_state(cls, state: "NM.ActiveConnectionState") -> "ConnectionState":
        if state is NM.ActiveConnectionState.ACTIVATING:
            return cls.CONNECTING
        elif state is NM.ActiveConnectionState.ACTIVATED:
            return cls.CONNECTED
        elif state in [
            NM.ActiveConnectionState.DEACTIVATED,
            NM.ActiveConnectionState.DEACTIVATING,
        ]:
            return cls.DISCONNECTED
        elif state is NM.ActiveConnectionState.UNKNOWN:
            return cls.UNKNOWN
        else:
            raise ValueError(state)


def connection_status(
    client: "NM.Client",
) -> Tuple[Optional[str], Optional["NM.ActiveConnectionState"]]:
    con = client.get_primary_connection()
    if type(con) != NM.VpnConnection:
        return None, None
    uuid = con.get_uuid()
    status = con.get_state()
    return uuid, status


def get_connection_state() -> ConnectionState:
    client = get_client()
    uuid = get_uuid()
    connections = [
        connection
        for connection in client.get_active_connections()
        if connection.get_uuid() == uuid
    ]
    if len(connections) == 1:
        connection = connections[0]
    else:
        return ConnectionState.DISCONNECTED
    if isinstance(connection, NM.VpnConnection):
        return ConnectionState.from_vpn_state(connection.get_vpn_state())
    elif isinstance(connection, NM.ActiveConnection):
        return ConnectionState.from_active_state(connection.get_state())
    else:
        _logger.warning(f"connection of unknown type: {connection!r}")
        return ConnectionState.UNKNOWN


def get_vpn_status(
    client: "NM.Client",
) -> Tuple["NM.VpnConnectionState", "NM.VpnConnectionStateReason"]:
    vpns = [
        a
        for a in NM.Client.new(None).get_active_connections()
        if type(a) == NM.VpnConnection
    ]
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
    ipv4_setting.set_property("never-default", not enable)
    ipv6_setting.set_property("never-default", not enable)
    connection.commit_changes(
        save_to_disk=True,
        cancellable=None,
    )


@lru_cache(maxsize=1)
def get_dbus() -> Optional["dbus.SystemBus"]:
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
    callback: Callable[[ConnectionState], Any],
) -> bool:
    """
    Subscribe to network status changes via the NM client.

    The callback argument is called with the connection state and reason
    whenever they change.
    """

    # The callback to monitor state changes
    # Let the state machine know for state updates
    def wrapped_callback(
        active: "NM.ActiveConnection", state_code: int, _reason_code: int
    ):
        if active.get_uuid() != get_uuid():
            return

        state = NM.ActiveConnectionState(state_code)
        callback(ConnectionState.from_active_state(state))

    # Connect the state changed signal for an active connection
    def connect(con: "NM.ActiveConnection"):
        con.connect("state-changed", wrapped_callback)

    # The callback when a connection gets added
    # Connect the signals
    def wrapped_connection_added(
        client: "NM.Client", active_con: "NM.ActiveConnection"
    ):
        if active_con.get_uuid() != get_uuid():
            return
        connect(active_con)

    # If a connection was found already then...
    client = get_client()
    active_con = get_active_connection()

    if active_con:
        connect(active_con)

    # Connect the active connection added signal
    client.connect("active-connection-added", wrapped_connection_added)
    return True


def action_with_mainloop(action: Callable):
    _logger.info("calling action with CLI mainloop")
    main_loop = get_mainloop()

    def quit_loop(*args, **kwargs):
        _logger.info("Quiting main loop, thanks!")
        main_loop.quit()

    # Schedule the action
    GLib.idle_add(lambda: action(callback=quit_loop))

    # Run the main loop
    main_loop.run()


def save_connection_with_mainloop(config, private_key, certificate):
    action_with_mainloop(
        action=lambda callback: save_connection_with_config(
            get_client(), config, private_key, certificate, callback
        )
    )

def activate_connection_with_mainloop(uuid):
    action_with_mainloop(
        action=lambda callback: activate_connection(get_client(), uuid, callback)
    )


def deactivate_connection_with_mainloop(uuid):
    action_with_mainloop(
        action=lambda callback: deactivate_connection(get_client(), uuid, callback)
    )


@cache
def is_wireguard_supported() -> bool:
    return hasattr(NM, "WireGuardPeer")
