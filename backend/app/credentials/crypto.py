"""Symmetric encryption for connector secrets at rest -- Sprint 32.

Fernet (AES-128-CBC + HMAC-SHA256, via the `cryptography` package) rather
than anything hand-rolled: it's an authenticated scheme (tamper-evident,
not just confidentiality), and the key is a single opaque token held in
one env var (APP_ENCRYPTION_KEY, on Railway -- never in the database
alongside the ciphertext it protects, and never in source control).

Deliberately NOT validated/required at import time -- an app with
CONNECTOR_CREDENTIALS_BACKEND=memory (the default) never calls into this
module at all, so it must stay importable with no key configured. The
error only surfaces the moment something actually tries to encrypt or
decrypt a secret without a valid key.
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class EncryptionNotConfiguredError(Exception):
    """Raised when APP_ENCRYPTION_KEY is missing or not a valid Fernet key,
    at the moment an encrypt/decrypt is actually attempted."""


def _fernet() -> Fernet:
    key = settings.APP_ENCRYPTION_KEY
    if not key:
        raise EncryptionNotConfiguredError(
            "APP_ENCRYPTION_KEY is not set. Generate one with:\n"
            '  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"\n'
            "and set it as an environment variable before storing connector credentials."
        )
    try:
        return Fernet(key.encode("utf-8") if isinstance(key, str) else key)
    except Exception as e:  # noqa: BLE001 -- any malformed-key error becomes one clear message
        raise EncryptionNotConfiguredError(f"APP_ENCRYPTION_KEY is not a valid Fernet key: {e}") from e


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as e:
        raise EncryptionNotConfiguredError(
            "Stored credential could not be decrypted -- APP_ENCRYPTION_KEY may have changed "
            "since this secret was written, or the ciphertext is corrupted."
        ) from e
