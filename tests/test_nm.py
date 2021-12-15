from unittest import TestCase, skipIf

from eduvpn.nm import (nm_available, add_connection,
                       import_ovpn, get_client, get_mainloop)
from eduvpn.ovpn import Ovpn
from eduvpn.storage import get_uuid
from tests.mock_config import mock_config, mock_key, mock_cert


@skipIf(not nm_available(), "Network manager not available")
class TestNm(TestCase):
    def test_nm_available(self):
        nm_available()

    def test_import_ovpn(self):
        ovpn = Ovpn.parse(mock_config)
        import_ovpn(ovpn, mock_key, mock_cert)

    def test_get_mainloop(self):
        get_mainloop()

    def test_get_add_connection(self):
        client = get_client()
        ovpn = Ovpn.parse(mock_config)
        simple_connection = import_ovpn(ovpn, mock_key, mock_cert)
        add_connection(client, simple_connection)

    def test_get_uuid(self):
        get_uuid()

    def test_activate_connection(self):
        get_client()
        get_uuid()
        # activate_connection(client, uuid)
        # get_cert_key(client, uuid)
        # connection_status(client, uuid)
        # deactivate_connection(client, uuid)
        # save_connection_with_config(client, ovpn, mock_key, mock_cert)
