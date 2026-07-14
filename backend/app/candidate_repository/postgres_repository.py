"""Postgres-backed CandidateRepository -- Sprint 30.

Replaces InMemoryCandidateRepository's process-memory list with a real
`candidates` table (see app/models/candidate.py) so candidates survive a
restart or redeploy -- the standing gap flagged repeatedly before this
sprint ("everything disappears on every Railway restart").

Deliberately reuses, rather than reimplements, every search/dedup/merge
algorithm from app/candidate_repository/merge.py -- the exact same pure
functions InMemoryCandidateRepository now delegates to (see Sprint 30's
refactor of that class). This repository's only real job is: load the
current pool from Postgres into `list[Candidate]`, hand it to the shared
functions, then write back whatever they decided. At this POC's candidate
volume (dozens to low hundreds, not millions), loading the full pool per
call is simple and fast enough -- the same "don't optimize what isn't
proven to be a bottleneck" judgment already applied elsewhere in this
codebase (e.g. InMemoryCandidateRepository.search()'s own linear scan).
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.candidate_repository.interfaces import CandidateRepository
from app.candidate_repository.merge import compute_upsert, find_potential_duplicate_in, search_in
from app.candidate_repository.models import Candidate
from app.candidate_repository.seed_loader import DEFAULT_SEED_PATH, load_seed_candidates
from app.database import SessionLocal
from app.models.candidate import CandidateRow
from app.search_planner.models import SearchPlan


class PostgresCandidateRepository(CandidateRepository):
    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        seed_path: Path | None = None,
    ):
        self._session_factory = session_factory or SessionLocal
        self._seed_path = seed_path or DEFAULT_SEED_PATH
        self._ensure_seeded()

    def _ensure_seeded(self) -> None:
        """Bootstraps the seed candidate pool into the table on first use --
        mirrors InMemoryCandidateRepository's constructor-time seed load,
        but only runs once (checked via row count) since a real table
        persists across process restarts, unlike a Python list."""
        with self._session_factory() as db:
            existing_count = db.execute(select(CandidateRow.id)).first()
            if existing_count is not None:
                return

            seed_candidates = load_seed_candidates(self._seed_path)
            for candidate in seed_candidates:
                db.add(CandidateRow(id=candidate.id, data=candidate.model_dump(mode="json")))
            db.commit()

    def _load_all(self, db: Session) -> list[Candidate]:
        rows = db.execute(select(CandidateRow)).scalars().all()
        return [Candidate.model_validate(row.data) for row in rows]

    def search(self, plan: SearchPlan) -> list[Candidate]:
        with self._session_factory() as db:
            return search_in(self._load_all(db), plan)

    def all(self) -> list[Candidate]:
        with self._session_factory() as db:
            return self._load_all(db)

    def get_by_id(self, candidate_id: str) -> Candidate | None:
        with self._session_factory() as db:
            row = db.get(CandidateRow, candidate_id)
            return Candidate.model_validate(row.data) if row else None

    def find_potential_duplicate(self, candidate: Candidate) -> Candidate | None:
        with self._session_factory() as db:
            return find_potential_duplicate_in(self._load_all(db), candidate)

    def upsert(self, candidate: Candidate) -> Candidate:
        with self._session_factory() as db:
            result = compute_upsert(self._load_all(db), candidate)

            row = db.get(CandidateRow, result.candidate.id)
            if row is None:
                db.add(CandidateRow(id=result.candidate.id, data=result.candidate.model_dump(mode="json")))
            else:
                row.data = result.candidate.model_dump(mode="json")
            db.commit()

            return result.candidate
