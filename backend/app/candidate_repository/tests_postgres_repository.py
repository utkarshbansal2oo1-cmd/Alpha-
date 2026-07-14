"""Tests for PostgresCandidateRepository -- Sprint 30.

Runs against an in-memory SQLite engine, not a real Postgres server --
SQLAlchemy's ORM layer and the generic JSON column type (see
app/models/candidate.py's docstring on why JSONB was deliberately avoided)
both work identically against SQLite for this repository's purposes, so
this gives real coverage of the actual read/write logic without requiring
a live database in CI. Uses a small seed fixture (2 candidates), mirroring
the pattern InMemoryCandidateRepository's own tests use.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.candidate_repository.postgres_repository import PostgresCandidateRepository
from app.database import Base
from app.search_planner.models import SearchPlan


@pytest.fixture
def seed_file(tmp_path):
    path = tmp_path / "seed.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": "c1",
                    "name": "Asha Rao",
                    "role": "Backend Engineer",
                    "experience": 5,
                    "skills": ["Python", "AWS"],
                    "location": "Bangalore",
                    "current_company": "Acme",
                    "source": "seed_data",
                },
                {
                    "id": "c2",
                    "name": "Ravi Kumar",
                    "role": "Frontend Engineer",
                    "experience": 3,
                    "skills": ["React"],
                    "location": "Pune",
                    "current_company": "Beta Corp",
                    "source": "seed_data",
                },
            ]
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def repo(seed_file):
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return PostgresCandidateRepository(session_factory=session_factory, seed_path=seed_file)


def test_seeds_from_file_on_first_use(repo):
    assert {c.id for c in repo.all()} == {"c1", "c2"}


def test_does_not_reseed_on_second_construction(seed_file):
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    repo1 = PostgresCandidateRepository(session_factory=session_factory, seed_path=seed_file)
    repo1.upsert(repo1.all()[0].model_copy(update={"skills": ["Python", "AWS", "Kubernetes"]}))

    repo2 = PostgresCandidateRepository(session_factory=session_factory, seed_path=seed_file)
    assert len(repo2.all()) == 2  # not re-seeded to 4


def test_search_filters_by_role(repo):
    plan = SearchPlan(search_terms=["backend engineer"])
    results = repo.search(plan)
    assert [c.id for c in results] == ["c1"]


def test_search_with_no_terms_returns_everyone(repo):
    plan = SearchPlan(search_terms=[])
    assert len(repo.search(plan)) == 2


def test_get_by_id_found_and_not_found(repo):
    assert repo.get_by_id("c1").name == "Asha Rao"
    assert repo.get_by_id("does-not-exist") is None


def test_upsert_new_candidate_persists(repo):
    from app.candidate_repository.models import Candidate

    new_candidate = Candidate(
        id="c3",
        name="New Person",
        role="Data Scientist",
        experience=2,
        skills=["Python"],
        location="Mumbai",
        current_company="Gamma",
        source="browser_extension",
    )
    result = repo.upsert(new_candidate)

    assert result.id == "c3"
    assert repo.get_by_id("c3").name == "New Person"
    assert len(repo.all()) == 3


def test_upsert_merges_into_existing_by_profile_url(repo):
    from app.candidate_repository.models import Candidate

    # First capture establishes the profile URL.
    first = Candidate(
        id="",
        name="Dup Person",
        role="Engineer",
        experience=4,
        skills=["Go"],
        location="Delhi",
        current_company="Delta",
        source="browser_extension",
        public_profile_url="https://example.com/dup",
    )
    created = repo.upsert(first)

    # Second capture, same URL, new skill -- should merge, not duplicate.
    second = Candidate(
        id="",
        name="Dup Person",
        role="",
        experience=0,
        skills=["Kubernetes"],
        location="",
        current_company="",
        source="browser_extension",
        public_profile_url="https://example.com/dup",
    )
    merged = repo.upsert(second)

    assert merged.id == created.id
    assert set(merged.skills) == {"Go", "Kubernetes"}
    assert len(repo.all()) == 3  # 2 seed + 1 (not 4)


def test_data_survives_across_repository_instances(seed_file):
    """The whole point of this sprint: unlike InMemoryCandidateRepository,
    data must survive a fresh instance being constructed against the same
    underlying store (simulating a process restart)."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    repo1 = PostgresCandidateRepository(session_factory=session_factory, seed_path=seed_file)
    from app.candidate_repository.models import Candidate

    repo1.upsert(
        Candidate(
            id="persisted-1",
            name="Persisted Person",
            role="SRE",
            experience=6,
            skills=["Terraform"],
            location="Remote",
            current_company="Epsilon",
            source="browser_extension",
        )
    )

    repo2 = PostgresCandidateRepository(session_factory=session_factory, seed_path=seed_file)
    assert repo2.get_by_id("persisted-1") is not None
