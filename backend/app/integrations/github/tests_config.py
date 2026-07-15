"""Tests for GitHubConfigStore -- Sprint 20B."""
from __future__ import annotations

import pytest

from app.integrations.github.config import GitHubConfig, GitHubConfigError, GitHubConfigStore


def test_not_configured_by_default():
    store = GitHubConfigStore()
    assert store.is_configured() is False
    with pytest.raises(GitHubConfigError):
        store.get()


def test_set_then_get_returns_config():
    store = GitHubConfigStore()
    store.set(GitHubConfig(personal_access_token="abc123"))
    assert store.is_configured() is True
    assert store.get().personal_access_token == "abc123"
    assert store.get().base_url == "https://api.github.com"


# --- Sprint 32: persistent (credential-store-backed) mode -------------------


class _FakeCredentialStore:
    """Minimal stand-in for ConnectorCredentialStore -- avoids pulling in
    real encryption/DB machinery just to prove GitHubConfigStore delegates
    correctly; app/credentials/tests_service.py already covers the real
    store's own persistence/encryption behavior."""

    def __init__(self):
        self._secrets: dict[str, str] = {}

    def get_secret(self, provider: str) -> str | None:
        return self._secrets.get(provider)

    def set_secret(self, provider: str, secret: str, created_by: str | None = None) -> None:
        self._secrets[provider] = secret


def test_persistent_mode_not_configured_by_default():
    store = GitHubConfigStore(credential_store=_FakeCredentialStore())
    assert store.is_configured() is False
    with pytest.raises(GitHubConfigError):
        store.get()


def test_persistent_mode_set_then_get_delegates_to_credential_store():
    credential_store = _FakeCredentialStore()
    store = GitHubConfigStore(credential_store=credential_store)

    store.set(GitHubConfig(personal_access_token="ghp_real", base_url="https://ghe.example.com"))

    assert store.is_configured() is True
    assert store.get().personal_access_token == "ghp_real"
    assert store.get().base_url == "https://ghe.example.com"
    assert credential_store.get_secret("github") == "ghp_real"  # actually persisted through


def test_persistent_mode_survives_new_store_instance_same_credential_backend():
    """The whole point of Sprint 32: a fresh GitHubConfigStore (simulating
    a process restart) sharing the same underlying credential store must
    still see a previously-configured PAT -- no need to re-POST
    /integrations/github/configure after every deploy."""
    credential_store = _FakeCredentialStore()
    store1 = GitHubConfigStore(credential_store=credential_store)
    store1.set(GitHubConfig(personal_access_token="ghp_persisted"))

    store2 = GitHubConfigStore(credential_store=credential_store)
    assert store2.is_configured() is True
    assert store2.get().personal_access_token == "ghp_persisted"


# --- Sprint 37: disconnect ---------------------------------------------


def test_clear_resets_memory_mode_to_unconfigured():
    store = GitHubConfigStore()
    store.set(GitHubConfig(personal_access_token="abc123"))
    assert store.is_configured() is True

    store.clear()

    assert store.is_configured() is False
    with pytest.raises(GitHubConfigError):
        store.get()
    assert store.get_status()["configured"] is False
    assert store.get_status()["status"] == "unconfigured"


def test_clear_is_a_noop_when_never_configured():
    store = GitHubConfigStore()
    store.clear()  # must not raise
    assert store.is_configured() is False


class _FakeCredentialStoreWithClear(_FakeCredentialStore):
    def clear_secret(self, provider: str) -> None:
        self._secrets.pop(provider, None)


def test_clear_delegates_to_credential_store_in_persistent_mode():
    credential_store = _FakeCredentialStoreWithClear()
    store = GitHubConfigStore(credential_store=credential_store)
    store.set(GitHubConfig(personal_access_token="ghp_real"))
    assert store.is_configured() is True

    store.clear()

    assert store.is_configured() is False
    assert credential_store.get_secret("github") is None


def test_memory_mode_and_persistent_mode_are_isolated():
    memory_store = GitHubConfigStore()
    memory_store.set(GitHubConfig(personal_access_token="memory-token"))

    persistent_store = GitHubConfigStore(credential_store=_FakeCredentialStore())
    assert persistent_store.is_configured() is False  # unaffected by the unrelated memory-mode store
