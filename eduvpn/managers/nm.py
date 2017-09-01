import os
import logging

import NetworkManager

from eduvpn.openvpn import format_like_ovpn, parse_ovpn
from eduvpn.io import write_cert, store_metadata, mkdir_p
from eduvpn.config import config_path, metadata
from eduvpn.util import make_unique_id


logger = logging.getLogger(__name__)


def _gen_nm_settings(config, uuid, display_name):
    """
    Generate a NetworkManager style config dict from a parsed ovpn config dict
    """
    settings = {'connection': {'id': display_name,
                               'type': 'vpn',
                               'uuid': uuid},
                'ipv4': {
                    'method': 'auto',
                },
                'ipv6': {
                    'method': 'auto',
                },
                'vpn': {'data': {'auth': config.get('auth', 'SHA256'),
                                 'cipher': config.get('cipher', 'AES-256-CBC'),
                                 'comp-lzo': config.get('auth', 'adaptive'),
                                 'connection-type': config.get('connection-type', 'tls'),
                                 'dev': 'tun',
                                 'remote': ",".join(":".join(r) for r in config['remote']),
                                 'remote-cert-tls': 'server',
                                 'ta-dir': config.get('key-direction', '1'),
                                 'tls-cipher': config.get('tls-cipher', 'TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384')},
                        'service-type': 'org.freedesktop.NetworkManager.openvpn'}
                }
    return settings


def _add_nm_config(settings):
    """
    Add a configuration to the networkmanager
    """
    name = settings['connection']['id']
    logger.info("generating or updating OpenVPN configuration with name {}".format(name))
    connection = NetworkManager.Settings.AddConnection(settings)
    return connection


def list_providers():
    """
    List all OpenVPN connections.
    """
    all_connections = NetworkManager.Settings.ListConnections()
    vpn_connections = [c.GetSettings()['connection'] for c in all_connections if c.GetSettings()['connection']['type'] == 'vpn']
    for conn in vpn_connections:
        yield {'uuid': conn['uuid'], 'display_name': conn['id']}


def store_provider(api_base_uri, profile_id, display_name, token, connection_type, authorization_type,
                   profile_display_name, two_factor, cert, key, config):
    logger.info("storing profile with name {} using NetworkManager".format(display_name))
    uuid = make_unique_id()
    ovpn_text = format_like_ovpn(config, cert, key)
    config_dict = parse_ovpn(ovpn_text)
    cert_path = write_cert(cert, 'cert', uuid)
    key_path = write_cert(key, 'key', uuid)
    ca_path = write_cert(config_dict.pop('ca'), 'ca', uuid)
    ta_path = write_cert(config_dict.pop('tls-auth'), 'ta', uuid)
    nm_config = _gen_nm_settings(config_dict, uuid=uuid, display_name=display_name)
    mkdir_p(config_path)
    l = locals()
    store = {i: l[i] for i in metadata}
    store_metadata(os.path.join(config_path, uuid + '.json'), **store)
    nm_config['vpn']['data'].update({'cert': cert_path, 'key': key_path, 'ca': ca_path, 'ta': ta_path})
    _add_nm_config(nm_config)


def delete_provider(uuid):
    logger.info("deleting profile with uuid {} using NetworkManager".format(uuid))
    all_connections = NetworkManager.Settings.ListConnections()
    conn = [c for c in all_connections if c.GetSettings()['connection']['uuid'] == uuid]
    if len(conn) != 1:
        raise Exception("{} connections matching uid {}".format(len(conn), uuid))
    conn[0].Delete()


def connect_provider(uuid):
    logger.info("connecting profile with name {} using NetworkManager".format(uuid))
    cs = [c for c in NetworkManager.Settings.ListConnections() if c.GetSettings()['connection']['uuid'] == uuid]
    if cs:
        NetworkManager.NetworkManager.ActivateConnection(cs[0], "/", "/")


def disconnect_provider(uuid):
    logger.info("deleting profile with name {} using NetworkManager".format(uuid))
    cs = [c for c in NetworkManager.Settings.ListConnections() if c.GetSettings()['connection']['id'] == uuid]
    if cs:
        NetworkManager.NetworkManager.DeactivateConnection(cs[0])


def status_provider(uuid):
    raise NotImplementedError
