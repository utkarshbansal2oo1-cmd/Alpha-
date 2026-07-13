"""Composition root for the Candidate Repository module.

Exposes get_candidate_repository(), the single function the rest of the
application should use to obtain a CandidateRepository -- mirroring the
same singleton-getter pattern already used for the Knowledge Engine
(app.knowledge.engine.get_knowledge_engine()) and the connector registry
(app.services.connectors.registry.get_active_connectors()). Callers depend
on the CandidateRepository interface and this getter, never on
InMemoryCandidateRepository directly, so swapping in a database-backed or
connector-fanned-out repository later is a one-line change here.
"""
from __future__ import annotations

from app.candidate_repository.interfaces import CandidateRepository
from app.candidate_repository.memory_repository import InMemoryCandidateRepository

_repository_instance: CandidateRepository | None = None


def get_candidate_repository() -> CandidateRepository:
    """Returns the process-wide CandidateRepository singleton, constructing
    it (and loading its seed data) on first access.
    """
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = InMemoryCandidateRepository()
    return _repository_instance
