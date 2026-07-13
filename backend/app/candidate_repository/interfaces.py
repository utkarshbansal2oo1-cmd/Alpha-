"""The repository contract every candidate data source implementation must
satisfy. Mirrors the same "one interface, many implementations" pattern
already established by SourceConnector (backend/app/services/connectors/base.py)
-- this is deliberate, not a new pattern: an in-memory repository, a
Postgres-backed repository, and a repository that fans out to real
connectors should all be interchangeable behind this one interface.

Sprint 12 addition: `upsert()` and `find_potential_duplicate()` are new,
additive abstract methods supporting the browser extension's candidate
capture flow (docs/BROWSER_EXTENSION_ARCHITECTURE.md). `search()`'s
contract and behavior are completely unchanged -- this is a strictly
additive extension of the interface, not a redesign of it.

Sprint 14 addition: `get_by_id()` -- needed so the new Candidate
Intelligence endpoints (health/enrichment-plan/evidence-timeline/versions,
see docs/CANDIDATE_INTELLIGENCE_LIFECYCLE.md) can look up one candidate
without going through search(). Read-only, like search()/all().
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.candidate_repository.models import Candidate
from app.search_planner.models import SearchPlan


class CandidateRepository(ABC):
    """Retrieves candidates matching a SearchPlan. Retrieval only -- no
    ranking, no scoring, no AI, no connectors, no database access is
    prescribed by the interface itself; those are implementation details of
    whichever concrete repository is behind it.
    """

    @abstractmethod
    def search(self, plan: SearchPlan) -> list[Candidate]:
        """Returns every Candidate that matches the given SearchPlan.

        "Matches" here means retrieval-level filtering only (does this
        candidate's role/skills intersect the plan's search terms) -- it is
        explicitly NOT ranking or scoring. Order of the returned list is not
        significant; a downstream Matching Engine (not part of this module)
        is responsible for scoring and ordering.
        """
        raise NotImplementedError

    @abstractmethod
    def find_potential_duplicate(self, candidate: Candidate) -> Candidate | None:
        """Returns an existing Candidate this one likely represents the same
        person as, or None if no match is found. See
        docs/BROWSER_EXTENSION_ARCHITECTURE.md Phase 6 for the matching
        signals and confidence reasoning -- deliberately conservative,
        mirroring the same reasoning already established in
        docs/EVIDENCE_GRAPH_ARCHITECTURE.md section 9.2 (false merges are
        more damaging than false separations).
        """
        raise NotImplementedError

    @abstractmethod
    def upsert(self, candidate: Candidate) -> Candidate:
        """Creates a new Candidate record, or merges into an existing one if
        `find_potential_duplicate` finds a match. Returns the resulting
        (created or merged) Candidate. This is the only write path into the
        repository -- `search()` and `all()` remain read-only as before.
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, candidate_id: str) -> Candidate | None:
        """Returns the Candidate with this id, or None if it doesn't exist.
        Read-only, like search()/all() -- added for the Candidate
        Intelligence Lifecycle's per-candidate endpoints (health,
        enrichment plan, evidence timeline, version history), none of
        which need a SearchPlan.
        """
        raise NotImplementedError
