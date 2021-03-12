from base64 import urlsafe_b64encode, b64decode
import hashlib
import random
import logging
import subprocess
from datetime import datetime
from typing import Optional, List
from functools import lru_cache
from cryptography.x509.oid import NameOID
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from eduvpn.settings import VERIFY_KEYS


logger = logging.getLogger(__name__)


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


@lru_cache(1)
def make_verifiers() -> List[VerifyKey]:
    """
    Create a list of NaCL verifiers.

    returns:
        a list of nacl verify key objects.
    """
    # expecting format: base64(<signature_algorithm> || <key_id> || <public_key>)

    return [VerifyKey(b64decode(k)[10:]) for k in VERIFY_KEYS]


def validate(signature: str, content: bytes) -> bytes:
    decoded = b64decode(signature)[10:]
    verifiers = make_verifiers()

    logger.debug(f"Trying {len(verifiers)} verifiers")
    for f in verifiers:
        try:
            message = f.verify(smessage=content, signature=decoded)
            logger.debug(f"Used signature {f}")
            return message
        except BadSignatureError:
            logger.debug(f"Skipping signature {f}")
    raise BadSignatureError


def get_certificate_expiry(certificate: str) -> Optional[datetime]:
    process = subprocess.Popen(
        ['openssl', 'x509', '-noout', '-enddate'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        certificate_bytes = certificate.encode('ascii')
    except UnicodeEncodeError:
        logger.error(f"non-ascii certificate: {certificate!r}")
        return None
    try:
        stdout, stderr = process.communicate(certificate_bytes, timeout=.5)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, strerr = process.communicate()
        logger.error(f"timeout getting certificate expiry: {stdout!r} {strerr!r}")
        return None
    if stderr:
        logger.error(f"failed getting certificate expiry: {stderr!r}")
        return None
    if process.returncode != 0:
        logger.warning("error getting certificate expiry")
    if not stdout.startswith(b'notAfter='):
        logger.error(f"unexpected output getting certificate expiry: {stdout!r}")
        return None
    expiry_text = stdout[len(b'notAfter='):].decode('ascii').strip()
    datetime_format = '%b %d %H:%M:%S %Y %Z'
    try:
        return datetime.strptime(expiry_text, datetime_format)
    except ValueError:
        logger.error(f"invalid expiry date format: {expiry_text!r}")
        return None
