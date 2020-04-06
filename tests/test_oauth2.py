# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import unittest
from unittest.mock import patch

from eduvpn.oauth2 import create_oauth_session, get_oauth_token_code, get_open_port, one_request


class TestCrypto(unittest.TestCase):
    def test_create_oauth_session(self):
        create_oauth_session(port=1025, auto_refresh_url='test', lets_connect=False)

    @patch('eduvpn.oauth2.one_request', side_effect=lambda port, letsconnect, timeout=None: {"code": "blabla",
                                                                                             "state": "blabla"})
    @patch('webbrowser.open')
    def test_get_oauth_token_code(self, _, __):
        get_oauth_token_code(port=1025, lets_connect=False)

    def test_get_open_port(self):
        get_open_port()

    @patch('eduvpn.oauth2.HTTPServer')
    @patch('eduvpn.oauth2.urlparse')
    def test_one_request(self, *_):
        one_request(1025, lets_connect=False)
