"""Tests for the Matching Engine -- Sprint 19."""
from __future__ import annotations

from app.candidate_repository.models import Candidate
from app.matching.config import MatchingConfig
from app.matching.engine import MatchingEngine
from app.search_planner.models import CanonicalJobRequirement, SearchPlan


def _plan(search_terms=None, weights=None):
    return SearchPlan(
        strict=[], expanded=[], search_terms=search_terms or [], weights=weights or {}, unresolved=[]
    )


def _candidate(**overrides):
    base = dict(
        id="c1",
        name="Test Candidate",
        role="Product Manager",
        experience=8.0,
        skills=["Roadmapping"],
        location="Mumbai",
        current_company="Acme",
        source="seed_data",
    )
    base.update(overrides)
    return Candidate(**base)


def test_every_candidate_is_scored_no_shortcut():
    engine = MatchingEngine()
    requirement = CanonicalJobRequirement(role="Product Manager", skills=["Roadmapping"])
    plan = _plan(["Product Manager", "Roadmapping"])
    candidates = [_candidate(id=str(i)) for i in range(5)]
    results = engine.score_all(candidates, requirement, plan)
    assert len(results) == 5
    assert all(r.overall_score >= 0 for r in results)


def test_exact_role_and_skill_match_scores_high():
    engine = MatchingEngine()
    requirement = CanonicalJobRequirement(role="Product Manager", skills=["Roadmapping"])
    plan = _plan(["Product Manager", "Roadmapping"])
    result = engine.score(_candidate(), requirement, plan)
    assert result.component_scores["role"] == 100.0
    assert result.component_scores["skills"] == 100.0
    assert "role" in result.matched_fields
    assert result.overall_score > 90


def test_unscorable_dimensions_are_neutral_and_reported_missing_not_penalizing():
    engine = MatchingEngine()
    requirement = CanonicalJobRequirement(role="Product Manager", skills=["Roadmapping"])
    plan = _plan(["Product Manager", "Roadmapping"])
    result = engine.score(_candidate(), requirement, plan)
    for dim in ["industry", "education", "certifications", "company_preference"]:
        assert result.component_scores[dim] == 50.0
        assert dim in result.missing_fields
    # A candidate with a perfect role/skill match and no other signal
    # should not be dragged down toward 50 by dimensions with no data --
    # only applicable dimensions move the overall score.
    assert result.overall_score > 90


def test_experience_heuristic_scales_below_requirement():
    engine = MatchingEngine()
    requirement = CanonicalJobRequirement(role="Product Manager", skills=[])
    plan = _plan([])
    junior = _candidate(experience=5.0)
    result = engine.score(junior, requirement, plan, raw_query="Product Manager with 10+ years experience")
    assert result.component_scores["experience"] == 50.0  # 5/10 * 100


def test_experience_heuristic_full_score_when_met():
    engine = MatchingEngine()
    requirement = CanonicalJobRequirement(role="Product Manager", skills=[])
    plan = _plan([])
    senior = _candidate(experience=12.0)
    result = engine.score(senior, requirement, plan, raw_query="Product Manager with 10+ years experience")
    assert result.component_scores["experience"] == 100.0
    assert "experience" in result.matched_fields


def test_location_heuristic_matches_substring_in_raw_query():
    engine = MatchingEngine()
    requirement = CanonicalJobRequirement(role="Product Manager", skills=[])
    plan = _plan([])
    result = engine.score(
        _candidate(location="Mumbai"), requirement, plan, raw_query="Product Manager in Mumbai"
    )
    assert result.component_scores["location"] == 100.0
    assert "location" in result.matched_fields


def test_location_mismatch_is_applicable_and_pulls_score_down():
    # This-sprint fix: previously a location MISMATCH was marked
    # inapplicable (excluded from the overall average entirely), which is
    # exactly what let an off-location candidate rank as if location had
    # never been asked about at all. It must now count against the
    # overall score, not vanish from it.
    engine = MatchingEngine()
    requirement = CanonicalJobRequirement(role="Product Manager", skills=[])
    plan = _plan([])
    result = engine.score(
        _candidate(location="Toluca, Mexico"),
        requirement,
        plan,
        raw_query="Product Manager with 5+ years in bengaluru",
    )
    assert result.component_scores["location"] == 10.0
    assert "location" not in result.matched_fields
    assert "location" not in result.missing_fields


def test_location_dimension_stays_neutral_when_query_names_no_location():
    # No location language in the query at all -- must NOT penalize any
    # candidate just because their location field doesn't happen to
    # appear in the query text.
    engine = MatchingEngine()
    requirement = CanonicalJobRequirement(role="Product Manager", skills=[])
    plan = _plan([])
    result = engine.score(
        _candidate(location="Toluca, Mexico"),
        requirement,
        plan,
        raw_query="Product Manager with 5+ years experience",
    )
    assert result.component_scores["location"] == 50.0
    assert "location" in result.missing_fields


def test_weights_from_config_change_overall_score():
    requirement = CanonicalJobRequirement(role="Product Manager", skills=["Roadmapping"])
    plan = _plan(["Product Manager", "Roadmapping"])
    candidate = _candidate(skills=[])  # role matches, skills does not

    default_engine = MatchingEngine()
    default_result = default_engine.score(candidate, requirement, plan)

    config = MatchingConfig(ranking_weights={"role": 10.0, "skills": 0.1})
    weighted_engine = MatchingEngine(config=config)
    weighted_result = weighted_engine.score(candidate, requirement, plan)

    # Heavily weighting role (which matches) over skills (which doesn't)
    # should push the overall score up compared to equal weighting.
    assert weighted_result.overall_score > default_result.overall_score
