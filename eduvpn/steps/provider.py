# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import base64
import logging
from eduvpn.manager import list_providers
from eduvpn.util import bytes2pixbuf, get_pixbuf


logger = logging.getLogger(__name__)


def update_providers(builder):
    logger.info("composing list of current eduVPN configurations")
    config_list = builder.get_object('configs-model')
    introduction = builder.get_object('introduction')
    config_list.clear()
    providers = list(list_providers())

    if len(providers) > 0:
        logger.info("hiding introduction")
        introduction.hide()
        for meta in providers:
            connection_type = "{}\n{}".format(meta.display_name, meta.connection_type)
            if meta.icon_data:
                icon = bytes2pixbuf(base64.b64decode(meta.icon_data.encode()))
            else:
                icon, _ = get_pixbuf()
            config_list.append((meta.uuid, meta.display_name, icon, connection_type))
    else:
        logger.info("showing introduction")
        introduction.show()
