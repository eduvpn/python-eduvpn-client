
import unittest
from eduvpn.metadata import Metadata


class TestMetadata(unittest.TestCase):
    def test_metadata(self):
        uuid = 'test'
        metadata = Metadata()
        metadata.display_name = 'test'
        metadata.uuid = uuid
        metadata.write()
        metadata2 = Metadata.from_uuid(uuid)

        self.assertEqual(metadata2.uuid, metadata.uuid)
        self.assertEqual(metadata2.display_name, metadata.display_name)
