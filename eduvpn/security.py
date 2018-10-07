"""
Due to an issue with systemd-resolvd on ubuntu 18.04 a connection is leaking DNS information. This module
implements a workaround that sets the link domain to ~.

more information in this issue:

https://github.com/eduvpn/python-eduvpn-client/issues/160
"""

import eduvpn.other_nm as NetworkManager
import dbus
import subprocess

type_tun = 16  # NM_DEVICE_TYPE_TUN
state_acticated = 100  # NM_DEVICE_STATE_ACTIVATED


def get_link(interface):
    # type: (str) -> int
    """
    Returns link ID associated with the interface name
    """
    return int(subprocess.check_output(['/sbin/ip', 'link', 'show', 'dev', interface]).decode('ascii').split()[0][:-1])


def get_active_vpn_device():
    # type: () -> str
    devices = NetworkManager.NetworkManager.GetDevices()
    interfaces = [x.Interface for x in devices if x.State == state_acticated and x.DeviceType == type_tun]
    assert(len(interfaces) == 1)
    interface = interfaces[0]
    return interface


def set_link_domain(link):
    # type: (int) -> None
    bus = dbus.SystemBus()
    node = "/org/freedesktop/resolve1"
    bus_name = 'org.freedesktop.resolve1'
    interface = "org.freedesktop.resolve1.Manager"
    resolve_proxy = bus.get_object(bus_name=bus_name, object_path=node)
    resolve_iface = dbus.Interface(object=resolve_proxy, dbus_interface=interface)
    resolve_iface.SetLinkDomains(link, ((".", True),))