# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import Gtk
from typing import Optional

def vpn_change(builder: Gtk.Builder, lets_connect, state: Optional[int]=0, reason: Optional[int]=0) -> None: ...
