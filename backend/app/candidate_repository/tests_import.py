"""Tests for the Sprint 12 browser-extension capture write path:
InMemoryCandidateRepository.find_potential_duplicate()/upsert(), the
CandidateImportRequest -> Candidate normalizer, and the full
POST /candidate/import endpoint via TestClient.

Each repository-level test builds its own InMemoryCandidateRepository
instance against a temp seed file (never the real singleton) so that
mutating state via upsert() in one test can't leak into another --
mirrors the existing pattern in tests.py (tmp_path-based seed files for
the malformed-data tests).
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.candidate_repository.import_schemas import CandidateImportRequest
from app.candidate_repository.memory_repository import InMemoryCandidateRepository
from app.candidate_repository.models import Candidate
from app.candidate_repository.normalizer import normalize_import
from app.candidate_repository.repository import get_candidate_repository
from app.main import app

_SEED_CANDIDATE = {
    "id": "seed-1",
    "name": "Ananya Gupta",
    "role": "Product Engineer",
    "experience": 6,
    "skills": ["Python"],
    "location": "Bangalore",
    "current_company": "Acme Corp",
    "source": "seed_data",
    "public_profile_url": "https://example.com/in/ananya",
}


@pytest.fixture()
def repo(tmp_path):
    seed_file = tmp_path / "candidates.json"
    seed_file.write_text(json.dumps([_SEED_CANDIDATE]), encoding="utf-8")
    return InMemoryCandidateRepository(seed_path=seed_file)


# --- normalizer ---------------------------------------------------------------


def test_normalize_import_maps_required_and_optional_fields():
    payload = CandidateImportRequest(
        name="Rohan Das",
        role="Backend Engineer",
        current_company="Globex",
        experience_years=4,
        skills=["Go", "Kubernetes"],
        location="Pune",
        public_profile_url="https://example.com/in/rohan",
        source_url="https://example.com/in/rohan",
        captured_by="recruiter@alphasource.ai",
    )
    candidate = normalize_import(payload)

    assert candidate.name == "Rohan Das"
    assert candidate.role == "Backend Engineer"
    assert candidate.current_company == "Globex"
    assert candidate.experience == 4
    assert candidate.skills == ["Go", "Kubernetes"]
    assert candidate.location == "Pune"
    assert candidate.public_profile_url == "https://example.com/in/rohan"
    assert len(candidate.capture_sources) == 1
    assert candidate.capture_sources[0].captured_by == "recruiter@alphasource.ai"
    assert candidate.version == 1


def test_normalize_import_fills_placeholders_for_missing_fields():
    payload = CandidateImportRequest(name="Unknown Fields Person")
    candidate = normalize_import(payload)

    assert candidate.role == "Unknown"
    assert candidate.location == "Unknown"
    assert candidate.current_company == "Unknown"
    assert candidate.experience == 0
    assert candidate.summary is None  # no role/company at all -> no fallback summary


def test_normalize_import_builds_fallback_summary_when_missing():
    payload = CandidateImportRequest(name="Jane Doe", role="Data Scientist", current_company="Initech")
    candidate = normalize_import(payload)

    assert candidate.summary == "Data Scientist at Initech, captured via browser extension."


def test_normalize_import_preserves_explicit_summary():
    payload = CandidateImportRequest(name="Jane Doe", summary="Already has a bio.")
    candidate = normalize_import(payload)

    assert candidate.summary == "Already has a bio."


def test_normalize_import_passes_through_github_enrichment_fields():
    """Sprint 20D: normalize_import() must pass the github_* fields from
    CandidateImportRequest onto Candidate unchanged, additively -- and
    every non-GitHub payload (every test above) must still get None/empty
    defaults for these fields."""
    payload = CandidateImportRequest(
        name="GitHub Sourced Person",
        github_quality_score=88.0,
        github_activity_score=70.0,
        github_repositories_analyzed=4,
        github_languages=["Python"],
        github_topics=["backend"],
        github_organizations=["octo-org"],
        github_skills_inferred=["FastAPI"],
        github_profile_completeness=90.0,
    )
    candidate = normalize_import(payload)

    assert candidate.github_quality_score == 88.0
    assert candidate.github_activity_score == 70.0
    assert candidate.github_repositories_analyzed == 4
    assert candidate.github_languages == ["Python"]
    assert candidate.github_topics == ["backend"]
    assert candidate.github_organizations == ["octo-org"]
    assert candidate.github_skills_inferred == ["FastAPI"]
    assert candidate.github_profile_completeness == 90.0


def test_normalize_import_defaults_github_fields_for_non_github_capture():
    payload = CandidateImportRequest(name="Regular Browser Capture")
    candidate = normalize_import(payload)

    assert candidate.github_quality_score is None
    assert candidate.github_languages == []
    assert candidate.github_skills_inferred == []


# --- find_potential_duplicate() ------------------------------------------------


def test_find_duplicate_matches_on_exact_profile_url(repo):
    incoming = Candidate(
        id="new",
        name="Someone Else",
        role="X",
        experience=1,
        skills=[],
        location="Y",
        current_company="Z",
        source="browser_extension",
        public_profile_url="https://example.com/in/ananya",
    )
    match = repo.find_potential_duplicate(incoming)
    assert match is not None
    assert match.id == "seed-1"


def test_find_duplicate_url_mismatch_does_not_fall_back_to_name_match(repo):
    incoming = Candidate(
        id="new",
        name="Ananya Gupta",
        role="Product Engineer",
        experience=6,
        skills=[],
        location="Bangalore",
        current_company="Acme Corp",
        source="browser_extension",
        public_profile_url="https://example.com/in/someone-different",
    )
    # Explicit URL provided and it doesn't match -- must NOT merge just
    # because name+company happen to coincide.
    assert repo.find_potential_duplicate(incoming) is None


def test_find_duplicate_matches_on_name_and_company_when_no_url(repo):
    incoming = Candidate(
        id="new",
        name="Ananya Gupta",
        role="Something Else",
        experience=2,
        skills=[],
        location="Bangalore",
        current_company="Acme Corp",
        source="browser_extension",
    )
    match = repo.find_potential_duplicate(incoming)
    assert match is not None
    assert match.id == "seed-1"


def test_find_duplicate_no_match_for_genuinely_new_person(repo):
    incoming = Candidate(
        id="new",
        name="Brand New Person",
        role="X",
        experience=1,
        skills=[],
        location="Y",
        current_company="Z",
        source="browser_extension",
    )
    assert repo.find_potential_duplicate(incoming) is None


# --- upsert() -------------------------------------------------------------------


def test_upsert_creates_new_candidate_when_no_duplicate(repo):
    new_candidate = Candidate(
        id="ignored",
        name="Brand New Person",
        role="Engineer",
        experience=3,
        skills=["Rust"],
        location="Delhi",
        current_company="NewCo",
        source="browser_extension",
    )
    result = repo.upsert(new_candidate)

    assert len(repo.all()) == 2
    assert result.name == "Brand New Person"
    assert result.version == 1


def test_upsert_merges_into_existing_candidate_on_duplicate(repo):
    capture = Candidate(
        id="ignored",
        name="Ananya Gupta",
        role="",
        experience=0,
        skills=["Kubernetes"],
        location="",
        current_company="",
        source="browser_extension",
        public_profile_url="https://example.com/in/ananya",
        headline="Senior Product Engineer",
    )
    result = repo.upsert(capture)

    assert len(repo.all()) == 1  # merged, not appended
    assert result.id == "seed-1"  # existing id preserved
    assert set(result.skills) == {"Python", "Kubernetes"}  # union
    assert result.role == "Product Engineer"  # existing value preserved, not blanked
    assert result.headline == "Senior Product Engineer"  # filled from new data
    assert result.version == 2  # incremented


def test_upsert_merge_never_drops_prior_capture_sources(repo):
    def _capture() -> Candidate:
        payload = CandidateImportRequest(
            name="Ananya Gupta",
            public_profile_url="https://example.com/in/ananya",
        )
        return normalize_import(payload)

    repo.upsert(_capture())
    second = repo.upsert(_capture())

    # Two captures of the same page -> two CaptureSource entries retained,
    # not overwritten.
    assert len(second.capture_sources) == 2


# --- POST /candidate/import (full endpoint, real app, isolated repo) ---------


@pytest.fixture()
def client(repo):
    app.dependency_overrides[get_candidate_repository] = lambda: repo
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_import_endpoint_creates_new_candidate(client):
    response = client.post(
        "/candidate/import",
        json={"name": "Fresh Capture", "role": "SRE", "current_company": "Acme"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["created"] is True
    assert body["version"] == 1
    assert "candidate_id" in body


def test_import_endpoint_merges_duplicate_by_profile_url(client):
    response = client.post(
        "/candidate/import",
        json={
            "name": "Ananya Gupta",
            "public_profile_url": "https://example.com/in/ananya",
            "headline": "Staff Engineer",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["created"] is False
    assert body["candidate_id"] == "seed-1"
    assert body["version"] == 2


def test_import_endpoint_rejects_blank_name(client):
    response = client.post("/candidate/import", json={"name": "   "})
    assert response.status_code == 422


def test_import_endpoint_rejects_missing_name(client):
    response = client.post("/candidate/import", json={"role": "Engineer"})
    assert response.status_code == 422


def test_import_endpoint_candidate_is_immediately_searchable(client, repo):
    from app.search_planner.models import SearchPlan

    client.post(
        "/candidate/import",
        json={"name": "Searchable Person", "role": "Rare Role Xyz", "skills": ["ObscureSkill"]},
    )

    plan = SearchPlan(strict=[], expanded=[], search_terms=["ObscureSkill"], weights={}, unresolved=[])
    results = repo.search(plan)
    assert any(c.name == "Searchable Person" for c in results)


def test_existing_search_endpoint_unaffected_by_import_router(client):
    # Sanity check: registering the new router did not disturb the existing
    # /api/v1/search route.
    response = client.post(
        "/api/v1/search",
        json={"query": "Find Product Engineers with 7+ years in Bangalore, skilled in AWS"},
    )
    assert response.status_code == 200
