"""A requirement-match confidence score for candidates -- Sprint 18.

Used only by the Discovery Decision Engine to judge whether the existing
Candidate Repository result set is good enough. Deliberately separate
from, and not to be confused with:

- app/candidate_intelligence's health_score / section_confidence, which
  measure data quality/provenance, not requirement fit.
- app/services/matching_engine.py's match_score, which belongs to the
  older, separate mock pipeline (POST /api/v1/search) and is untouched.

This is new, additive scoring logic scoped entirely to the Discovery
Engine's own decision-making -- it does not change how
CandidateRepository.search() ranks or returns results (search() remains
unranked, per its own docstring).
"""
from __future__ import annotations

from app.candidate_repository.models import Candidate
from app.search_planner.models import SearchPlan


def match_confidence(candidate: Candidate, plan: SearchPlan) -> float:
    """0-100 heuristic: what fraction of the plan's search terms this
    candidate's role/skills actually satisfy. An unfiltered plan (empty
    search_terms) is treated as full confidence, since every candidate is
    an equally valid match by definition in that case."""
    terms = {t.strip().lower() for t in plan.search_terms if t.strip()}
    if not terms:
        return 100.0

    candidate_terms = {candidate.role.strip().lower()} | {s.strip().lower() for s in candidate.skills}
    matched = terms & candidate_terms
    return round(100.0 * len(matched) / len(terms), 2)


def average_match_confidence(candidates: list[Candidate], plan: SearchPlan) -> float:
    """0 for an empty candidate list -- there is nothing to have
    confidence in, which is exactly the signal that should push the
    Decision Engine toward discovery."""
    if not candidates:
        return 0.0
    scores = [match_confidence(c, plan) for c in candidates]
    return round(sum(scores) / len(scores), 2)
