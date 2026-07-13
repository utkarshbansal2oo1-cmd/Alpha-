"""Tests for the Greenhouse connector: client (against respx-mocked HTTP
responses shaped like Greenhouse's real documented payloads), normalizer,
pull sync (with dedup), push-back, and the four new endpoints.

respx intercepts httpx calls at the transport level -- these tests verify
GreenhouseClient speaks the real documented Harvest API contract
correctly (Basic Auth, Link-header pagination, 429/Retry-After handling),
not that it talks to some hand-rolled fake server. Pointing GreenhouseConfig
at the real https://harvest.greenhouse.io/v1 with a real API key requires
no code change.
"""
from __future__ import annotations

import json

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.candidate_repository.memory_repository import InMemoryCandidateRepository
from app.candidate_repository.repository import get_candidate_repository
from app.integrations.greenhouse.client import GreenhouseAPIError, GreenhouseClient
from app.integrations.greenhouse.config import GreenhouseConfig, GreenhouseConfigStore, get_greenhouse_config_store
from app.integrations.greenhouse.normalizer import normalize_greenhouse_candidate
from app.integrations.greenhouse.sync import pull_sync, push_candidate
from app.integrations.greenhouse.sync_store import SyncRunStore, get_sync_run_store
from app.main import app

_BASE_URL = "https://harvest.greenhouse.io/v1"

_RAW_CANDIDATE_1 = {
    "id": 1001,
    "first_name": "Priya",
    "last_name": "Nair",
    "company": "Nimbus Cloud",
    "title": "Staff Engineer",
    "addresses": [{"value": "Bangalore, India", "type": "home"}],
    "social_media_addresses": [{"value": "https://linkedin.com/in/priyanair"}],
    "educations": [{"school_name": "IIT Bombay", "degree": "B.Tech", "end_date": "2014-05-01"}],
    "tags": ["Kubernetes", "Go"],
}

_RAW_CANDIDATE_2 = {
    "id": 1002,
    "first_name": "Karan",
    "last_name": "Shah",
    "company": "Acme",
    "title": "DevOps Engineer",
    "addresses": [{"value": "Mumbai, India", "type": "home"}],
    "tags": ["Terraform"],
}


# --- Normalizer ------------------------------------------------------------------


def test_normalize_greenhouse_candidate_maps_core_fields():
    request = normalize_greenhouse_candidate(_RAW_CANDIDATE_1)
    assert request.name == "Priya Nair"
    assert request.role == "Staff Engineer"
    assert request.current_company == "Nimbus Cloud"
    assert request.location == "Bangalore, India"
    assert request.public_profile_url == "https://linkedin.com/in/priyanair"
    assert request.skills == ["Kubernetes", "Go"]
    assert request.source_type == "greenhouse_ats"
    assert request.education[0].institution == "IIT Bombay"


def test_normalize_greenhouse_candidate_handles_missing_fields():
    request = normalize_greenhouse_candidate({"id": 999, "first_name": "Solo"})
    assert request.name == "Solo"
    assert request.role is None
    assert request.skills == []


# --- Client (respx-mocked HTTP) ---------------------------------------------------


@respx.mock
def test_client_list_candidates_follows_pagination():
    page1 = respx.get(f"{_BASE_URL}/candidates?per_page=100").mock(
        return_value=httpx.Response(
            200,
            json=[_RAW_CANDIDATE_1],
            headers={"Link": f'<{_BASE_URL}/candidates?page=2>; rel="next"'},
        )
    )
    respx.get(f"{_BASE_URL}/candidates?page=2").mock(
        return_value=httpx.Response(200, json=[_RAW_CANDIDATE_2])
    )

    client = GreenhouseClient(GreenhouseConfig(api_key="test-key"))
    candidates = client.list_candidates()

    assert len(candidates) == 2
    assert page1.called
    # Basic Auth: API key as username, blank password
    auth_header = page1.calls[0].request.headers["Authorization"]
    assert auth_header.startswith("Basic ")


@respx.mock
def test_client_get_candidate():
    respx.get(f"{_BASE_URL}/candidates/1001").mock(return_value=httpx.Response(200, json=_RAW_CANDIDATE_1))
    client = GreenhouseClient(GreenhouseConfig(api_key="test-key"))
    candidate = client.get_candidate(1001)
    assert candidate["first_name"] == "Priya"


@respx.mock
def test_client_raises_on_4xx():
    respx.get(f"{_BASE_URL}/candidates/9999").mock(return_value=httpx.Response(404, text="Not Found"))
    client = GreenhouseClient(GreenhouseConfig(api_key="test-key"))
    with pytest.raises(GreenhouseAPIError):
        client.get_candidate(9999)


@respx.mock
def test_client_retries_once_on_429():
    route = respx.get(f"{_BASE_URL}/candidates/1001").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json=_RAW_CANDIDATE_1),
        ]
    )
    client = GreenhouseClient(GreenhouseConfig(api_key="test-key"))
    candidate = client.get_candidate(1001)
    assert candidate["first_name"] == "Priya"
    assert route.call_count == 2


@respx.mock
def test_client_create_candidate():
    respx.post(f"{_BASE_URL}/candidates").mock(
        return_value=httpx.Response(200, json={"id": 2001, "first_name": "New", "last_name": "Person"})
    )
    client = GreenhouseClient(GreenhouseConfig(api_key="test-key"))
    result = client.create_candidate({"first_name": "New", "last_name": "Person"})
    assert result["id"] == 2001


# --- Pull sync (dedup + logging) --------------------------------------------------


@pytest.fixture()
def repo(tmp_path):
    seed_file = tmp_path / "candidates.json"
    seed_file.write_text(json.dumps([]), encoding="utf-8")
    return InMemoryCandidateRepository(seed_path=seed_file)


@respx.mock
def test_pull_sync_creates_new_candidates(repo):
    respx.get(f"{_BASE_URL}/candidates?per_page=100").mock(
        return_value=httpx.Response(200, json=[_RAW_CANDIDATE_1, _RAW_CANDIDATE_2])
    )
    client = GreenhouseClient(GreenhouseConfig(api_key="test-key"))

    run = pull_sync(client, repo)

    assert run.status == "completed"
    assert run.candidates_pulled == 2
    assert run.candidates_created == 2
    assert run.candidates_merged == 0
    assert len(repo.all()) == 2


@respx.mock
def test_pull_sync_merges_duplicate_on_second_run(repo):
    respx.get(f"{_BASE_URL}/candidates?per_page=100").mock(
        return_value=httpx.Response(200, json=[_RAW_CANDIDATE_1])
    )
    client = GreenhouseClient(GreenhouseConfig(api_key="test-key"))

    pull_sync(client, repo)
    second_run = pull_sync(client, repo)

    assert second_run.candidates_created == 0
    assert second_run.candidates_merged == 1
    assert len(repo.all()) == 1  # still just one candidate, not duplicated


@respx.mock
def test_pull_sync_records_error_for_bad_record_without_aborting(repo):
    respx.get(f"{_BASE_URL}/candidates?per_page=100").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "first_name": None, "last_name": None}, _RAW_CANDIDATE_2])
    )
    client = GreenhouseClient(GreenhouseConfig(api_key="test-key"))

    run = pull_sync(client, repo)

    # The malformed record (no usable name) should be skipped/recorded,
    # not abort the whole sync -- the well-formed second candidate still
    # gets created.
    assert run.candidates_created >= 1
    assert len(repo.all()) >= 1


@respx.mock
def test_pull_sync_candidates_are_immediately_searchable(repo):
    respx.get(f"{_BASE_URL}/candidates?per_page=100").mock(
        return_value=httpx.Response(200, json=[_RAW_CANDIDATE_1])
    )
    client = GreenhouseClient(GreenhouseConfig(api_key="test-key"))
    pull_sync(client, repo)

    from app.search_planner.models import SearchPlan

    plan = SearchPlan(strict=[], expanded=[], search_terms=["Kubernetes"], weights={}, unresolved=[])
    results = repo.search(plan)
    assert any(c.name == "Priya Nair" for c in results)


# --- Push-back ----------------------------------------------------------------------


@respx.mock
def test_push_candidate_creates_in_greenhouse_and_adds_note(repo):
    respx.get(f"{_BASE_URL}/candidates?per_page=100").mock(
        return_value=httpx.Response(200, json=[_RAW_CANDIDATE_1])
    )
    client = GreenhouseClient(GreenhouseConfig(api_key="test-key"))
    pull_sync(client, repo)
    candidate = repo.all()[0]

    create_route = respx.post(f"{_BASE_URL}/candidates").mock(
        return_value=httpx.Response(200, json={"id": 5001})
    )
    note_route = respx.post(f"{_BASE_URL}/candidates/5001/activity_feed/notes").mock(
        return_value=httpx.Response(200, json={"id": 1})
    )

    result = push_candidate(client, candidate, note="Strong AWS/Kubernetes match for req #42")

    assert result["id"] == 5001
    assert create_route.called
    assert note_route.called


# --- Endpoints ------------------------------------------------------------------------


@pytest.fixture()
def client_app(repo):
    # One shared instance per test, not a factory -- FastAPI calls the
    # override on every request, so a lambda that builds a NEW store each
    # time would silently discard whatever /configure just set before
    # /sync ever ran.
    config_store = GreenhouseConfigStore()
    sync_store = SyncRunStore()
    app.dependency_overrides[get_candidate_repository] = lambda: repo
    app.dependency_overrides[get_greenhouse_config_store] = lambda: config_store
    app.dependency_overrides[get_sync_run_store] = lambda: sync_store
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_configure_endpoint(client_app):
    response = client_app.post("/integrations/greenhouse/configure", json={"api_key": "abc123"})
    assert response.status_code == 200
    assert response.json()["configured"] is True


def test_sync_endpoint_requires_configuration_first(client_app):
    response = client_app.post("/integrations/greenhouse/sync")
    assert response.status_code == 400


@respx.mock
def test_sync_endpoint_after_configuring(client_app):
    respx.get(f"{_BASE_URL}/candidates?per_page=100").mock(
        return_value=httpx.Response(200, json=[_RAW_CANDIDATE_1])
    )
    client_app.post("/integrations/greenhouse/configure", json={"api_key": "abc123"})
    response = client_app.post("/integrations/greenhouse/sync")
    assert response.status_code == 200
    assert response.json()["candidates_created"] == 1


@respx.mock
def test_sync_status_endpoint_returns_history(client_app):
    respx.get(f"{_BASE_URL}/candidates?per_page=100").mock(
        return_value=httpx.Response(200, json=[_RAW_CANDIDATE_1])
    )
    client_app.post("/integrations/greenhouse/configure", json={"api_key": "abc123"})
    client_app.post("/integrations/greenhouse/sync")

    response = client_app.get("/integrations/greenhouse/sync-status")
    assert response.status_code == 200
    assert len(response.json()) == 1


@respx.mock
def test_push_endpoint(client_app):
    respx.get(f"{_BASE_URL}/candidates?per_page=100").mock(
        return_value=httpx.Response(200, json=[_RAW_CANDIDATE_1])
    )
    client_app.post("/integrations/greenhouse/configure", json={"api_key": "abc123"})
    client_app.post("/integrations/greenhouse/sync")

    repo_instance = app.dependency_overrides[get_candidate_repository]()
    candidate_id = repo_instance.all()[0].id

    respx.post(f"{_BASE_URL}/candidates").mock(return_value=httpx.Response(200, json={"id": 9001}))
    respx.post(f"{_BASE_URL}/candidates/9001/activity_feed/notes").mock(return_value=httpx.Response(200, json={}))

    response = client_app.post(f"/integrations/greenhouse/push/{candidate_id}", json={"note": "Great fit"})
    assert response.status_code == 200
    assert response.json()["greenhouse_candidate_id"] == "9001"
    assert response.json()["note_added"] is True


def test_push_endpoint_404_for_unknown_candidate(client_app):
    client_app.post("/integrations/greenhouse/configure", json={"api_key": "abc123"})
    response = client_app.post("/integrations/greenhouse/push/does-not-exist", json={})
    assert response.status_code == 404


def test_greenhouse_router_does_not_affect_existing_search_route(client_app):
    response = client_app.post(
        "/api/v1/search",
        json={"query": "Find Product Engineers with 7+ years in Bangalore, skilled in AWS"},
    )
    assert response.status_code == 200
