"""Sprint 18/19/20B/20C: the Autonomous Talent Intelligence Platform's entry point.

A new, additive endpoint -- POST /api/search/smart -- built entirely on
top of the existing, unmodified pipeline (Query Understanding -> Search
Planner -> Candidate Repository) from search_pipeline.py. It does not
replace or modify POST /api/search; that endpoint, and every module it
depends on, is untouched, and remains available exactly as before.

Sprint 18 added: if the initial repository.search() result isn't good
enough (per the Discovery Decision Engine), invoke the Discovery
Orchestrator to pull in new candidates from connected sources and
re-search automatically, instead of returning a thin or empty result set.

Sprint 19 adds, on top of that, without changing any of it: every
candidate (before and after discovery) is scored by the new Matching
Engine across multiple weighted dimensions and ordered by the new
Ranking Engine -- no exact-match/first-match shortcut, every candidate is
evaluated (Module 2's explicit rule) -- and the Discovery Decision Engine
now uses those real match scores (instead of Sprint 18's simpler
requirement-term-overlap heuristic) to decide whether discovery is
needed. Connector wiring moved from an inline list to a ConnectorRegistry
(Module 6), and every threshold/weight is sourced from one injectable
MatchingConfig (Module 10).

Sprint 20B adds the GitHubDiscoveryConnector to that same registry --
GitHub's official REST API as one more connected, authorized source the
Discovery Orchestrator can pull candidates from, on equal footing with
Greenhouse and the Sprint 18 stubs.

Sprint 20C adds the Connector Intelligence Layer (app.discovery.
query_translation): a ConnectorQueryTranslator is now passed into
orchestrator.run() alongside the recruiter's raw query text, so a
connector like GitHub can receive several connector-native search
expressions instead of one literal job title. Nothing about the
orchestrator's decision/import/re-search flow, or any connector's own
implementation, changes -- see orchestrator.py's own docstring for
exactly what stays byte-for-byte identical when no translator is used.

Sprint 33 (this change): pagination is no longer "recompute the whole
pool and slice it" per request (Sprint 31's approach). POST /api/search/
smart now runs the full pipeline -- Query Understanding through Ranking
-- exactly ONCE, persists the ranked output as a SearchSession (see
app/search_sessions/store.py), and returns page 1 plus a `session_id`.
GET /api/search/session/{session_id} pages through that SAME stored
output -- no Query Understanding, Search Planner, Discovery, Matching,
or Ranking re-run, ever, for that search. A second POST is always a new
search: it runs the full pipeline again and creates an independent,
unrelated session, exactly matching the product's explicit "search
again" requirement.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.dependencies import get_current_recruiter
from app.candidate_repository.interfaces import CandidateRepository
from app.candidate_repository.models import Candidate
from app.candidate_repository.repository import get_candidate_repository
from app.models.recruiter import RecruiterRow
from app.discovery.connector_registry import ConnectorRegistry
from app.discovery.connectors.future_connectors import (
    BrowserExtensionDiscoveryConnector,
    CsvImportDiscoveryConnector,
    HrmsDiscoveryConnector,
    ResumeImportDiscoveryConnector,
)
from app.discovery.connectors.github_connector import GitHubDiscoveryConnector
from app.discovery.connectors.greenhouse_connector import GreenhouseDiscoveryConnector
from app.discovery.decision_engine import DiscoveryDecisionEngine
from app.discovery.models import DiscoveryRun
from app.discovery.orchestrator import DiscoveryOrchestrator
from app.discovery.query_translation.models import ConnectorTranslationConfig, get_connector_translation_config
from app.discovery.query_translation.translator import ConnectorQueryTranslator
from app.integrations.github.config import GitHubConfigStore, get_github_config_store
from app.integrations.greenhouse.config import GreenhouseConfigStore, get_greenhouse_config_store
from app.matching.config import MatchingConfig, get_matching_config
from app.matching.engine import MatchingEngine
from app.matching.models import RankedCandidate
from app.matching.ranking import RankingEngine
from app.query_understanding.models import LLMClientError, QueryValidationError, ResponseParseError
from app.query_understanding.service import QueryUnderstandingService
from app.routers.search_pipeline import (
    SearchQueryRequest,
    get_query_understanding_service,
    get_search_planner,
)
from app.search_planner.models import CanonicalJobRequirement, SearchPlan
from app.search_planner.planner import SearchPlanner
from app.search_sessions.store import SearchSessionNotFoundError, SearchSessionStore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["discovery"])


class SmartSearchResponse(BaseModel):
    """Same shape as search_pipeline.py's SearchQueryResponse, plus the
    `discovery` field (Sprint 18) describing what the Discovery Engine
    did, and `rankings` (Sprint 19): each returned candidate's match
    result and rank, in the same order as `candidates`.

    Sprint 33: `session_id` identifies the persisted SearchSession this
    response's page came from -- pass it to GET /api/search/session/
    {session_id} to page through the SAME ranked pool without re-running
    the pipeline. `has_next`/`has_previous` are provided alongside
    `page`/`total_pages` so the frontend doesn't need to compute them.
    This is the exact same response shape returned by both endpoints, so
    the frontend renders a page identically regardless of which one
    produced it."""

    session_id: str
    requirement: CanonicalJobRequirement
    search_plan: SearchPlan
    candidates: list[Candidate]
    count: int
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
    discovery: DiscoveryRun
    rankings: list[RankedCandidate]


# --- Dependency injection ----------------------------------------------------
# Same pattern search_pipeline.py already established: plain provider
# functions, swappable via FastAPI's dependency_overrides in tests.


def get_discovery_decision_engine(
    config: MatchingConfig = Depends(get_matching_config),
) -> DiscoveryDecisionEngine:
    return DiscoveryDecisionEngine(
        min_result_threshold=config.min_candidate_threshold,
        min_confidence_threshold=config.min_score,
    )


def get_matching_engine(config: MatchingConfig = Depends(get_matching_config)) -> MatchingEngine:
    return MatchingEngine(config=config)


def get_ranking_engine() -> RankingEngine:
    return RankingEngine()


def get_query_translator(
    config: ConnectorTranslationConfig = Depends(get_connector_translation_config),
) -> ConnectorQueryTranslator:
    return ConnectorQueryTranslator(config=config)


def get_connector_registry(
    config_store: GreenhouseConfigStore = Depends(get_greenhouse_config_store),
    github_config_store: GitHubConfigStore = Depends(get_github_config_store),
    config: MatchingConfig = Depends(get_matching_config),
) -> ConnectorRegistry:
    registry = ConnectorRegistry(config=config)
    registry.register(GreenhouseDiscoveryConnector(config_store))
    registry.register(GitHubDiscoveryConnector(github_config_store))  # Sprint 20B
    registry.register(BrowserExtensionDiscoveryConnector())
    registry.register(CsvImportDiscoveryConnector())
    registry.register(ResumeImportDiscoveryConnector())
    registry.register(HrmsDiscoveryConnector())
    return registry


def get_discovery_orchestrator(
    repository: CandidateRepository = Depends(get_candidate_repository),
    registry: ConnectorRegistry = Depends(get_connector_registry),
    decision_engine: DiscoveryDecisionEngine = Depends(get_discovery_decision_engine),
) -> DiscoveryOrchestrator:
    return DiscoveryOrchestrator(connectors=registry, repository=repository, decision_engine=decision_engine)


_search_session_store_instance: SearchSessionStore | None = None


def get_search_session_store() -> SearchSessionStore:
    """Process-wide singleton, same lazy-construction pattern as
    get_candidate_repository() -- constructing a SearchSessionStore
    doesn't touch the database until create()/get_page() is actually
    called, so this is safe to call unconditionally."""
    global _search_session_store_instance
    if _search_session_store_instance is None:
        _search_session_store_instance = SearchSessionStore()
    return _search_session_store_instance


def _candidates_for_rankings(
    rankings: list[RankedCandidate], repository: CandidateRepository
) -> tuple[list[Candidate], list[RankedCandidate]]:
    """Re-fetches each ranked candidate_id from the repository, in rank
    order. A candidate that no longer exists (unlikely, but the
    repository is the sole source of truth, not this session's stored
    ids) is skipped rather than raising -- its ranking entry is dropped
    alongside it so `candidates` and `rankings` stay 1:1, same invariant
    discovery_search.py has always maintained."""
    candidates: list[Candidate] = []
    surviving_rankings: list[RankedCandidate] = []
    for ranked in rankings:
        candidate = repository.get_by_id(ranked.candidate_id)
        if candidate is None:
            continue
        candidates.append(candidate)
        surviving_rankings.append(ranked)
    return candidates, surviving_rankings


@router.post("/api/search/smart", response_model=SmartSearchResponse)
def smart_search(
    payload: SearchQueryRequest,
    query_service: QueryUnderstandingService = Depends(get_query_understanding_service),
    planner: SearchPlanner = Depends(get_search_planner),
    repository: CandidateRepository = Depends(get_candidate_repository),
    orchestrator: DiscoveryOrchestrator = Depends(get_discovery_orchestrator),
    matching_engine: MatchingEngine = Depends(get_matching_engine),
    ranking_engine: RankingEngine = Depends(get_ranking_engine),
    query_translator: ConnectorQueryTranslator = Depends(get_query_translator),
    session_store: SearchSessionStore = Depends(get_search_session_store),
    _recruiter: RecruiterRow = Depends(get_current_recruiter),  # Sprint 30: no-op unless REQUIRE_AUTH is on
) -> SmartSearchResponse:
    try:
        requirement = query_service.parse(payload.query)
    except QueryValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except ResponseParseError as e:
        raise HTTPException(status_code=502, detail=f"Query understanding failed: {e}") from e
    except LLMClientError as e:
        raise HTTPException(status_code=502, detail=f"Query understanding failed: {e}") from e

    plan = planner.build_plan(requirement)
    candidates = repository.search(plan)

    # Sprint 26: repository.search() is a keyword/role pre-filter -- useful
    # for the Decision Engine's "did we already have an obvious match"
    # signal, but it must not be the only thing standing between a
    # candidate and the recruiter's screen. Merge in the rest of the
    # internal pool (deduped by id) so the Matching Engine scores, and the
    # Ranking Engine ranks, every candidate on file -- not just the subset
    # whose role/skills happened to literally match a search term. The
    # system's job is to surface everyone with an honest confidence bar;
    # deciding who's "good enough" is the recruiter's call, not this
    # endpoint's. (Explicit product requirement: a TA searching for one
    # role should see every plausible profile, ranked, not a silently
    # pre-filtered shortlist of one.)
    seen_ids = {c.id for c in candidates}
    candidates = candidates + [c for c in repository.all() if c.id not in seen_ids]

    # Module 1/2: every candidate is scored and ranked -- no exact-match
    # or first-match shortcut -- before the Decision Engine ever looks at
    # the result quality.
    matches = matching_engine.score_all(candidates, requirement, plan, raw_query=payload.query)

    discovery_run, candidates = orchestrator.run(
        requirement,
        plan,
        candidates,
        match_results=matches,
        query_translator=query_translator,  # Sprint 20C: Connector Intelligence Layer
        raw_query=payload.query,
    )

    if discovery_run.triggered:
        # Discovery may have imported new candidates and re-run
        # repository.search() -- re-score against the refreshed set
        # rather than reusing pre-discovery scores.
        matches = matching_engine.score_all(candidates, requirement, plan, raw_query=payload.query)

    rankings = ranking_engine.rank(candidates, matches)

    # Sprint 33: this is the ONLY place the full pipeline's ranked output
    # is computed. Persist it now -- every page of this search, including
    # this first one, is served by slicing this stored session, never by
    # recomputing any of the above.
    session_id = session_store.create(
        recruiter_id=_recruiter.id,
        query=payload.query,
        session_data={
            "requirement": requirement.model_dump(mode="json"),
            "search_plan": plan.model_dump(mode="json"),
            "discovery": discovery_run.model_dump(mode="json"),
        },
        rankings=rankings,
    )

    page = session_store.get_page(session_id, page=payload.page, page_size=payload.page_size)
    page_candidates, page_rankings = _candidates_for_rankings(page.rankings, repository)

    return SmartSearchResponse(
        session_id=session_id,
        requirement=requirement,
        search_plan=plan,
        candidates=page_candidates,
        count=len(page_candidates),
        total_count=page.total_count,
        page=page.page,
        page_size=page.page_size,
        total_pages=page.total_pages,
        has_next=page.has_next,
        has_previous=page.has_previous,
        discovery=discovery_run,
        rankings=page_rankings,
    )


@router.get("/api/search/session/{session_id}", response_model=SmartSearchResponse)
def get_search_session_page(
    session_id: str,
    page: int = 1,
    page_size: int = 20,
    repository: CandidateRepository = Depends(get_candidate_repository),
    session_store: SearchSessionStore = Depends(get_search_session_store),
    _recruiter: RecruiterRow = Depends(get_current_recruiter),
) -> SmartSearchResponse:
    """Sprint 33: pages through an already-completed search's stored,
    ranked output. Deliberately does NOT touch QueryUnderstandingService,
    SearchPlanner, DiscoveryOrchestrator, MatchingEngine, or RankingEngine
    -- every one of those ran exactly once, back in the POST that created
    this session. Only the CandidateRepository is used here, to re-fetch
    the actual Candidate objects for this page's slice of ranked ids."""
    if page < 1:
        raise HTTPException(status_code=422, detail="page must be >= 1")
    if page_size < 1 or page_size > 50:
        raise HTTPException(status_code=422, detail="page_size must be between 1 and 50")

    try:
        session_page = session_store.get_page(session_id, page=page, page_size=page_size)
    except SearchSessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    candidates, rankings = _candidates_for_rankings(session_page.rankings, repository)
    session_data = session_page.session_data

    return SmartSearchResponse(
        session_id=session_page.session_id,
        requirement=CanonicalJobRequirement.model_validate(session_data["requirement"]),
        search_plan=SearchPlan.model_validate(session_data["search_plan"]),
        candidates=candidates,
        count=len(candidates),
        total_count=session_page.total_count,
        page=session_page.page,
        page_size=session_page.page_size,
        total_pages=session_page.total_pages,
        has_next=session_page.has_next,
        has_previous=session_page.has_previous,
        discovery=DiscoveryRun.model_validate(session_data["discovery"]),
        rankings=rankings,
    )
