"""Tests for SearchSessionStore -- Sprint 33. Runs against in-memory
SQLite, same pattern as app/auth/tests_service.py and
app/credentials/tests_service.py."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.matching.models import MatchResult, RankedCandidate
from app.search_sessions.store import SearchSessionNotFoundError, SearchSessionStore


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture
def store(session_factory):
    return SearchSessionStore(session_factory=session_factory)


def _ranked(candidate_id: str, rank: int, score: float = 80.0) -> RankedCandidate:
    return RankedCandidate(
        candidate_id=candidate_id,
        rank=rank,
        match=MatchResult(
            candidate_id=candidate_id,
            overall_score=score,
            component_scores={"skills": score},
            matched_fields=["skills"],
            missing_fields=[],
            reasons=[f"matched for {candidate_id}"],
        ),
    )


def _make_rankings(n: int) -> list[RankedCandidate]:
    return [_ranked(f"cand-{i}", rank=i + 1, score=100.0 - i) for i in range(n)]


# --- Sprint 36: Source Group support (source column, filter, counts) -------


def test_create_persists_source_per_candidate(store):
    session_id = store.create(
        recruiter_id=None,
        query="Java Developer",
        session_data={},
        rankings=_make_rankings(3),
        candidate_sources={"cand-0": "github", "cand-1": "seed_data", "cand-2": "github"},
    )
    page = store.get_page(session_id, page=1, page_size=10)
    counts = store.get_source_counts(session_id)
    assert counts == {"github": 2, "seed_data": 1}
    assert len(page.rankings) == 3


def test_create_without_candidate_sources_leaves_source_none(store):
    """Backward compatibility: pre-Sprint-36 callers that don't pass
    candidate_sources still work, rows just get source=None."""
    session_id = store.create(
        recruiter_id=None, query="Java Developer", session_data={}, rankings=_make_rankings(2)
    )
    counts = store.get_source_counts(session_id)
    assert counts == {None: 2}


def test_get_page_source_filter_restricts_to_one_source_group(store):
    session_id = store.create(
        recruiter_id=None,
        query="Java Developer",
        session_data={},
        rankings=_make_rankings(5),
        candidate_sources={
            "cand-0": "github",
            "cand-1": "github",
            "cand-2": "seed_data",
            "cand-3": "seed_data",
            "cand-4": "seed_data",
        },
    )
    github_page = store.get_page(session_id, page=1, page_size=10, source="github")
    assert github_page.total_count == 2
    assert {r.candidate_id for r in github_page.rankings} == {"cand-0", "cand-1"}
    # Global rank numbers are preserved even when filtered to one source.
    assert [r.rank for r in github_page.rankings] == [1, 2]

    seed_page = store.get_page(session_id, page=1, page_size=10, source="seed_data")
    assert seed_page.total_count == 3
    assert {r.candidate_id for r in seed_page.rankings} == {"cand-2", "cand-3", "cand-4"}


def test_get_page_source_filter_combines_with_min_score(store):
    session_id = store.create(
        recruiter_id=None,
        query="Java Developer",
        session_data={},
        rankings=_make_rankings(5),  # scores 100, 99, 98, 97, 96
        candidate_sources={f"cand-{i}": "github" for i in range(5)},
    )
    page = store.get_page(session_id, page=1, page_size=10, min_score=98, source="github")
    assert page.total_count == 3
    assert {r.candidate_id for r in page.rankings} == {"cand-0", "cand-1", "cand-2"}


def test_get_source_counts_respects_min_score(store):
    session_id = store.create(
        recruiter_id=None,
        query="Java Developer",
        session_data={},
        rankings=_make_rankings(5),  # scores 100, 99, 98, 97, 96
        candidate_sources={f"cand-{i}": "github" for i in range(5)},
    )
    counts = store.get_source_counts(session_id, min_score=98)
    assert counts == {"github": 3}


def test_get_source_counts_unknown_session_raises(store):
    with pytest.raises(SearchSessionNotFoundError):
        store.get_source_counts("does-not-exist")


def test_create_returns_a_session_id(store):
    session_id = store.create(
        recruiter_id="recruiter-1", query="Java Developer", session_data={"foo": "bar"}, rankings=_make_rankings(3)
    )
    assert isinstance(session_id, str)
    assert len(session_id) > 10


def test_get_page_returns_first_page_in_rank_order(store):
    session_id = store.create(
        recruiter_id="recruiter-1", query="Java Developer", session_data={}, rankings=_make_rankings(25)
    )

    page = store.get_page(session_id, page=1, page_size=20)

    assert page.total_count == 25
    assert page.total_pages == 2
    assert page.page == 1
    assert page.has_next is True
    assert page.has_previous is False
    assert len(page.rankings) == 20
    assert [r.candidate_id for r in page.rankings] == [f"cand-{i}" for i in range(20)]
    assert [r.rank for r in page.rankings] == list(range(1, 21))


def test_get_page_second_page_has_remainder_no_overlap(store):
    session_id = store.create(
        recruiter_id="recruiter-1", query="Java Developer", session_data={}, rankings=_make_rankings(25)
    )

    page1 = store.get_page(session_id, page=1, page_size=20)
    page2 = store.get_page(session_id, page=2, page_size=20)

    assert len(page2.rankings) == 5
    assert page2.has_next is False
    assert page2.has_previous is True
    page1_ids = {r.candidate_id for r in page1.rankings}
    page2_ids = {r.candidate_id for r in page2.rankings}
    assert page1_ids.isdisjoint(page2_ids)


def test_get_page_preserves_match_result_fields(store):
    session_id = store.create(
        recruiter_id="recruiter-1", query="Java Developer", session_data={}, rankings=_make_rankings(1)
    )
    page = store.get_page(session_id, page=1, page_size=20)

    ranked = page.rankings[0]
    assert ranked.match.overall_score == 100.0
    assert ranked.match.component_scores == {"skills": 100.0}
    assert ranked.match.matched_fields == ["skills"]
    assert ranked.match.reasons == ["matched for cand-0"]


def test_get_page_raises_for_unknown_session(store):
    with pytest.raises(SearchSessionNotFoundError):
        store.get_page("does-not-exist", page=1, page_size=20)


def test_session_data_round_trips(store):
    session_data = {"requirement": {"role": "Java Developer"}, "search_plan": {"strict": []}}
    session_id = store.create(
        recruiter_id="recruiter-1", query="Java Developer", session_data=session_data, rankings=_make_rankings(1)
    )
    page = store.get_page(session_id, page=1, page_size=20)
    assert page.session_data == session_data
    assert page.query == "Java Developer"


def test_two_searches_create_independent_sessions(store):
    session_a = store.create(
        recruiter_id="recruiter-1", query="Java Developer", session_data={}, rankings=_make_rankings(3)
    )
    session_b = store.create(
        recruiter_id="recruiter-1", query="Java Developer", session_data={}, rankings=_make_rankings(5)
    )

    assert session_a != session_b
    assert store.get_page(session_a, page=1, page_size=20).total_count == 3
    assert store.get_page(session_b, page=1, page_size=20).total_count == 5


def test_create_dedupes_duplicate_candidate_ids_defensively(store):
    dup_rankings = [_ranked("cand-x", rank=1), _ranked("cand-x", rank=2)]
    session_id = store.create(
        recruiter_id="recruiter-1", query="Java Developer", session_data={}, rankings=dup_rankings
    )
    page = store.get_page(session_id, page=1, page_size=20)
    assert page.total_count == 1


# --- Sprint 35 Phase 2: min_score filtering ----------------------------------


def test_get_page_min_score_filters_out_weak_matches(store):
    """_make_rankings(25) scores candidates 100.0 down to 76.0 (100-i for
    i in 0..24) -- min_score=90 keeps scores 100..90 inclusive, 11
    candidates, regardless of page_size."""
    session_id = store.create(
        recruiter_id="recruiter-1", query="Java Developer", session_data={}, rankings=_make_rankings(25)
    )

    page = store.get_page(session_id, page=1, page_size=20, min_score=90.0)

    assert page.total_count == 11
    assert len(page.rankings) == 11
    assert all(r.match.overall_score >= 90.0 for r in page.rankings)
    # The TRUE total is unaffected by the filter.
    assert page.total_unfiltered_count == 25


def test_get_page_min_score_none_returns_everything_with_correct_unfiltered_count(store):
    session_id = store.create(
        recruiter_id="recruiter-1", query="Java Developer", session_data={}, rankings=_make_rankings(5)
    )

    page = store.get_page(session_id, page=1, page_size=20, min_score=None)

    assert page.total_count == 5
    assert page.total_unfiltered_count == 5


def test_get_page_min_score_paginates_the_filtered_set_correctly(store):
    """min_score=90 leaves exactly 11 matching candidates (scores
    100..90 inclusive) -- page_size=4 must paginate THAT filtered set,
    not the original 25, so page 3 holds the final 3 remaining matches."""
    session_id = store.create(
        recruiter_id="recruiter-1", query="Java Developer", session_data={}, rankings=_make_rankings(25)
    )

    page3 = store.get_page(session_id, page=3, page_size=4, min_score=90.0)

    assert page3.total_count == 11
    assert page3.total_pages == 3
    assert len(page3.rankings) == 3
    assert page3.has_next is False
    assert page3.has_previous is True


def test_recruiter_id_may_be_none_for_anonymous(store):
    session_id = store.create(recruiter_id=None, query="Java Developer", session_data={}, rankings=_make_rankings(1))
    page = store.get_page(session_id, page=1, page_size=20)
    assert page.total_count == 1
