"""Orchestrates the full search pipeline: query -> requirement -> fetch ->
dedupe -> rank -> persisted-in-memory result set for candidate-detail lookups.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict

from app.schemas import CandidateOut, JobRequirement, SearchResponse
from app.services import query_parser, dedup, matching_engine
from app.services.connectors.registry import get_active_connectors

# In-memory store standing in for Postgres in the MVP.
# candidate_id -> {candidate: RawCandidate, sources: [str]}
CANDIDATE_STORE: Dict[str, dict] = {}
SEARCH_STORE: Dict[str, dict] = {}


def run_search(query: str) -> SearchResponse:
    requirement: JobRequirement = query_parser.parse(query)

    candidates_by_source = {}
    for connector in get_active_connectors():
        candidates_by_source[connector.name] = connector.fetch(requirement)

    merged = dedup.dedupe(candidates_by_source)
    ranked = matching_engine.rank(merged, requirement)

    search_id = str(uuid.uuid4())
    results = []
    for item in ranked:
        candidate = item["candidate"]
        candidate_id = CANDIDATE_STORE.setdefault(
            candidate.external_id, {"id": str(uuid.uuid4())}
        )["id"]
        CANDIDATE_STORE[candidate.external_id] = {
            "id": candidate_id,
            "candidate": candidate,
            "sources": item["sources"],
        }
        results.append(
            CandidateOut(
                candidate_id=candidate_id,
                full_name=candidate.full_name,
                current_title=candidate.current_title,
                current_company=candidate.current_company,
                location=candidate.location,
                total_experience_yrs=candidate.total_experience_yrs,
                match_score=item["match_score"],
                reasoning=item["reasoning"],
                sources=item["sources"],
            )
        )

    SEARCH_STORE[search_id] = {
        "query": query,
        "requirement": requirement,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    return SearchResponse(
        search_id=search_id,
        parsed_requirement=requirement,
        results=results,
        count=len(results),
    )


def get_candidate_detail(candidate_id: str):
    for entry in CANDIDATE_STORE.values():
        if entry["id"] == candidate_id:
            return entry
    return None
