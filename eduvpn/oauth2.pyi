# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from typing import Any
from eduvpn.metadata import Metadata

landing_page = ...  # type: str
client_id = ...  # type: str
scope = ...  # type: Any

def get_open_port(): ...
def one_request(port: int): ...
def create_oauth_session(port :int, auto_refresh_url: str): ...
def get_oauth_token_code(port: int, timeout: int = None): ...
def oauth_from_token(meta: Metadata): ...
