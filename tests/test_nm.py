from unittest import TestCase

import gi

gi.require_version('NM', '1.0')
from gi.repository import NM, GLib   # type: ignore

from eduvpn.nm import (nm_available, add_connection,
                       import_ovpn)
from tests.mock_config import mock_config, mock_key, mock_cert


class TestNm(TestCase):
    def test_nm(self):
        nm_available()
        connection = import_ovpn(mock_config, mock_key, mock_cert)
        main_loop = GLib.MainLoop()
        client = NM.Client.new(None)
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
