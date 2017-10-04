# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import json
from os import path
import logging

from eduvpn.config import others_path, providers_path
from eduvpn.io import mkdir_p
from eduvpn.exceptions import EduvpnException


logger = logging.getLogger(__name__)

distibuted_tokens_path = path.join(others_path, 'distributed.json')


def get_distributed_tokens():
    json_path = distibuted_tokens_path
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except (IOError, ValueError) as e:
        logger.warning("can't open '{}': {}".format(json_path, str(e)))
        return {}


class Metadata:
    def __init__(self):
        self.api_base_uri = None
        self.profile_id = None
        self.token = None
        self.token_endpoint = None
        self.authorization_type = None
        self.profile_display_name = None
        self.two_factor = None
        self.cert = None
        self.key = None
        self.config = None
        self.uuid = None
        self.icon_data = None
        self.instance_base_uri = None
        self.username = None
        self.discovery_uri = None
        self.display_name = "Unknown"
        self.connection_type = "Unknown"

    @staticmethod
    def from_uuid(uuid, display_name=None):
        metadata_path = path.join(providers_path, uuid + '.json')
        metadata = Metadata()
        try:
            with open(metadata_path, 'r') as f:
                x = json.load(f)
                for key, value in x.items():
                    if value:
                        setattr(metadata, key, value)
                return metadata
        except (ValueError, IOError) as e:
            logger.error("can't open metdata file for {}: {}".format(uuid, str(e)))
            metadata.uuid = uuid
            if display_name:
                metadata.display_name = display_name
            else:
                metadata.display_name = uuid
            return metadata

    def write(self):
        if not self.uuid:
            raise EduvpnException('uuid field not set')
        fields = [f for f in dir(self) if not f.startswith('_') and not callable(getattr(self, f))]
        d = {field: getattr(self, field) for field in fields}
        p = path.join(providers_path, self.uuid + '.json')
        logger.info("storing metadata in {}".format(p))
        serialized = json.dumps(d)
        mkdir_p(providers_path)
        with open(p, 'w') as f:
            f.write(serialized)

    def update_token(self, token):
        self.token = token
        if self.authorization_type == 'distributed':
            tokens = get_distributed_tokens()
            if self.discovery_uri in tokens:
                tokens[self.discovery_uri]['token'] = token
            else:
                error = "updating distributed token for {} but it isn't present in {}, recreating"
                logger.error(error.format(self.discovery_uri, distibuted_tokens_path))
                tokens[self.discovery_uri] = {'token': token, 'token_endpoint': self.token_endpoint}
            serialized = json.dumps(tokens)
            mkdir_p(others_path)
            with open(distibuted_tokens_path, 'w') as f:
                logger.info("updating distributed token for {} to {}".format(self.discovery_uri,
                                                                             distibuted_tokens_path))
                f.write(serialized)
        else:
            self.write()

    def refresh_token(self):
        if self.authorization_type == 'distributed':
            tokens = get_distributed_tokens()
            if self.discovery_uri in tokens:
                logger.info("using distributed token from {}".format(self.discovery_uri))
                self.token = tokens[self.discovery_uri]['token']
                self.token_endpoint = tokens[self.discovery_uri]['token_endpoint']
