# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from eduvpn.metadata import Metadata

def browser_step(builder, meta: Metadata, verifier): ...
def _phase1_background(meta: Metadata, dialog, verifier, builder): ...
