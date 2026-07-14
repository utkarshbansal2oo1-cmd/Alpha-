"""Integration tests for POST /api/search."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.query_understanding.gemini_client import LLMClient
from app.query_understanding.service import QueryUnderstandingService
from app.routers.search_pipeline import get_query_understanding_service
from app.testing.fakes import FakeLLMClient


def _override_query_understanding(responses: list[str]) -> FakeLLMClient:
    fake_llm = FakeLLMClient(responses)
    app.dependency_overrides[get_query_understanding_service] = (
        lambda: QueryUnderstandingService(llm_client=fake_llm)
    )
    return fake_llm


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


def test_search_endpoint_full_pipeline_happy_path():
    _override_query_understanding(
        ['{"role": "Product Engineer", "skills": ["AWS"]}']
    )

    response = client.post("/api/search", json={"query": "Find Product Engineers with AWS"})

    assert response.status_code == 200
    body = response.json()
    assert "candidates" in body
    assert "count" in body
    assert body["count"] == len(body["candidates"])
    assert body["count"] > 0

    names = {c["name"] for c in body["candidates"]}
    assert "Rahul Mehta" in names
    assert "Asha Rao" in names


def test_search_endpoint_returns_requirement_and_search_plan():
    _override_query_understanding(['{"role": "Product Engineer", "skills": ["AWS"]}'])

    response = client.post("/api/search", json={"query": "Find Product Engineers with AWS"})

    assert response.status_code == 200
    body = response.json()

    assert body["requirement"] == {"role": "Product Engineer", "skills": ["AWS"]}

    plan = body["search_plan"]
    strict_values = {f["canonical_value"] for f in plan["strict"]}
    assert strict_values == {"Product Engineer", "AWS"}
    expanded_values = {f["expanded_value"] for f in plan["expanded"]}
    assert "EC2" in expanded_values
    assert "Backend Engineer" in expanded_values
    assert plan["weights"]["EC2"] == 0.9


def test_search_endpoint_response_matches_candidate_schema():
    _override_query_understanding(['{"role": "Data Scientist", "skills": ["Machine Learning"]}'])

    response = client.post("/api/search", json={"query": "Data Scientist with ML"})

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    candidate = body["candidates"][0]
    for field in ["id", "name", "role", "experience", "skills", "location", "current_company", "source"]:
        assert field in candidate


def test_search_endpoint_no_matches_returns_empty_list_not_error():
    _override_query_understanding(['{"role": "Astronaut", "skills": ["Zero Gravity Piloting"]}'])

    response = client.post("/api/search", json={"query": "Astronaut with zero gravity piloting"})

    assert response.status_code == 200
    body = response.json()
    assert body["candidates"] == []
    assert body["count"] == 0


def test_search_endpoint_succeeds_after_one_retry():
    fake_llm = _override_query_understanding(
        [
            "not valid json at all",
            '{"role": "Backend Engineer", "skills": ["Kubernetes"]}',
        ]
    )

    response = client.post("/api/search", json={"query": "Backend Engineer who knows Kubernetes"})

    assert response.status_code == 200
    assert fake_llm.call_count == 2


def test_search_endpoint_returns_502_when_llm_fails_twice():
    _override_query_understanding(["not json", "still not json"])

    response = client.post("/api/search", json={"query": "Product Manager from FinTech"})

    assert response.status_code == 502
    assert "Query understanding failed" in response.json()["detail"]


def test_search_endpoint_returns_502_when_llm_client_itself_fails():
    class FailingLLMClient(LLMClient):
        def generate(self, prompt: str) -> str:
            raise RuntimeError("simulated provider outage")

    app.dependency_overrides[get_query_understanding_service] = (
        lambda: QueryUnderstandingService(llm_client=FailingLLMClient())
    )

    response = client.post("/api/search", json={"query": "Product Engineer with AWS"})

    assert response.status_code == 502
    assert "Query understanding failed" in response.json()["detail"]


def test_search_endpoint_returns_422_for_empty_query():
    _override_query_understanding([])

    response = client.post("/api/search", json={"query": "   "})

    assert response.status_code == 422


def test_search_endpoint_returns_422_for_missing_query_field():
    response = client.post("/api/search", json={})
    assert response.status_code == 422


def test_search_endpoint_response_has_no_ranking_fields():
    _override_query_understanding(['{"role": "Product Engineer", "skills": ["AWS"]}'])

    response = client.post("/api/search", json={"query": "Product Engineer with AWS"})

    body = response.json()
    for candidate in body["candidates"]:
        assert "match_score" not in candidate
        assert "rank" not in candidate
        assert "reasoning" not in candidate


def test_old_v1_search_route_still_works_independently():
    response = client.post(
        "/api/v1/search",
        json={"query": "Find Product Engineers with 7+ years in Bangalore, skilled in AWS"},
    )
    assert response.status_code == 200
    assert "results" in response.json()
