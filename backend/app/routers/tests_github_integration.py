"""Tests for POST /integrations/github/configure -- Sprint 20B, PAT
verification added Sprint 32."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.integrations.github.client import GitHubAPIError
from app.integrations.github.config import GitHubConfigStore, get_github_config_store
from app.main import app
from app.routers.github_integration import get_github_verifier


def _fake_verifier(username="octocat", scopes=None):
    """Stands in for get_github_verifier() -- returns a fixed
    (username, scopes) without making any real network call."""
    def _verify(config):
        return username, (scopes if scopes is not None else ["read:user", "public_repo"])
    return _verify


def _failing_verifier(status_code=401):
    def _verify(config):
        raise GitHubAPIError(status_code, "Bad credentials")
    return _verify


def test_configure_sets_pat_and_default_base_url():
    store = GitHubConfigStore()
    app.dependency_overrides[get_github_config_store] = lambda: store
    app.dependency_overrides[get_github_verifier] = _fake_verifier
    try:
        client = TestClient(app)
        resp = client.post("/integrations/github/configure", json={"personal_access_token": "ghp_fake"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["configured"] is True
        assert body["base_url"] == "https://api.github.com"
        assert body["verified_username"] == "octocat"
        assert body["verified_scopes"] == ["read:user", "public_repo"]
        assert store.is_configured() is True
        assert store.get().personal_access_token == "ghp_fake"
        assert store.get_status()["status"] == "connected"
        assert store.get_status()["verified_username"] == "octocat"
    finally:
        app.dependency_overrides.clear()


def test_configure_accepts_base_url_override():
    store = GitHubConfigStore()
    app.dependency_overrides[get_github_config_store] = lambda: store
    app.dependency_overrides[get_github_verifier] = _fake_verifier
    try:
        client = TestClient(app)
        resp = client.post(
            "/integrations/github/configure",
            json={"personal_access_token": "ghp_fake", "base_url": "https://ghe.example.com/api/v3"},
        )
        assert resp.status_code == 200
        assert resp.json()["base_url"] == "https://ghe.example.com/api/v3"
    finally:
        app.dependency_overrides.clear()


def test_configure_rejects_invalid_token_and_saves_nothing():
    store = GitHubConfigStore()
    app.dependency_overrides[get_github_config_store] = lambda: store
    app.dependency_overrides[get_github_verifier] = _failing_verifier
    try:
        client = TestClient(app)
        resp = client.post("/integrations/github/configure", json={"personal_access_token": "ghp_bad"})
        assert resp.status_code == 401
        assert "Invalid GitHub Personal Access Token" in resp.json()["detail"]
        # Nothing was persisted -- the whole point of verify-before-save.
        assert store.is_configured() is False
    finally:
        app.dependency_overrides.clear()


def test_configure_returns_502_on_non_401_verification_failure():
    store = GitHubConfigStore()
    app.dependency_overrides[get_github_config_store] = lambda: store
    app.dependency_overrides[get_github_verifier] = lambda: _failing_verifier(status_code=503)
    try:
        client = TestClient(app)
        resp = client.post("/integrations/github/configure", json={"personal_access_token": "ghp_fake"})
        assert resp.status_code == 502
        assert store.is_configured() is False
    finally:
        app.dependency_overrides.clear()


# --- Sprint 37: POST /integrations/github/disconnect ------------------------


def test_disconnect_after_configure_reverts_to_unconfigured():
    store = GitHubConfigStore()
    app.dependency_overrides[get_github_config_store] = lambda: store
    app.dependency_overrides[get_github_verifier] = _fake_verifier
    try:
        client = TestClient(app)
        client.post("/integrations/github/configure", json={"personal_access_token": "ghp_fake"})
        assert store.is_configured() is True

        resp = client.post("/integrations/github/disconnect")
        assert resp.status_code == 200
        assert resp.json() == {"configured": False}
        assert store.is_configured() is False
        assert store.get_status()["status"] == "unconfigured"
    finally:
        app.dependency_overrides.clear()


def test_disconnect_when_never_configured_is_idempotent_not_an_error():
    store = GitHubConfigStore()
    app.dependency_overrides[get_github_config_store] = lambda: store
    try:
        client = TestClient(app)
        resp = client.post("/integrations/github/disconnect")
        assert resp.status_code == 200
        assert resp.json() == {"configured": False}
    finally:
        app.dependency_overrides.clear()


def test_reconnect_after_disconnect_works():
    store = GitHubConfigStore()
    app.dependency_overrides[get_github_config_store] = lambda: store
    app.dependency_overrides[get_github_verifier] = _fake_verifier
    try:
        client = TestClient(app)
        client.post("/integrations/github/configure", json={"personal_access_token": "ghp_first"})
        client.post("/integrations/github/disconnect")

        resp = client.post("/integrations/github/configure", json={"personal_access_token": "ghp_second"})
        assert resp.status_code == 200
        assert resp.json()["configured"] is True
        assert store.get().personal_access_token == "ghp_second"
    finally:
        app.dependency_overrides.clear()
