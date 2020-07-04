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

from eduvpn.storage import set_uuid, get_uuid, write_config
from eduvpn.utils import get_logger

logger = get_logger(__file__)


def get_client() -> NM.Client:
    """
    Create a new client object. We put this here so other modules don't need to import NM
    """
    return NM.Client.new(None)


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


def add_callback(client, result):
    new_con = client.add_connection_finish(result)
    set_uuid(uuid=new_con.get_uuid())


def add_connection(client: 'NM.Client', connection: 'NM.Connection'):
    logger.info("Adding new connection")
    client.add_connection_async(connection=connection, save_to_disk=True, callback=add_callback)


def update_connection(old_con: 'NM.Connection', new_con: 'NM.Connection'):
    """
    Update an existing Network Manager connection with the settings from another Network Manager connection
    """
    logger.info("Updating existing connection with new configuration")

    old_con.replace_settings_from_connection(new_con)
    old_con.commit_changes_async(save_to_disk=True, cancellable=None, user_data=None)


def save_connection(client: 'NM.Client', config, private_key, certificate):
    logger.info("writing configuration to Network Manager")
    new_con = import_ovpn(config, private_key, certificate)
    uuid = get_uuid()
    if uuid:
        old_con = client.get_connection_by_uuid(uuid)
        if old_con:
            update_connection(old_con, new_con)
        else:
            add_connection(client=client, connection=new_con)
    else:
        add_connection(client=client, connection=new_con)


def get_cert_key(client: 'NM.Client', uuid: str) -> Tuple[str, str]:
    connection = client.get_connection_by_uuid(uuid)
    cert_path = connection.get_setting_vpn().get_data_item('cert')
    key_path = connection.get_setting_vpn().get_data_item('key')
    cert = open(cert_path).read()
    key = open(key_path).read()
    return cert, key


def activate_connection(client: 'NM.Client', uuid: str):
    con = client.get_connection_by_uuid(uuid)
    client.activate_connection_async(connection=con)


def deactivate_connection(client: 'NM.Client', uuid: str):
    con = client.get_primary_connection()

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
