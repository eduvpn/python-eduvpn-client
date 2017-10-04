# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

import base64
import hashlib
import random
import nacl.signing
import nacl.encoding


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
