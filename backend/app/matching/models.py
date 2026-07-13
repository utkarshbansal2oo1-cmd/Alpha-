"""Pydantic models for the Matching + Ranking Engines -- Sprint 19."""
from __future__ import annotations

from pydantic import BaseModel, Field


class MatchResult(BaseModel):
    """The Matching Engine's scored output for one candidate against one
    requirement. `component_scores` always contains every dimension the
    engine evaluates (see matching/engine.py DIMENSIONS), even ones the
    requirement didn't specify enough to score meaningfully -- those are
    reported at a neutral score and listed in `missing_fields`, never
    silently omitted or fabricated."""

    candidate_id: str
    overall_score: float = Field(ge=0.0, le=100.0)
    component_scores: dict[str, float] = Field(default_factory=dict)
    matched_fields: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class RankedCandidate(BaseModel):
    """One candidate plus its match result, in final ranked order."""

    candidate_id: str
    match: MatchResult
    rank: int = Field(ge=1)
