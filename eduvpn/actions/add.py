# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import logging
from eduvpn.metadata import Metadata
from eduvpn.config import secure_internet_uri, institute_access_uri
from eduvpn.steps.instance import fetch_instance_step
from eduvpn.steps.custom_url import custom_url

logger = logging.getLogger(__name__)


def new_provider(builder, verifier):
    """The connection type selection step"""
    logger.info("add configuration clicked")
    dialog = builder.get_object('connection-type-dialog')
    dialog.show_all()
    response = dialog.run()
    dialog.hide()

    meta = Metadata()

    if response == 0:  # cancel
        logger.info("cancel button pressed")
        return

    elif response == 1:
        logger.info("secure button pressed")
        meta.connection_type = 'Secure Internet'
        meta.discovery_uri = secure_internet_uri
        fetch_instance_step(meta=meta, builder=builder, verifier=verifier)

    elif response == 2:
        logger.info("institute button pressed")
        meta.connection_type = 'Institute Access'
        meta.discovery_uri = institute_access_uri
        fetch_instance_step(meta=meta, builder=builder, verifier=verifier)

    elif response == 3:
        logger.info("custom button pressed")
        custom_url(builder=builder, meta=meta, verifier=verifier)
