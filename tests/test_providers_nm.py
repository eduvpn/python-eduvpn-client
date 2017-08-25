import os
import sys
import unittest

run = os.name == 'posix' and not sys.platform.startswith('darwin')

if run:
    from eduvpn.managers.nm import list_providers, store_provider, delete_provider, connect_provider, status_provider


@unittest.skipUnless(run, "requires NetworkManager (Linux)")
class TestNm(unittest.TestCase):
    def setUp(self):
        self.name = 'test'
        self.config = 'test'
        self.cert = 'test'
        self.key = 'test'

    def test_list_providers(self):
        list_providers()

    def test_store_provider(self):
        store_provider(self.name, self.config, self.cert, self.key)

    def test_delete_provider(self):
        delete_provider(self.name)

    def test_connect_provider(self):
        connect_provider(self.name)

    def test_status_provider(self):
        status_provider(self.name)
