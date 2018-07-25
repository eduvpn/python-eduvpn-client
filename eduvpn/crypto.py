# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import base64
import hashlib
import random
import nacl.signing
import nacl.encoding
from cryptography.x509.oid import NameOID
from cryptography import x509
from cryptography.hazmat.backends import default_backend


def common_name_from_cert(pem_data):
    """
    Extract common name from client certificate.

    args:
        pem_data (str): PEM encoded certificate

    returns:
        str: the common name of the client certificate.

    """
    cert = x509.load_pem_x509_certificate(pem_data, default_backend())
    return cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value


def gen_code_verifier(length=128):
    """
    Generate a high entropy code verifier, used for PKCE

    args:
        length (int): length of the code

    returns:
        str:
    """
    choices = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~'
    r = random.SystemRandom()
    return "".join(r.choice(choices) for _ in range(length))


def gen_base32(length=20):
    choices = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
    r = random.SystemRandom()
    return "".join(r.choice(choices) for _ in range(length))


def gen_code_challenge(code_verifier):
    """
    Transform the PKCE code verifier in a code challenge

    args:
        code_verifier (str): a string generated with `gen_code_verifier()`
    """
    sha256 = hashlib.sha256(code_verifier.encode())
    encoded = base64.urlsafe_b64encode(sha256.digest())
    return encoded.rstrip(b'=')


def make_verifier(key):
    """
    Create a NaCL verifier

    args:
        key (str): A verification key

    returns:
        nacl.signing.VerifyKey: a nacl verifykey object
    """
    return nacl.signing.VerifyKey(key, encoder=nacl.encoding.Base64Encoder)
