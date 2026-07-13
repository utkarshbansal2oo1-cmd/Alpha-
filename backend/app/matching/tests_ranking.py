"""Tests for the Ranking Engine -- Sprint 19."""
from __future__ import annotations

from app.candidate_repository.models import Candidate
from app.matching.models import MatchResult
from app.matching.ranking import RankingEngine


def _candidate(cid, **overrides):
    base = dict(
        id=cid,
        name=f"Candidate {cid}",
        role="Product Manager",
        experience=5.0,
        skills=[],
        location="Mumbai",
        current_company="Acme",
        source="seed_data",
    )
    base.update(overrides)
    return Candidate(**base)


def _match(cid, overall_score, confidence=0.0, health=0.0):
    return MatchResult(
        candidate_id=cid,
        overall_score=overall_score,
        component_scores={"confidence": confidence, "health": health},
        matched_fields=[],
        missing_fields=[],
        reasons=["test"],
    )


def test_every_candidate_is_ranked():
    candidates = [_candidate(str(i)) for i in range(4)]
    matches = [_match(str(i), overall_score=50.0) for i in range(4)]
    ranked = RankingEngine().rank(candidates, matches)
    assert len(ranked) == 4
    assert [r.rank for r in ranked] == [1, 2, 3, 4]


def test_higher_overall_score_ranks_first():
    candidates = [_candidate("low"), _candidate("high")]
    matches = [_match("low", 40.0), _match("high", 90.0)]
    ranked = RankingEngine().rank(candidates, matches)
    assert ranked[0].candidate_id == "high"
    assert ranked[1].candidate_id == "low"


def test_ties_broken_by_confidence_then_health_then_id():
    candidates = [_candidate("b"), _candidate("a")]
    matches = [
        _match("b", overall_score=70.0, confidence=90.0, health=50.0),
        _match("a", overall_score=70.0, confidence=90.0, health=50.0),
    ]
    ranked = RankingEngine().rank(candidates, matches)
    # Same score/confidence/health -- final tie-break is candidate id, alphabetical.
    assert ranked[0].candidate_id == "a"
    assert ranked[1].candidate_id == "b"


def test_rank_candidates_by_id_reorders_original_objects():
    candidates = [_candidate("low"), _candidate("high")]
    matches = [_match("low", 40.0), _match("high", 90.0)]
    engine = RankingEngine()
    ranked = engine.rank(candidates, matches)
    reordered = engine.rank_candidates_by_id(ranked, candidates)
    assert [c.id for c in reordered] == ["high", "low"]
