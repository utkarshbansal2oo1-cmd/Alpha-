"""Tests for GET/POST /connectors -- Sprint 20A (Module 5)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.discovery.connector_registry_v2 import ManagedConnectorRegistry, get_managed_connector_registry
from app.discovery.connectors.framework import ConnectorMetadata
from app.main import app


class _Connector:
    def __init__(self, name, priority_value=10, enabled=True, available=True):
        self._metadata = ConnectorMetadata(name=name, version="2.0.0", capabilities=["candidate_search"], enabled=enabled)
        self._priority = priority_value
        self._available = available

    @property
    def metadata(self):
        return self._metadata

    def discover(self, requirement):
        return []

    def supports(self, requirement):
        return True

    def priority(self):
        return self._priority

    def health(self):
        return {"available": self._available}

    def status(self):
        if not self._metadata.enabled:
            return "disabled"
        return "connected" if self._available else "not_connected"

    def configure(self, config):
        if "enabled" in config:
            self._metadata.enabled = bool(config["enabled"])


def _client_with_test_registry():
    registry = ManagedConnectorRegistry()
    registry.register(_Connector("test_source"))
    app.dependency_overrides[get_managed_connector_registry] = lambda: registry
    return TestClient(app)


def test_list_connectors_returns_registered_connectors():
    client = _client_with_test_registry()
    try:
        resp = client.get("/connectors")
        assert resp.status_code == 200
        names = {c["name"] for c in resp.json()}
        assert "test_source" in names
    finally:
        app.dependency_overrides.clear()


def test_disable_then_enable_connector_round_trip():
    client = _client_with_test_registry()
    try:
        resp = client.post("/connectors/disable", json={"name": "test_source"})
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False
        assert resp.json()["status"] == "disabled"

        resp = client.post("/connectors/enable", json={"name": "test_source"})
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True
        assert resp.json()["status"] == "connected"
    finally:
        app.dependency_overrides.clear()


def test_configure_unknown_connector_returns_404():
    client = _client_with_test_registry()
    try:
        resp = client.post("/connectors/configure", json={"name": "does_not_exist", "config": {}})
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_list_connectors_against_real_dynamically_loaded_registry():
    client = TestClient(app)
    resp = client.get("/connectors")
    assert resp.status_code == 200
    names = {c["name"] for c in resp.json()}
    assert "greenhouse_ats" in names
