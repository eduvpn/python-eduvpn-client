# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from typing import Any

def get_distributed_tokens(): ...


class Metadata:
    api_base_uri = ...  # type: str
    profile_id = ...  # type: str
    token = ...  # type: dict
    token_endpoint = ...  # type: str
    authorization_type = ...  # type: str
    authorization_endpoint = ... # type: str
    profile_display_name = ...  # type: str
    two_factor = ...  # type: bool
    cert = ...  # type: str
    key = ...  # type: str
    config = ...  # type: str
    uuid = ...  # type: str
    icon_data = ...  # type: str
    instance_base_uri = ...  # type: str
    username = ...  # type: str
    discovery_uri = ...  # type: str
    display_name = ...  # type: str
    connection_type = ...  # type: str

    def __init__(self): ...
    @staticmethod
    def from_uuid(uuid, display_name=None) -> Metadata: ...
    def write(self): ...
    def _get_distributed_token(self): ...
    def set_token(self, oauth, code, code_verifier): ...
    def update_token(self, token: dict): ...
    def refresh_token(self): ...
