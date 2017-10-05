# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import unittest

from mock import patch

from eduvpn.remote import create_keypair, get_auth_url, get_instance_info, get_instances, get_profile_config, \
    system_messages, user_messages, create_config, list_profiles, translate_display_name, user_info
from tests.util import MockResponse, MockOAuth, VerifyMock


class TestRemote(unittest.TestCase):

    def setUp(self):
        self.oauth = MockOAuth()
        self.verify = VerifyMock()

    def test_create_keypair(self):
        create_keypair(oauth=self.oauth, api_base_uri='test')

    def test_get_auth_url(self):
        get_auth_url(oauth=self.oauth, code_verifier='test', auth_endpoint='test')

    @patch('requests.get')
    def test_get_instance_info(self, _):
        get_instance_info(instance_uri='test', verifier=self.verify)

    @patch('requests.get', side_effect=lambda x: MockResponse())
    @patch('base64.b64decode', side_effect=lambda x: "decoded")
    def test_get_instances(self, _, __):
        get_instances(discovery_uri='test', verifier=self.verify)

    def test_get_profile_config(self):
        get_profile_config(oauth=self.oauth, api_base_uri='test', profile_id='test')

    def test_system_messages(self):
        system_messages(oauth=self.oauth, api_base_uri='http://test')

    def test_user_messages(self):
        user_messages(oauth=self.oauth, api_base_uri='http://test')

    def test_create_config(self):
        create_config(oauth=self.oauth, api_base_uri='http://test', display_name='test', profile_id='test')

    def test_list_profiles(self):
        list_profiles(oauth=self.oauth, api_base_uri='http://test')

    def test_translate_display_name(self):
        translate_display_name("translate test")

    def test_user_info(self):
        user_info(oauth=self.oauth, api_base_uri='http://test')
