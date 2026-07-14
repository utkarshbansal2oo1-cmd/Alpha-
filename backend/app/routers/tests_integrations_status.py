"""Tests for GET /integrations/status -- Sprint 32."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.integrations.github.config import GitHubConfig, GitHubConfigStore, get_github_config_store
from app.main import app


def test_status_unconfigured_by_default():
    store = GitHubConfigStore()
    app.dependency_overrides[get_github_config_store] = lambda: store
    try:
        client = TestClient(app)
        resp = client.get("/integrations/status")
        assert resp.status_code == 200
        body = resp.json()["github"]
        assert body["configured"] is False
        assert body["status"] == "unconfigured"
        assert body["verified_username"] is None
        assert body["last_error"] is None
    finally:
        app.dependency_overrides.clear()


def test_status_reflects_verified_connection():
    store = GitHubConfigStore()
    store.set(GitHubConfig(personal_access_token="ghp_fake"))
    store.mark_verified("octocat", ["read:user", "public_repo"])
    app.dependency_overrides[get_github_config_store] = lambda: store
    try:
        client = TestClient(app)
        resp = client.get("/integrations/status")
        assert resp.status_code == 200
        body = resp.json()["github"]
        assert body["configured"] is True
        assert body["status"] == "connected"
        assert body["verified_username"] == "octocat"
        assert body["verified_scopes"] == ["read:user", "public_repo"]
        assert body["last_verified_at"] is not None
    finally:
        app.dependency_overrides.clear()


def test_status_reflects_invalid_token_after_runtime_error():
    store = GitHubConfigStore()
    store.set(GitHubConfig(personal_access_token="ghp_fake"))
    store.mark_verified("octocat")
    store.mark_error("GitHub authentication failed (401) during search.")
    app.dependency_overrides[get_github_config_store] = lambda: store
    try:
        client = TestClient(app)
        resp = client.get("/integrations/status")
        assert resp.status_code == 200
        body = resp.json()["github"]
        assert body["status"] == "invalid"
        assert "401" in body["last_error"]
    finally:
        app.dependency_overrides.clear()
