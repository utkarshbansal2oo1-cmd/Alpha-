"""Composition root for the Candidate Repository module.

Exposes get_candidate_repository(), the single function the rest of the
application should use to obtain a CandidateRepository -- mirroring the
same singleton-getter pattern already used for the Knowledge Engine
(app.knowledge.engine.get_knowledge_engine()) and the connector registry
(app.services.connectors.registry.get_active_connectors()). Callers depend
on the CandidateRepository interface and this getter, never on
InMemoryCandidateRepository directly.

Sprint 30: which concrete implementation this returns is now a config
choice (settings.CANDIDATE_REPOSITORY_BACKEND), same pattern as Sprint 29's
QUERY_PROVIDER -- "memory" (default, zero setup, matches every existing
test) or "postgres" (persists across restarts, requires a reachable
DATABASE_URL with migrations applied). This is exactly the "swapping in a
database-backed repository later is a one-line change here" this module's
docstring always promised.
"""
from __future__ import annotations

from app.candidate_repository.interfaces import CandidateRepository
from app.candidate_repository.memory_repository import InMemoryCandidateRepository
from app.config import settings

_repository_instance: CandidateRepository | None = None


def _build_repository() -> CandidateRepository:
    backend = settings.CANDIDATE_REPOSITORY_BACKEND.strip().lower()
    if backend == "postgres":
        from app.candidate_repository.postgres_repository import PostgresCandidateRepository

        return PostgresCandidateRepository()
    if backend == "memory":
        return InMemoryCandidateRepository()
    raise ValueError(f"Unknown CANDIDATE_REPOSITORY_BACKEND: {backend!r} (expected 'memory' or 'postgres')")


def get_candidate_repository() -> CandidateRepository:
    """Returns the process-wide CandidateRepository singleton, constructing
    it (and loading its seed data) on first access.
    """
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = _build_repository()
    return _repository_instance
