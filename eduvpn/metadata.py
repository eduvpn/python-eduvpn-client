import json
from os import path
import logging

from eduvpn.config import config_path
from eduvpn.io import mkdir_p


logger = logging.getLogger(__name__)

fields = ("api_base_uri", "profile_id", "display_name", "token", "connection_type", "authorization_type",
          "profile_display_name", "two_factor", "cert", "key", "config", "uuid", "icon_data", "instance_base_uri",
          "username")


class Metadata:
    def __init__(self):
        for field in fields:
            setattr(self, field, None)

        self.display_name = "Unknown"
        self.connection_type = "Unknown"

    def __getitem__(self, item):
        if type(item) == int:
            return fields[item]
        else:
            return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    @staticmethod
    def from_uuid(uuid, display_name=None):
        metadata_path = path.join(config_path, uuid + '.json')
        metadata = Metadata()
        try:
            with open(metadata_path, 'r') as f:
                x = json.load(f)
                for key, value in x.items():
                    if value:
                        metadata[key] = value
        except IOError as e:
            logger.error("can't open metdata file for {}: {}".format(uuid, str(e)))
            metadata.uuid = uuid
            if display_name:
                metadata.display_name = display_name
            else:
                metadata.display_name = uuid
            metadata.connection_type = 'Unknown'
        finally:
            return metadata

    def write(self):
        if not self.uuid:
            raise Exception('uuid field not set')
        d = {}
        for field in fields:
            d[field] = getattr(self, field)
        p = path.join(config_path, self.uuid + '.json')
        logger.info("storing metadata in {}".format(p))
        serialized = json.dumps(d)
        mkdir_p(config_path)
        with open(p, 'w') as f:
            f.write(serialized)