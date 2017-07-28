import uuid
import logging
import os
import sys

if os.name == 'posix' and not sys.platform.startswith('darwin'):
    import NetworkManager

logger = logging.getLogger(__name__)

# only used if network manager is not available
config_store = os.path.expanduser('~/.config/eduvpn')



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
    if os.name != 'posix' or sys.platform.startswith('darwin'):
        logger.error('Adding an OpenVPN config on a non Linux platform is not supported for now.')
        return
    connection = NetworkManager.Settings.AddConnection(settings)
    return connection


def list_vpn_no_networkmanager():
    if os.path.isdir(config_store):
        return [x[:-5] for x in os.listdir(config_store) if x.endswith('.ovpn')]
    else:
        return []


def list_vpn():
    if os.name != 'posix' or sys.platform.startswith('darwin'):
        logger.warning('Listing VPN connections on non Linux platform is not supported for now.')
        return list_vpn_no_networkmanager()

    all_connections = NetworkManager.Settings.ListConnections()
    vpn_connections = [c.GetSettings()['connection']['id'] for c in all_connections if c.GetSettings()['connection']['type'] == 'vpn']
    return vpn_connections
