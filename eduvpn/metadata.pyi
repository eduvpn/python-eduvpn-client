# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+
from typing import Any

def get_distributed_tokens():
    ...


class Metadata:
    api_base_uri = ...  # type: Any
    profile_id = ...  # type: Any
    token = ...  # type: Any
    token_endpoint = ...  # type: Any
    authorization_type = ...  # type: Any
    profile_display_name = ...  # type: Any
    two_factor = ...  # type: Any
    cert = ...  # type: Any
    key = ...  # type: Any
    config = ...  # type: Any
    uuid = ...  # type: Any
    icon_data = ...  # type: Any
    instance_base_uri = ...  # type: Any
    username = ...  # type: Any
    discovery_uri = ...  # type: Any
    display_name = ...  # type: str
    connection_type = ...  # type: str
    def __init__(self):
        ...

    @staticmethod
    def from_uuid(uuid, display_name=None):
        ...

    def write(self):
        ...

    def _get_distributed_token(self):
        ...

    def set_token(self, oauth, code, code_verifier):
        ...

    def update_token(self, token: dict):
        ...
