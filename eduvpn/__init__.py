# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import pkg_resources

try:
    __version__ = pkg_resources.require("eduvpn")[0].version
except pkg_resources.DistributionNotFound:
    __version__ = "0.0dev"
