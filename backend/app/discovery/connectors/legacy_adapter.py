"""Adapts a Sprint 18 DiscoveryConnector (name/priority/is_available()/
discover()) into the Sprint 20A Connector framework, so every
already-shipped connector shows up in the new registry/management
endpoints without being reimplemented. Purely a wrapper -- it does not
change the wrapped connector's own behavior or state.
"""
from __future__ import annotations

from app.candidate_repository.import_schemas import CandidateImportRequest
from app.discovery.connectors.framework import ConnectorMetadata
from app.search_planner.models import CanonicalJobRequirement


class LegacyConnectorAdapter:
    def __init__(self, wrapped, metadata: ConnectorMetadata):
        self._wrapped = wrapped
        self._metadata = metadata

    @property
    def metadata(self) -> ConnectorMetadata:
        return self._metadata

    def discover(self, requirement: CanonicalJobRequirement) -> list[CandidateImportRequest]:
        return self._wrapped.discover(requirement)

    def supports(self, requirement: CanonicalJobRequirement) -> bool:
        if not self._metadata.supported_roles:
            return True
        role = (requirement.role or "").strip().lower()
        return any(role == r.strip().lower() for r in self._metadata.supported_roles)

    def priority(self) -> int:
        return getattr(self._wrapped, "priority", 100)

    def health(self) -> dict:
        return {
            "name": self._metadata.name,
            "available": self._wrapped.is_available(),
            "enabled": self._metadata.enabled,
        }

    def status(self) -> str:
        if not self._metadata.enabled:
            return "disabled"
        return "connected" if self._wrapped.is_available() else "not_connected"

    def configure(self, config: dict) -> None:
        """Generic configuration hook -- Sprint 18 connectors that need
        richer configuration (Greenhouse's API key) already have their
        own dedicated endpoint (POST /integrations/greenhouse/configure);
        this hook only handles the fields the new framework itself
        understands (currently just `enabled`), so it composes with,
        rather than replaces, a connector's own configuration path."""
        if "enabled" in config:
            self._metadata.enabled = bool(config["enabled"])
