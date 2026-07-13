from fastapi import APIRouter

from app.schemas import SearchRequest, SearchResponse
from app.services.pipeline import run_search

router = APIRouter(prefix="/api/v1", tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest) -> SearchResponse:
    return run_search(payload.query)
