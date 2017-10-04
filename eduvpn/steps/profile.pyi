# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from eduvpn.metadata import Metadata

def fetch_profile_step(builder, meta: Metadata, oauth): ...
def select_profile_step(builder, profiles, meta: Metadata, oauth): ...
def _background(oauth, meta: Metadata, builder, dialog): ...
