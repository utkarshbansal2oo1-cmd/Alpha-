"""Tests for the Universal Connector Framework -- Sprint 20A/20B."""
from __future__ import annotations

from app.discovery.connectors.framework import ConnectorMetadata, discover_connectors
from app.discovery.connectors.legacy_adapter import LegacyConnectorAdapter
from app.search_planner.models import CanonicalJobRequirement


class _FakeLegacyConnector:
    name = "fake_source"
    priority = 42

    def __init__(self):
        self.available = True

    def is_available(self):
        return self.available

    def discover(self, requirement):
        return []


def test_discover_connectors_finds_every_managed_connector_dynamically():
    # Sprint 18's Greenhouse connector, Sprint 20B's GitHub connector, and
    # all four future-connector stubs each expose a MANAGED_*_CONNECTOR
    # module-level instance -- this confirms the dynamic loader finds
    # them all without a hardcoded list.
    found = discover_connectors()
    names = {c.metadata.name for c in found}
    assert {
        "greenhouse_ats",
        "github",
        "browser_extension",
        "csv_import",
        "resume_import",
        "internal_hrms",
    } <= names


def test_legacy_adapter_wraps_priority_and_availability():
    wrapped = _FakeLegacyConnector()
    metadata = ConnectorMetadata(name="fake_source", capabilities=["candidate_search"])
    adapter = LegacyConnectorAdapter(wrapped=wrapped, metadata=metadata)

    assert adapter.priority() == 42
    assert adapter.status() == "connected"
    assert adapter.health()["available"] is True

    wrapped.available = False
    assert adapter.status() == "not_connected"


def test_legacy_adapter_configure_toggles_enabled_and_status():
    wrapped = _FakeLegacyConnector()
    metadata = ConnectorMetadata(name="fake_source")
    adapter = LegacyConnectorAdapter(wrapped=wrapped, metadata=metadata)

    adapter.configure({"enabled": False})
    assert adapter.metadata.enabled is False
    assert adapter.status() == "disabled"

    adapter.configure({"enabled": True})
    assert adapter.metadata.enabled is True
    assert adapter.status() == "connected"


def test_legacy_adapter_supports_checks_supported_roles():
    wrapped = _FakeLegacyConnector()
    metadata = ConnectorMetadata(name="fake_source", supported_roles=["Product Manager"])
    adapter = LegacyConnectorAdapter(wrapped=wrapped, metadata=metadata)

    assert adapter.supports(CanonicalJobRequirement(role="Product Manager", skills=[])) is True
    assert adapter.supports(CanonicalJobRequirement(role="Backend Engineer", skills=[])) is False


def test_legacy_adapter_supports_any_role_when_unrestricted():
    wrapped = _FakeLegacyConnector()
    metadata = ConnectorMetadata(name="fake_source", supported_roles=[])
    adapter = LegacyConnectorAdapter(wrapped=wrapped, metadata=metadata)

    assert adapter.supports(CanonicalJobRequirement(role="Anything", skills=[])) is True
