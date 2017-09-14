# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import os
import sys


if sys.platform.startswith('darwin'):
    from .osx import *
else:
    from .dbus import *