from unittest import TestCase, skip

from eduvpn.nm import (nm_available, add_connection,
                       import_ovpn, get_client, get_mainloop)
from tests.mock_config import mock_config, mock_key, mock_cert


# @skipIf(not nm_available(), "Network manager not available")
@skip("skip this test for now until it is matured")
class TestNm(TestCase):
    def test_nm(self):
        nm_available()
        connection = import_ovpn(mock_config, mock_key, mock_cert)
        main_loop = get_mainloop()
        client = get_client()
        add_connection(client, connection)
        # main_loop.run()

        """
        activate_connection(client, uuid)
        get_cert_key(client, uuid)
        nm_ovpn_import(target_path)
        connection_status(client, uuid)
        deactivate_connection(client, uuid)
        save_connection(client, mock_config, mock_key, mock_cert)
        update_connection(old_con, new_con)
        """
