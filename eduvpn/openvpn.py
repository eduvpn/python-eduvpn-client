# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
from eduvpn.exceptions import EduvpnException

import re

from eduvpn.io import write_cert

from typing import Any, Optional
from eduvpn.metadata import Metadata

logger = logging.getLogger(__name__)


def format_like_ovpn(config, cert, key):  # type: (str, str, str) -> str
    """create a OVPN format config text."""
    logger.info("formatting config into ovpn format")
    return config + '\n<cert>\n{}\n</cert>\n<key>\n{}\n</key>\n'.format(cert, key)


def parse_ovpn(configtext):  # type: (str) -> dict
    """
    Parse a ovpn like config file, return it in dict

    configtext (str): content of a OpenVPN like config file
    """
    config = {}

    def configurator(text):
        #type: (str) -> Any
        for line in text.split('\n'):
            split = line.split('#')[0].strip().split()
            if len(split) == 0:
                continue
            if len(split) == 1:
                yield (split[0], None)
            elif len(split) == 2:
                yield split
            else:
                yield (split[0], split[1:])

    for tag in 'ca', 'tls-auth', 'cert', 'key', 'tls-crypt':
        x = re.search('<{}>(.*)</{}>'.format(tag, tag), configtext, flags=re.S)
        if x:
            full_match = x.group(0)
            config[tag] = x.group(1).replace('\r\n', '\n')
            configtext = configtext.replace(full_match, '')

    # handle duplicate keys, make them a list
    results = {}  # type: dict
    multiple = ['remote']  # remote needs to always be a list
    for keyword, value in configurator(configtext):
        if keyword in results:
            if keyword in multiple:
                results[keyword].append(value)
            else:
                results[keyword] = [results[keyword], value]
                multiple.append(keyword)
        else:
            if keyword in multiple:
                results[keyword] = [value]
            else:
                results[keyword] = value

    config.update(results)
    return config


def ovpn_to_nm(config, meta, display_name, username=None):  # type: (dict, Metadata, str, Optional[str]) -> object
    """Generate a NetworkManager style config dict from a parsed ovpn config dict."""
    logger.info("generating config for {} ({})".format(display_name, meta.uuid))
    settings = {'connection': {'id': display_name,
                               'type': 'vpn',
                               'uuid': meta.uuid},
                'ipv4': {'method': 'auto'},
                'ipv6': {'method': 'auto'},
                'vpn': {'data': {'auth': config.get('auth', 'SHA256'),
                                 'cipher': config.get('cipher', 'AES-256-CBC'),
                                 'connection-type': config.get('connection-type', 'tls'),
                                 'dev': 'tun',
                                 'remote': ",".join(":".join(r) for r in config['remote']),
                                 'remote-cert-tls': 'server',
                                 # 'tls-cipher' is not supported on older nm (like ubuntu 16.04)
                                 # 'tls-cipher': config.get('tls-cipher', 'TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384')
                                 },
                        'service-type': 'org.freedesktop.NetworkManager.openvpn'}
                }

    # issue #138, not supported by older network-manager-openvpn
    # if 'server-poll-timeout' in config:
    #     settings['vpn']['data']['connect-timeout'] = config['server-poll-timeout']

    if 'comp-lzo' in config:
        settings['vpn']['data']['comp-lzo'] = config['comp-lzo'] or 'adaptive'

    # 2 factor auth enabled
    if 'auth-user-pass' in config:
        if not username:
            raise EduvpnException("You need to enroll for 2FA in the user portal "
                                  "first before being able to connect to this profile.")
        logger.info("looks like 2 factor authentication is enabled, enabling this in NM config")
        settings['vpn']['data']['cert-pass-flags'] = '0'
        settings['vpn']['data']['connection-type'] = 'password-tls'
        settings['vpn']['data']['password-flags'] = '2'
        settings['vpn']['data']['username'] = username

    if 'ca' in config:
        ca_path = write_cert(config.get('ca'), 'ca', meta.uuid)
        settings['vpn']['data']['ca'] = ca_path

    if 'tls-auth' in config:
        settings['vpn']['data']['ta'] = write_cert(config.get('tls-auth'), 'ta', meta.uuid)
        settings['vpn']['data']['ta-dir'] = config.get('key-direction', '1')
    elif 'tls-crypt' in config:
        settings['vpn']['data']['tls-crypt'] = write_cert(config.get('tls-crypt'), 'tc', meta.uuid)
    else:
        logging.info("'tls-crypt' and 'tls-auth' not found in configuration returned by server")

    return settings
