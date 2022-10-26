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
from eduvpn.variants import ApplicationVariant
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


# A manager for a manager :-)
class NMManager:
    def __init__(self, variant: ApplicationVariant):
        self.variant = variant
        try:
            self.client = NM.Client.new(None)
        except Exception:
            self.client = None

    @property
    def available(self) -> bool:
        if NM is None:
            return False
        if self.client is None:
            return False
        return True

    @property
    def managed(self) -> bool:
        """
        check if any device of the primary connection is managed by Network Manager
        """
        active_connection = self.client.get_primary_connection()
        if active_connection is None:
            return False

        master_devices = active_connection.get_devices()
        if master_devices is None:
            return False

        return any(d.get_managed() for d in master_devices)

    @property
    def uuid(self):
        return get_uuid(self.variant)

    @uuid.setter
    def uuid(self, new_uuid):
        set_uuid(self.variant, new_uuid)

    @property
    def connection_state(self) -> ConnectionState:
        connections = [
            connection
            for connection in self.client.get_active_connections()
            if connection.get_uuid() == self.uuid
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

    @property
    def vpn_status(
        self,
    ) -> Tuple["NM.VpnConnectionState", "NM.VpnConnectionStateReason"]:
        vpns = [
            a
            for a in self.client.get_active_connections()
            if type(a) == NM.VpnConnection
        ]
        if len(vpns) > 1:
            _logger.warning("more than one VPN connection active")
            return NM.VpnConnectionState.UNKNOWN, NM.VpnConnectionStateReason.UNKNOWN
        elif len(vpns) == 0:
            return NM.VpnConnectionState.UNKNOWN, NM.VpnConnectionStateReason.UNKNOWN
        else:
            return vpns[0].get_state(), vpns[0].get_state_reason()

    @property
    def active_connection(self) -> Optional["NM.ActiveConnection"]:
        """
        Gets the active connection for the current uuid
        """
        for connection in self.client.get_active_connections():
            if connection.get_uuid() == self.uuid:
                return connection
        return None

    @property
    def iface(self) -> Optional[str]:
        """
        Get the interface as a string for an openvpn or wireguard connection if there is one
        """
        active_con = self.active_connection
        if not active_con:
            return None

        devices = active_con.get_devices()
        if not devices:
            return None

        # Not always a master device is configured
        # So get the interface for the first device we have
        return devices[0].get_iface()

    @property
    def ipv4(self) -> Optional[str]:
        """
        Get the ipv4 address for an openvpn or wireguard connection as a string if there is one
        """
        active_con = self.active_connection
        if not active_con:
            return None

        ip4_config = active_con.get_ip4_config()
        if not ip4_config:
            return None

        addresses = ip4_config.get_addresses()
        if not addresses:
            return None

        return addresses[0].get_address()

    @property
    def ipv6(self) -> Optional[str]:
        """
        Get the ipv6 address for an openvpn or wireguard connection as a string if there is one
        """
        active_con = self.active_connection

        if not active_con:
            return None

        ip6_config = active_con.get_ip6_config()

        if not ip6_config:
            return None

        addresses = ip6_config.get_addresses()
        if not addresses:
            return None
        return addresses[0].get_address()

    @property
    def existing_connection(self) -> Optional[str]:
        connection = self.client.get_connection_by_uuid(self.uuid)
        if connection is None:
            return None
        else:
            return uuid

    def ovpn_import(self, target: Path) -> Optional["NM.Connection"]:
        """
        Use the Network Manager VPN config importer to import an OpenVPN configuration file.
        """
        vpn_infos = [
            i for i in NM.VpnPluginInfo.list_load() if i.get_name() == "openvpn"
        ]

        if len(vpn_infos) != 1:
            raise Exception(f"Expected one openvpn VPN plugins, got: {len(vpn_infos)}")

        conn = vpn_infos[0].load_editor_plugin().import_(str(target))
        conn.normalize()
        return conn

    def import_ovpn_with_certificate(
        self, ovpn: Ovpn, private_key: str, certificate: str
    ) -> "NM.SimpleConnection":
        """
        Import the OVPN string into Network Manager.
        """
        target_parent = Path(mkdtemp())
        target = target_parent / f"{self.variant.vpn_name}.ovpn"
        write_ovpn(ovpn, private_key, certificate, target)
        connection = self.ovpn_import(target)
        rmtree(target_parent)
        return connection

    def import_ovpn(self, ovpn: Ovpn) -> "NM.SimpleConnection":
        """
        Import the OVPN string into Network Manager.
        """
        target_parent = Path(mkdtemp())
        target = target_parent / f"{self.variant.vpn_name}.ovpn"
        _logger.debug(f"Writing configuration to {target}")
        with open(target, mode="w+t") as f:
            ovpn.write(f)
        connection = self.ovpn_import(target)
        rmtree(target_parent)
        return connection

    def add_connection(
        self,
        connection: "NM.Connection",
        callback: Optional[Callable] = None,
    ) -> None:
        _logger.debug("Adding new connection")
        self.client.add_connection_async(
            connection=connection,
            save_to_disk=True,
            callback=add_connection_callback,
            user_data=(self, callback),
        )

    def update_connection(
        self, old_con: "NM.Connection", new_con: "NM.Connection", callback=None
    ):
        """
        Update an existing Network Manager connection with the settings from another Network Manager connection
        """
        _logger.debug("Updating existing connection with new configuration")

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
            user_data=(self, callback),
        )

    def set_connection(
        self,
        new_connection: SimpleConnection,
        callback: Callable,
        default_gateway: bool,
        system_wide: bool,
    ):
        new_connection = self.set_setting_default_gateway(
            new_connection, default_gateway
        )
        new_connection = self.set_setting_ensure_permissions(
            new_connection, not system_wide
        )
        if self.uuid:
            old_con = self.client.get_connection_by_uuid(self.uuid)
            if old_con:
                self.update_connection(old_con, new_connection, callback)
                return
        self.add_connection(new_connection, callback)

    def set_setting_default_gateway(
        self, con: "NM.SimpleConnection", enable: bool
    ) -> "NM.SimpleConnection":
        "If True, make the VPN connection the default gateway."
        _logger.debug(f"setting default gateway: {enable}")
        ipv4_setting = con.get_setting_ip4_config()
        ipv6_setting = con.get_setting_ip6_config()
        ipv4_setting.set_property("never-default", not enable)
        ipv6_setting.set_property("never-default", not enable)
        con.add_setting(ipv4_setting)
        con.add_setting(ipv6_setting)
        return con

    def set_setting_ensure_permissions(
        self, con: "NM.SimpleConnection", enable: bool
    ) -> "NM.SimpleConnection":
        if enable:
            s_con = con.get_setting_connection()
            s_con.add_permission("user", GLib.get_user_name(), None)
            con.add_setting(s_con)
        return con

    def save_connection(
        self,
        ovpn: Ovpn,
        private_key,
        certificate,
        callback,
        default_gateway,
        system_wide,
    ):
        _logger.debug("writing configuration to Network Manager")
        new_con = self.import_ovpn_with_certificate(ovpn, private_key, certificate)
        self.set_connection(new_con, callback, default_gateway, system_wide)

    def save_connection_with_config(
        config,
        private_key,
        certificate,
        callback=None,
    ):
        ovpn = Ovpn.parse(config)
        settings_config = self.variant.config
        return self.save_connection(
            vpn, private_key, certificate, callback, settings_config.nm_system_wide
        )

    def start_openvpn_connection(
        self, ovpn: Ovpn, default_gateway, *, callback=None
    ) -> None:
        _logger.debug("writing ovpn configuration to Network Manager")
        new_con = self.import_ovpn(ovpn)
        settings_config = self.variant.config
        self.set_connection(
            new_con, callback, default_gateway, settings_config.nm_system_wide
        )

    def start_wireguard_connection(
        self,
        config: ConfigParser,
        default_gateway,
        *,
        callback=None,
    ) -> None:
        _logger.debug("writing wireguard configuration to Network Manager")

        ipv4s = []
        ipv6s = []
        for ip in config["Interface"]["Address"].split(","):
            addr = ip_interface(ip.strip())
            if addr.version == 4:
                ipv4s.append(
                    NM.IPAddress(AF_INET, str(addr.ip), addr.network.prefixlen)
                )
            elif addr.version == 6:
                ipv6s.append(
                    NM.IPAddress(AF_INET6, str(addr.ip), addr.network.prefixlen)
                )

        dns4 = []
        dns6 = []
        dns_hostnames = []

        # DNS entries are not required
        dns_entries = config["Interface"].get("DNS")
        if dns_entries:
            for dns_entry in dns_entries.split(","):
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
        s_con.set_property(
            NM.SETTING_CONNECTION_ID, f"{self.variant.vpn_name}-wireguard"
        )
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

        settings_config = self.variant.config
        self.set_connection(
            profile, callback, default_gateway, settings_config.nm_system_wide
        )

    def activate_connection(self, callback: Optional[Callable] = None) -> None:
        con = self.client.get_connection_by_uuid(self.uuid)
        _logger.debug(f"activate_connection: {con}")
        if con is None:
            # Temporary workaround, connection is sometimes created too
            # late while according to the logging the connection is already
            # created. Need to find the correct event to sync on.
            time.sleep(0.1)
            GLib.idle_add(lambda: self.activate_connection(callback))
            return

        def activate_connection_callback(a_client, res, callback=None):
            try:
                result = a_client.activate_connection_finish(res)
            except Exception as e:
                _logger.error(e)
            else:
                _logger.debug(f"activate_connection_async result: {result}")
            finally:
                if callback:
                    callback()

        self.client.activate_connection_async(
            connection=con, callback=activate_connection_callback, user_data=callback
        )

    def deactivate_connection(self, callback: Optional[Callable] = None) -> None:
        connection = self.active_connection
        if connection is None:
            _logger.warning(f"no connection to deactivate of uuid {uuid}")
            return
        type = connection.get_connection_type()
        if type == "vpn":
            self.deactivate_connection_vpn(callback)
        elif type == "wireguard":
            self.deactivate_connection_wg(callback)
        else:
            _logger.warning(f"unexpected connection type {type}")

    def deactivate_connection_vpn(self, callback: Optional[Callable] = None) -> None:
        con = self.active_connection
        _logger.debug(f"deactivate_connection uuid: {uuid} connection: {con}")
        if con:

            def on_deactivate_connection(a_client: "NM.Client", res, callback=None):
                try:
                    result = a_client.deactivate_connection_finish(res)
                except Exception as e:
                    _logger.error(e)
                else:
                    _logger.debug(f"deactivate_connection_async result: {result}")
                finally:
                    if callback:
                        self.delete_connection(callback)

            self.client.deactivate_connection_async(
                active=con, callback=on_deactivate_connection, user_data=callback
            )
        else:
            _logger.debug("No active connection to deactivate")

    def delete_connection(self, callback: Callable) -> None:
        # We run the disconnected callback early if a delete fail happens
        if self.uuid is None:
            callback()
            _logger.warning("No uuid found for deleting the connection")
            return

        con = self.client.get_connection_by_uuid(self.uuid)
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
                _logger.debug(f"delete_async result: {result}")
            finally:
                if callback:
                    callback()

        con.delete_async(callback=on_deleted, user_data=callback)

    def deactivate_connection_wg(self, callback: Optional[Callable] = None) -> None:
        devices = [
            device
            for device in self.client.get_all_devices()
            if device.get_type_description() == "wireguard"
            and self.uuid
            in {conn.get_uuid() for conn in device.get_available_connections()}
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
                _logger.debug(f"disconnect_async result: {result}")
            finally:
                if callback:
                    self.delete_connection(callback)

        _logger.debug(f"disconnect uuid: {uuid}")
        device.disconnect_async(callback=on_disconnect, user_data=callback)

    def subscribe_to_status_changes(
        self,
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
            if active.get_uuid() != self.uuid:
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
            if active_con.get_uuid() != self.uuid:
                return
            connect(active_con)

        # If a connection was found already then...
        active_con = self.active_connection

        if active_con:
            connect(active_con)

        # Connect the active connection added signal
        self.client.connect("active-connection-added", wrapped_connection_added)
        return True

    def connection_status(
        self,
    ) -> Tuple[Optional[str], Optional["NM.ActiveConnectionState"]]:
        con = self.client.get_primary_connection()
        if type(con) != NM.VpnConnection:
            return None, None
        uuid = con.get_uuid()
        status = con.get_state()
        return uuid, status


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


def action_with_mainloop(action: Callable):
    _logger.debug("calling action with CLI mainloop")
    main_loop = GLib.MainLoop()

    def quit_loop(*args, **kwargs):
        _logger.debug("Quiting main loop, thanks!")
        main_loop.quit()

    # Schedule the action
    GLib.idle_add(lambda: action(callback=quit_loop))

    # Run the main loop
    main_loop.run()


def add_connection_callback(
    client: Client, result: Task, user_data: Tuple[NMManager, Optional[Callable]]
) -> None:
    object, callback = user_data
    new_con = client.add_connection_finish(result)
    object.uuid = new_con.get_uuid()
    _logger.debug(f"Connection added for uuid: {object.uuid}")
    if callback is not None:
        callback(new_con is not None)


def update_connection_callback(
    remote_connection, result, user_data: Tuple[NMManager, Optional[Callable]]
):
    object, callback = user_data
    res = remote_connection.commit_changes_finish(result)
    _logger.debug(
        f"Connection updated for uuid: {object.uuid}, result: {res}, remote_con: {remote_connection}"
    )
    if callback is not None:
        callback(result)


def is_wireguard_supported() -> bool:
    return hasattr(NM, "WireGuardPeer")
