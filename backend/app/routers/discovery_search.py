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
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

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
from app.discovery.source_groups import get_source_group_info
from app.integrations.github.config import GitHubConfigStore, get_github_config_store
from app.integrations.greenhouse.config import GreenhouseConfigStore, get_greenhouse_config_store
from app.matching.config import MatchingConfig, get_matching_config
from app.matching.engine import MatchingEngine
from app.matching.models import MatchResult, RankedCandidate
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


class CandidateProvenance(BaseModel):
    """Sprint 36: full provenance for one candidate, kept separate from
    Candidate itself (which stays exactly as the Candidate Repository
    defines it -- untouched per this sprint's explicit constraint).

    `source` (where this candidate belongs -- its Source Group) and
    `connector` (which mechanism most recently touched this record) are
    deliberately two different fields, not aliases of each other -- see
    app/discovery/source_groups.py's module docstring for why they can
    diverge once a candidate has been captured/enriched by more than one
    connector over its lifetime (Candidate.capture_sources already models
    that -- this is the first place that distinction is surfaced to a
    caller). Today, for every existing connector, they happen to be equal
    (a GitHub candidate's most recent capture IS the GitHub connector),
    but nothing here assumes that stays true forever.
    """

    candidate_id: str
    source: str
    connector: str
    discovery_method: str
    discovered_at: datetime | None = None
    last_updated: datetime | None = None
    evidence: list[str] = Field(default_factory=list)


class SourceGroup(BaseModel):
    """Sprint 36: a Source Group is a DOMAIN concept (where a candidate
    belongs), not a UI section -- the frontend renders one of these per
    group, but the grouping itself is computed here, from real discovery/
    ranking output, not invented for display. Every field is either
    presentation metadata from app/discovery/source_groups.py (display_name,
    icon, trust_level, is_live, is_fallback) or a real count/timing drawn
    from this search's actual DiscoveryRun/MatchResult/RankedCandidate
    data -- nothing here is fabricated to look complete.

    Global ranking is untouched: `rankings` here is a per-source SLICE of
    the one globally-computed rank list (see smart_search()'s single
    `ranking_engine.rank()` call) -- each RankedCandidate keeps its real,
    global `rank` number, so "rank 7 overall" and "rank 2 within GitHub"
    are both visible and never contradict each other."""

    source: str
    display_name: str
    icon: str
    trust_level: str
    is_live: bool
    is_fallback: bool
    candidate_count: int  # how many of this source are on THIS page/response
    searched_count: int  # how many this source's connector considered, session-wide
    qualified_count: int  # how many of this source cleared the relevance threshold, session-wide
    discovery_time_ms: float | None = None
    matching_time_ms: float | None = None
    ranking_time_ms: float | None = None
    candidates: list[Candidate]
    rankings: list[RankedCandidate]
    provenance: list[CandidateProvenance]


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

    # --- Sprint 35 (Phase 1 + Phase 2) additions ----------------------------
    # relevance_threshold: the score (0-100) below which a match is
    # considered "weak" for THIS search -- adaptive to pool size (see
    # MatchingConfig.adaptive_relevance_threshold). total_all_candidates/
    # weak_match_count describe the FULL ranked pool for this session,
    # regardless of `include_weak_matches` -- so the frontend can always
    # render "Show N weaker matches" even on a filtered page.
    # seed_fallback_used records whether Phase 1's GitHub-first/seed-as-
    # fallback decision actually pulled in seed_data candidates for this
    # search (False whenever live discovery alone was sufficient).
    relevance_threshold: float
    total_all_candidates: int
    weak_match_count: int
    include_weak_matches: bool
    seed_fallback_used: bool

    # --- Sprint 36 addition -------------------------------------------------
    # `source_groups`: the SAME globally-ranked `candidates`/`rankings`
    # above, additionally partitioned by Source Group for presentation --
    # never a second ranking, never a re-score. `candidates`/`rankings`
    # are kept as-is (not deprecated in this sprint) so any existing
    # caller of the flat shape is completely unaffected; `source_groups`
    # is the new, recommended way for the frontend to render results.
    source_groups: list[SourceGroup] = Field(default_factory=list)


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


def _build_provenance(candidate: Candidate, match: MatchResult | None) -> CandidateProvenance:
    """Sprint 36: derives full provenance entirely from fields Candidate
    already carries (capture_sources, github_last_activity) -- no schema
    change to Candidate itself. `connector` intentionally reads from the
    MOST RECENT capture_sources entry (not simply Candidate.source) so
    that once a candidate has been touched by more than one connector
    over its lifetime, `source` (its stable Source Group) and `connector`
    (what most recently touched it) can genuinely diverge, per this
    sprint's explicit Source-vs-Connector distinction."""
    group_info = get_source_group_info(candidate.source)
    if candidate.capture_sources:
        connector = candidate.capture_sources[-1].source_type
        discovered_at = candidate.capture_sources[0].capture_time
        last_updated = candidate.capture_sources[-1].capture_time
    else:
        connector = candidate.source
        discovered_at = None
        last_updated = candidate.github_last_activity if candidate.source == "github" else None
    return CandidateProvenance(
        candidate_id=candidate.id,
        source=candidate.source,
        connector=connector,
        discovery_method=group_info.discovery_method,
        discovered_at=discovered_at,
        last_updated=last_updated,
        evidence=list(match.reasons) if match is not None else [],
    )


def _build_source_groups(
    page_candidates: list[Candidate],
    page_rankings: list[RankedCandidate],
    searched_counts: dict[str, int],
    qualified_counts: dict[str, int],
) -> list[SourceGroup]:
    """Sprint 36: partitions an ALREADY globally-ranked page into Source
    Groups for presentation -- no re-ranking, no re-scoring. Each
    RankedCandidate keeps its real global `rank`. Fallback sources (today
    only seed_data) are always ordered last, never interleaved with live
    sources regardless of score -- this is the one place source ordering
    is enforced, and it is presentation-only: it does not change which
    candidates were selected or how they were scored, only display order
    of the groups themselves.
    """
    rankings_by_id = {r.candidate_id: r for r in page_rankings}
    by_source: dict[str, list[Candidate]] = {}
    for candidate in page_candidates:
        by_source.setdefault(candidate.source, []).append(candidate)

    live_sources = [s for s in by_source if not get_source_group_info(s).is_fallback]
    fallback_sources = [s for s in by_source if get_source_group_info(s).is_fallback]

    groups: list[SourceGroup] = []
    for source in [*live_sources, *fallback_sources]:
        info = get_source_group_info(source)
        group_candidates = by_source[source]
        group_rankings = [rankings_by_id[c.id] for c in group_candidates if c.id in rankings_by_id]
        groups.append(
            SourceGroup(
                source=source,
                display_name=info.display_name,
                icon=info.icon,
                trust_level=info.trust_level,
                is_live=info.is_live,
                is_fallback=info.is_fallback,
                candidate_count=len(group_candidates),
                searched_count=searched_counts.get(source, len(group_candidates)),
                qualified_count=qualified_counts.get(source, len(group_candidates)),
                # Sprint 36 Phase 1 scope: per-source timing instrumentation
                # is genuinely new work (nothing in the pipeline times
                # Discovery/Matching/Ranking per-source today) -- left None
                # here rather than fabricated, to be filled in by a
                # follow-up phase that adds real timers around those calls.
                discovery_time_ms=None,
                matching_time_ms=None,
                ranking_time_ms=None,
                candidates=group_candidates,
                rankings=group_rankings,
                provenance=[
                    _build_provenance(c, rankings_by_id[c.id].match if c.id in rankings_by_id else None)
                    for c in group_candidates
                ],
            )
        )
    return groups


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
    matching_config: MatchingConfig = Depends(get_matching_config),
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

    # --- Sprint 35 Phase 1: seed data is a FALLBACK, never a default
    # participant. Live-discovered/live-sourced candidates (source !=
    # "seed_data") are ranked and shown on their own merits first; the
    # bundled seed dataset is appended ONLY when live candidates alone
    # don't clear the relevance bar for enough of them -- so a query with
    # 87 real GitHub matches returns 87 GitHub / 0 seed, while a query
    # with only 8 weak live matches still gets topped up to a usable
    # count instead of returning a near-empty page.
    matches_by_id = {m.candidate_id: m for m in matches}
    seed_candidates = [c for c in candidates if c.source == "seed_data"]
    live_candidates = [c for c in candidates if c.source != "seed_data"]
    live_matches = [matches_by_id[c.id] for c in live_candidates]

    # Sprint 35 Phase 2: adaptive relevance threshold -- a small pool
    # tolerates weaker matches (better a 45%-confidence hit than nothing),
    # a large pool can afford to be pickier. Sized off the FULL live pool,
    # since that's the pool this decision is actually about.
    relevance_threshold = matching_config.adaptive_relevance_threshold(len(live_candidates))
    good_live_count = sum(1 for m in live_matches if m.overall_score >= relevance_threshold)

    seed_fallback_used = False
    if seed_candidates and good_live_count < matching_config.min_candidate_threshold:
        seed_fallback_used = True
        seed_matches = [matches_by_id[c.id] for c in seed_candidates]
        final_candidates = live_candidates + seed_candidates
        final_matches = live_matches + seed_matches
    else:
        final_candidates = live_candidates
        final_matches = live_matches

    rankings = ranking_engine.rank(final_candidates, final_matches)

    # Sprint 36: Source Group totals, computed once here from real
    # in-memory data -- never recomputed, never estimated beyond what's
    # honestly known. `searched_counts` prefers a connector's own reported
    # raw count (e.g. GitHub's raw_candidates_found) when available,
    # falling back to how many of that source survived into the
    # post-discovery candidate pool for connectors that don't report a
    # raw count yet. `qualified_counts` is exactly how many of each
    # source made it into `final_candidates` -- i.e. actually got ranked.
    searched_counts: dict[str, int] = {}
    for candidate in candidates:
        searched_counts[candidate.source] = searched_counts.get(candidate.source, 0) + 1
    for result in discovery_run.connector_results:
        if result.raw_candidates_found is not None:
            searched_counts[result.source_name] = result.raw_candidates_found

    qualified_counts: dict[str, int] = {}
    for candidate in final_candidates:
        qualified_counts[candidate.source] = qualified_counts.get(candidate.source, 0) + 1

    # Sprint 36: a denormalized copy of each candidate's source, passed to
    # SearchSessionStore.create() so GET /api/search/session/{id} can
    # filter/group by source later without ever re-deriving it.
    candidate_sources = {c.id: c.source for c in final_candidates}

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
            # Sprint 35: persisted so GET /api/search/session/{id} can
            # reproduce the exact same threshold/fallback facts without
            # ever re-running Matching or the Phase 1 decision above.
            "relevance_threshold": relevance_threshold,
            "seed_fallback_used": seed_fallback_used,
        },
        rankings=rankings,
        candidate_sources=candidate_sources,
    )

    min_score = None if payload.include_weak_matches else relevance_threshold
    page = session_store.get_page(
        session_id,
        page=payload.page,
        page_size=payload.page_size,
        min_score=min_score,
        source=payload.source_filter,
    )
    page_candidates, page_rankings = _candidates_for_rankings(page.rankings, repository)
    source_groups = _build_source_groups(page_candidates, page_rankings, searched_counts, qualified_counts)

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
        relevance_threshold=relevance_threshold,
        total_all_candidates=page.total_unfiltered_count,
        weak_match_count=page.total_unfiltered_count - page.total_count,
        include_weak_matches=payload.include_weak_matches,
        seed_fallback_used=seed_fallback_used,
        source_groups=source_groups,
    )


@router.get("/api/search/session/{session_id}", response_model=SmartSearchResponse)
def get_search_session_page(
    session_id: str,
    page: int = 1,
    page_size: int = 20,
    include_weak_matches: bool = False,
    source: str | None = None,
    repository: CandidateRepository = Depends(get_candidate_repository),
    session_store: SearchSessionStore = Depends(get_search_session_store),
    _recruiter: RecruiterRow = Depends(get_current_recruiter),
) -> SmartSearchResponse:
    """Sprint 33: pages through an already-completed search's stored,
    ranked output. Deliberately does NOT touch QueryUnderstandingService,
    SearchPlanner, DiscoveryOrchestrator, MatchingEngine, or RankingEngine
    -- every one of those ran exactly once, back in the POST that created
    this session. Only the CandidateRepository is used here, to re-fetch
    the actual Candidate objects for this page's slice of ranked ids.

    Sprint 35 Phase 2: `include_weak_matches` re-applies the SAME
    relevance_threshold computed (and persisted) at POST time -- via
    session_data["relevance_threshold"] -- rather than recomputing
    anything, so a weak match hidden on page 1 stays hidden (or shown)
    consistently across every subsequent page of the same session.

    Sprint 36: `source`, when given, restricts this page to one Source
    Group (e.g. "github") -- one more WHERE clause on the already-stored,
    already-globally-ranked rows (see SearchSessionStore.get_page()), not
    a re-run of anything. `source_groups`' searched_count/qualified_count
    are reconstructed from storage: qualified_count via
    get_source_counts(min_score=relevance_threshold) (how many of each
    source are actually persisted above threshold), searched_count
    preferring the real per-connector raw count already persisted in
    session_data["discovery"]["connector_results"] when a connector
    reported one, falling back to the same persisted qualified total
    otherwise (an honest lower bound, never a fabricated larger number)."""
    if page < 1:
        raise HTTPException(status_code=422, detail="page must be >= 1")
    if page_size < 1 or page_size > 50:
        raise HTTPException(status_code=422, detail="page_size must be between 1 and 50")

    # A quick, unfiltered peek at session_data to know the persisted
    # threshold before deciding what min_score to apply -- get_page()
    # itself does the actual (possibly filtered) candidate query below.
    try:
        probe = session_store.get_page(session_id, page=1, page_size=1)
    except SearchSessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    relevance_threshold = probe.session_data.get("relevance_threshold", 0.0)
    seed_fallback_used = probe.session_data.get("seed_fallback_used", False)

    min_score = None if include_weak_matches else relevance_threshold
    try:
        session_page = session_store.get_page(
            session_id, page=page, page_size=page_size, min_score=min_score, source=source
        )
    except SearchSessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    candidates, rankings = _candidates_for_rankings(session_page.rankings, repository)
    session_data = session_page.session_data

    # Sprint 36: reconstruct Source Group totals from storage -- no
    # recomputation of Discovery/Matching/Ranking.
    qualified_counts = session_store.get_source_counts(session_id, min_score=relevance_threshold)
    searched_counts = dict(session_store.get_source_counts(session_id, min_score=None))
    for result in session_data.get("discovery", {}).get("connector_results", []):
        if result.get("raw_candidates_found") is not None:
            searched_counts[result["source_name"]] = result["raw_candidates_found"]
    source_groups = _build_source_groups(candidates, rankings, searched_counts, qualified_counts)

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
        relevance_threshold=relevance_threshold,
        total_all_candidates=session_page.total_unfiltered_count,
        weak_match_count=session_page.total_unfiltered_count - session_page.total_count,
        include_weak_matches=include_weak_matches,
        seed_fallback_used=seed_fallback_used,
        source_groups=source_groups,
    )
