"""Pydantic models for the Discovery Engine -- Sprint 18.

Kept in their own module (rather than reusing search_planner's or
candidate_intelligence's models) because a discovery decision/run is a
new concept that doesn't belong to either of those frozen modules.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class DiscoveryDecision(BaseModel):
    """Output of the Discovery Decision Engine: whether the candidates
    CandidateRepository.search() already returned are good enough, or
    whether the Discovery Orchestrator should be invoked."""

    should_discover: bool
    reason: str
    candidate_count: int
    average_match_confidence: float = Field(ge=0.0, le=100.0)
    min_result_threshold: int
    min_confidence_threshold: float


class ConnectorRunResult(BaseModel):
    """What one connector did during a single discovery run -- returned
    for transparency, not just internal bookkeeping, so the UI (and any
    future audit trail) can show exactly which connected sources were
    tried and what each one found."""

    source_name: str
    attempted: bool = True
    configured: bool = True
    candidates_found: int = 0
    candidates_imported: int = 0
    candidates_merged: int = 0
    error: str | None = None


class DiscoveryStage(BaseModel):
    """One step of the discovery process, in the order it happened --
    the UI renders this list as the progress sequence the sprint brief
    describes ("Searching internal talent intelligence...", "Searching
    connected ATS...", etc.)."""

    label: str
    detail: str | None = None
    count: int | None = None


class DiscoveryRun(BaseModel):
    """The full record of one discovery attempt, returned alongside the
    (possibly refreshed) search results in a single response so the
    frontend never needs a second round trip to find out what happened."""

    triggered: bool
    decision: DiscoveryDecision
    connector_results: list[ConnectorRunResult] = Field(default_factory=list)
    new_candidates_imported: int = 0
    stages: list[DiscoveryStage] = Field(default_factory=list)
    ran_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
