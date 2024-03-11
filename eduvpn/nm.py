import enum
import ipaddress
import logging
import os
import socket
import sys
import time
import uuid
from configparser import ConfigParser
from ipaddress import ip_address, ip_interface
from pathlib import Path
from shutil import rmtree
from socket import AF_INET, AF_INET6, IPPROTO_TCP
from tempfile import mkdtemp
from typing import Any, Callable, Optional, TextIO, Tuple

import gi
from eduvpn_common.main import Jar

from eduvpn.ovpn import Ovpn
from eduvpn.storage import get_uuid, set_uuid, write_ovpn
from eduvpn.utils import run_in_glib_thread
from eduvpn.variants import ApplicationVariant

from gi.repository.Gio import Cancellable, Task  # type: ignore

_logger = logging.getLogger(__name__)

LINUX_NET_FOLDER = Path("/sys/class/net")

try:
    import gi

    gi.require_version("NM", "1.0")
    from gi.repository import NM, GLib  # type: ignore
except (ImportError, ValueError):
    _logger.warning("Network Manager not available")
    NM = None


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
        self.proxy = None
        try:
            self._client = NM.Client.new(None)
            self.wg_gateway_ip: Optional[ipaddress.IPv4Address] = None
        except Exception:
            self._client = None
        self.cancel_jar = Jar(lambda x: x.cancel())

    @property
    def client(self) -> "NM.Client":
        if self._client is None:
            raise Exception("no client available")
        return self._client

    @property
    def available(self) -> bool:
        return self._client is not None

    # TODO: Move this somewhere else?
    def open_stats_file(self, filename: str) -> Optional[TextIO]:
        """
        Helper function to open a statistics network file
        """
        if not self.iface:
            return None
        filepath = LINUX_NET_FOLDER / self.iface / "statistics" / filename  # type: ignore
        if not filepath.is_file():
            return None
        return open(filepath, "r")

    # TODO: Move this somewhere else?
    def get_stats_bytes(self, filehandler: Optional[TextIO]) -> Optional[int]:
        """
        Helper function to get a statistics file to calculate the total data transfer
        """
        # If the interface is not set
        # or the file is not present, we cannot get the stat
        if not self.iface:
            # Warning was already shown
            return None
        if not filehandler:
            # Warning was already shown
            return None

        # Get the statistic from the file
        # and go to the beginning
        try:
            stat = int(filehandler.readline())
        except ValueError:
            stat = 0
        filehandler.seek(0)
        return stat

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
    def mtu(self) -> Optional[int]:
        protocol = self.protocol
        # For WireGuard, we can get the MTU from the device
        if protocol == "WireGuard":
            device = self.wireguard_device
            if device is None:
                return None
            return device.get_mtu()
        elif protocol == "OpenVPN":
            # TODO: How to query networkmanager for this?
            return 1500
        return None

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
    def active_connection(self) -> Optional["NM.ActiveConnection"]:
        """
        Gets the active connection for the current uuid
        """
        for connection in self.client.get_active_connections():
            if connection.get_uuid() == self.uuid:
                return connection
        return None

    @property
    def protocol(self) -> Optional[str]:
        """
        Get the VPN protocol as a string for the active connection
        """
        connection = self.active_connection
        if connection is None:
            return None
        type = connection.get_connection_type()
        if type == "vpn":
            return "OpenVPN"
        elif type == "wireguard":
            if self.proxy:
                return "WireGuard (Proxyguard)"
            return "WireGuard"
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
    def ipv4_config(self) -> Optional["NM.IPConfig"]:
        """
        Get the ipv4 config for the active VPN connection
        """
        active_con = self.active_connection
        if not active_con:
            return None

        return active_con.get_ip4_config()

    @property
    def ipv4(self) -> Optional[str]:
        """
        Get the ipv4 address for an openvpn or wireguard connection as a string if there is one
        """
        ip4_config = self.ipv4_config
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

        for addr in addresses:
            try:
                ipv6_str = addr.get_address()
                ipv6 = ip_address(ipv6_str)
                if not ipv6.is_link_local:
                    return ipv6_str
            except ValueError:
                continue
        return None

    @property
    def failover_endpoint_ip(self) -> Optional[str]:
        protocol = self.protocol
        if protocol == "OpenVPN":
            # if OpenVPN return the gateway from the ip config
            ipv4_config = self.ipv4_config
            if not ipv4_config:
                _logger.debug("no ipv4_config found in OpenVPN failover endpoint")
                return None
            return ipv4_config.get_gateway()
        elif protocol == "WireGuard":
            # if WireGuard return the cached IP
            if not self.wg_gateway_ip:
                _logger.debug("no wg gateway ip found in failover endpoint")
                return None
            return str(self.wg_gateway_ip)
        else:
            _logger.debug(f"Unknown protocol: {protocol}")
            return None

    @property
    def existing_connection(self) -> Optional[str]:
        if not self.uuid:
            return None
        connection = self.client.get_connection_by_uuid(self.uuid)
        if connection is None:
            return None
        else:
            return self.uuid

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
        target = target_parent / f"{self.variant.name}.ovpn"
        write_ovpn(ovpn, private_key, certificate, target)
        connection = self.ovpn_import(target)
        rmtree(target_parent)
        return connection

    def import_ovpn(self, ovpn: Ovpn) -> "NM.SimpleConnection":
        """
        Import the OVPN string into Network Manager.
        """
        target_parent = Path(mkdtemp())
        target = target_parent / f"{self.variant.name}.ovpn"
        _logger.debug(f"Writing configuration to {target}")
        with open(target, mode="w+t") as f:
            ovpn.write(f)
        connection = self.ovpn_import(target)
        rmtree(target_parent)
        return connection

    @run_in_glib_thread
    def add_connection(
        self,
        connection: "NM.Connection",
        callback: Optional[Callable] = None,
    ) -> None:
        _logger.debug("Adding new connection")
        c = self.new_cancellable()
        self.client.add_connection_async(
            connection=connection,
            save_to_disk=True,
            callback=add_connection_callback,
            cancellable=c,
            user_data=(self, c, callback),
        )

    def set_connection(
        self,
        new_connection: "NM.SimpleConnection",
        callback: Callable,
    ):
        new_connection = self.set_setting_ensure_permissions(new_connection)
        if self.existing_connection:

            def deleted(success: bool):
                if success:
                    self.add_connection(new_connection, callback)
                else:
                    callback(False)

            self.delete_connection(deleted)
        else:
            self.add_connection(new_connection, callback)

    def set_setting_ensure_permissions(
        self, con: "NM.SimpleConnection"
    ) -> "NM.SimpleConnection":
        s_con = con.get_setting_connection()
        s_con.add_permission("user", GLib.get_user_name(), None)
        con.add_setting(s_con)
        return con

    def start_openvpn_connection(
        self, ovpn: Ovpn, default_gateway, dns_search_domains, *, callback=None
    ) -> None:
        _logger.debug("writing ovpn configuration to Network Manager")
        new_con = self.import_ovpn(ovpn)
        s_ip4 = new_con.get_setting_ip4_config()
        s_ip6 = new_con.get_setting_ip6_config()

        # avoid DNS leaks in default gateway
        # see man nm-settings for dns-priority
        # and https://systemd.io/RESOLVED-VPNS/
        if default_gateway:
            s_ip4.set_property(NM.SETTING_IP_CONFIG_DNS_PRIORITY, -2147483648)
            s_ip6.set_property(NM.SETTING_IP_CONFIG_DNS_PRIORITY, -2147483648)
            s_ip4.add_dns_search("~.")
            s_ip6.add_dns_search("~.")
        for i in dns_search_domains:
            s_ip4.add_dns_search(i)
            s_ip6.add_dns_search(i)
        s_ip4.set_property("never-default", not default_gateway)
        s_ip6.set_property("never-default", not default_gateway)
        new_con.add_setting(s_ip4)
        new_con.add_setting(s_ip6)

        self.proxy = None
        self.set_connection(new_con, callback)  # type: ignore

    def get_priorities(self, has_proxy: bool, has_lan: bool):
        # rule, proxy, lan
        if has_proxy:
            if has_lan:
                return [3, 2, 1]
            else:
                return [2, 1, -1]
        else:
            if has_lan:
                return [2, -1, 1]
            else:
                return [1, -1, -1]

    def start_wireguard_connection(  # noqa: C901
        self,
        config: ConfigParser,
        default_gateway,
        *,
        allow_wg_lan=False,
        proxy=None,
        proxy_peer_ips=None,
        callback=None,
    ) -> None:
        _logger.debug("writing wireguard configuration to Network Manager")
        ipv4s = []
        ipv6s = []
        self.wg_gateway_ip = None
        for ip in config["Interface"]["Address"].split(","):
            addr = ip_interface(ip.strip())
            if addr.version == 4:
                if not self.wg_gateway_ip:
                    self.wg_gateway_ip = addr.network[1]
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
        s_con.set_property(NM.SETTING_CONNECTION_ID, self.variant.name)
        s_con.set_property(NM.SETTING_CONNECTION_TYPE, "wireguard")
        s_con.set_property(NM.SETTING_CONNECTION_UUID, str(uuid.uuid4()))
        s_con.set_property(
            NM.SETTING_CONNECTION_INTERFACE_NAME, self.variant.translation_domain
        )

        # https://lazka.github.io/pgi-docs/NM-1.0/classes/WireGuardPeer.html#NM.WireGuardPeer
        peer = NM.WireGuardPeer.new()
        wg_endpoint = config["Peer"]["Endpoint"]
        peer.set_endpoint(wg_endpoint, allow_invalid=False)

        peer.set_public_key(config["Peer"]["PublicKey"], accept_invalid=False)
        for ip in config["Peer"]["AllowedIPs"].split(","):
            peer.append_allowed_ip(ip.strip(), accept_invalid=False)

        s_ip4 = NM.SettingIP4Config.new()
        s_ip6 = NM.SettingIP6Config.new()

        for i in dns4:
            s_ip4.add_dns(i)
        for i in dns6:
            s_ip6.add_dns(i)

        # avoid DNS leaks in default gateway
        # see man nm-settings for dns-priority
        # and https://systemd.io/RESOLVED-VPNS/
        if default_gateway:
            s_ip4.set_property(NM.SETTING_IP_CONFIG_DNS_PRIORITY, -2147483648)
            s_ip6.set_property(NM.SETTING_IP_CONFIG_DNS_PRIORITY, -2147483648)
            s_ip4.add_dns_search("~.")
            s_ip6.add_dns_search("~.")
        for i in dns_hostnames:
            s_ip4.add_dns_search(i)
            s_ip6.add_dns_search(i)

        s_ip4.set_property("never-default", not default_gateway)
        s_ip6.set_property("never-default", not default_gateway)

        s_ip4.set_property(NM.SETTING_IP_CONFIG_METHOD, "manual")
        s_ip6.set_property(NM.SETTING_IP_CONFIG_METHOD, "manual")

        for i in ipv4s:
            s_ip4.add_address(i)
        for i in ipv6s:
            s_ip6.add_address(i)

        # https://lazka.github.io/pgi-docs/NM-1.0/classes/SettingWireGuard.html
        w_con = NM.SettingWireGuard.new()

        # manual routing
        w_con.set_property(NM.SETTING_WIREGUARD_IP4_AUTO_DEFAULT_ROUTE, 0)
        w_con.set_property(NM.SETTING_WIREGUARD_IP6_AUTO_DEFAULT_ROUTE, 0)

        # we set some sensible default with an override using EDUVPN_WG_FWMARK
        fwmark = int(os.environ.get("EDUVPN_WG_FWMARK", 51860))
        listen_port = int(os.environ.get("EDUVPN_WG_LISTEN_PORT", 0))

        s_ip4.set_property(NM.SETTING_IP_CONFIG_ROUTE_TABLE, fwmark)
        s_ip6.set_property(NM.SETTING_IP_CONFIG_ROUTE_TABLE, fwmark)
        w_con.set_property(NM.DEVICE_WIREGUARD_FWMARK, fwmark)
        w_con.set_property(NM.DEVICE_WIREGUARD_LISTEN_PORT, listen_port)

        # The routing that is done by NM by default doesn't cut it
        # It automatically adds a suppress prefixlength rule such that LAN traffic is allowed
        # We want to make this configurable
        # Additionally, the overlap case with split tunnel doesn't work: https://github.com/eduvpn/python-eduvpn-client/issues/551

        rules = [(4, AF_INET, s_ip4, 32), (6, AF_INET6, s_ip6, 128)]
        # priority 1 not fwmark fwmarknum table fwmarknum

        prios = self.get_priorities(proxy is not None, allow_wg_lan)
        for ipver, family, setting, subnet in rules:
            rule = NM.IPRoutingRule.new(family)
            rule.set_priority(prios[0])
            rule.set_invert(True)
            # fwmask 0xffffffff is the default
            rule.set_fwmark(fwmark, 0xFFFFFFFF)
            rule.set_table(fwmark)
            setting.add_routing_rule(rule)

            if proxy:
                dport_proxy = proxy.peer_port
                for proxy_peer_ip in proxy_peer_ips:
                    address = ip_address(proxy_peer_ip)
                    if address.version != ipver:
                        continue
                    proxy_rule = NM.IPRoutingRule.new(family)
                    proxy_rule.set_priority(prios[1])
                    sport = int(proxy.source_port)
                    proxy_rule.set_source_port(sport, sport)
                    proxy_rule.set_to(proxy_peer_ip, subnet)
                    proxy_rule.set_destination_port(dport_proxy, dport_proxy)
                    proxy_rule.set_ipproto(IPPROTO_TCP)
                    setting.add_routing_rule(proxy_rule)

            # when LAN should be allowed, we have to add a higher priority suppress prefixlength rule
            if allow_wg_lan:
                lan_rule = NM.IPRoutingRule.new(family)
                # Downgrade the default wireguard rule priority
                # And set the lan rule to a higher priority
                lan_rule.set_priority(prios[2])
                lan_rule.set_suppress_prefixlength(0)
                setting.add_routing_rule(lan_rule)

        w_con.append_peer(peer)
        private_key = config["Interface"]["PrivateKey"]
        w_con.set_property(NM.SETTING_WIREGUARD_PRIVATE_KEY, private_key)

        # set MTU if available in the config
        mtu = config["Interface"].get("MTU")
        if mtu:
            try:
                w_con.set_property(NM.SETTING_WIREGUARD_MTU, int(mtu))
            except ValueError:
                _logger.warning(f"got invalid WireGuard MTU value: {mtu}")

        profile.add_setting(s_ip4)
        profile.add_setting(s_ip6)
        profile.add_setting(s_con)
        profile.add_setting(w_con)

        self.proxy = proxy

        self.set_connection(profile, callback)  # type: ignore

    def new_cancellable(self):
        c = Cancellable.new()
        self.cancel_jar.add(c)
        c.connect(lambda: self.delete_cancellable(c))
        return c

    def new_connect_cancellable(self):
        c = Cancellable.new()
        c.connect(lambda: self.delete_connection_cancellable(c))
        self.cancel_jar.add(c)
        return c

    def delete_connection_cancellable(self, c):
        self.delete_cancellable(c)
        self.deactivate_connection()

    def cancel(self) -> bool:
        needed_cancel = len(self.cancel_jar.cookies) > 0
        self.cancel_jar.cancel()
        return needed_cancel

    def delete_cancellable(self, c):
        try:
            self.cancel_jar.delete(c)
        except ValueError:
            pass

    @run_in_glib_thread
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

        def activate_connection_callback(a_client, res, user_data=None):
            callback = None
            c = None
            # Add the ability to cancel the connecting...
            if user_data is not None:
                c, callback = user_data
            try:
                result = a_client.activate_connection_finish(res)
            except Exception as e:
                _logger.error(e)
                if c:
                    self.delete_cancellable(c)
                if callback:
                    callback(False)
            else:
                _logger.debug(f"activate_connection_async result: {result}")
                signal = None

                def changed_state(
                    active: "NM.ActiveConnection", state_code: int, _reason_code: int
                ):
                    state = NM.ActiveConnectionState(state_code)
                    if (
                        ConnectionState.from_active_state(state)
                        == ConnectionState.CONNECTED
                    ):
                        if c:
                            self.delete_cancellable(c)
                        if signal:
                            active.disconnect(signal)
                        if callback:
                            callback(result is not None)

                    # This happens if the connection cancellable is called
                    if (
                        ConnectionState.from_active_state(state)
                        == ConnectionState.DISCONNECTED
                    ):
                        if c:
                            self.delete_cancellable(c)
                        if signal:
                            active.disconnect(signal)
                        if callback:
                            callback(False)

                signal = self.active_connection.connect("state-changed", changed_state)

        c = self.new_connect_cancellable()
        self.client.activate_connection_async(
            connection=con,
            callback=activate_connection_callback,
            cancellable=c,
            user_data=(c, callback),
        )

    def deactivate_connection(self, callback: Optional[Callable] = None) -> None:
        connection = self.active_connection
        if connection is None:
            _logger.warning(f"no connection to deactivate of uuid {uuid}")
            if callback:
                callback(False)
            return
        type = connection.get_connection_type()
        if type == "vpn":
            self.deactivate_connection_vpn(callback)
        elif type == "wireguard":
            self.deactivate_connection_wg(callback)
        else:
            _logger.warning(f"unexpected connection type {type}")
            if callback:
                callback(False)

    @run_in_glib_thread
    def deactivate_connection_vpn(self, callback: Optional[Callable] = None) -> None:
        con = self.active_connection
        _logger.debug(f"deactivate_connection uuid: {uuid} connection: {con}")
        if con:

            def on_deactivate_connection(a_client: "NM.Client", res, user_data=None):
                callback = None
                c = None
                if user_data is not None:
                    c, callback = user_data
                try:
                    result = a_client.deactivate_connection_finish(res)
                except Exception as e:
                    _logger.error(f"deactive_connection_async exception: {e}")
                    if callback:
                        callback(False)
                else:
                    _logger.debug(f"deactivate_connection_async result: {result}")
                finally:

                    def on_deleted(success: bool):
                        if c:
                            self.delete_cancellable(c)
                        if callback:
                            # Whether or not deletion was a success, we return true
                            callback(success)

                    self.delete_connection(on_deleted)

            c = self.new_cancellable()
            self.client.deactivate_connection_async(
                active=con,
                callback=on_deactivate_connection,
                cancellable=c,
                user_data=(c, callback),
            )
        else:
            _logger.debug("No active connection to deactivate")

    @run_in_glib_thread
    def delete_connection(self, callback: Callable) -> None:
        # We run the disconnected callback early if a delete fail happens
        if self.uuid is None:
            _logger.debug("No uuid found for deleting the connection")
            if callback:
                callback(False)
            return

        con = self.client.get_connection_by_uuid(self.uuid)
        if con is None:
            _logger.debug(f"No uuid connection found to delete with uuid {uuid}")
            callback(False)
            return

        # Delete the connection and after that do the callback
        def on_deleted(a_con: "NM.RemoteConnection", res, user_data=None):
            callback = None
            c = None
            if user_data is not None:
                c, callback = user_data
            try:
                result = a_con.delete_finish(res)
            except Exception as e:
                _logger.error(f"delete_connection_async exception: {e}")
                if callback:
                    callback(False)
            else:
                _logger.debug(f"delete_async result: {result}")
            finally:
                if c:
                    self.delete_cancellable(c)
                if callback:
                    callback(result)

        c = self.new_cancellable()
        con.delete_async(callback=on_deleted, cancellable=c, user_data=(c, callback))

    @property
    def wireguard_device(self) -> Optional["NM.DeviceWireGuard"]:
        devices = [
            device
            for device in self.client.get_all_devices()
            if device.get_type_description() == "wireguard"
            and self.uuid
            in {conn.get_uuid() for conn in device.get_available_connections()}
        ]
        if not devices:
            return None

        return devices[0]

    @run_in_glib_thread
    def deactivate_connection_wg(self, callback: Optional[Callable] = None) -> None:
        def on_disconnect(a_device: "NM.DeviceWireGuard", res, user_data=None):
            callback = None
            c = None
            if user_data is not None:
                c, callback = user_data
            try:
                result = a_device.disconnect_finish(res)
            except Exception as e:
                _logger.error(e)
                if callback:
                    callback(False)
            else:
                _logger.debug(f"disconnect_async result: {result}")
            finally:

                def on_deleted(success: bool):
                    if c:
                        self.delete_cancellable(c)
                    if callback:
                        callback(success)

                self.delete_connection(on_deleted)

        _logger.debug(f"disconnect uuid: {uuid}")
        device = self.wireguard_device
        if device is None:
            _logger.warning("Cannot disconnect, no WireGuard device")
            return
        c = self.new_cancellable()
        device.disconnect_async(
            callback=on_disconnect, cancellable=c, user_data=(c, callback)
        )

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
        if not isinstance(con, NM.VpnConnection):
            return None, None
        uuid = con.get_uuid()
        status = con.get_state()
        return uuid, status


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


def add_connection_callback(client: NM.Client, result: Task, user_data) -> None:
    object, c, callback = user_data
    try:
        new_con = client.add_connection_finish(result)
    except Exception as e:
        object.delete_cancellable(c)
        _logger.error(f"add connection error: {e}")
        if callback is not None:
            callback(False)
    else:
        object.delete_cancellable(c)
        object.uuid = new_con.get_uuid()
        _logger.debug(f"Connection added for uuid: {object.uuid}")
        if callback is not None:
            callback(new_con is not None)


def is_wireguard_supported() -> bool:
    return hasattr(NM, "WireGuardPeer")
