"""Tests for the Sprint 14 Candidate Intelligence Lifecycle: the Health
Engine, Enrichment Planner + registry, Confidence Engine, Evidence
Timeline diffing, Profile Versioning, the lifecycle orchestrator, and the
four new read endpoints via TestClient.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.candidate_intelligence.confidence_engine import initial_confidence, update_confidence
from app.candidate_intelligence.enrichment_planner import plan_enrichment
from app.candidate_intelligence.enrichment_registry import EnrichmentSourceRegistry
from app.candidate_intelligence.evidence_timeline import diff_fields
from app.candidate_intelligence.health_engine import compute_health
from app.candidate_intelligence.lifecycle import apply_lifecycle
from app.candidate_intelligence.versioning import build_snapshot
from app.candidate_repository.memory_repository import InMemoryCandidateRepository
from app.candidate_repository.models import Candidate
from app.candidate_repository.repository import get_candidate_repository
from app.main import app

_SPARSE_CANDIDATE = Candidate(
    id="c1",
    name="Asha Rao",
    role="Product Engineer",
    experience=8.5,
    skills=["AWS"],
    location="Bangalore",
    current_company="Acme Cloud",
    source="seed_data",
)


def _fully_filled_candidate() -> Candidate:
    from app.candidate_repository.models import EducationEntry

    return Candidate(
        id="c2",
        name="Rahul Mehta",
        role="Staff Engineer",
        experience=10,
        skills=["AWS", "Kubernetes"],
        location="Bangalore",
        current_company="Acme Cloud",
        source="seed_data",
        headline="Staff Engineer @ Acme",
        summary="Experienced backend engineer.",
        education=[EducationEntry(degree="B.Tech", institution="IIT", year="2012")],
        public_profile_url="https://example.com/in/rahul",
        resume_link="https://example.com/resume/rahul.pdf",
    )


# --- Health Engine -------------------------------------------------------------


def test_health_engine_flags_missing_sections():
    health = compute_health(_SPARSE_CANDIDATE)
    missing_sections = {s.section for s in health.sections if not s.complete}
    assert "education" in missing_sections
    assert "contact" in missing_sections
    assert "summary" in missing_sections
    assert "identity" not in missing_sections


def test_health_engine_full_profile_scores_higher_than_sparse():
    sparse_health = compute_health(_SPARSE_CANDIDATE)
    full_health = compute_health(_fully_filled_candidate())
    assert full_health.overall > sparse_health.overall


def test_health_engine_score_bounded_0_to_100():
    health = compute_health(_fully_filled_candidate())
    assert 0.0 <= health.overall <= 100.0


def test_health_engine_uses_recorded_section_confidence():
    candidate = _SPARSE_CANDIDATE.model_copy(update={"section_confidence": {"identity": 1.0}})
    health = compute_health(candidate)
    identity_section = next(s for s in health.sections if s.section == "identity")
    assert identity_section.confidence == 1.0


# --- Enrichment Planner + registry ----------------------------------------------


def test_enrichment_planner_lists_missing_fields_with_sources():
    health = compute_health(_SPARSE_CANDIDATE)
    plan = plan_enrichment(_SPARSE_CANDIDATE, health)
    fields = {item.field for item in plan.items}
    assert "summary" in fields
    assert "education" in fields
    for item in plan.items:
        assert item.candidate_source_types  # every default-registered field has a known source


def test_enrichment_planner_empty_for_fully_filled_candidate():
    full = _fully_filled_candidate()
    health = compute_health(full)
    plan = plan_enrichment(full, health)
    assert plan.items == []


def test_enrichment_planner_sorts_by_priority_descending():
    health = compute_health(_SPARSE_CANDIDATE)
    plan = plan_enrichment(_SPARSE_CANDIDATE, health)
    priorities = [item.priority for item in plan.items]
    assert priorities == sorted(priorities, reverse=True)


def test_enrichment_registry_is_pluggable():
    registry = EnrichmentSourceRegistry()
    assert registry.capable_sources_for("name") == []
    registry.register_source("my_new_connector", ["name", "location"])
    assert registry.capable_sources_for("name") == ["my_new_connector"]
    assert registry.capable_sources_for("skills") == []


# --- Confidence Engine -----------------------------------------------------------


def test_confidence_initial_matches_source_confidence():
    assert initial_confidence(0.7) == 0.7
    assert initial_confidence(1.5) == 1.0  # clamped
    assert initial_confidence(-0.2) == 0.0  # clamped


def test_confidence_corroboration_increases():
    updated = update_confidence(0.5, 0.8, agreement=True)
    assert updated > 0.5


def test_confidence_conflict_decreases():
    updated = update_confidence(0.8, 0.9, agreement=False)
    assert updated < 0.8


def test_confidence_stays_within_bounds():
    for _ in range(20):
        c = 0.1
        c = update_confidence(c, 0.99, agreement=True)
    assert c <= 1.0
    c2 = 0.9
    for _ in range(20):
        c2 = update_confidence(c2, 0.99, agreement=False)
    assert c2 >= 0.0


# --- Evidence Timeline (diff_fields) ---------------------------------------------


def test_diff_fields_flags_new_field_as_created():
    events = diff_fields(None, {"name": "New Person"}, "browser_extension", None, 0.7, "test")
    assert len(events) == 1
    event, agreement = events[0]
    assert event.change_type == "created"
    assert agreement is True
    assert event.old_value is None
    assert event.new_value == "New Person"


def test_diff_fields_flags_conflicting_scalar_as_updated_disagreement():
    events = diff_fields(_SPARSE_CANDIDATE, {"role": "Totally Different Role"}, "csv_import", None, 0.6, "test")
    event, agreement = events[0]
    assert event.change_type == "updated"
    assert agreement is False


def test_diff_fields_treats_list_growth_as_agreement():
    events = diff_fields(_SPARSE_CANDIDATE, {"skills": ["AWS", "Kubernetes"]}, "browser_extension", None, 0.7, "test")
    event, agreement = events[0]
    assert event.change_type == "updated"
    assert agreement is True


def test_diff_fields_ignores_unchanged_empty_field():
    events = diff_fields(_SPARSE_CANDIDATE, {"resume_link": None}, "csv_import", None, 0.6, "test")
    assert events == []


def test_diff_fields_never_blanks_a_known_value():
    events = diff_fields(_fully_filled_candidate(), {"summary": None}, "csv_import", None, 0.6, "test")
    assert events == []  # a merge never removes a known value, so nothing to report


# --- Versioning ------------------------------------------------------------------


def test_build_snapshot_captures_current_fields():
    snapshot = build_snapshot(_SPARSE_CANDIDATE, version=1, reason="test")
    assert snapshot.version == 1
    assert snapshot.fields["name"] == "Asha Rao"
    assert snapshot.fields["skills"] == ["AWS"]


def test_snapshot_excludes_lifecycle_bookkeeping_fields():
    snapshot = build_snapshot(_SPARSE_CANDIDATE, version=1, reason="test")
    assert "version_history" not in snapshot.fields
    assert "evidence_history" not in snapshot.fields
    assert "health_score" not in snapshot.fields


# --- Lifecycle orchestrator -------------------------------------------------------


def test_apply_lifecycle_populates_all_four_outputs():
    candidate = _SPARSE_CANDIDATE.model_copy(deep=True)
    apply_lifecycle(
        existing=None,
        merged=candidate,
        incoming_fields={"name": candidate.name, "skills": candidate.skills},
        source_type="seed_data",
        source_url=None,
        confidence=0.9,
        reason="test bootstrap",
    )
    assert candidate.health_score is not None
    assert "identity" in candidate.section_confidence or "skills" in candidate.section_confidence
    assert len(candidate.evidence_history) >= 1
    assert len(candidate.version_history) == 1


# --- Repository integration: get_by_id + lifecycle wiring ------------------------


@pytest.fixture()
def repo(tmp_path):
    seed_file = tmp_path / "candidates.json"
    seed_file.write_text(
        json.dumps(
            [
                {
                    "id": "seed-1",
                    "name": "Test Person",
                    "role": "Engineer",
                    "experience": 5,
                    "skills": ["Python"],
                    "location": "Remote",
                    "current_company": "TestCo",
                    "source": "seed_data",
                }
            ]
        ),
        encoding="utf-8",
    )
    return InMemoryCandidateRepository(seed_path=seed_file)


def test_seed_candidates_get_lifecycle_bootstrap(repo):
    candidate = repo.get_by_id("seed-1")
    assert candidate.health_score is not None
    assert len(candidate.version_history) == 1
    assert len(candidate.evidence_history) >= 1


def test_get_by_id_returns_none_for_unknown_id(repo):
    assert repo.get_by_id("does-not-exist") is None


def test_upsert_new_candidate_gets_lifecycle_applied(repo):
    from app.candidate_repository.models import CaptureSource

    new_candidate = Candidate(
        id="ignored",
        name="Brand New",
        role="Engineer",
        experience=2,
        skills=["Go"],
        location="Delhi",
        current_company="NewCo",
        source="browser_extension",
        capture_sources=[CaptureSource(source_type="browser_extension", confidence=0.7)],
    )
    result = repo.upsert(new_candidate)
    assert result.health_score is not None
    assert len(result.version_history) == 1
    assert len(result.evidence_history) >= 1


# --- Endpoints ---------------------------------------------------------------------


@pytest.fixture()
def client(repo):
    app.dependency_overrides[get_candidate_repository] = lambda: repo
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health_endpoint_returns_score(client):
    response = client.get("/candidate/seed-1/health")
    assert response.status_code == 200
    body = response.json()
    assert "overall" in body
    assert "sections" in body


def test_health_endpoint_404_for_unknown_candidate(client):
    response = client.get("/candidate/nope/health")
    assert response.status_code == 404


def test_enrichment_plan_endpoint(client):
    response = client.get("/candidate/seed-1/enrichment-plan")
    assert response.status_code == 200
    body = response.json()
    assert body["candidate_id"] == "seed-1"
    assert isinstance(body["items"], list)


def test_evidence_timeline_endpoint(client):
    response = client.get("/candidate/seed-1/evidence-timeline")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_versions_endpoint(client):
    response = client.get("/candidate/seed-1/versions")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["version"] == 1


def test_intelligence_endpoints_dont_affect_existing_search_route(client):
    response = client.post(
        "/api/v1/search",
        json={"query": "Find Product Engineers with 7+ years in Bangalore, skilled in AWS"},
    )
    assert response.status_code == 200
