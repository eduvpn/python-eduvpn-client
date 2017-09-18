# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import unittest
import mock

from eduvpn.oauth2 import create_oauth_session, get_oauth_token_code, get_open_port, one_request


class TestCrypto(unittest.TestCase):
    def test_create_oauth_session(self):
        create_oauth_session(port=1025)

    @mock.patch('eduvpn.oauth2.one_request', side_effect=lambda x: {"code": "blabla"})
    @mock.patch('webbrowser.open')
    def test_get_oauth_token_code(self, moch_open, moch_one_request):
        get_oauth_token_code(port=1025)

    def test_get_open_port(self):
        get_open_port()

    @mock.patch('http.server.HTTPServer.handle_request')
    def test_one_request(self, mock_handle_request):
        # TODO: need to find a proper way to mock that path
        with self.assertRaises(AttributeError):
            one_request(1025)
