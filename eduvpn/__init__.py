# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import pkg_resources

__version__ = pkg_resources.require("eduvpn")[0].version # type: str
