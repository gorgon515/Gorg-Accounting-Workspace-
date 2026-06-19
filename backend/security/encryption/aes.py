"""AES-256-GCM encryption primitives for HELIOS.

All encryption uses AES-256-GCM (authenticated encryption). Keys are derived
from a master password using PBKDF2-HMAC-SHA256 with a random 32-byte salt.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from typing import Optional

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False


PBKDF2_ITERATIONS = 600_000
KEY_LEN = 32  # 256 bits
NONCE_LEN = 12  # 96 bits (GCM standard)
SALT_LEN = 32  # 256 bits


def _require_crypto() -> None:
    if not _CRYPTO_AVAILABLE:
        raise RuntimeError(
            "cryptography package not installed. Run: pip install cryptography"
        )


def derive_key(password: str, salt: bytes, iterations: int = PBKDF2_ITERATIONS) -> bytes:
    """Derive a 256-bit AES key from a master password using PBKDF2-HMAC-SHA256."""
    _require_crypto()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LEN,
        salt=salt,
        iterations=iterations,
        backend=default_backend(),
    )
    return kdf.derive(password.encode("utf-8"))


def new_salt() -> bytes:
    """Generate a cryptographically random 32-byte salt."""
    return secrets.token_bytes(SALT_LEN)


def encrypt(key: bytes, plaintext: bytes, associated_data: Optional[bytes] = None) -> bytes:
    """Encrypt plaintext with AES-256-GCM. Returns nonce + ciphertext + tag as one blob."""
    _require_crypto()
    nonce = secrets.token_bytes(NONCE_LEN)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
    return nonce + ciphertext


def decrypt(key: bytes, blob: bytes, associated_data: Optional[bytes] = None) -> bytes:
    """Decrypt AES-256-GCM blob. Raises on authentication failure."""
    _require_crypto()
    nonce = blob[:NONCE_LEN]
    ciphertext = blob[NONCE_LEN:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, associated_data)


def encrypt_str(key: bytes, text: str, associated_data: Optional[bytes] = None) -> str:
    """Encrypt a string; return base64-encoded ciphertext blob."""
    blob = encrypt(key, text.encode("utf-8"), associated_data)
    return base64.b64encode(blob).decode("ascii")


def decrypt_str(key: bytes, encoded: str, associated_data: Optional[bytes] = None) -> str:
    """Decrypt a base64-encoded blob back to a string."""
    blob = base64.b64decode(encoded)
    return decrypt(key, blob, associated_data).decode("utf-8")


def encrypt_json(key: bytes, data: dict, associated_data: Optional[bytes] = None) -> str:
    """Serialize dict to JSON then encrypt it."""
    return encrypt_str(key, json.dumps(data, separators=(",", ":")), associated_data)


def decrypt_json(key: bytes, encoded: str, associated_data: Optional[bytes] = None) -> dict:
    """Decrypt and deserialize JSON."""
    return json.loads(decrypt_str(key, encoded, associated_data))


def sha256_hex(data: bytes) -> str:
    """Return hex SHA-256 of data."""
    return hashlib.sha256(data).hexdigest()


def hmac_sha256(key: bytes, data: bytes) -> str:
    """Return hex HMAC-SHA256 for tamper detection."""
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def content_hash(path: str) -> str:
    """SHA-256 of a file's content for integrity verification."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def encrypt_file(key: bytes, src_path: str, dst_path: str) -> str:
    """Encrypt a file to dst_path. Returns SHA-256 hash of plaintext."""
    with open(src_path, "rb") as f:
        plaintext = f.read()
    content_sha = sha256_hex(plaintext)
    blob = encrypt(key, plaintext)
    with open(dst_path, "wb") as f:
        f.write(blob)
    return content_sha


def decrypt_file(key: bytes, src_path: str, dst_path: str, expected_hash: Optional[str] = None) -> bool:
    """Decrypt src_path to dst_path. Returns True if hash matches (or no hash given)."""
    with open(src_path, "rb") as f:
        blob = f.read()
    plaintext = decrypt(key, blob)
    if expected_hash and sha256_hex(plaintext) != expected_hash:
        return False
    with open(dst_path, "wb") as f:
        f.write(plaintext)
    return True
