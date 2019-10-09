# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import json
import os
import logging

from eduvpn.config import others_path, providers_path
from eduvpn.io import mkdir_p
from eduvpn.exceptions import EduvpnException
from typing import Any, List, Optional, Tuple


logger = logging.getLogger(__name__)
distibuted_tokens_path = os.path.join(others_path, 'distributed.json')


def get_distributed_tokens():  # type: () -> Any
    json_path = distibuted_tokens_path
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except (IOError, ValueError) as e:
        logger.warning("can't open '{}': {}".format(json_path, str(e)))
        return {}


class Metadata:
    def __init__(self):
        self.api_base_uri = None  # type: str
        self.profile_id = None  # type: str
        self.token = None  # type: dict
        self.token_endpoint = None  # type: str
        self.authorization_type = None  # type: str
        self.two_factor = None  # type: bool
        self.two_factor_method = []  # type: List[str]
        self.cert = None  # type: str
        self.key = None  # type: str
        self.config = None  # type: str
        self.uuid = None  # type: str
        self.icon_data = None  # type: str
        self.instance_base_uri = None  # type: str
        self.username = None  # type: str
        self.discovery_uri = None  # type: str
        self.user_id = None  # type: str
        self.display_name = "Unknown"  # type: str
        self.connection_type = "Unknown"  # type: str
        self.profile_display_name = "Unknown"  # type: str

    @staticmethod
    def from_uuid(uuid, display_name=None):  # type: (str, str) -> Metadata
        metadata_path = os.path.join(providers_path, uuid + '.json')
        metadata = Metadata()
        try:
            with open(metadata_path, 'r') as f:
                x = json.load(f)
                for key, value in x.items():
                    if value:
                        setattr(metadata, key, value)
                return metadata
        except (ValueError, IOError) as e:
            logger.error("can't open metdata"
                         "file for {}: {}".format(uuid, str(e)))
            metadata.uuid = uuid
            if display_name:
                metadata.display_name = display_name
            else:
                metadata.display_name = uuid
            return metadata

    def write(self):  # type: () -> None
        if not self.uuid:
            # raise EduvpnException('uuid field not set')
            logger.warning("uuid field not yet set")
            return
        fields = [f for f in dir(self) if not f.startswith('_') and not callable(getattr(self, f))]
        d = {field: getattr(self, field) for field in fields}
        p = os.path.join(providers_path, self.uuid + '.json')
        logger.info("storing metadata in {}".format(p))
        serialized = json.dumps(d)
        mkdir_p(providers_path)
        with open(p, 'w') as f:
            f.write(serialized)

        if self.authorization_type == 'distributed':
            self.write_distributed_token()

    def write_distributed_token(self):  # type: () -> None
        tokens = get_distributed_tokens()
        if self.discovery_uri in tokens:
            tokens[self.discovery_uri]['token'] = self.token
        else:
            error = "updating distributed token for {} but it isn't present in {}, recreating"
            logger.error(error.format(self.discovery_uri, distibuted_tokens_path))
            tokens[self.discovery_uri] = {'token': self.token, 'token_endpoint': self.token_endpoint}
        serialized = json.dumps(tokens)
        mkdir_p(others_path)
        with open(distibuted_tokens_path, 'w') as f:
            logger.info("updating distributed token for {} to {}".format(self.discovery_uri,
                                                                         distibuted_tokens_path))
            f.write(serialized)

    def update_token(self, token):  # type: (dict) -> None
        self.token = token
        self.write()

    def refresh_token(self):  # type: () -> None
        if self.authorization_type == 'distributed':
            tokens = get_distributed_tokens()
            if self.discovery_uri in tokens:
                logger.info("using distributed token from {}".format(self.discovery_uri))
                self.token = tokens[self.discovery_uri]['token']
                self.token_endpoint = tokens[self.discovery_uri]['token_endpoint']


def get_all_metadata():  # type: () -> List[Metadata]
    if not os.access(providers_path, os.X_OK):
        return []
    metadatas = [Metadata.from_uuid(i[:-5]) for i in os.listdir(providers_path) if i.endswith('.json')]
    return metadatas


def reuse_token_from_base_uri(instance_base_uri):  # type: (str) -> Optional[dict]
    for metadata in get_all_metadata():
        if metadata.connection_type in (u'Institute Access', u'Custom Instance') and \
                metadata.instance_base_uri == instance_base_uri:
            return metadata.token
    return None
