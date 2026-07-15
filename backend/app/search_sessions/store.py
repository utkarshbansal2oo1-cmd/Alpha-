"""Persistent search sessions -- Sprint 33.

The whole point: POST /api/search/smart runs Query Understanding, Search
Planner, Discovery (including live connector calls like GitHub),
Matching, and Ranking exactly ONCE per search, then SearchSessionStore
persists the ranked output. Every subsequent page (GET /api/search/
session/{id}) reads that stored output -- none of those six stages ever
runs again for the same search. A genuinely new search (a new POST) is
the only thing that runs the pipeline again, and it always creates a
brand-new, independent session -- this store never merges into or
extends an existing one (see `create()`'s own docstring).

Deliberately NOT the same class as ConnectorCredentialStore or AuthService
even though it follows the identical session_factory-injection pattern
established by both -- sessions are pipeline-output data, not secrets or
identity, so this has no encryption and no password hashing, just plain
persisted structured data.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.database import SessionLocal
from app.matching.models import MatchResult, RankedCandidate
from app.models.search_session import SearchSessionCandidateRow, SearchSessionRow


@dataclass
class SearchSessionPage:
    session_id: str
    query: str
    session_data: dict
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
    rankings: list[RankedCandidate]  # already sliced to this page, in rank order
    # Sprint 35 Phase 2: the TRUE total candidate count for this session,
    # regardless of any min_score filtering applied to `total_count`/
    # `rankings` above -- lets a caller report "42 weaker matches hidden"
    # even on a filtered page.
    total_unfiltered_count: int = 0


class SearchSessionNotFoundError(Exception):
    """Raised by get_page() when session_id doesn't exist -- e.g. an
    expired/garbage-collected session (none exist yet -- sessions are
    never deleted by this sprint) or simply a typo'd/stale id."""


class SearchSessionStore:
    def __init__(self, session_factory: sessionmaker[Session] | None = None):
        self._session_factory = session_factory or SessionLocal

    def create(
        self,
        *,
        recruiter_id: str | None,
        query: str,
        session_data: dict,
        rankings: list[RankedCandidate],
        candidate_sources: dict[str, str] | None = None,
    ) -> str:
        """Persists one full pipeline run's ranked output as a brand-new
        session -- always an insert, never an update. A recruiter running
        the "same" search again is, per the product spec, a NEW search:
        this method has no notion of "the existing session for this
        query" and never looks one up to reuse.

        Sprint 36: `candidate_sources` (candidate_id -> Candidate.source)
        is optional so every pre-Sprint-36 caller keeps working unchanged
        (rows just get `source=None`) -- discovery_search.py's
        smart_search() already has every candidate's `.source` in memory
        at persist time, so it's a cheap dict to build and pass, not a
        second lookup."""
        session_id = str(uuid.uuid4())
        candidate_sources = candidate_sources or {}

        # Defensive dedup by candidate_id -- the Ranking Engine already
        # guarantees one entry per candidate, but the unique constraint
        # on (session_id, candidate_id) means a genuine duplicate here
        # would otherwise surface as an opaque IntegrityError instead of
        # silently doing the right thing.
        seen_ids: set[str] = set()
        deduped_rankings: list[RankedCandidate] = []
        for ranked in rankings:
            if ranked.candidate_id in seen_ids:
                continue
            seen_ids.add(ranked.candidate_id)
            deduped_rankings.append(ranked)

        with self._session_factory() as db:
            db.add(
                SearchSessionRow(
                    id=session_id,
                    recruiter_id=recruiter_id,
                    query=query,
                    total_count=len(deduped_rankings),
                    session_data=session_data,
                    created_at=datetime.now(timezone.utc),
                )
            )
            # There is no ORM-level relationship() between SearchSessionRow
            # and SearchSessionCandidateRow (just a plain FK column) -- so
            # the unit-of-work has no dependency edge to sort insert order
            # on, and nothing guarantees the parent row's INSERT is emitted
            # before the batched child INSERTs below in the same flush.
            # This flush executes the parent insert now, inside the same
            # transaction, before any child rows exist as pending objects --
            # fixes a latent FK-violation-on-Postgres bug that SQLite (used
            # in this store's tests) never happened to surface.
            db.flush()
            for ranked in deduped_rankings:
                db.add(
                    SearchSessionCandidateRow(
                        id=str(uuid.uuid4()),
                        session_id=session_id,
                        candidate_id=ranked.candidate_id,
                        rank=ranked.rank,
                        overall_score=ranked.match.overall_score,
                        component_scores=ranked.match.component_scores,
                        matched_fields=ranked.match.matched_fields,
                        missing_fields=ranked.match.missing_fields,
                        reasons=ranked.match.reasons,
                        source=candidate_sources.get(ranked.candidate_id),
                    )
                )
            db.commit()

        return session_id

    def get_page(
        self,
        session_id: str,
        page: int,
        page_size: int,
        min_score: float | None = None,
        source: str | None = None,
    ) -> SearchSessionPage:
        """Sprint 35 Phase 2: `min_score`, when given, restricts this page
        (and its pagination math) to candidates whose stored
        `overall_score >= min_score` -- e.g. a relevance threshold, so a
        recruiter's default view can hide weak matches without the
        Ranking Engine ever re-running. `total_unfiltered_count` on the
        returned page is always the TRUE total regardless of this filter,
        so a caller can report how many weak matches were hidden.

        Sprint 36: `source`, when given, additionally restricts this page
        to one Source Group (e.g. "GitHub only") -- the SAME underlying
        global rank order and scores are used, just filtered to rows
        whose stored `source` column matches. This is what lets future
        per-source filtering ("show me only Ashby candidates") work with
        no change to the Ranking Engine or to how a session is created --
        it's one more WHERE clause on an already-persisted, already-
        globally-ranked table, exactly like min_score above."""
        with self._session_factory() as db:
            session_row = db.get(SearchSessionRow, session_id)
            if session_row is None:
                raise SearchSessionNotFoundError(f"No search session found for id {session_id!r}.")

            total_unfiltered_count = session_row.total_count

            count_query = select(SearchSessionCandidateRow).where(
                SearchSessionCandidateRow.session_id == session_id
            )
            if min_score is not None:
                count_query = count_query.where(SearchSessionCandidateRow.overall_score >= min_score)
            if source is not None:
                count_query = count_query.where(SearchSessionCandidateRow.source == source)
            total_count = len(db.execute(count_query).scalars().all())

            total_pages = max(1, math.ceil(total_count / page_size)) if total_count else 1
            start = (page - 1) * page_size

            rows_query = (
                select(SearchSessionCandidateRow)
                .where(SearchSessionCandidateRow.session_id == session_id)
                .order_by(SearchSessionCandidateRow.rank)
            )
            if min_score is not None:
                rows_query = rows_query.where(SearchSessionCandidateRow.overall_score >= min_score)
            if source is not None:
                rows_query = rows_query.where(SearchSessionCandidateRow.source == source)
            candidate_rows = (
                db.execute(rows_query.offset(start).limit(page_size))
                .scalars()
                .all()
            )

            rankings = [
                RankedCandidate(
                    candidate_id=row.candidate_id,
                    rank=row.rank,
                    match=MatchResult(
                        candidate_id=row.candidate_id,
                        overall_score=row.overall_score,
                        component_scores=row.component_scores,
                        matched_fields=row.matched_fields,
                        missing_fields=row.missing_fields,
                        reasons=row.reasons,
                    ),
                )
                for row in candidate_rows
            ]

            return SearchSessionPage(
                session_id=session_id,
                query=session_row.query,
                session_data=session_row.session_data,
                total_count=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=(start + page_size) < total_count,
                has_previous=page > 1,
                rankings=rankings,
                total_unfiltered_count=total_unfiltered_count,
            )

    def get_source_counts(self, session_id: str, min_score: float | None = None) -> dict[str, int]:
        """Sprint 36: per-Source-Group totals for this session -- e.g.
        {"github": 18, "seed_data": 12} -- computed directly from the
        persisted rows, with no re-run of Discovery/Matching/Ranking.
        Used to build each Source Group's `candidate_count` on
        GET /api/search/session/{id} (the POST path already has this data
        in memory pre-persistence and doesn't need to call this). Rows
        with `source=None` (sessions created before Sprint 36, or by a
        caller that didn't pass `candidate_sources`) are reported under
        the key `None` rather than silently dropped."""
        with self._session_factory() as db:
            session_row = db.get(SearchSessionRow, session_id)
            if session_row is None:
                raise SearchSessionNotFoundError(f"No search session found for id {session_id!r}.")

            query = select(SearchSessionCandidateRow).where(
                SearchSessionCandidateRow.session_id == session_id
            )
            if min_score is not None:
                query = query.where(SearchSessionCandidateRow.overall_score >= min_score)
            rows = db.execute(query).scalars().all()

            counts: dict[str, int] = {}
            for row in rows:
                counts[row.source] = counts.get(row.source, 0) + 1
            return counts
