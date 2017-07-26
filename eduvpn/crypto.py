import base64
import hashlib
import random


def gen_code_verifier(length=128):
    """
    Generate a high entropy code verifier, used for PKCE
    """
    choices = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~'
    r = random.SystemRandom()
    return "".join(r.choice(choices) for _ in range(length))


def gen_code_challenge(code_verifier):
    """
    Transform the PKCE code verifier in a code challenge
    """
    return base64.urlsafe_b64encode(hashlib.sha256(code_verifier).digest()).rstrip('=')
