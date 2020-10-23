from unittest import TestCase, skipIf

from eduvpn.nm import (nm_available, add_connection,
                       import_ovpn, get_client, get_mainloop, activate_connection,
                       get_cert_key, connection_status, deactivate_connection, save_connection)
from eduvpn.storage import get_uuid
from tests.mock_config import mock_config, mock_key, mock_cert


@skipIf(not nm_available(), "Network manager not available")
class TestNm(TestCase):
    def test_nm(self):
        nm_available()
        simple_connection = import_ovpn(mock_config, mock_key, mock_cert)
        main_loop = get_mainloop()
        client = get_client()
        add_connection(client, simple_connection)
        # main_loop.run()
        uuid = get_uuid()
        activate_connection(client, uuid)
        get_cert_key(client, uuid)
        connection_status(client, uuid)
        deactivate_connection(client, uuid)
        save_connection(client, mock_config, mock_key, mock_cert)
        # update_connection(connection, connection)
