# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from typing import Any, Optional


def format_like_ovpn(config, cert, key): ...
def parse_ovpn(configtext): ...
def ovpn_to_nm(config, meta, display_name, username: Optional[Any] = ...): ...
