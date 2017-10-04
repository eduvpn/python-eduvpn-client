from unittest import TestCase, skip
from mock import MagicMock
from eduvpn.test_util import MockBuilder, MockOAuth
from eduvpn.metadata import Metadata
from eduvpn.steps.browser import browser_step, _phase1_background, _phase1_callback, _phase2_background,\
    _phase2_callback, _show_dialog


class TestSteps(TestCase):
    uuid = 'test'

    @classmethod
    def setUpClass(cls):
        cls.meta = Metadata()
        cls.meta.uuid = cls.uuid
        cls.meta.api_base_uri = "test_url"
        cls.meta.token = {'token_endpoint': 'https://test'}
        cls.meta.api_base_uri = 'https://test'
        cls.builder = MockBuilder()
        cls.verifier = MagicMock()
        cls.oauth = MockOAuth()

    def test_browser_step(self):
        browser_step(builder=self.builder, meta=self.meta, verifier=self.verifier)

    @skip("TODO")
    def test_phase1_background(self):
        _phase1_background(builder=self.builder, meta=self.meta, verifier=self.verifier, dialog=None)

    @skip("TODO")
    def test_phase1_callback(self):
        _phase1_callback(builder=self.builder, meta=self.meta, auth_url=None, dialog=None, code_verifier=None,
                         oauth=self.oauth, port=1)

    @skip("TODO")
    def test_phase2_background(self):
        _phase2_background(builder=self.builder, meta=self.meta, auth_url=None, dialog=None, code_verifier=None,
                           oauth=self.oauth, port=1)

    def test_phase2_callback(self):
        _phase2_callback(builder=self.builder, meta=self.meta, dialog=None, oauth=self.oauth)

    @skip("TODO")
    def test_show_dialog(self):
        _show_dialog(builder=self.builder, auth_url=None, dialog=None)

