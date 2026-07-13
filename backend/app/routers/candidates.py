from fastapi import APIRouter, HTTPException

from app.schemas import CandidateDetailOut, CandidateSourceOut, ShortlistRequest
from app.services.pipeline import get_candidate_detail

router = APIRouter(prefix="/api/v1", tags=["candidates"])


@router.get("/candidates/{candidate_id}", response_model=CandidateDetailOut)
def get_candidate(candidate_id: str) -> CandidateDetailOut:
    entry = get_candidate_detail(candidate_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate = entry["candidate"]
    return CandidateDetailOut(
        candidate_id=entry["id"],
        full_name=candidate.full_name,
        email=candidate.email,
        phone=candidate.phone,
        location=candidate.location,
        current_title=candidate.current_title,
        current_company=candidate.current_company,
        total_experience_yrs=candidate.total_experience_yrs,
        skills=candidate.skills,
        summary=candidate.summary,
        resume_url=candidate.resume_url,
        sources=[
            CandidateSourceOut(name=s, external_id=candidate.external_id, fetched_at="")
            for s in entry["sources"]
        ],
    )


@router.post("/candidates/{candidate_id}/shortlist", status_code=202)
def shortlist_candidate(candidate_id: str, payload: ShortlistRequest) -> dict:
    entry = get_candidate_detail(candidate_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Candidate not found")
    # Stub: real integration will POST this candidate + search context into AlphaRecrewt.
    return {"status": "queued", "candidate_id": candidate_id, "target": "alpharecrewt"}
