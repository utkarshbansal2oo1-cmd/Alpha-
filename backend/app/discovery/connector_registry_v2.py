"""The Sprint 20A Managed Connector Registry.

Distinct from, and does not replace, Sprint 19's ConnectorRegistry
(app/discovery/connector_registry.py), which the existing Discovery
Orchestrator still uses unmodified. This one manages connectors built
against the new Universal Connector Framework
(app/discovery/connectors/framework.py::Connector) -- richer metadata,
enable/disable, and runtime configuration -- and backs the new
GET/POST /connectors management endpoints.

Populated via `discover_connectors()` (dynamic, no hardcoded list, per
Module 3) rather than a fixed constructor argument, though a caller may
also `register()` additional connectors directly (e.g. in tests).
"""
from __future__ import annotations

from app.discovery.connectors.framework import Connector, discover_connectors


class ManagedConnectorRegistry:
    def __init__(self, connectors: list[Connector] | None = None):
        self._connectors: dict[str, Connector] = {}
        for connector in connectors or []:
            self.register(connector)

    @classmethod
    def with_dynamically_loaded_connectors(cls) -> "ManagedConnectorRegistry":
        return cls(discover_connectors())

    def register(self, connector: Connector) -> None:
        self._connectors[connector.metadata.name] = connector

    def unregister(self, name: str) -> None:
        self._connectors.pop(name, None)

    def get(self, name: str) -> Connector | None:
        return self._connectors.get(name)

    def list(self) -> list[Connector]:
        return sorted(self._connectors.values(), key=lambda c: c.priority())

    def enabled(self) -> list[Connector]:
        return [c for c in self.list() if c.metadata.enabled]

    def disabled(self) -> list[Connector]:
        return [c for c in self.list() if not c.metadata.enabled]

    def health(self) -> dict[str, dict]:
        return {name: connector.health() for name, connector in self._connectors.items()}

    def configure(self, name: str, config: dict) -> Connector:
        connector = self.get(name)
        if connector is None:
            raise KeyError(f"No connector registered with name '{name}'")
        connector.configure(config)
        return connector

    def enable(self, name: str) -> Connector:
        return self.configure(name, {"enabled": True})

    def disable(self, name: str) -> Connector:
        return self.configure(name, {"enabled": False})


# Module-level singleton, same pattern as GreenhouseConfigStore's _store
# (app/integrations/greenhouse/config.py) -- enable/disable/configure
# calls must persist across requests within one running process.
_registry = ManagedConnectorRegistry.with_dynamically_loaded_connectors()


def get_managed_connector_registry() -> ManagedConnectorRegistry:
    """FastAPI dependency-injection provider, same pattern every other
    provider function in this codebase follows."""
    return _registry
