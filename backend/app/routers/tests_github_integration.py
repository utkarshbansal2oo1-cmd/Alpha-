"""Tests for POST /integrations/github/configure -- Sprint 20B."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.integrations.github.config import GitHubConfigStore, get_github_config_store
from app.main import app


def test_configure_sets_pat_and_default_base_url():
    store = GitHubConfigStore()
    app.dependency_overrides[get_github_config_store] = lambda: store
    try:
        client = TestClient(app)
        resp = client.post("/integrations/github/configure", json={"personal_access_token": "ghp_fake"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["configured"] is True
        assert body["base_url"] == "https://api.github.com"
        assert store.is_configured() is True
        assert store.get().personal_access_token == "ghp_fake"
    finally:
        app.dependency_overrides.clear()


def test_configure_accepts_base_url_override():
    store = GitHubConfigStore()
    app.dependency_overrides[get_github_config_store] = lambda: store
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
