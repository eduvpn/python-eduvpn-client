# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from eduvpn.metadata import Metadata

def two_auth_step(builder, oauth, meta: Metadata, config_dict: dict) -> None: ...
def _background(meta: Metadata, oauth, builder, config_dict: dict) -> None: ...
def _choice_window(options, meta: Metadata, oauth, builder, config_dict: dict) -> None: ...


