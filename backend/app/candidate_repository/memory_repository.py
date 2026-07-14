"""In-memory CandidateRepository implementation, backed by a JSON seed file.

Retrieval (search()/all()) is unchanged from before Sprint 12: filters the
pool by role/skill membership against a SearchPlan's flattened
search_terms, no ranking, no scoring. Swapping this for a real
database-backed repository later means implementing the same
CandidateRepository interface, not changing any caller -- see Sprint 30's
PostgresCandidateRepository for exactly that.

Sprint 12 adds the write path -- upsert()/find_potential_duplicate() --
supporting the browser extension's candidate capture flow (see
docs/BROWSER_EXTENSION_ARCHITECTURE.md).

Sprint 14 wires the Candidate Intelligence Lifecycle into both the initial
seed load and every upsert().

Sprint 30: the actual search/dedup/merge/seed-load algorithms were
extracted verbatim into app/candidate_repository/merge.py and
seed_loader.py, so PostgresCandidateRepository can share them exactly
rather than duplicating this logic. This class now only owns "how to
store a Python list in process memory" -- append vs. replace-by-identity
-- everything about *what* the resulting Candidate should look like lives
in the shared functions. Behavior is byte-for-byte unchanged; every
pre-Sprint-30 test in tests.py still passes untouched.
"""
from __future__ import annotations

from pathlib import Path

from app.candidate_repository.interfaces import CandidateRepository
from app.candidate_repository.merge import compute_upsert, find_potential_duplicate_in, search_in
from app.candidate_repository.models import Candidate
from app.candidate_repository.seed_loader import (
    CandidateSeedDataError,  # noqa: F401 -- re-exported, existing callers import it from here
    DEFAULT_SEED_PATH as _DEFAULT_SEED_PATH,
    load_seed_candidates,
)
from app.search_planner.models import SearchPlan


class InMemoryCandidateRepository(CandidateRepository):
    def __init__(self, seed_path: Path | None = None):
        self._seed_path = seed_path or _DEFAULT_SEED_PATH
        self._candidates: list[Candidate] = load_seed_candidates(self._seed_path)

    def search(self, plan: SearchPlan) -> list[Candidate]:
        return search_in(self._candidates, plan)

    def all(self) -> list[Candidate]:
        return list(self._candidates)

    def get_by_id(self, candidate_id: str) -> Candidate | None:
        for candidate in self._candidates:
            if candidate.id == candidate_id:
                return candidate
        return None

    # --- Sprint 12: write path for browser-extension capture -------------

    def find_potential_duplicate(self, candidate: Candidate) -> Candidate | None:
        return find_potential_duplicate_in(self._candidates, candidate)

    def upsert(self, candidate: Candidate) -> Candidate:
        result = compute_upsert(self._candidates, candidate)

        if result.previous is None:
            self._candidates.append(result.candidate)
        else:
            index = self._candidates.index(result.previous)
            self._candidates[index] = result.candidate

        return result.candidate
