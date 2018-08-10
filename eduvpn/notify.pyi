# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from typing import Any, Optional
from gi.repository import Notify

def init_notify(lets_connect: bool) -> Notify: ...
def notify(notification: Notify, msg, small_msg: Optional[Any] = ...) -> None: ...
