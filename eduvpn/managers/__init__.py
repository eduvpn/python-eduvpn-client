# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import os
import sys

if os.name == 'posix' and not sys.platform.startswith('darwin'):
    from .nm import list_providers, store_provider, delete_provider, connect_provider, status_provider,\
        disconnect_provider, is_provider_connected, update_config_provider, update_keys_provider
else:
    from .other import list_providers, store_provider, delete_provider, connect_provider, status_provider,\
        disconnect_provider, is_provider_connected, update_config_provider, update_keys_provider
