"""The Universal Connector Framework -- Sprint 20A.

STOP-scope note (per the sprint brief): this builds the *framework* only.
No GitHub connector, and nothing about Sprint 18/19's existing
DiscoveryConnector Protocol (app/discovery/connectors/base.py),
ConnectorRegistry (app/discovery/connector_registry.py), or
DiscoveryOrchestrator is modified -- everything below is new and
additive, living alongside the Sprint 18/19 interface rather than
replacing it. A LegacyConnectorAdapter (legacy_adapter.py) lets every
already-shipped connector (Greenhouse, GitHub, the four Sprint 18 stubs)
show up in this new framework too, so nothing needs to be reimplemented
twice.

The new Connector protocol adds exactly what the sprint brief asks for
on top of Sprint 18/19's `is_available()`/`discover()`:

    discover(requirement)   -- unchanged from Sprint 18
    supports(requirement)   -- can this connector plausibly help with this
                               requirement at all (e.g. role in its
                               supported_roles), independent of whether
                               it's currently *configured*
    priority()              -- a method (not the plain int attribute
                               Sprint 18 connectors expose), so priority
                               can be dynamic (e.g. read from live config)
    health()                -- a structured health snapshot, richer than
                               Sprint 18's plain is_available() bool
    status()                -- "connected" | "not_connected" | "disabled"
    configure(config)       -- push new configuration into the connector
                               at runtime (Module 2's POST
                               /connectors/configure)

Every connector also declares static ConnectorMetadata: name, version,
capabilities, whether it requires authentication, which roles it's known
to help with, and whether it's currently enabled.
"""
from __future__ import annotations

import importlib
import pkgutil
from typing import Protocol

from pydantic import BaseModel, Field

from app.candidate_repository.import_schemas import CandidateImportRequest
from app.search_planner.models import CanonicalJobRequirement


class ConnectorMetadata(BaseModel):
    """Static, declarative facts about one connector -- Module 4."""

    name: str
    version: str = "1.0.0"
    capabilities: list[str] = Field(default_factory=list, description="e.g. ['candidate_search', 'bulk_sync']")
    requires_auth: bool = True
    supported_roles: list[str] = Field(
        default_factory=list, description="Empty list means 'no role restriction, may help with any role'"
    )
    enabled: bool = True


class Connector(Protocol):
    """The Sprint 20A connector interface. A Protocol (structural typing),
    same reasoning as Sprint 18's DiscoveryConnector: no import-time
    coupling required from any connector implementation."""

    @property
    def metadata(self) -> ConnectorMetadata: ...

    def discover(self, requirement: CanonicalJobRequirement) -> list[CandidateImportRequest]: ...

    def supports(self, requirement: CanonicalJobRequirement) -> bool: ...

    def priority(self) -> int: ...

    def health(self) -> dict: ...

    def status(self) -> str: ...

    def configure(self, config: dict) -> None: ...


def discover_connectors() -> list[Connector]:
    """Dynamic connector loading (Module 3: 'no hardcoded connector
    list'). Walks every module in app.discovery.connectors and collects
    every module-level attribute whose name starts with `MANAGED_` and
    ends with `CONNECTOR` (a module may expose one -- `MANAGED_CONNECTOR`
    -- or several, e.g. `MANAGED_CSV_IMPORT_CONNECTOR`). Adding a new
    connector is therefore just adding a new .py file (or a new
    module-level name in an existing one) with that naming convention;
    nothing here or in the registry/router needs to be edited to
    register it by name.

    Skips infrastructure modules (base/framework/legacy_adapter) and any
    test module (tests_*/test_*) living alongside the connectors in this
    same package -- those are not connector implementations and must
    never be imported as one, even though pkgutil.iter_modules sees
    every .py file in the directory indiscriminately.
    """
    import app.discovery.connectors as connectors_pkg

    found: list[Connector] = []
    for module_info in pkgutil.iter_modules(connectors_pkg.__path__):
        if module_info.name in ("base", "framework", "legacy_adapter"):
            continue  # infrastructure modules, not connector modules
        if module_info.name.startswith("tests_") or module_info.name.startswith("test_"):
            continue  # test modules, not connector modules
        module = importlib.import_module(f"app.discovery.connectors.{module_info.name}")
        for attr_name in dir(module):
            if not attr_name.startswith("MANAGED_") or not attr_name.endswith("CONNECTOR"):
                continue
            candidate = getattr(module, attr_name)
            if candidate is not None and candidate not in found:
                found.append(candidate)
    return found
