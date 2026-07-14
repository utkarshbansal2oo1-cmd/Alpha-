"""Tests for app/credentials/crypto.py -- Sprint 32."""
from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from app.credentials.crypto import EncryptionNotConfiguredError, decrypt_secret, encrypt_secret


@pytest.fixture(autouse=True)
def _reset_key(monkeypatch):
    monkeypatch.setattr("app.credentials.crypto.settings.APP_ENCRYPTION_KEY", "")
    yield


def test_encrypt_raises_when_no_key_configured():
    with pytest.raises(EncryptionNotConfiguredError):
        encrypt_secret("ghp_fake")


def test_decrypt_raises_when_no_key_configured():
    with pytest.raises(EncryptionNotConfiguredError):
        decrypt_secret("anything")


def test_encrypt_raises_on_malformed_key(monkeypatch):
    monkeypatch.setattr("app.credentials.crypto.settings.APP_ENCRYPTION_KEY", "not-a-valid-fernet-key")
    with pytest.raises(EncryptionNotConfiguredError):
        encrypt_secret("ghp_fake")


def test_roundtrip_with_valid_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr("app.credentials.crypto.settings.APP_ENCRYPTION_KEY", key)

    ciphertext = encrypt_secret("ghp_supersecret")

    assert ciphertext != "ghp_supersecret"  # never stored as plaintext
    assert decrypt_secret(ciphertext) == "ghp_supersecret"


def test_decrypt_raises_when_key_rotated_away(monkeypatch):
    key1 = Fernet.generate_key().decode()
    monkeypatch.setattr("app.credentials.crypto.settings.APP_ENCRYPTION_KEY", key1)
    ciphertext = encrypt_secret("ghp_supersecret")

    key2 = Fernet.generate_key().decode()
    monkeypatch.setattr("app.credentials.crypto.settings.APP_ENCRYPTION_KEY", key2)

    with pytest.raises(EncryptionNotConfiguredError):
        decrypt_secret(ciphertext)
