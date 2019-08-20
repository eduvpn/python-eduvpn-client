# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+


class EduvpnException(Exception):
    """base eduVPN exception"""
    pass


class EduvpnAuthException(Exception):
    """eduVPN authentication exception"""
    pass
