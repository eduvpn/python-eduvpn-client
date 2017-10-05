# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from mock import MagicMock


class MockSelection:
    def __init__(self, num_fields):
        self.model = [['test'] * num_fields]
        self.treeiter = 0

    def get_selected(self):
        return self.model, self.treeiter

    def clear(self):
        return


class MockResponse:
    def __init__(self, content_json=None):
        self.status_code = 200

        if content_json:
            self.content_json = content_json
        else:
            self.content_json = {
                "create_keypair": {"data": {"certificate": "mockcert", "private_key": "mockkey"}},
                "profile_list": {"data": {}},
                "user_info": {'data': {'is_disabled': False, 'two_factor_enrolled': False}},
                "authorization_type": "test",
                "instances": [],

            }

    @property
    def content(self):
        return str(self.content_json).encode()

    def json(self):
        return self.content_json

    def text(self):
        return str(self.content_json)


class MockOAuth:
    def __init__(self, response=MockResponse()):
        self.response = response

    def get(self, _):
        return self.response

    def authorization_url(self, auth_endpoint, code_challenge_method, code_challenge):
        url = "https://mock url"
        state = "mock state"
        return url, state

    def post(self, uri, data):
        return MockResponse()

    def fetch_token(self, token_endpoint, code, code_verifier):
        return {}


class MockBuilder:
    def __init__(self):
        self.objects = {
            'profiles-selection': MockSelection(3),
            'instances-selection': MockSelection(2),
        }

    def get_object(self, o):
        return self.objects.get(o, MagicMock())


class VerifyMock:
    def verify(self, *args, **kwargs):
        return True


class MockDialog:
    def __init__(self, return_code=0):
        self.return_code = return_code

    def run(self):
        return self.return_code

    def hide(self):
        return True
