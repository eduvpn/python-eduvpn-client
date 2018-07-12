# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from typing import  Tuple
from eduvpn.ui import EduVpnApp

def main() -> int: ...

def parse_args() -> Tuple[str, str, str, str]: ...
def init() -> EduVpnApp: ...