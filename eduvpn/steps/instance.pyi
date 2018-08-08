# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from eduvpn.metadata import Metadata

def _fetch_background(meta:Metadata, verifier, builder, lets_connect: bool) -> None: ...
def fetch_instance_step(meta: Metadata, builder, verifier, lets_connect: bool) -> None: ...
def select_instance_step(meta: Metadata, instances, builder, verifier, lets_connect: bool) -> None: ...
