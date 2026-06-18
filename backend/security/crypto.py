"""Core cryptography for HELIOS — real AES-256-GCM with scrypt key derivation.

No mock crypto: AES-256-GCM provides authenticated encryption (confidentiality +
tamper detection); scrypt derives the key from a master password with a per-store
random salt; SHA-256 + HMAC support integrity verification and hash chaining.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

KEY_BYTES = 32  # AES-256
NONCE_BYTES = 12
SALT_BYTES = 16
# scrypt cost parameters (interactive-strength; tune up for at-rest master keys).
SCRYPT_N = 2 ** 14
SCRYPT_R = 8
SCRYPT_P = 1


class DecryptionError(RuntimeError):
    """Wrong key/password or tampered ciphertext."""


def new_salt() -> bytes:
    return os.urandom(SALT_BYTES)


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 256-bit key from a master password using scrypt."""
    kdf = Scrypt(salt=salt, length=KEY_BYTES, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    return kdf.derive(password.encode("utf-8"))


def generate_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def encrypt(key: bytes, plaintext: bytes, aad: bytes | None = None) -> str:
    """AES-256-GCM encrypt → base64(nonce || ciphertext+tag)."""
    nonce = os.urandom(NONCE_BYTES)
    ct = AESGCM(key).encrypt(nonce, plaintext, aad)
    return base64.b64encode(nonce + ct).decode("ascii")


def decrypt(key: bytes, blob: str, aad: bytes | None = None) -> bytes:
    raw = base64.b64decode(blob)
    nonce, ct = raw[:NONCE_BYTES], raw[NONCE_BYTES:]
    try:
        return AESGCM(key).decrypt(nonce, ct, aad)
    except InvalidTag as exc:
        raise DecryptionError("decryption failed — wrong key or tampered data") from exc


def encrypt_json(key: bytes, obj, aad: bytes | None = None) -> str:
    return encrypt(key, json.dumps(obj).encode("utf-8"), aad)


def decrypt_json(key: bytes, blob: str, aad: bytes | None = None):
    return json.loads(decrypt(key, blob, aad).decode("utf-8"))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str, chunk: int = 65536) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def hmac_sha256(key: bytes, data: bytes) -> str:
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def verify_password(password: str, salt: bytes, expected_check: str) -> bool:
    """Constant-time verification of a master password against a stored check hash."""
    candidate = sha256(derive_key(password, salt))
    return hmac.compare_digest(candidate, expected_check)
