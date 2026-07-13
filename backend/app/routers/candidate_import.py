"""POST /candidate/import -- the backend counterpart of the browser
extension's "Add to AlphaSource" capture flow.

Deliberately a separate router/path from the existing search pipeline
(app/routers/search_pipeline.py) and the legacy /api/v1/candidates routes
(app/routers/candidates.py) -- neither of those is modified. This endpoint
is the only new write path into the candidate pool; everything downstream
of it (search(), the /api/search pipeline, the marketing/product UI) is
completely unaware of where a given Candidate came from and requires no
changes to treat a captured candidate the same as a seed-data one.

Pipeline: validate (Pydantic) -> normalize (normalizer.py) -> dedup-check +
create-or-update (CandidateRepository.upsert(), which internally calls
find_potential_duplicate()) -> return the resulting Candidate's id.

"Candidate Intelligence" for this POC (Sprint 12 Phase 7) is limited to
what normalize_import() already produces (a templated summary when the
page had none) plus the fact that the candidate is immediately searchable
through the existing, unmodified CandidateRepository.search() the moment
this call returns -- there is no separate AI-summary or search-indexing
step to run, because none of that logic lives outside the repository/
search-pipeline modules this sprint is explicitly not allowed to touch.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.candidate_repository.import_schemas import (
    CandidateImportRequest,
    CandidateImportResponse,
)
from app.candidate_repository.interfaces import CandidateRepository
from app.candidate_repository.normalizer import normalize_import
from app.candidate_repository.repository import get_candidate_repository

router = APIRouter(tags=["candidate-import"])


@router.post("/candidate/import", response_model=CandidateImportResponse, status_code=201)
def import_candidate(
    payload: CandidateImportRequest,
    repository: CandidateRepository = Depends(get_candidate_repository),
) -> CandidateImportResponse:
    if not payload.name.strip():
        # Pydantic's min_length=1 already blocks an empty string, but a
        # whitespace-only name would pass that check and produce a
        # nameless-looking candidate record -- reject it explicitly with a
        # clear message rather than silently normalizing it away.
        raise HTTPException(status_code=422, detail="Candidate name cannot be blank")

    candidate = normalize_import(payload)

    existing_match = repository.find_potential_duplicate(candidate)
    result = repository.upsert(candidate)

    return CandidateImportResponse(
        candidate_id=result.id,
        created=existing_match is None,
        version=result.version,
    )
