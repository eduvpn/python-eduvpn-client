import unittest
import mock
from eduvpn.remote import create_keypair, get_auth_url, get_instance_info, get_instances, get_profile_config



class TestRemote(unittest.TestCase):
    def test_create_keypair(self):
        m = mock.Mock()
        m.post = mock.Mock()
        m.post.content = mock.MagicMock(return_value={'create_keypair': {'data': 'bla'}})
        create_keypair(oauth=mock.Mock(), api_base_uri='test')

    def test_get_auth_url(self):
        m = ()
        m.authorization_url = mock.MagicMock(return_value=('test', 'test'))
        get_auth_url(oauth=mock.Mock(), code_verifier='test', auth_endpoint='test')

    def test_get_instance_info(self):
        get_instance_info(instance_uri='test', verify_key='test')

    def test_get_instances(self):
        get_instances(base_uri='test', verify_key='test')

    def test_get_profile_config(self):
        get_profile_config(oauth=mock.Mock(), api_base_uri='test')