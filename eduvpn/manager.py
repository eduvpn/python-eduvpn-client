# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import os
import logging
import json

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
    logger.info("There are {} VPN connections in networkmanager".format(len(vpn_connections)))
    for conn in vpn_connections:
        try:
            metadata = json.load(open(os.path.join(config_path, conn['uuid'] + '.json'), 'r'))
        except Exception as e:
            logger.error("can't load metadata file: " + str(e))
            yield {'uuid': conn['uuid'], 'display_name': conn['id'], 'icon_data': None, 'connection_type': 'unknown'}
        else:
            yield metadata


def store_provider(api_base_uri, profile_id, display_name, token, connection_type, authorization_type,
                   profile_display_name, two_factor, cert, key, config, icon_data):
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
    conns = [c for c in all_connections if c.GetSettings()['connection']['uuid'] == uuid]
    if len(conns) != 1:
        raise Exception("{} connections matching uid {}".format(len(conns), uuid))

    conn = conns[0]
    logger.info("removing certificates for {}".format(uuid))
    for f in ['ca', 'cert', 'key', 'ta']:
        path = conn.GetSettings()['vpn']['data'][f]
        logger.info("removing certificate {}".format(path))
        try:
            os.remove(path)
        except Exception as e:
            logger.error("can't remove certificate {}".format(path))

    try:
        conn.Delete()
    except Exception as e:
        logger.error("can't remove networkmanager connection: {}".format(str(e)))
        raise

    metadata = os.path.join(config_path, uuid + '.json')
    logger.info("deleting metadata file {}".format(metadata))
    try:
        os.remove(metadata)
    except Exception as e:
        logger.error("can't remove ovpn file: {}".format(str(e)))


def connect_provider(uuid):
    logger.info("connecting profile with uuid {} using NetworkManager".format(uuid))
    connection = NetworkManager.Settings.GetConnectionByUuid(uuid)
    return NetworkManager.NetworkManager.ActivateConnection(connection, "/", "/")


def list_active():
    return NetworkManager.NetworkManager.ActiveConnections


def disconnect_provider(uuid):
    logger.info("Disconnecting profile with uuid {} using NetworkManager".format(uuid))
    conns = [i for i in NetworkManager.NetworkManager.ActiveConnections if i.Uuid == uuid]
    if len(conns) == 0:
        raise Exception("no active connection found with uuid {}".format(uuid))
    for conn in conns:
        NetworkManager.NetworkManager.DeactivateConnection(conn)


def is_provider_connected(uuid):
    """
    returns:
        tuple or None: returns ipv4 and ipv6 address if connected
    """
    for active in list_active():
        if uuid == active.Uuid:
            if active.State == 2:
                return active.Ip4Config.AddressData[0]['address'], active.Ip6Config.AddressData[0]['address']
            else:
                return "", ""


def status_provider(uuid):
    connection = NetworkManager.Settings.GetConnectionByUuid(uuid)
    raise NotImplementedError


def update_config_provider(uuid, display_name, config):
    config_dict = parse_ovpn(config)
    ca_path = write_cert(config_dict.pop('ca'), 'ca', uuid)
    ta_path = write_cert(config_dict.pop('tls-auth'), 'ta', uuid)
    nm_config = _gen_nm_settings(config_dict, uuid=uuid, display_name=display_name)
    old_conn = NetworkManager.Settings.GetConnectionByUuid(uuid)
    old_settings = old_conn.GetSettings()
    nm_config['vpn']['data'].update({'cert': old_settings['vpn']['data']['cert'],
                                     'key': old_settings['vpn']['data']['key'],
                                     'ca': ca_path, 'ta': ta_path})
    old_conn.Delete()
    _add_nm_config(nm_config)


def update_keys_provider(uuid, cert, key):
    logger.info("updating key pare for uuid {}".format(uuid))
    cert_path = write_cert(cert, 'cert', uuid)
    key_path = write_cert(key, 'key', uuid)


def update_token(uuid, token):
    logger.info("writing new token information for {}".format(uuid))
    path = os.path.join(config_path, uuid + '.json')
    metadata = json.load(open(path, 'r'))
    metadata['token'] = token
    logger.error(metadata['token']['expires_at'])
    logger.error(token['expires_at'])
    with open(path, 'w') as f:
        json.dump(metadata, f)
