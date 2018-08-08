# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from typing import Any, Iterable

builder_files = ...  # type: Iterable[str]

class EduVpnApp:
    secure_internet_uri = ... # type str
    institute_access_uri = ... # type str

    lets_connect = ... # type bool

    selected_meta = ...  # type: Any
    prefix = ...  # type: Any
    builder = ...  # type: Any
    window = ...  # type: Any
    verifier = ...  # type: Any

    def __init__(self, secure_internet_uri: str, institute_access_uri: str,
                 verify_key: str, lets_connect: bool) -> None: ...
    def run(self): ...
    def add(self, _): ...
    def delete(self, _): ...
    def select(self, _): ...
    def vpn_change(self, *args, **kwargs): ...
    def switched(self, selection, _): ...
