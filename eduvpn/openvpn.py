# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import re
import logging


logger = logging.getLogger(__name__)


def format_like_ovpn(profile_config, cert, key):
    """create a OVPN format config text"""
    logger.info("formatting config into ovpn format")
    return profile_config + '\n<cert>\n{}\n</cert>\n<key>\n{}\n</key>\n'.format(cert, key)


def parse_ovpn(configtext):
    """
    Parse a ovpn like config file, return it in dict

    configtext (str): content of a OpenVPN like config file
    """
    config = {}

    def configurator(text):
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

    for tag in 'ca', 'tls-auth', 'cert', 'key':
        x = re.search('<{}>(.*)</{}>'.format(tag, tag), configtext, flags=re.S)
        if x:
            full_match = x.group(0)
            config[tag] = x.group(1).replace('\r\n', '\n')
            configtext = configtext.replace(full_match, '')

    # handle duplicate keys, make them a list
    results = {}
    multiple = []
    for keyword, value in configurator(configtext):
        if keyword in results:
            if keyword in multiple:
                results[keyword].append(value)
            else:
                results[keyword] = [results[keyword], value]
                multiple.append(keyword)
        else:
            results[keyword] = value

    config.update(results)
    return config
