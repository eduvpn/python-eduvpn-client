# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from typing import Any, Optional

image_path = ...  # type: Any
image = ...  # type: Any
notification = ...  # type: Any

def notify(msg, small_msg: Optional[Any] = ...): ...
