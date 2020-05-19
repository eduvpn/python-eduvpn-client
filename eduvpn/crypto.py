from base64 import urlsafe_b64encode, b64decode
import hashlib
import random
from cryptography.x509.oid import NameOID
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from nacl.signing import VerifyKey


def gen_code_challenge(code_verifier: str) -> bytes:
    """
    Transform the PKCE code verifier in a code challenge.

    args:
        code_verifier (str): a string generated with `gen_code_verifier()`
    """
    sha256 = hashlib.sha256(code_verifier.encode())
    encoded = urlsafe_b64encode(sha256.digest())
    return encoded.rstrip(b'=')


def gen_code_verifier(length: int = 128) -> str:
    """
    Generate a high entropy code verifier, used for PKCE.

    args:
        length (int): length of the code
    returns:
        str:
    """
    choices = 'abcdefghijklmnopqrstuvwxyz' \
              'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~'
    r = random.SystemRandom()
    return "".join(r.choice(choices) for _ in range(length))


def common_name_from_cert(pem_data: bytes) -> str:
    """
    Extract common name from client certificate.

    args:
        pem_data (str): PEM encoded certificate
    returns:
        str: the common name of the client certificate.
    """
    cert = x509.load_pem_x509_certificate(pem_data, default_backend())
    return cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value


def make_verifier(key: str) -> VerifyKey:
    """
    Create a NaCL verifier.

    args:
        key (str): A public key in minisign format
                   base64(<signature_algorithm> || <key_id> || <public_key>)
    returns:
        nacl.signing.VerifyKey: a nacl verifykey object
    """
    decoded = b64decode(key)[10:]
    return VerifyKey(decoded)
