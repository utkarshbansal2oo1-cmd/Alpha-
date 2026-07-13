"""The Connector Registry -- Sprint 19 (Module 6).

Dynamic registration/lookup for Discovery Connectors, replacing the
previously hardcoded connector list built inline in
app/routers/discovery_search.py. Every connector still only needs to
satisfy the DiscoveryConnector Protocol (app/discovery/connectors/base.py)
-- the registry adds no new coupling, it's purely a lookup/ordering layer
on top of that same interface. Connector priority can be overridden per
deployment via MatchingConfig.connector_priority without touching a
connector's own code.
"""
from __future__ import annotations

from app.discovery.connectors.base import DiscoveryConnector
from app.matching.config import MatchingConfig


class ConnectorRegistry:
    def __init__(self, config: MatchingConfig | None = None):
        self._config = config or MatchingConfig()
        self._connectors: dict[str, DiscoveryConnector] = {}

    def register(self, connector: DiscoveryConnector) -> None:
        self._connectors[connector.name] = connector

    def unregister(self, name: str) -> None:
        self._connectors.pop(name, None)

    def get(self, name: str) -> DiscoveryConnector | None:
        return self._connectors.get(name)

    def get_all(self) -> list[DiscoveryConnector]:
        """Every registered connector, in priority order (config override
        takes precedence over the connector's own declared priority)."""
        return sorted(
            self._connectors.values(),
            key=lambda c: self._config.priority_for(c.name, c.priority),
        )

    def get_available(self) -> list[DiscoveryConnector]:
        return [c for c in self.get_all() if c.is_available()]

    def status(self) -> list[dict]:
        """A health/status snapshot per registered connector -- Module 6's
        `health()`/`status()` requirement, surfaced here rather than
        requiring every connector implementation to expose it, since
        availability is already the one signal every connector must
        report via is_available()."""
        return [
            {
                "name": c.name,
                "priority": self._config.priority_for(c.name, c.priority),
                "available": c.is_available(),
                "status": "connected" if c.is_available() else "not_connected",
            }
            for c in self.get_all()
        ]
