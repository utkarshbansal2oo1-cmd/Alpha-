"""Tests for the Candidate Repository: models, in-memory repository
retrieval, and the full SearchPlan -> Repository -> Candidate[] acceptance
chain (built via the real Search Planner + Knowledge Engine, since both are
already approved and frozen -- no reason to fake them here).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.candidate_repository.interfaces import CandidateRepository
from app.candidate_repository.memory_repository import InMemoryCandidateRepository
from app.candidate_repository.models import Candidate
from app.candidate_repository.repository import get_candidate_repository
from app.search_planner.models import CanonicalJobRequirement, SearchPlan
from app.search_planner.planner import SearchPlanner

FIXTURES = Path(__file__).parent / "tests_fixtures"


# --- Candidate model ---------------------------------------------------------


def test_candidate_model_accepts_well_formed_data():
    candidate = Candidate(
        id="c1",
        name="Asha Rao",
        role="Product Engineer",
        experience=8.5,
        skills=["AWS", "Kubernetes"],
        location="Bangalore",
        current_company="Acme Cloud",
        source="seed_data",
    )
    assert candidate.id == "c1"
    assert candidate.skills == ["AWS", "Kubernetes"]


def test_candidate_model_rejects_negative_experience():
    with pytest.raises(ValidationError):
        Candidate(
            id="c1",
            name="X",
            role="Y",
            experience=-1,
            skills=[],
            location="Z",
            current_company="W",
            source="seed_data",
        )


def test_candidate_model_defaults_skills_to_empty_list():
    candidate = Candidate(
        id="c1",
        name="X",
        role="Y",
        experience=1,
        location="Z",
        current_company="W",
        source="seed_data",
    )
    assert candidate.skills == []


# --- InMemoryCandidateRepository: loading -------------------------------------


def test_repository_loads_real_seed_data():
    repo = InMemoryCandidateRepository()
    # Sprint 16: seed data grew from 8 to 9 -- cand-009 (Ritika Malhotra,
    # Enterprise Sales Manager / Cybersecurity) was added so the
    # connectivity sprint's example query ("Get me a sales person with
    # cyber expertise") has a real, matchable candidate instead of
    # legitimately returning zero results.
    assert len(repo.all()) == 9


def test_repository_raises_on_missing_seed_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        InMemoryCandidateRepository(seed_path=tmp_path / "does_not_exist.json")


def test_repository_implements_the_interface():
    repo = InMemoryCandidateRepository()
    assert isinstance(repo, CandidateRepository)


# --- InMemoryCandidateRepository: search() with hand-built SearchPlans -------


def _plan(search_terms: list[str]) -> SearchPlan:
    return SearchPlan(strict=[], expanded=[], search_terms=search_terms, weights={}, unresolved=[])


def test_search_matches_by_role():
    repo = InMemoryCandidateRepository()
    results = repo.search(_plan(["Data Scientist"]))
    names = {c.name for c in results}
    assert names == {"Vikram Nair"}


def test_search_matches_by_skill():
    repo = InMemoryCandidateRepository()
    results = repo.search(_plan(["Kafka"]))
    names = {c.name for c in results}
    assert names == {"Meera Pillai"}


def test_search_matches_role_or_skill_case_insensitively():
    repo = InMemoryCandidateRepository()
    results = repo.search(_plan(["data scientist", "kafka"]))
    names = {c.name for c in results}
    assert names == {"Vikram Nair", "Meera Pillai"}


def test_search_with_no_matches_returns_empty_list():
    repo = InMemoryCandidateRepository()
    results = repo.search(_plan(["Nonexistent Skill Xyz"]))
    assert results == []


def test_search_with_empty_search_terms_returns_all_candidates():
    repo = InMemoryCandidateRepository()
    results = repo.search(_plan([]))
    assert len(results) == len(repo.all())


def test_search_result_is_pure_candidate_list_no_scores_attached():
    repo = InMemoryCandidateRepository()
    results = repo.search(_plan(["AWS"]))
    for c in results:
        assert isinstance(c, Candidate)
        assert not hasattr(c, "match_score")
        assert not hasattr(c, "rank")


def test_search_matches_sales_cybersecurity_seed_candidate():
    # Sprint 16 connectivity-sprint canary: confirms the example query from
    # the sprint brief ("Get me a sales person with cyber expertise") has a
    # real match once Query Understanding extracts a skill like
    # "Cybersecurity" -- see cand-009 in data/candidates.json.
    repo = InMemoryCandidateRepository()
    results = repo.search(_plan(["Cybersecurity"]))
    names = {c.name for c in results}
    assert names == {"Ritika Malhotra"}


# --- get_candidate_repository() singleton ------------------------------------


def test_get_candidate_repository_returns_singleton():
    repo1 = get_candidate_repository()
    repo2 = get_candidate_repository()
    assert repo1 is repo2


# --- Acceptance: SearchPlan -> Repository -> Candidate[], via the real ------
# --- Search Planner + Knowledge Engine (both already approved & frozen) -----


def test_acceptance_search_plan_through_repository_to_candidates():
    requirement = CanonicalJobRequirement(role="Product Engineer", skills=["AWS"])
    plan = SearchPlanner().build_plan(requirement)

    repo = InMemoryCandidateRepository()
    results = repo.search(plan)

    names = {c.name for c in results}
    # cand-001 (AWS, role Senior Product Engineer -> contains "Product Engineer"? role text
    # differs; matched via skill AWS), cand-002 (role Product Engineer + AWS skill),
    # cand-003 (Backend Engineer role via expansion, EC2 skill via expansion),
    # cand-004 (Backend Engineer role via expansion),
    # cand-005 (Platform Engineer role via expansion, EKS/IAM skills via expansion),
    # cand-006 (Lambda/S3/CloudFormation skills via expansion),
    # cand-008 (Software Engineer? no -- role API Engineer via expansion, AWS skill)
    assert "Rahul Mehta" in names  # exact role + exact skill match
    assert "Asha Rao" in names  # exact skill match (AWS)
    assert "Priya Singh" in names  # role expansion (Backend Engineer) + skill expansion (EC2)
    assert "Neha Kulkarni" in names  # role expansion (Platform Engineer) + skill expansion (EKS/IAM)
    assert "Farah Sheikh" in names  # skill expansion (Lambda/S3/CloudFormation)
    assert "Meera Pillai" in names  # role expansion (API Engineer) + exact skill (AWS)
    # Vikram Nair (Data Scientist, unrelated skills) should not match at all.
    assert "Vikram Nair" not in names


def test_acceptance_unrelated_requirement_excludes_unrelated_candidates():
    requirement = CanonicalJobRequirement(role="Data Scientist", skills=["Machine Learning"])
    plan = SearchPlanner().build_plan(requirement)

    repo = InMemoryCandidateRepository()
    results = repo.search(plan)

    names = {c.name for c in results}
    assert names == {"Vikram Nair"}


def test_acceptance_sales_cybersecurity_requirement_via_real_planner():
    # Sprint 16: end-to-end proof (real, unmodified SearchPlanner +
    # KnowledgeEngine, no fakes) that a requirement shaped like what Query
    # Understanding would plausibly extract from "Get me a sales person
    # with cyber expertise" resolves to a SearchPlan that matches cand-009,
    # even though "Sales Person"/"Cybersecurity" aren't in the canonical
    # taxonomy (they pass through as unresolved-but-still-searched terms --
    # existing SearchPlanner behavior, unchanged).
    requirement = CanonicalJobRequirement(role="Sales Person", skills=["Cybersecurity"])
    plan = SearchPlanner().build_plan(requirement)

    repo = InMemoryCandidateRepository()
    results = repo.search(plan)

    names = {c.name for c in results}
    assert "Ritika Malhotra" in names


# --- InMemoryCandidateRepository: malformed seed data (code review addition) -


def test_repository_raises_seed_data_error_on_invalid_json(tmp_path):
    from app.candidate_repository.memory_repository import CandidateSeedDataError

    bad_file = tmp_path / "candidates.json"
    bad_file.write_text("{ this is not valid json", encoding="utf-8")

    with pytest.raises(CandidateSeedDataError):
        InMemoryCandidateRepository(seed_path=bad_file)


def test_repository_raises_seed_data_error_on_record_missing_required_field(tmp_path):
    from app.candidate_repository.memory_repository import CandidateSeedDataError

    bad_file = tmp_path / "candidates.json"
    bad_file.write_text(
        '[{"id": "c1", "name": "X", "role": "Y"}]',  # missing required fields
        encoding="utf-8",
    )

    with pytest.raises(CandidateSeedDataError):
        InMemoryCandidateRepository(seed_path=bad_file)
