# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import unittest
from eduvpn.remote import create_keypair, get_auth_url, get_instance_info, get_instances, get_profile_config


class MochResponse:
    content = '{"create_keypair": {"data": {"certificate": "mockcert", "private_key": "mockkey"}}}'

    def json(self):
        return {"create_keypair": {"data": {"certificate": "mockcert", "private_key": "mockkey"}}}

    def text(self):
        return "bla"



class MockOAuth:
    authorization_url = 'mock'
    def get(self, url):
        return MochResponse()

    def authorization_url(self, auth_endpoint, code_challenge_method, code_challenge):
        authorization_url = "mock url"
        state = "mock state"
        return authorization_url, state

    def post(self, url, data):
        return MochResponse()


class TestRemote(unittest.TestCase):

    def setUp(self):
        self.oauth = MockOAuth()

    def test_create_keypair(self):

        create_keypair(oauth=self.oauth, api_base_uri='test')

    def test_get_auth_url(self):
        get_auth_url(oauth=self.oauth, code_verifier='test', auth_endpoint='test')

    @unittest.skip("todo: need to mock request")
    def test_get_instance_info(self):
        get_instance_info(instance_uri='test', verify_key='test')

    @unittest.skip("todo: need to mock request")
    def test_get_instances(self):
        get_instances(discovery_uri='test', verify_key='test')

    def test_get_profile_config(self):
        get_profile_config(oauth=self.oauth, api_base_uri='test', profile_id='test')
