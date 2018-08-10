# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import base64
import logging
from eduvpn.manager import list_providers
from eduvpn.util import bytes2pixbuf, get_pixbuf
from eduvpn.brand import lets_connect_main_logo, eduvpn_main_logo
from eduvpn.brand import get_brand


logger = logging.getLogger(__name__)


# ui thread
def refresh_start(builder, lets_connect):
    logger.info("composing list of current eduVPN configurations")
    config_list = builder.get_object('configs-model')
    introduction = builder.get_object('introduction')
    main_image = builder.get_object('main_image')
    window = builder.get_object('eduvpn-window')

    logo, name = get_brand(lets_connect)
    main_image.set_from_file(logo)
    window.set_title("{} Configuration Manager".format(name))

    config_list.clear()
    providers = list(list_providers())
    providers.sort(key=lambda x: x.display_name)

    if len(providers) > 0:
        logger.info("hiding introduction")
        introduction.hide()
        for meta in providers:
            connection_type = "<b>{}</b>\n{}\n<small><i>{}</i></small>".format(meta.display_name, meta.connection_type, meta.profile_display_name)
            if meta.icon_data:
                icon = bytes2pixbuf(base64.b64decode(meta.icon_data.encode()))
            else:
                icon, _ = get_pixbuf(logo)
            config_list.append((meta.uuid, meta.display_name, icon, connection_type))
    else:
        logger.info("showing introduction")
        introduction.show()
