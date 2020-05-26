from sys import modules
from logging import getLogger
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Optional, Tuple

logger = getLogger(__name__)

try:
    import gi
    gi.require_version('NM', '1.0')
    from gi.repository import NM, GLib  # type: ignore
except (ImportError, ValueError) as e:
    logger.warning("Network Manager not available")

from eduvpn.storage import set_uuid, get_uuid, write_config
from eduvpn.utils import get_logger

logger = get_logger(__file__)


def nm_available() -> bool:
    """
    check if Network Manager is available
    """
    return bool('gi.repository.NM' in modules)


def nm_ovpn_import(target: Path) -> Optional['NM.Connection']:
    """
    Use the Network Manager VPN config importer to import an OpenVPN configuration file.
    """
    conn = None
    for vpn_info in NM.VpnPluginInfo.list_load():
        try:
            conn = vpn_info.load_editor_plugin().import_(str(target))
            conn.normalize()
        except Exception as e:
            logger.debug(f"{vpn_info} can't import {target}: {e}")
            continue

    if not conn:
        logger.error(f"Network Manager is not able to import '{target}'")

    return conn


def import_ovpn(config: str, private_key: str, certificate: str) -> Optional['NM.Connection']:
    """
    Import the OVPN string into Network Manager.
    """
    target_parent = Path(mkdtemp())
    target = target_parent / "eduVPN.ovpn"
    write_config(config, private_key, certificate, target)
    connection = nm_ovpn_import(target)
    rmtree(target_parent)
    return connection


def add_connection(client: 'NM.Client', connection: 'NM.Connection', main_loop: 'GLib.MainLoop'):
    logger.info("Adding new connection")

    def add_callback(client, result, data):
        try:
            new_con = client.add_connection_finish(result)
            set_uuid(uuid=new_con.get_uuid())
        except Exception as e:
            logger.error("ERROR: failed to add connection: %s\n" % e)
        main_loop.quit()

    client.add_connection_async(connection=connection, save_to_disk=True, cancellable=None,
                                callback=add_callback, user_data=None)


def update_connection(old_con: 'NM.Connection', new_con: 'NM.Connection', main_loop: 'GLib.MainLoop'):
    """
    Update an existing Network Manager connection with the settings from another Network Manager connection
    """
    logger.info("Updating existing connection with new configuration")

    def update_callback(client, result, data):
        main_loop.quit()

    old_con.replace_settings_from_connection(new_con)
    old_con.commit_changes_async(save_to_disk=True, cancellable=None, callback=update_callback, user_data=None)


def save_connection(config, private_key, certificate):
    print("writing configuration to Network Manager")
    new_con = import_ovpn(config, private_key, certificate)
    uuid = get_uuid()
    main_loop = GLib.MainLoop()
    client = NM.Client.new()
    if uuid:
        old_con = client.get_connection_by_uuid(uuid)
        if old_con:
            update_connection(old_con, new_con, main_loop)
        else:
            add_connection(client=client, connection=new_con, main_loop=main_loop)
    else:
        add_connection(client=client, connection=new_con, main_loop=main_loop)
    main_loop.run()


def get_cert_key(uuid: str) -> Tuple[str, str]:
    client = NM.Client.new()
    connection = client.get_connection_by_uuid(uuid)
    cert_path = connection.get_setting_vpn().get_data_item('cert')
    key_path = connection.get_setting_vpn().get_data_item('key')
    cert = open(cert_path).read()
    key = open(key_path).read()
    return cert, key


def activate_connection(uuid: str):
    client = NM.Client.new()
    con = client.get_connection_by_uuid(uuid)
    main_loop = GLib.MainLoop()

    def callback(*args, **kwargs):
        main_loop.quit()

    client.activate_connection_async(connection=con, callback=callback)


def deactivate_connection(uuid: str):
    client = NM.Client.new()
    con = client.get_primary_connection()
    active_uuid = con.get_uuid()

    if uuid == active_uuid:
        main_loop = GLib.MainLoop()

        def callback(*args, **kwargs):
            main_loop.quit()

        client.deactivate_connection_async(active=con, callback=callback)
