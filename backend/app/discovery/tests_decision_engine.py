"""Tests for the Discovery Decision Engine -- Sprint 18."""
from __future__ import annotations

from app.candidate_repository.models import Candidate
from app.discovery.decision_engine import DiscoveryDecisionEngine
from app.search_planner.models import SearchPlan


def _plan(search_terms: list[str]) -> SearchPlan:
    return SearchPlan(strict=[], expanded=[], search_terms=search_terms, weights={}, unresolved=[])


def _candidate(role: str = "Product Engineer", skills: list[str] | None = None) -> Candidate:
    return Candidate(
        id="c1",
        name="X",
        role=role,
        experience=1,
        skills=skills or [],
        location="Bangalore",
        current_company="Acme",
        source="seed_data",
    )


def test_triggers_discovery_when_too_few_candidates():
    engine = DiscoveryDecisionEngine(min_result_threshold=5, min_confidence_threshold=0)
    decision = engine.evaluate([_candidate()] * 2, _plan(["Product Engineer"]))
    assert decision.should_discover is True
    assert decision.candidate_count == 2
    assert "only 2 candidate(s)" in decision.reason


def test_triggers_discovery_when_confidence_too_low():
    engine = DiscoveryDecisionEngine(min_result_threshold=1, min_confidence_threshold=70)
    candidates = [_candidate(role="Backend Engineer", skills=["Python"]) for _ in range(5)]
    decision = engine.evaluate(candidates, _plan(["Cybersecurity"]))
    assert decision.should_discover is True
    assert decision.average_match_confidence == 0.0


def test_does_not_trigger_discovery_when_sufficient():
    engine = DiscoveryDecisionEngine(min_result_threshold=1, min_confidence_threshold=50)
    candidates = [_candidate(role="Product Engineer", skills=["AWS"])]
    decision = engine.evaluate(candidates, _plan(["Product Engineer"]))
    assert decision.should_discover is False
    assert decision.average_match_confidence == 100.0


def test_empty_search_terms_means_full_confidence():
    engine = DiscoveryDecisionEngine(min_result_threshold=1, min_confidence_threshold=50)
    decision = engine.evaluate([_candidate()], _plan([]))
    assert decision.average_match_confidence == 100.0


def test_empty_candidate_list_has_zero_confidence():
    engine = DiscoveryDecisionEngine(min_result_threshold=1, min_confidence_threshold=0)
    decision = engine.evaluate([], _plan(["Anything"]))
    assert decision.average_match_confidence == 0.0
    assert decision.should_discover is True
