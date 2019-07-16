# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+


class EduvpnException(Exception):
	#type: (Exception) -> None
    """base eduVPN exception"""
    pass


class EduvpnAuthException(Exception):
	#type: (Exception) -> None
    """eduVPN authentication exception"""
    pass
