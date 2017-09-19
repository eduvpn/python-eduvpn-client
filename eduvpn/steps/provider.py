import base64
import logging
from eduvpn.metadata import Metadata
from eduvpn.config import secure_internet_uri, institute_access_uri
from eduvpn.manager import list_providers
from eduvpn.util import bytes2pixbuf, get_pixbuf


logger = logging.getLogger(__name__)


def selection_connection_step(self, _):
    """The connection type selection step"""
    logger.info("add configuration clicked")
    dialog = self.builder.get_object('connection-type-dialog')
    dialog.show_all()
    response = dialog.run()
    dialog.hide()

    meta = Metadata()

    if response == 0:  # cancel
        logger.info("cancel button pressed")
        return

    elif response == 1:
        logger.info("secure button pressed")
        meta.discovery_uri = secure_internet_uri
        meta.connection_type = 'Secure Internet'
        self.fetch_instance_step(meta)

    elif response == 2:
        logger.info("institute button pressed")
        meta.discovery_uri = institute_access_uri
        meta.connection_type = 'Institute Access'
        self.fetch_instance_step(meta)

    elif response == 3:
        logger.info("custom button pressed")
        self.custom_url(meta)


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

