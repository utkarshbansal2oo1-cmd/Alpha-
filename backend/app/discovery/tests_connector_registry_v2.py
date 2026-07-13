"""Tests for the Sprint 20A ManagedConnectorRegistry."""
from __future__ import annotations

import pytest

from app.discovery.connector_registry_v2 import ManagedConnectorRegistry
from app.discovery.connectors.framework import ConnectorMetadata


class _Connector:
    def __init__(self, name, priority_value, enabled=True, available=True):
        self._metadata = ConnectorMetadata(name=name, enabled=enabled)
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


def test_register_and_list_in_priority_order():
    registry = ManagedConnectorRegistry()
    registry.register(_Connector("slow", 50))
    registry.register(_Connector("fast", 10))
    assert [c.metadata.name for c in registry.list()] == ["fast", "slow"]


def test_unregister_removes_connector():
    registry = ManagedConnectorRegistry()
    registry.register(_Connector("temp", 10))
    registry.unregister("temp")
    assert registry.list() == []
    assert registry.get("temp") is None


def test_enabled_and_disabled_partition_connectors():
    registry = ManagedConnectorRegistry()
    registry.register(_Connector("on", 10, enabled=True))
    registry.register(_Connector("off", 20, enabled=False))
    assert [c.metadata.name for c in registry.enabled()] == ["on"]
    assert [c.metadata.name for c in registry.disabled()] == ["off"]


def test_health_returns_snapshot_per_connector():
    registry = ManagedConnectorRegistry()
    registry.register(_Connector("a", 10, available=True))
    registry.register(_Connector("b", 20, available=False))
    health = registry.health()
    assert health["a"]["available"] is True
    assert health["b"]["available"] is False


def test_enable_and_disable_persist_through_configure():
    registry = ManagedConnectorRegistry()
    registry.register(_Connector("toggle", 10, enabled=False))
    registry.enable("toggle")
    assert registry.get("toggle").metadata.enabled is True
    registry.disable("toggle")
    assert registry.get("toggle").metadata.enabled is False


def test_configure_unknown_connector_raises_key_error():
    registry = ManagedConnectorRegistry()
    with pytest.raises(KeyError):
        registry.configure("nope", {})
