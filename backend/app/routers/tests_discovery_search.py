"""Tests for POST /api/search/smart -- Sprint 18, pagination via persistent
search sessions added Sprint 33."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.candidate_repository.import_schemas import CandidateImportRequest
from app.candidate_repository.memory_repository import InMemoryCandidateRepository
from app.candidate_repository.normalizer import normalize_import
from app.candidate_repository.repository import get_candidate_repository
from app.database import Base
from app.integrations.greenhouse.config import GreenhouseConfigStore, get_greenhouse_config_store
from app.main import app
from app.query_understanding.service import QueryUnderstandingService
from app.routers.discovery_search import get_connector_registry, get_search_session_store
from app.routers.search_pipeline import get_query_understanding_service
from app.search_sessions.store import SearchSessionStore
from app.testing.fakes import FakeLLMClient


def _client_with_repo(tmp_path):
    seed = tmp_path / "candidates.json"
    seed.write_text("[]", encoding="utf-8")
    repo = InMemoryCandidateRepository(seed_path=seed)
    config_store = GreenhouseConfigStore()

    # Sprint 33: POST /api/search/smart now persists a SearchSession via
    # SearchSessionStore, which by default talks to the real (production)
    # DATABASE_URL -- overridden here with an in-memory SQLite-backed
    # store, same pattern as app/auth/tests_service.py and
    # app/credentials/tests_service.py, so these tests never need a real
    # Postgres instance.
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_store = SearchSessionStore(session_factory=sessionmaker(bind=engine))

    app.dependency_overrides[get_candidate_repository] = lambda: repo
    app.dependency_overrides[get_greenhouse_config_store] = lambda: config_store
    app.dependency_overrides[get_search_session_store] = lambda: session_store
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
        assert "session_id" in body and body["session_id"]
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
        assert body["total_count"] == 5
    finally:
        app.dependency_overrides.clear()


def test_smart_search_returns_502_on_query_understanding_failure_same_as_existing_endpoint(tmp_path):
    client, repo, config_store = _client_with_repo(tmp_path)
    resp = client.post("/api/search/smart", json={"query": "Anything"})
    assert resp.status_code == 502
    app.dependency_overrides.clear()


class _TenCandidateConnector:
    name = "github"
    priority = 15

    def is_available(self):
        return True

    def discover(self, requirement):
        return [
            CandidateImportRequest(
                name=f"Gopher {i}",
                role="Unknown",
                skills=["Go"],
                source_type="github",
                public_profile_url=f"https://github.com/gopher{i}",
            )
            for i in range(10)
        ]


class _FakeConnectorRegistry:
    def __init__(self, connectors):
        self._connectors = connectors

    def get_all(self):
        return self._connectors


def test_smart_search_returns_all_ten_discovered_candidates_not_a_reduced_subset(tmp_path):
    client, repo, config_store = _client_with_repo(tmp_path)
    fake_llm = FakeLLMClient(responses=['{"role": "Senior Golang Developer", "skills": ["Golang"]}'])
    app.dependency_overrides[get_query_understanding_service] = lambda: QueryUnderstandingService(llm_client=fake_llm)
    app.dependency_overrides[get_connector_registry] = lambda: _FakeConnectorRegistry([_TenCandidateConnector()])

    try:
        # Sprint 35 Phase 2: role="Unknown"/skills=["Go"] vs a "Senior
        # Golang Developer"/"Golang" requirement score BELOW the adaptive
        # relevance threshold (no exact role/skill token overlap), so by
        # default these would be hidden as weak matches. This test's own
        # concern -- discovery not silently truncating the raw pool -- is
        # orthogonal to that visibility feature, so include_weak_matches
        # isolates it (same list of 10 candidates either way).
        resp = client.post(
            "/api/search/smart",
            json={"query": "Senior Golang Developer with Golang", "include_weak_matches": True},
        )
        assert resp.status_code == 200
        body = resp.json()

        assert body["discovery"]["triggered"] is True
        github_result = next(r for r in body["discovery"]["connector_results"] if r["source_name"] == "github")
        assert github_result["candidates_found"] == 10
        assert github_result["candidates_imported"] == 10

        assert body["count"] == 10
        assert len(body["candidates"]) == 10
        assert len(body["rankings"]) == 10

        ranking_ids_in_order = [r["candidate_id"] for r in body["rankings"]]
        candidate_ids_in_order = [c["id"] for c in body["candidates"]]
        assert ranking_ids_in_order == candidate_ids_in_order
        assert [r["rank"] for r in body["rankings"]] == list(range(1, 11))
    finally:
        app.dependency_overrides.clear()


# --- Sprint 33: persistent search sessions + pagination ---------------------


def _seed_candidates(repo, count):
    for i in range(count):
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


def test_smart_search_creates_session_and_returns_page_1_default_size_20(tmp_path):
    client, repo, config_store = _client_with_repo(tmp_path)
    _seed_candidates(repo, 25)
    fake_llm = FakeLLMClient(responses=['{"role": "Product Manager", "skills": ["Roadmapping"]}'])
    app.dependency_overrides[get_query_understanding_service] = lambda: QueryUnderstandingService(llm_client=fake_llm)

    try:
        resp = client.post("/api/search/smart", json={"query": "Product Manager"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 1
        assert body["page_size"] == 20
        assert body["count"] == 20
        assert body["total_count"] == 25
        assert body["total_pages"] == 2
        assert body["has_next"] is True
        assert body["has_previous"] is False
        assert len(body["candidates"]) == 20
        assert len(body["rankings"]) == 20
    finally:
        app.dependency_overrides.clear()


def test_get_session_page_2_does_not_repeat_the_pipeline(tmp_path, monkeypatch):
    client, repo, config_store = _client_with_repo(tmp_path)
    _seed_candidates(repo, 25)
    fake_llm = FakeLLMClient(responses=['{"role": "Product Manager", "skills": ["Roadmapping"]}'])
    app.dependency_overrides[get_query_understanding_service] = lambda: QueryUnderstandingService(llm_client=fake_llm)

    try:
        page1 = client.post("/api/search/smart", json={"query": "Product Manager"}).json()
        session_id = page1["session_id"]

        # The FakeLLMClient was only given ONE scripted response above --
        # if GET /api/search/session/{id} re-ran Query Understanding, this
        # would raise (no more responses left) instead of returning 200.
        resp = client.get(f"/api/search/session/{session_id}", params={"page": 2, "page_size": 20})
        assert resp.status_code == 200
        page2 = resp.json()

        assert page2["session_id"] == session_id
        assert page2["page"] == 2
        assert len(page2["candidates"]) == 5  # remainder: 25 - 20
        assert page2["total_count"] == 25
        assert page2["has_next"] is False
        assert page2["has_previous"] is True

        page1_ids = {c["id"] for c in page1["candidates"]}
        page2_ids = {c["id"] for c in page2["candidates"]}
        assert page1_ids.isdisjoint(page2_ids)
        assert [r["rank"] for r in page2["rankings"]] == list(range(21, 26))

        # Same requirement/search_plan/discovery echoed from storage, not
        # recomputed.
        assert page2["requirement"] == page1["requirement"]
        assert page2["search_plan"] == page1["search_plan"]
    finally:
        app.dependency_overrides.clear()


def test_get_session_unknown_id_returns_404(tmp_path):
    client, repo, config_store = _client_with_repo(tmp_path)
    resp = client.get("/api/search/session/does-not-exist")
    assert resp.status_code == 404


def test_a_second_post_is_a_new_independent_search_session(tmp_path):
    client, repo, config_store = _client_with_repo(tmp_path)
    _seed_candidates(repo, 3)
    fake_llm = FakeLLMClient(
        responses=[
            '{"role": "Product Manager", "skills": ["Roadmapping"]}',
            '{"role": "Product Manager", "skills": ["Roadmapping"]}',
        ]
    )
    app.dependency_overrides[get_query_understanding_service] = lambda: QueryUnderstandingService(llm_client=fake_llm)

    try:
        first = client.post("/api/search/smart", json={"query": "Product Manager"}).json()
        second = client.post("/api/search/smart", json={"query": "Product Manager"}).json()

        assert first["session_id"] != second["session_id"]
        # Both sessions independently persisted and independently pageable.
        assert client.get(f"/api/search/session/{first['session_id']}").status_code == 200
        assert client.get(f"/api/search/session/{second['session_id']}").status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_smart_search_page_beyond_last_returns_empty_not_error(tmp_path):
    client, repo, config_store = _client_with_repo(tmp_path)
    fake_llm = FakeLLMClient(responses=['{"role": "Product Manager", "skills": ["Roadmapping"]}'])
    app.dependency_overrides[get_query_understanding_service] = lambda: QueryUnderstandingService(llm_client=fake_llm)

    try:
        resp = client.post("/api/search/smart", json={"query": "Product Manager", "page": 99, "page_size": 10})
        assert resp.status_code == 200
        body = resp.json()
        assert body["candidates"] == []
        assert body["count"] == 0
        assert body["total_count"] == 0
    finally:
        app.dependency_overrides.clear()


def test_no_duplicate_candidate_within_one_session(tmp_path):
    client, repo, config_store = _client_with_repo(tmp_path)
    _seed_candidates(repo, 10)
    fake_llm = FakeLLMClient(responses=['{"role": "Product Manager", "skills": ["Roadmapping"]}'])
    app.dependency_overrides[get_query_understanding_service] = lambda: QueryUnderstandingService(llm_client=fake_llm)

    try:
        resp = client.post("/api/search/smart", json={"query": "Product Manager", "page_size": 50})
        body = resp.json()
        ids = [c["id"] for c in body["candidates"]]
        assert len(ids) == len(set(ids))
    finally:
        app.dependency_overrides.clear()


# --- Sprint 35 Phase 1 (seed-as-fallback) + Phase 2 (relevance threshold) ---


class _WeakMatchConnector:
    """Live candidates whose role/skills share nothing with the
    requirement -- guaranteed poor matches, so Phase 1's "are there
    enough GOOD live candidates" check reads zero regardless of the
    configured threshold."""

    name = "github"
    priority = 15

    def is_available(self):
        return True

    def discover(self, requirement):
        return [
            CandidateImportRequest(
                name=f"Unrelated Dev {i}",
                role="Totally Unrelated Field",
                skills=["Basket Weaving"],
                source_type="github",
                public_profile_url=f"https://github.com/unrelated{i}",
            )
            for i in range(2)
        ]


def test_seed_fallback_used_when_live_candidates_are_weak(tmp_path):
    client, repo, config_store = _client_with_repo(tmp_path)
    _seed_candidates(repo, 5)  # role="Product Manager", skills=["Roadmapping"] -- strong seed matches
    fake_llm = FakeLLMClient(responses=['{"role": "Product Manager", "skills": ["Roadmapping"]}'])
    app.dependency_overrides[get_query_understanding_service] = lambda: QueryUnderstandingService(llm_client=fake_llm)
    app.dependency_overrides[get_connector_registry] = lambda: _FakeConnectorRegistry([_WeakMatchConnector()])

    try:
        resp = client.post("/api/search/smart", json={"query": "Product Manager"})
        assert resp.status_code == 200
        body = resp.json()

        # Live discovery alone (2 weak matches) isn't enough -- seed data
        # must have been appended as a fallback.
        assert body["seed_fallback_used"] is True
        sources = {c["source"] for c in body["candidates"]}
        assert "seed_data" in sources
        assert body["total_count"] >= 5  # at least the 5 seed candidates present
    finally:
        app.dependency_overrides.clear()


class _TenStrongMatchConnector:
    """Unlike _TenCandidateConnector (role="Unknown"), these candidates'
    role/skills are an EXACT match for the requirement below -- genuinely
    strong live matches, guaranteed to clear the relevance threshold."""

    name = "github"
    priority = 15

    def is_available(self):
        return True

    def discover(self, requirement):
        return [
            CandidateImportRequest(
                name=f"Golang Expert {i}",
                role="Senior Golang Developer",
                skills=["Golang"],
                source_type="github",
                public_profile_url=f"https://github.com/golangexpert{i}",
            )
            for i in range(10)
        ]


def test_seed_not_used_when_live_candidates_are_already_strong(tmp_path):
    client, repo, config_store = _client_with_repo(tmp_path)
    _seed_candidates(repo, 5)  # present, but should never surface below
    fake_llm = FakeLLMClient(responses=['{"role": "Senior Golang Developer", "skills": ["Golang"]}'])
    app.dependency_overrides[get_query_understanding_service] = lambda: QueryUnderstandingService(llm_client=fake_llm)
    app.dependency_overrides[get_connector_registry] = lambda: _FakeConnectorRegistry([_TenStrongMatchConnector()])

    try:
        resp = client.post("/api/search/smart", json={"query": "Senior Golang Developer with Golang"})
        assert resp.status_code == 200
        body = resp.json()

        # 10 strong live (github) matches easily clear min_candidate_threshold
        # -- seed data (unrelated "Product Manager" profiles) must NOT be
        # appended just because it exists.
        assert body["seed_fallback_used"] is False
        sources = {c["source"] for c in body["candidates"]}
        assert "seed_data" not in sources
        assert body["count"] == 10
    finally:
        app.dependency_overrides.clear()


# --- Sprint 36: Source Groups (presentation-layer grouping) ----------------


def test_source_groups_fallback_group_always_ordered_last(tmp_path):
    client, repo, config_store = _client_with_repo(tmp_path)
    # Deliberately few (2, not 5) so the initial repository.search() result
    # is NOT "already sufficient" per the Decision Engine -- discovery must
    # actually trigger and call the weak github connector, so both a
    # "github" group and a "seed_data" fallback group genuinely exist to
    # order.
    _seed_candidates(repo, 2)
    fake_llm = FakeLLMClient(responses=['{"role": "Product Manager", "skills": ["Roadmapping"]}'])
    app.dependency_overrides[get_query_understanding_service] = lambda: QueryUnderstandingService(llm_client=fake_llm)
    app.dependency_overrides[get_connector_registry] = lambda: _FakeConnectorRegistry([_WeakMatchConnector()])

    try:
        resp = client.post("/api/search/smart", json={"query": "Product Manager", "include_weak_matches": True})
        assert resp.status_code == 200
        body = resp.json()
        assert body["seed_fallback_used"] is True

        sources_in_order = [g["source"] for g in body["source_groups"]]
        assert sources_in_order[-1] == "seed_data"
        assert "github" in sources_in_order
        # Fallback group correctly marked, and never labeled "seed" to the recruiter.
        seed_group = next(g for g in body["source_groups"] if g["source"] == "seed_data")
        assert seed_group["is_fallback"] is True
        assert "seed" not in seed_group["display_name"].lower()
        assert seed_group["display_name"] == "Suggested Profiles"
    finally:
        app.dependency_overrides.clear()


def test_source_groups_preserve_global_rank_and_partition_candidates(tmp_path):
    client, repo, config_store = _client_with_repo(tmp_path)
    _seed_candidates(repo, 5)
    fake_llm = FakeLLMClient(responses=['{"role": "Senior Golang Developer", "skills": ["Golang"]}'])
    app.dependency_overrides[get_query_understanding_service] = lambda: QueryUnderstandingService(llm_client=fake_llm)
    app.dependency_overrides[get_connector_registry] = lambda: _FakeConnectorRegistry([_TenStrongMatchConnector()])

    try:
        resp = client.post("/api/search/smart", json={"query": "Senior Golang Developer with Golang"})
        assert resp.status_code == 200
        body = resp.json()

        # No seed fallback here (strong live matches) -- only one group.
        assert len(body["source_groups"]) == 1
        github_group = body["source_groups"][0]
        assert github_group["source"] == "github"
        assert github_group["candidate_count"] == 10
        assert github_group["is_fallback"] is False

        # Every RankedCandidate inside the group keeps its real GLOBAL rank
        # -- the same rank numbers that appear in the flat top-level
        # `rankings` list, not a re-numbered 1..N within the group.
        flat_ranks_by_id = {r["candidate_id"]: r["rank"] for r in body["rankings"]}
        for ranking in github_group["rankings"]:
            assert ranking["rank"] == flat_ranks_by_id[ranking["candidate_id"]]

        # Every candidate in the group has full provenance.
        assert len(github_group["provenance"]) == 10
        for prov in github_group["provenance"]:
            assert prov["source"] == "github"
            assert prov["discovery_method"]
    finally:
        app.dependency_overrides.clear()


def test_source_filter_restricts_results_to_one_source_group(tmp_path):
    client, repo, config_store = _client_with_repo(tmp_path)
    _seed_candidates(repo, 5)
    fake_llm = FakeLLMClient(responses=['{"role": "Product Manager", "skills": ["Roadmapping"]}'])
    app.dependency_overrides[get_query_understanding_service] = lambda: QueryUnderstandingService(llm_client=fake_llm)
    app.dependency_overrides[get_connector_registry] = lambda: _FakeConnectorRegistry([_WeakMatchConnector()])

    try:
        resp = client.post(
            "/api/search/smart",
            json={"query": "Product Manager", "include_weak_matches": True, "source_filter": "seed_data"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 5
        assert all(c["source"] == "seed_data" for c in body["candidates"])
        assert len(body["source_groups"]) == 1
        assert body["source_groups"][0]["source"] == "seed_data"
    finally:
        app.dependency_overrides.clear()


def test_get_session_page_source_query_param_filters_and_rebuilds_groups(tmp_path):
    client, repo, config_store = _client_with_repo(tmp_path)
    _seed_candidates(repo, 2)  # few enough that discovery still triggers -- see comment above
    fake_llm = FakeLLMClient(responses=['{"role": "Product Manager", "skills": ["Roadmapping"]}'])
    app.dependency_overrides[get_query_understanding_service] = lambda: QueryUnderstandingService(llm_client=fake_llm)
    app.dependency_overrides[get_connector_registry] = lambda: _FakeConnectorRegistry([_WeakMatchConnector()])

    try:
        first = client.post(
            "/api/search/smart", json={"query": "Product Manager", "include_weak_matches": True}
        ).json()
        session_id = first["session_id"]

        resp = client.get(
            f"/api/search/session/{session_id}",
            params={"include_weak_matches": True, "source": "github"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert all(c["source"] == "github" for c in body["candidates"])
        assert len(body["source_groups"]) == 1
        assert body["source_groups"][0]["source"] == "github"
    finally:
        app.dependency_overrides.clear()


def test_smart_search_response_includes_relevance_threshold_fields(tmp_path):
    client, repo, config_store = _client_with_repo(tmp_path)
    _seed_candidates(repo, 3)
    fake_llm = FakeLLMClient(responses=['{"role": "Product Manager", "skills": ["Roadmapping"]}'])
    app.dependency_overrides[get_query_understanding_service] = lambda: QueryUnderstandingService(llm_client=fake_llm)

    try:
        resp = client.post("/api/search/smart", json={"query": "Product Manager"})
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["relevance_threshold"], (int, float))
        assert "total_all_candidates" in body
        assert "weak_match_count" in body
        assert body["include_weak_matches"] is False
    finally:
        app.dependency_overrides.clear()
