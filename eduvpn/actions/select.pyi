# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from typing import Optional
from eduvpn.metadata import Metadata

def select_profile(builder, verifier, lets_connect: bool) -> Optional[Metadata]: ...
