"""Tests for the Connector Registry -- Sprint 19 (Module 6)."""
from __future__ import annotations

from app.discovery.connector_registry import ConnectorRegistry
from app.matching.config import MatchingConfig


class _Connector:
    def __init__(self, name, priority, available=True):
        self.name = name
        self.priority = priority
        self._available = available

    def is_available(self):
        return self._available

    def discover(self, requirement):
        return []


def test_get_all_returns_connectors_in_priority_order():
    registry = ConnectorRegistry()
    registry.register(_Connector("slow", 50))
    registry.register(_Connector("fast", 10))
    names = [c.name for c in registry.get_all()]
    assert names == ["fast", "slow"]


def test_config_priority_override_takes_precedence():
    config = MatchingConfig(connector_priority={"slow": 1})
    registry = ConnectorRegistry(config=config)
    registry.register(_Connector("slow", 50))
    registry.register(_Connector("fast", 10))
    names = [c.name for c in registry.get_all()]
    assert names == ["slow", "fast"]


def test_get_available_excludes_unconfigured_connectors():
    registry = ConnectorRegistry()
    registry.register(_Connector("live", 10, available=True))
    registry.register(_Connector("not_connected", 20, available=False))
    names = [c.name for c in registry.get_available()]
    assert names == ["live"]


def test_status_reports_connection_state_per_connector():
    registry = ConnectorRegistry()
    registry.register(_Connector("live", 10, available=True))
    registry.register(_Connector("not_connected", 20, available=False))
    status = registry.status()
    by_name = {s["name"]: s for s in status}
    assert by_name["live"]["status"] == "connected"
    assert by_name["not_connected"]["status"] == "not_connected"


def test_unregister_removes_connector():
    registry = ConnectorRegistry()
    registry.register(_Connector("temp", 10))
    registry.unregister("temp")
    assert registry.get_all() == []
    assert registry.get("temp") is None
