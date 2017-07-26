import uuid
import logging

import NetworkManager

logger = logging.basicConfig(__name__)


def gen_nm_settings(config, name):
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
                                 'remote': ":".join(config['remote']),
                                 'remote-cert-tls': 'server',
                                 'ta-dir': config.get('key-direction', '1'),
                                 'tls-cipher': config.get('tls-cipher', 'TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384')},
                        'service-type': 'org.freedesktop.NetworkManager.openvpn'}
                }
    return settings


def add_nm_config(settings):
    name = settings['connection']['id']
    logger.info("generating or updating OpenVPN configuration with name {}".format(name))
    connection = NetworkManager.Settings.AddConnection(settings)
    return connection