"""Browser extension query translation strategy -- Sprint 20C.

Per the sprint brief: "Return canonical recruiter query only." The
browser extension connector doesn't run a live search at all (see its
module docstring in app/discovery/connectors/future_connectors.py --
captured candidates are already in the repository by the time discovery
runs), so there's nothing to optimize; this exists purely so the
Connector Intelligence Layer has a complete, uniform answer for every
registered connector, and so this connector's entry in the observability
log reads the same way every other connector's does.
"""
from __future__ import annotations

from app.discovery.query_translation.models import ConnectorQuery
from app.search_planner.models import CanonicalJobRequirement, SearchPlan


def translate(
    connector_name: str,
    requirement: CanonicalJobRequirement,
    raw_query: str | None,
    plan: SearchPlan,
    config,
) -> ConnectorQuery:
    canonical = requirement.role
    return ConnectorQuery(
        connector_name=connector_name,
        original_query=raw_query or canonical,
        connector_queries=[canonical],
        filters={},
        metadata={"strategy": "browser_extension", "passthrough": True},
        confidence=1.0,
    )
