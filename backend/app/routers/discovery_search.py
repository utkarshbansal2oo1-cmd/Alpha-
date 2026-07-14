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
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.candidate_repository.interfaces import CandidateRepository
from app.candidate_repository.models import Candidate
from app.candidate_repository.repository import get_candidate_repository
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

logger = logging.getLogger(__name__)

router = APIRouter(tags=["discovery"])


class SmartSearchResponse(BaseModel):
    """Same shape as search_pipeline.py's SearchQueryResponse, plus the
    `discovery` field (Sprint 18) describing what the Discovery Engine
    did, and `rankings` (Sprint 19): each returned candidate's match
    result and rank, in the same order as `candidates`."""

    requirement: CanonicalJobRequirement
    search_plan: SearchPlan
    candidates: list[Candidate]
    count: int
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
    candidates = ranking_engine.rank_candidates_by_id(rankings, candidates)

    return SmartSearchResponse(
        requirement=requirement,
        search_plan=plan,
        candidates=candidates,
        count=len(candidates),
        discovery=discovery_run,
        rankings=rankings,
    )
