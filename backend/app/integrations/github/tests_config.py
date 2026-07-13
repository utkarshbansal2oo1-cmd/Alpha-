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
