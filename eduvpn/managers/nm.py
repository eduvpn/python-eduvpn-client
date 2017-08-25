import uuid
import logging

import NetworkManager

from eduvpn.openvpn import format_like_ovpn, parse_ovpn
from eduvpn.io import write_cert


logger = logging.getLogger(__name__)


def _gen_nm_settings(config, name):
    """
    Generate a NetworkManager style config dict from a parsed ovpn config dict
    """
    settings = {'connection': {'id': name,
                               'type': 'vpn',
                               'uuid': str(uuid.uuid4())},
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
    vpn_connections = [c.GetSettings()['connection']['id'] for c in all_connections if c.GetSettings()['connection']['type'] == 'vpn']
    return vpn_connections


def store_provider(name, config, cert, key):
    logger.info("storing profile with name {} using NetworkManager".format(name))
    ovpn_text = format_like_ovpn(config, cert, key)
    config_dict = parse_ovpn(ovpn_text)
    cert_path = write_cert(cert, 'cert', name)
    key_path = write_cert(key, 'key', name)
    ca_path = write_cert(config_dict.pop('ca'), 'ca', name)
    ta_path = write_cert(config_dict.pop('tls-auth'), 'ta', name)
    nm_config = _gen_nm_settings(config_dict, name=name)
    nm_config['vpn']['data'].update({'cert': cert_path, 'key': key_path, 'ca': ca_path, 'ta': ta_path})
    _add_nm_config(nm_config)


def delete_provider(name):
    logger.info("deleting profile with name {} using NetworkManager".format(name))
    all_connections = NetworkManager.Settings.ListConnections()
    [c.Delete() for c in all_connections if c.GetSettings()['connection']['id'] == name]


def connect_provider(name):
    logger.info("connecting profile with name {} using NetworkManager".format(name))
    cs = [c for c in NetworkManager.Settings.ListConnections() if c.GetSettings()['connection']['id'] == name]
    if cs:
        NetworkManager.NetworkManager.ActivateConnection(cs[0], "/", "/")


def status_provider(name):
    logger.info("deleting profile with name {} using NetworkManager".format(name))
    cs = [c for c in NetworkManager.Settings.ListConnections() if c.GetSettings()['connection']['id'] == name]
    if cs:
        NetworkManager.NetworkManager.DeactivateConnection(cs[0])
