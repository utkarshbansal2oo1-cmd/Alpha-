"""Fallback strategy -- Sprint 20C.

Used for any connector with no dedicated strategy registered. Returns
the original recruiter search completely unchanged, as a single
passthrough query -- exactly today's Sprint 18/19/20B behavior for that
connector, so adding this layer never regresses a connector nobody has
written a translation strategy for yet.
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
    original = raw_query or requirement.role
    return ConnectorQuery(
        connector_name=connector_name,
        original_query=original,
        connector_queries=[original],
        filters={},
        metadata={"strategy": "generic", "passthrough": True},
        confidence=1.0,
    )
