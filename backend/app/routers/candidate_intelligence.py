"""Read-only endpoints exposing the Candidate Intelligence Lifecycle
(Sprint 14, docs/CANDIDATE_INTELLIGENCE_LIFECYCLE.md) for one candidate at
a time. Deliberately separate from both the search pipeline
(routers/search_pipeline.py) and the capture endpoint
(routers/candidate_import.py) -- none of those files changed to support
this router.

  GET /candidate/{id}/health            -> HealthScore (recomputed fresh
                                            from current field values, not
                                            just the last-cached number, so
                                            it's always consistent with
                                            whatever's on the record right
                                            now)
  GET /candidate/{id}/enrichment-plan   -> EnrichmentPlan
  GET /candidate/{id}/evidence-timeline -> list[EvidenceEvent]
  GET /candidate/{id}/versions          -> list[CandidateSnapshot]

All four are pure reads against CandidateRepository.get_by_id() (Sprint 14
addition to the interface) -- none of them write anything.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.candidate_intelligence.enrichment_planner import plan_enrichment
from app.candidate_intelligence.health_engine import compute_health
from app.candidate_repository.interfaces import CandidateRepository
from app.candidate_repository.models import CandidateSnapshot, EnrichmentPlan, EvidenceEvent, HealthScore
from app.candidate_repository.repository import get_candidate_repository

router = APIRouter(tags=["candidate-intelligence"])


def _get_candidate_or_404(candidate_id: str, repository: CandidateRepository):
    candidate = repository.get_by_id(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"Candidate not found: {candidate_id}")
    return candidate


@router.get("/candidate/{candidate_id}/health", response_model=HealthScore)
def get_candidate_health(
    candidate_id: str,
    repository: CandidateRepository = Depends(get_candidate_repository),
) -> HealthScore:
    candidate = _get_candidate_or_404(candidate_id, repository)
    return compute_health(candidate)


@router.get("/candidate/{candidate_id}/enrichment-plan", response_model=EnrichmentPlan)
def get_candidate_enrichment_plan(
    candidate_id: str,
    repository: CandidateRepository = Depends(get_candidate_repository),
) -> EnrichmentPlan:
    candidate = _get_candidate_or_404(candidate_id, repository)
    health = compute_health(candidate)
    return plan_enrichment(candidate, health)


@router.get("/candidate/{candidate_id}/evidence-timeline", response_model=list[EvidenceEvent])
def get_candidate_evidence_timeline(
    candidate_id: str,
    repository: CandidateRepository = Depends(get_candidate_repository),
) -> list[EvidenceEvent]:
    candidate = _get_candidate_or_404(candidate_id, repository)
    # Newest first -- recruiters reviewing "what changed" care about recent
    # activity before ancient history.
    return sorted(candidate.evidence_history, key=lambda e: e.timestamp, reverse=True)


@router.get("/candidate/{candidate_id}/versions", response_model=list[CandidateSnapshot])
def get_candidate_versions(
    candidate_id: str,
    repository: CandidateRepository = Depends(get_candidate_repository),
) -> list[CandidateSnapshot]:
    candidate = _get_candidate_or_404(candidate_id, repository)
    return sorted(candidate.version_history, key=lambda s: s.version, reverse=True)
