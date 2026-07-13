"""Tests for the Discovery Orchestrator's Sprint 20C query-translation
integration -- additive behavior only exercised when a query_translator
is supplied. app/discovery/tests_orchestrator.py (Sprint 18/19) already
covers, and continues to pass unchanged, the no-translator path.
"""
from __future__ import annotations

from app.candidate_repository.import_schemas import CandidateImportRequest
from app.candidate_repository.memory_repository import InMemoryCandidateRepository
from app.discovery.decision_engine import DiscoveryDecisionEngine
from app.discovery.orchestrator import DiscoveryOrchestrator
from app.discovery.query_translation.models import ConnectorQuery
from app.search_planner.models import CanonicalJobRequirement, SearchPlan


def _plan(search_terms=None):
    return SearchPlan(strict=[], expanded=[], search_terms=search_terms or [], weights={}, unresolved=[])


def _repo(tmp_path):
    seed = tmp_path / "candidates.json"
    seed.write_text("[]", encoding="utf-8")
    return InMemoryCandidateRepository(seed_path=seed)


class _MultiQueryConnector:
    """Simulates GitHub: returns a different candidate per query string
    it's asked to search for, plus one duplicate to prove cross-query
    dedup runs before import."""

    name = "github"
    priority = 15

    def __init__(self):
        self.discover_calls = []

    def is_available(self):
        return True

    def discover(self, requirement):
        self.discover_calls.append(requirement.role)
        if requirement.role == "golang":
            return [
                CandidateImportRequest(name="Gopher One", public_profile_url="https://github.com/gopher1"),
            ]
        if requirement.role == "backend golang":
            return [
                # Same person as above, found again by a different query.
                CandidateImportRequest(name="Gopher One", public_profile_url="https://github.com/gopher1"),
                CandidateImportRequest(name="Gopher Two", public_profile_url="https://github.com/gopher2"),
            ]
        return []


class _FakeMultiQueryTranslator:
    def translate(self, connector_name, requirement, raw_query, plan):
        return ConnectorQuery(
            connector_name=connector_name,
            original_query=raw_query or requirement.role,
            connector_queries=["golang", "backend golang"],
            metadata={"strategy": "fake", "passthrough": False},
        )


class _PassthroughTranslator:
    def __init__(self):
        self.calls = []

    def translate(self, connector_name, requirement, raw_query, plan):
        self.calls.append(connector_name)
        return ConnectorQuery(
            connector_name=connector_name,
            original_query=raw_query or requirement.role,
            connector_queries=[raw_query or requirement.role],
            metadata={"strategy": "fake_passthrough", "passthrough": True},
        )


def test_query_translator_none_preserves_single_discover_call(tmp_path):
    """Backward-compat guard: omitting query_translator entirely must
    behave exactly like Sprint 18/19 -- one discover() call, no dedup
    logic invoked."""
    repo = _repo(tmp_path)
    connector = _MultiQueryConnector()
    orchestrator = DiscoveryOrchestrator(
        connectors=[connector],
        repository=repo,
        decision_engine=DiscoveryDecisionEngine(min_result_threshold=5, min_confidence_threshold=0),
    )
    requirement = CanonicalJobRequirement(role="Senior Golang Developer", skills=[])
    orchestrator.run(requirement, _plan(), existing_candidates=[])

    assert connector.discover_calls == ["Senior Golang Developer"]


def test_query_translator_runs_one_discover_call_per_translated_query(tmp_path):
    repo = _repo(tmp_path)
    connector = _MultiQueryConnector()
    orchestrator = DiscoveryOrchestrator(
        connectors=[connector],
        repository=repo,
        decision_engine=DiscoveryDecisionEngine(min_result_threshold=5, min_confidence_threshold=0),
    )
    requirement = CanonicalJobRequirement(role="Senior Golang Developer", skills=[])
    run, candidates = orchestrator.run(
        requirement,
        _plan(),
        existing_candidates=[],
        query_translator=_FakeMultiQueryTranslator(),
        raw_query="Senior Golang Developer",
    )

    assert connector.discover_calls == ["golang", "backend golang"]
    # 3 raw results found across both queries, but "Gopher One" was
    # returned twice -- cross-query dedup must collapse it to one before
    # import, so only 2 distinct candidates land in the repository.
    names = {c.name for c in candidates}
    assert names == {"Gopher One", "Gopher Two"}


def test_passthrough_translator_still_makes_exactly_one_discover_call(tmp_path):
    """Greenhouse/browser-extension-style strategies (is_passthrough=True)
    must result in exactly one discover() call against the ORIGINAL
    requirement, never the translated query list."""
    repo = _repo(tmp_path)

    class _SingleCallConnector:
        name = "greenhouse_ats"
        priority = 10

        def __init__(self):
            self.discover_calls = []

        def is_available(self):
            return True

        def discover(self, requirement):
            self.discover_calls.append(requirement)
            return []

    connector = _SingleCallConnector()
    translator = _PassthroughTranslator()
    orchestrator = DiscoveryOrchestrator(
        connectors=[connector],
        repository=repo,
        decision_engine=DiscoveryDecisionEngine(min_result_threshold=5, min_confidence_threshold=0),
    )
    requirement = CanonicalJobRequirement(role="Backend Engineer", skills=["Go"])
    orchestrator.run(
        requirement,
        _plan(),
        existing_candidates=[],
        query_translator=translator,
        raw_query="Backend Engineer with Go",
    )

    assert len(connector.discover_calls) == 1
    assert connector.discover_calls[0] is requirement  # the ORIGINAL object, untouched
    assert translator.calls == ["greenhouse_ats"]
