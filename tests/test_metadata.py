
import unittest
from mock import patch
from eduvpn.metadata import Metadata
from eduvpn.exceptions import EduvpnException


class MockFile:
    def __init__(self, content=None):
        if content:
            self.content = content
        else:
            self.content = '{"display_name": "correct", "uuid": "correct"}'

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        return False

    def read(self):
        return self.content


class TestMetadata(unittest.TestCase):
    def test_metadata_write(self):
        metadata = Metadata()
        with self.assertRaises(EduvpnException):
            metadata.write()
        metadata.uuid = 'test'
        metadata.write()

    @patch('eduvpn.metadata.open', side_effect=lambda path, mode: MockFile(), create=True)
    def test_metadata_from(self, _):
        uuid = "test"
        metadata = Metadata.from_uuid(uuid=uuid)
        self.assertEqual(metadata.display_name, "correct")
        self.assertEqual(metadata.uuid, "correct")

    @patch('eduvpn.metadata.open', side_effect=lambda path, mode: MockFile('invalid'), create=True)
    def test_metadata_from_uuid_invalid(self, _):
        uuid = "test"
        display_name = "end_of_the_world"
        metadata = Metadata.from_uuid(uuid=uuid, display_name=display_name)
        self.assertEqual(metadata.display_name, display_name)
