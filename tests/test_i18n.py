from unittest import TestCase
from eduvpn.i18n import extract_translation


class TestI18n(TestCase):
    def test_extract_translation(self):
        self.assertEqual("bla bla", extract_translation("bla bla"))

        self.assertEqual('bleu bleu', extract_translation({'de': 'bleu bleu'}))
