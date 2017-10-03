# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from eduvpn.metadata import Metadata
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


def activate_connection(meta: Metadata, builder: Gtk.Builder): ...