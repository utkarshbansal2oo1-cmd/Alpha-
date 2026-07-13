"""Greenhouse query translation strategy -- Sprint 20C.

Per the sprint brief: "Return original recruiter query plus canonical
role plus canonical skills. No API changes." Greenhouse's own connector
(app/discovery/connectors/greenhouse_connector.py) already does its own
keyword matching against requirement.role/requirement.skills internally
and is explicitly frozen this sprint -- this strategy does not change
how it's called. `connector_queries` here exists purely for
observability (Module "OBSERVABILITY": logging what a recruiter's search
looked like per-connector) -- the Discovery Orchestrator still calls
discover() with the original, untouched requirement exactly once
(`is_passthrough` is True).
"""
from __future__ import annotations

from app.search_planner.models import CanonicalJobRequirement, SearchPlan
from app.discovery.query_translation.models import ConnectorQuery


def translate(
    connector_name: str,
    requirement: CanonicalJobRequirement,
    raw_query: str | None,
    plan: SearchPlan,
    config,
) -> ConnectorQuery:
    original = raw_query or requirement.role
    queries = [original, requirement.role, *requirement.skills]
    # De-duplicate while preserving order -- a recruiter query that's
    # just the role (no extra skills) shouldn't show the same string twice.
    seen: set[str] = set()
    deduped = []
    for q in queries:
        key = q.strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(q)

    return ConnectorQuery(
        connector_name=connector_name,
        original_query=original,
        connector_queries=deduped,
        filters={},
        metadata={"strategy": "greenhouse", "passthrough": True},
        confidence=1.0,
    )
