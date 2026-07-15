"""First working end-to-end vertical slice of AlphaSource:

    POST /api/search
    { "query": "Find Product Engineers with AWS" }
        -> QueryUnderstandingService.parse(query)
        -> SearchPlanner.build_plan(requirement)
        -> CandidateRepository.search(plan)
        -> { requirement, search_plan, candidates, count } as JSON

Deliberately a separate router/path from the pre-existing POST /api/v1/search
(app/routers/search.py, which runs the older mock-connector pipeline from
the architecture phase) -- that route is untouched. This one wires together
the four modules built and approved since then (Knowledge Engine, Search
Planner, Query Understanding, Candidate Repository) into the first real
pipeline, with no ranking, no matching, no connectors, and no
authentication, per the brief.

Sprint 3: the response now also includes the intermediate pipeline state
(`requirement` and `search_plan`) alongside the candidate pool, so the
frontend can display what the AI understood and explain why each candidate
matched -- without the backend computing any new ranking or matching logic.
Both objects were already produced mid-pipeline; they are simply now
returned instead of discarded after use.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.candidate_repository.interfaces import CandidateRepository
from app.candidate_repository.models import Candidate
from app.candidate_repository.repository import get_candidate_repository
from app.query_understanding.models import (
    LLMClientError,
    QueryValidationError,
    ResponseParseError,
)
from app.query_understanding.service import QueryUnderstandingService
from app.search_planner.models import CanonicalJobRequirement, SearchPlan
from app.search_planner.planner import SearchPlanner

router = APIRouter(tags=["search-pipeline"])


# --- Request / response schemas ---------------------------------------------


class SearchQueryRequest(BaseModel):
    """Request body for POST /api/search.

    Sprint 31 addition: `page`/`page_size` -- used only by POST
    /api/search/smart (see discovery_search.py) to paginate through an
    already fully-computed, fully-ranked candidate pool. They are inert
    here: this endpoint (the original, untouched Sprint 3 pipeline) never
    reads them, so old callers that don't send them are unaffected."""

    query: str = Field(..., description="Recruiter's free-text hiring requirement")
    page: int = Field(1, ge=1, description="1-indexed page number (smart search only)")
    page_size: int = Field(20, ge=1, le=50, description="Candidates per page (smart search only)")
    # Sprint 35 Phase 2: whether to include below-relevance-threshold
    # matches in the response (smart search only) -- inert here, same
    # pattern as page/page_size above.
    include_weak_matches: bool = Field(
        False, description="Include below-threshold weak matches (smart search only)"
    )
    # Sprint 36: restrict results to one Source Group (e.g. "github") --
    # inert here, same pattern as the fields above. See
    # app/discovery/source_groups.py for the set of recognized source
    # strings; an unrecognized value simply yields zero results rather
    # than an error, same as any other filter with no matches.
    source_filter: str | None = Field(
        default=None, description="Restrict to one Source Group by `source` value (smart search only)"
    )


class SearchQueryResponse(BaseModel):
    """Response body for POST /api/search.

    Sprint 3 addition: alongside the raw candidate pool, the response now
    also returns the intermediate pipeline state -- `requirement` (what
    Query Understanding extracted) and `search_plan` (what the Knowledge
    Engine expanded it into) -- so the frontend can show the recruiter what
    the AI understood and why each candidate showed up, without the backend
    computing or scoring any of that explanation itself. This is a response
    shape change to an existing endpoint, not a new backend module, and adds
    no ranking or matching logic -- `requirement` and `search_plan` are
    exactly the objects already produced mid-pipeline; they are simply now
    included in the response instead of being discarded after use.

    `candidates` order still carries no ranking significance (see
    CandidateRepository.search()'s docstring). `count` is retained for
    convenience/backward compatibility with Sprint 2's response shape.
    """

    requirement: CanonicalJobRequirement
    search_plan: SearchPlan
    candidates: list[Candidate]
    count: int


# --- Dependency injection ----------------------------------------------------
# Each provider function is what makes every collaborator swappable/testable:
# FastAPI's dependency_overrides lets tests replace
# get_query_understanding_service with one wired to a fake LLM client
# without touching this router at all -- the same DI seam
# QueryUnderstandingService itself already exposes via its constructor.


def get_query_understanding_service() -> QueryUnderstandingService:
    return QueryUnderstandingService()


def get_search_planner() -> SearchPlanner:
    return SearchPlanner()


# get_candidate_repository is imported directly from
# app.candidate_repository.repository -- it already is a singleton-getter
# DI provider, per that module's own design; redefining it here would just
# be a second name for the same thing.


# --- Route --------------------------------------------------------------------


@router.post("/api/search", response_model=SearchQueryResponse)
def search(
    payload: SearchQueryRequest,
    query_service: QueryUnderstandingService = Depends(get_query_understanding_service),
    planner: SearchPlanner = Depends(get_search_planner),
    repository: CandidateRepository = Depends(get_candidate_repository),
) -> SearchQueryResponse:
    try:
        requirement = query_service.parse(payload.query)
    except QueryValidationError as e:
        # Recruiter input problem (e.g. empty query, or the LLM's second
        # attempt still didn't produce a valid shape) -> client error.
        raise HTTPException(status_code=422, detail=str(e)) from e
    except ResponseParseError as e:
        # The LLM provider didn't return parseable JSON even after the one
        # allowed retry -> treat as an upstream/dependency failure, not a
        # fault in the recruiter's request.
        raise HTTPException(status_code=502, detail=f"Query understanding failed: {e}") from e
    except LLMClientError as e:
        # The LLM provider call itself failed (missing API key, network
        # error, rate limit, SDK exception, etc.) -- an upstream dependency
        # failure, same class of problem as ResponseParseError above, just
        # one step earlier in the pipeline. Added during code review: this
        # previously propagated as an unhandled exception -> generic 500.
        raise HTTPException(status_code=502, detail=f"Query understanding failed: {e}") from e

    plan = planner.build_plan(requirement)
    candidates = repository.search(plan)

    return SearchQueryResponse(
        requirement=requirement,
        search_plan=plan,
        candidates=candidates,
        count=len(candidates),
    )
