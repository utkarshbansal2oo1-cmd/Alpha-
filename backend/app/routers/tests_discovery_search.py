"""Tests for POST /api/search/smart -- Sprint 18."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.candidate_repository.import_schemas import CandidateImportRequest
from app.candidate_repository.memory_repository import InMemoryCandidateRepository
from app.candidate_repository.normalizer import normalize_import
from app.candidate_repository.repository import get_candidate_repository
from app.integrations.greenhouse.config import GreenhouseConfigStore, get_greenhouse_config_store
from app.main import app
from app.query_understanding.service import QueryUnderstandingService
from app.routers.discovery_search import get_connector_registry
from app.routers.search_pipeline import get_query_understanding_service
from app.testing.fakes import FakeLLMClient


def _client_with_repo(tmp_path):
    seed = tmp_path / "candidates.json"
    seed.write_text("[]", encoding="utf-8")
    repo = InMemoryCandidateRepository(seed_path=seed)
    config_store = GreenhouseConfigStore()

    app.dependency_overrides[get_candidate_repository] = lambda: repo
    app.dependency_overrides[get_greenhouse_config_store] = lambda: config_store
    return TestClient(app), repo, config_store


def test_smart_search_triggers_discovery_and_reports_unconfigured_connectors(tmp_path):
    client, repo, config_store = _client_with_repo(tmp_path)
    fake_llm = FakeLLMClient(responses=['{"role": "Product Manager", "skills": ["Roadmapping"]}'])
    app.dependency_overrides[get_query_understanding_service] = lambda: QueryUnderstandingService(llm_client=fake_llm)

    try:
        resp = client.post(
            "/api/search/smart",
            json={"query": "Product Manager in Mumbai with 10+ years experience"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["discovery"]["triggered"] is True
        assert body["count"] == 0
        greenhouse_result = next(
            r for r in body["discovery"]["connector_results"] if r["source_name"] == "greenhouse_ats"
        )
        assert greenhouse_result["configured"] is False
        assert greenhouse_result["attempted"] is False
    finally:
        app.dependency_overrides.clear()


def test_smart_search_skips_discovery_when_results_already_sufficient(tmp_path):
    client, repo, config_store = _client_with_repo(tmp_path)

    for i in range(5):
        repo.upsert(
            normalize_import(
                CandidateImportRequest(
                    name=f"Candidate {i}",
                    role="Product Manager",
                    skills=["Roadmapping"],
                    source_type="seed_data",
                )
            )
        )

    fake_llm = FakeLLMClient(responses=['{"role": "Product Manager", "skills": ["Roadmapping"]}'])
    app.dependency_overrides[get_query_understanding_service] = lambda: QueryUnderstandingService(llm_client=fake_llm)

    try:
        resp = client.post("/api/search/smart", json={"query": "Product Manager"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["discovery"]["triggered"] is False
        assert body["count"] == 5
    finally:
        app.dependency_overrides.clear()


def test_smart_search_returns_502_on_query_understanding_failure_same_as_existing_endpoint(tmp_path):
    client, repo, config_store = _client_with_repo(tmp_path)
    # No dependency override for the LLM client -> real GeminiClient with no
    # GEMINI_API_KEY configured in this test process -> LLMClientError,
    # exactly the same failure mode POST /api/search already handles.
    resp = client.post("/api/search/smart", json={"query": "Anything"})
    assert resp.status_code == 502
    app.dependency_overrides.clear()


# --- Sprint 23: end-to-end proof for the "10 discovered/imported but only
# 2 returned" report. A fake connector below stands in for the real
# GitHub connector: it discovers 10 candidates whose normalized `role`
# ("Unknown", exactly what the GitHub normalizer produces) and `skills`
# (GitHub's own repo languages, e.g. "Go") do NOT literally match the
# plan's search terms (built from the recruiter's own wording, e.g.
# "Golang") -- the exact mismatch class that caused the pre-Sprint-20H
# bug (docs/SILENT_FAILURE_AUDIT.md finding #1: a second, literal-match
# `repository.search(plan)` call after discovery silently dropped
# candidates like these). This test exercises the FULL real HTTP path
# (orchestrator -> Matching Engine -> Ranking Engine -> response
# serialization), not just the orchestrator unit tests already covering
# this -- so it also would have caught a regression introduced anywhere
# in matching/ranking/the response builder, not only in the orchestrator.


class _TenCandidateConnector:
    """A connector that discovers exactly 10 candidates, none of whose
    role/skills literally match the recruiter's query wording -- proving
    the full pipeline doesn't silently reduce this to fewer than 10."""

    name = "github"
    priority = 15

    def is_available(self):
        return True

    def discover(self, requirement):
        return [
            CandidateImportRequest(
                name=f"Gopher {i}",
                role="Unknown",  # exactly what the real GitHub normalizer sets
                skills=["Go"],  # GitHub's own language spelling, not "Golang"
                source_type="github",
                public_profile_url=f"https://github.com/gopher{i}",
            )
            for i in range(10)
        ]


class _FakeConnectorRegistry:
    """Duck-typed stand-in for ConnectorRegistry -- DiscoveryOrchestrator
    only ever calls `.get_all()` on whatever `connectors` it's given."""

    def __init__(self, connectors):
        self._connectors = connectors

    def get_all(self):
        return self._connectors


def test_smart_search_returns_all_ten_discovered_candidates_not_a_reduced_subset(tmp_path):
    """The literal regression test for the reported bug: connector
    discovers/imports 10 candidates whose fields don't literally match
    the plan -- the final HTTP response must still contain all 10, in
    ranked order, with `count == 10`."""
    client, repo, config_store = _client_with_repo(tmp_path)
    fake_llm = FakeLLMClient(responses=['{"role": "Senior Golang Developer", "skills": ["Golang"]}'])
    app.dependency_overrides[get_query_understanding_service] = lambda: QueryUnderstandingService(llm_client=fake_llm)
    app.dependency_overrides[get_connector_registry] = lambda: _FakeConnectorRegistry([_TenCandidateConnector()])

    try:
        resp = client.post("/api/search/smart", json={"query": "Senior Golang Developer with Golang"})
        assert resp.status_code == 200
        body = resp.json()

        assert body["discovery"]["triggered"] is True
        github_result = next(r for r in body["discovery"]["connector_results"] if r["source_name"] == "github")
        assert github_result["candidates_found"] == 10
        assert github_result["candidates_imported"] == 10

        # This is the exact assertion that would have failed against the
        # pre-Sprint-20H code (it would have returned 0, since none of
        # these candidates' role="Unknown"/skills=["Go"] literally match
        # the plan's "Senior Golang Developer"/"Golang" search terms).
        assert body["count"] == 10
        assert len(body["candidates"]) == 10
        assert len(body["rankings"]) == 10

        # Ranked order is preserved: `candidates` and `rankings` line up
        # 1:1 by position, and rank numbers are 1..10 with no gaps.
        ranking_ids_in_order = [r["candidate_id"] for r in body["rankings"]]
        candidate_ids_in_order = [c["id"] for c in body["candidates"]]
        assert ranking_ids_in_order == candidate_ids_in_order
        assert [r["rank"] for r in body["rankings"]] == list(range(1, 11))
    finally:
        app.dependency_overrides.clear()
