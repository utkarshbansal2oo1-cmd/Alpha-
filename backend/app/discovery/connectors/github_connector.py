"""GitHub-backed Discovery Connector -- Sprint 20B, enriched in Sprint 20D,
made fully dynamic (zero hardcoded technology lists) in Sprint 20F, and
upgraded to semantic evidence matching in Sprint 20G.

Built on the Universal Connector Framework introduced in Sprint 20A, and
satisfying Sprint 18's DiscoveryConnector interface (name/priority/
is_available()/discover()) so it plugs straight into the existing
Discovery Orchestrator and POST /api/search/smart -- no orchestrator or
search-pipeline code is touched. Uses ONLY GitHub's official REST API
(app/integrations/github/client.py) -- no scraping, no browser
automation, no bypassing authentication, per the standing Discovery
Engine rules from Sprint 18.

Every candidate this connector finds goes through the exact same
CandidateImportRequest -> normalize_import() -> upsert() seam every other
connector uses, which is what runs the Candidate Intelligence Lifecycle
(health/confidence/evidence/versioning), stores it in the Repository, and
-- back in discovery_search.py's smart_search() -- feeds the Matching and
Ranking Engines on the re-search that follows. This connector does not
call any of those downstream stages itself.

Sprint 20D addition: before normalizing, each matched candidate is run
through GitHubEnrichmentEngine (app/integrations/github/intelligence/) --
repository/activity/organization analysis, skill extraction, and a
0-100 quality score -- and the result is attached via
normalize_github_candidate()'s optional `enrichment` parameter.

Sprint 20E (live validation, first fix): live testing proved 5 of 6 real
recruiter queries returned zero GitHub candidates because the filter
compared skills only against GitHub's own repo `language` field.

Sprint 20F: the filter was switched to literal-word overlap between the
recruiter's own query text and the candidate's real GitHub evidence
(repo name/language/description/topics) -- removing all dependency on
any fixed technology table, but still requiring an exact shared word.

Sprint 20G (this change): literal-word overlap cannot recognize that
"Computer Vision" and "YOLO, OpenCV, Detectron2" describe the same thing
-- they share no words at all. The filter is now PRIMARILY a semantic
comparison: both the requirement text and the candidate's real evidence
text are embedded (via GeminiEmbeddingClient, reusing the same
GEMINI_API_KEY Query Understanding already uses) and compared by cosine
similarity (app/integrations/github/intelligence/semantic_matcher.py).
The embedding model was never told this product's skills or roles -- it
maps arbitrary text to arbitrary text, so it requires no maintenance as
new job titles/technologies appear. If the embedding API is unavailable
(no key configured, or a transient failure), the connector falls back to
Sprint 20F's literal-token evidence match rather than returning nothing
-- availability must never depend on one remote call succeeding.

Sprint 20H: `_DISCOVERY_USER_LIMIT` used to be a hardcoded module constant
capping every search to the first 10 GitHub users, regardless of how many
real matches existed (live-confirmed: total_count 1729 for "golang" alone
-- 10 was a connector-imposed ceiling, not a GitHub API limitation). That
cap now lives on GitHubIntelligenceConfig.max_search_results, so it can be
raised (or lowered) per deployment/config without touching this file. The
default (10) is unchanged, so every existing caller keeps its current
behavior.

Sprint 32 addition: a 401 from GitHub's search API during discover() now
also marks the credential store's status as "invalid" via
config_store.mark_error() -- a token that passed verification at
configure-time can still go bad later (revoked, expired, org policy
change), and this is what lets GET /integrations/status (and, in a
future sprint, a frontend "Reconnect GitHub" banner) reflect that instead
of a search silently and permanently falling back to seed data.

Sprint 34 (this change): discover() used to make exactly ONE call to
GitHub's Search Users API (per_page capped at
GitHubIntelligenceConfig.max_search_results, historically 10), so a
query like "Java Developer" -- which can match thousands of real GitHub
users -- only ever considered the first page. discover() now walks
GitHub's own native pagination (the documented `page` query param, see
GitHubClient.search_users()) across multiple pages, collecting a much
larger raw candidate pool before deduplication, enrichment, matching, or
ranking ever run. This is deliberately NOT lazy/on-demand enrichment --
every stage after "collect the raw pool" (profile fetch, org/README
fetch, semantic/token relevance filtering, enrichment) is completely
unchanged; it just now runs over a bigger, deduplicated input list.

Three independent limits (app/config.py: GITHUB_SEARCH_PAGE_SIZE,
GITHUB_MAX_SEARCH_PAGES, GITHUB_MAX_RAW_CANDIDATES, surfaced here via
GitHubIntelligenceConfig.search_page_size/max_search_pages/
max_raw_candidates) bound the fetch: pages stop being requested when any
of the sprint's defined stop conditions is hit (max pages reached, max
raw candidates reached, GitHub returned no more results, a rate limit
was hit, or the connector became unavailable mid-run). Whichever
condition fired is recorded on `self.last_discovery_stats` -- a plain
dict, not part of the DiscoveryConnector interface -- which
DiscoveryOrchestrator.run() reads via getattr() and folds into that
connector's ConnectorRunResult for this run (see app/discovery/
orchestrator.py and app/discovery/models.py). Because DiscoveryRun is
stored verbatim into Sprint 33's SearchSession.session_data, these
discovery statistics land in the persisted Search Session with no
changes needed anywhere in app/search_sessions/.

Deduplication is by GitHub's own immutable user id when the API supplies
one (real /search/users responses always include it), falling back to
`login` only when it's absent (as in some of this file's own hand-built
test fixtures) -- never by any derived/mutable field. A duplicate seen
on a later page is dropped before it ever reaches the enrichment loop
below, so no candidate is ever profile-fetched, org-fetched, or
README-fetched twice for the same discover() call.
"""
from __future__ import annotations

import logging
import re
import time

from app.candidate_repository.import_schemas import CandidateImportRequest
from app.integrations.github.client import GitHubAPIError, GitHubClient
from app.integrations.github.config import GitHubConfigStore
from app.integrations.github.intelligence.config import (
    GitHubIntelligenceConfig,
    get_github_intelligence_config,
)
from app.integrations.github.intelligence.enrichment import GitHubEnrichmentEngine
from app.integrations.github.intelligence.semantic_matcher import (
    EmbeddingUnavailableError,
    SemanticEvidenceMatcher,
)
from app.integrations.github.normalizer import normalize_github_candidate
from app.search_planner.models import CanonicalJobRequirement

logger = logging.getLogger(__name__)

# Sprint 20H: no longer used as the live cap (see
# GitHubIntelligenceConfig.max_search_results) -- kept only as the
# documented default value tests/callers can reference, matching the
# config field's own default.
_DISCOVERY_USER_LIMIT = 10

# Every enriched candidate costs up to this many extra README fetches (one
# per top repo considered) on top of the profile/repos/orgs calls already
# made -- capped small to keep a single discovery pass fast and to stay
# well inside GitHub's rate limits. README evidence is a nice-to-have for
# skill extraction, not a requirement, so keeping this low is safe.
_README_FETCH_LIMIT = 5

# Generic recruiting/seniority words that carry no technology signal at
# all -- stripping them keeps the fallback literal-token match from
# matching on noise (almost every repo description contains "engineer" or
# "senior" somewhere). This is NOT a technology list: it names zero
# programming languages, frameworks, platforms, or tools, and never needs
# an entry added for a new skill/role -- only for a new generic English
# job-title word, which is a closed, tiny, language-grammar set.
_ROLE_NOISE_WORDS = {
    "senior", "junior", "mid", "lead", "staff", "principal", "chief",
    "engineer", "engineers", "engineering", "developer", "developers",
    "consultant", "architect", "researcher", "scientist", "specialist",
    "analyst", "manager", "expert", "professional", "candidate", "role",
    "with", "years", "year", "experience", "in", "and", "or", "the", "a",
    "of", "for", "to",
}

# A tiny synonym table for the same real-world thing GitHub's own repo
# `language` field spells differently than common recruiter usage (e.g.
# GitHub reports Go repos as language="Go", not "Golang"). Used only by
# the literal-token fallback path -- the primary semantic path needs no
# such table, since embeddings already place "Golang" and "Go" close
# together in meaning.
_LANGUAGE_SPELLING_ALIASES: dict[str, str] = {
    "golang": "go",
    "nodejs": "javascript",
    "node.js": "javascript",
    "node": "javascript",
}

_WORD_PATTERN = re.compile(r"[a-z0-9][a-z0-9+#.]*")


def _tokenize(*texts: str | None) -> set[str]:
    """Splits arbitrary recruiter text into lowercase word tokens, with no
    technology knowledge involved -- pure text splitting, so it works
    identically for "Python" and for a term nobody has typed before."""
    tokens: set[str] = set()
    for text in texts:
        if not text:
            continue
        for match in _WORD_PATTERN.findall(text.lower()):
            if len(match) < 2 or match in _ROLE_NOISE_WORDS:
                continue
            tokens.add(match)
            alias = _LANGUAGE_SPELLING_ALIASES.get(match)
            if alias:
                tokens.add(alias)
    return tokens


def _repo_evidence_text(repo: dict) -> str:
    """Every real, GitHub-supplied text field for one repo, concatenated
    into a single lowercase blob. Nothing here is inferred or guessed --
    every word came back from GitHub's own API for this specific repo."""
    parts = [
        repo.get("name") or "",
        repo.get("language") or "",
        repo.get("description") or "",
        " ".join(repo.get("topics") or []),
    ]
    return " ".join(parts).lower()


def _requirement_text(requirement: CanonicalJobRequirement) -> str:
    parts = [requirement.role or "", *requirement.skills]
    return " ".join(p for p in parts if p).strip()


class GitHubDiscoveryConnector:
    name = "github"
    priority = 15  # Runs after Greenhouse (10), before the Sprint 18 stubs (20+).

    def __init__(
        self,
        config_store: GitHubConfigStore,
        intelligence_config: GitHubIntelligenceConfig | None = None,
        semantic_matcher: SemanticEvidenceMatcher | None = None,
    ):
        self._config_store = config_store
        # Sprint 20D addition: optional, defaults to the module-level
        # default config -- every pre-Sprint-20D caller (including
        # MANAGED_CONNECTOR's construction below and every existing test
        # that builds GitHubDiscoveryConnector(store) with one positional
        # arg) is unaffected.
        self._intelligence_config = intelligence_config or get_github_intelligence_config()
        self._enrichment_engine = GitHubEnrichmentEngine(self._intelligence_config)
        # Sprint 20G addition: optional, defaults to a real
        # SemanticEvidenceMatcher (Gemini embeddings) -- same
        # backward-compatible-default pattern as intelligence_config.
        # Tests inject a fake matcher; production uses the real one.
        self._semantic_matcher = semantic_matcher or SemanticEvidenceMatcher()
        # Sprint 34: set by every discover() call (including early-return
        # branches) -- a plain dict, not part of the DiscoveryConnector
        # interface, read by DiscoveryOrchestrator.run() via getattr() and
        # folded into this connector's ConnectorRunResult. None until the
        # first discover() call.
        self.last_discovery_stats: dict | None = None

    def is_available(self) -> bool:
        return self._config_store.is_configured()

    def _fetch_raw_candidates(
        self, client: GitHubClient, search_query: str
    ) -> tuple[list[dict], dict]:
        """Sprint 34: walks GitHub's native Search Users pagination
        (`page`/`per_page`) collecting a deduplicated raw candidate pool,
        stopping at whichever of the sprint's defined stop conditions
        fires first. Returns (raw_users, stats) -- stats is exactly the
        dict this module attaches to `self.last_discovery_stats`."""
        page_size = self._intelligence_config.search_page_size
        max_pages = self._intelligence_config.max_search_pages
        max_raw = self._intelligence_config.max_raw_candidates

        raw_users: list[dict] = []
        seen_identities: set = set()
        pages_fetched = 0
        total_items_seen = 0  # across all pages, BEFORE dedup
        stop_reason = "max_pages_reached"

        for page_num in range(1, max_pages + 1):
            try:
                items, _total_count = client.search_users(search_query, per_page=page_size, page=page_num)
            except GitHubAPIError as exc:
                logger.info(
                    "github.discover.search_failed",
                    extra={"query": search_query, "page": page_num, "error": str(exc)},
                )
                if exc.status_code == 401:
                    # Sprint 32: a token that passed verification at
                    # configure-time can still go bad later (revoked,
                    # expired, org policy change). Record that here so
                    # GET /integrations/status -- and, in a future
                    # sprint, a frontend "Reconnect GitHub" banner --
                    # reflects reality instead of a search silently and
                    # permanently falling back to seed data with no
                    # visible explanation.
                    self._config_store.mark_error(
                        "GitHub authentication failed (401) during search -- "
                        "the token may have been revoked or expired. Reconfigure it via "
                        "POST /integrations/github/configure."
                    )
                    stop_reason = "connector_unavailable"
                elif exc.status_code == 403:
                    # GitHubClient already retries a primary rate-limit
                    # 403 once internally (waiting for X-RateLimit-Reset)
                    # -- a 403 reaching here means that retry ALSO hit
                    # the limit, so further pagination isn't attempted
                    # this run rather than waiting indefinitely.
                    stop_reason = "rate_limited"
                else:
                    stop_reason = "search_error"
                break

            pages_fetched += 1

            if not items:
                stop_reason = "no_more_results"
                break

            total_items_seen += len(items)

            hit_cap = False
            for item in items:
                identity = item.get("id", item.get("login"))
                if identity is None or identity in seen_identities:
                    continue
                seen_identities.add(identity)
                raw_users.append(item)
                if len(raw_users) >= max_raw:
                    hit_cap = True
                    break

            if hit_cap:
                stop_reason = "max_raw_candidates_reached"
                break
            if len(items) < page_size:
                # GitHub's own signal that this was the last page --
                # native pagination, not a custom heuristic.
                stop_reason = "no_more_results"
                break
            if pages_fetched >= max_pages:
                stop_reason = "max_pages_reached"
                break
        else:
            stop_reason = "max_pages_reached"

        stats = {
            "github_pages_fetched": pages_fetched,
            "raw_candidates_found": total_items_seen,
            "raw_candidates_after_dedup": len(raw_users),
            "discovery_stop_reason": stop_reason,
        }
        return raw_users, stats

    def discover(self, requirement: CanonicalJobRequirement) -> list[CandidateImportRequest]:
        if not self.is_available():
            self.last_discovery_stats = {
                "github_pages_fetched": 0,
                "raw_candidates_found": 0,
                "raw_candidates_after_dedup": 0,
                "discovery_stop_reason": "connector_unavailable",
            }
            return []

        started_at = time.monotonic()
        config = self._config_store.get()
        client = GitHubClient(config)
        try:
            query_terms = [requirement.role, *requirement.skills]
            query = " ".join(t for t in query_terms if t and t.strip()).strip() or "developer"
            search_query = f"{query} type:user"

            # Sprint 34: raw_users is already deduplicated (by GitHub's
            # immutable user id, falling back to login) and capped at
            # GITHUB_MAX_RAW_CANDIDATES across however many pages were
            # fetched -- everything below this line is completely
            # unchanged from before Sprint 34, just operating over a much
            # larger input list than the old single-page fetch produced.
            raw_users, discovery_stats = self._fetch_raw_candidates(client, search_query)
            self.last_discovery_stats = discovery_stats
            users_found = discovery_stats["raw_candidates_found"]

            if not raw_users:
                logger.info(
                    "github.discover.trace",
                    extra={
                        "search_query": search_query,
                        "users_found": 0,
                        "candidates_returned": 0,
                        **discovery_stats,
                    },
                )
                return []

            requirement_text = _requirement_text(requirement)
            # Sprint 20F fallback vocabulary -- derived entirely from THIS
            # query's own text, no fixed skills/roles/technologies table.
            requirement_tokens = _tokenize(requirement.role, *requirement.skills)
            results: list[CandidateImportRequest] = []
            profiles_fetched = 0
            profile_fetch_failures = 0
            filtered_out_no_evidence = 0
            matched_semantically = 0
            matched_by_fallback_tokens = 0
            semantic_unavailable = False

            for user_summary in raw_users:
                username = user_summary.get("login")
                if not username:
                    continue
                try:
                    profile = client.get_user(username)
                    repos = client.list_repos(username)
                except GitHubAPIError:
                    profile_fetch_failures += 1
                    continue
                profiles_fetched += 1

                if requirement_tokens:
                    evidence_text = " ".join(_repo_evidence_text(r) for r in repos)
                    is_relevant = False
                    match_method = None

                    # Sprint 20G: semantic comparison is the primary check
                    # -- it can recognize a candidate as relevant even
                    # when they share zero literal words with the query
                    # (e.g. "Computer Vision" <-> "YOLO, OpenCV").
                    try:
                        is_relevant, similarity = self._semantic_matcher.is_relevant(
                            requirement_text, evidence_text
                        )
                        match_method = "semantic"
                    except EmbeddingUnavailableError as exc:
                        # Availability must never depend on one remote
                        # call succeeding -- fall back to Sprint 20F's
                        # literal-token evidence match instead of
                        # dropping every candidate.
                        semantic_unavailable = True
                        logger.info(
                            "github.discover.semantic_unavailable",
                            extra={"error": str(exc)},
                        )
                        is_relevant = any(token in evidence_text for token in requirement_tokens)
                        match_method = "fallback_tokens"

                    if not is_relevant:
                        filtered_out_no_evidence += 1
                        continue
                    if match_method == "semantic":
                        matched_semantically += 1
                    else:
                        matched_by_fallback_tokens += 1

                orgs: list[dict] = []
                try:
                    orgs = client.list_orgs(username)
                except GitHubAPIError:
                    # Public org list is enrichment, not a search
                    # prerequisite -- a failure here must not drop an
                    # otherwise-matched candidate.
                    orgs = []

                readmes: dict[str, str] = {}
                if self._intelligence_config.enable_repository_analysis:
                    # Only fetch READMEs for a handful of top (most-starred)
                    # repos -- README text is used for skill-evidence only,
                    # so this stays a best-effort, bounded fan-out.
                    top_repos = sorted(
                        (r for r in repos if not r.get("fork", False)),
                        key=lambda r: r.get("stargazers_count", 0) or 0,
                        reverse=True,
                    )[:_README_FETCH_LIMIT]
                    for repo in top_repos:
                        repo_name = repo.get("name")
                        if not repo_name:
                            continue
                        try:
                            text = client.get_readme(
                                username, repo_name, max_bytes=self._intelligence_config.max_readme_bytes
                            )
                        except GitHubAPIError:
                            text = None
                        if text:
                            readmes[repo_name] = text

                enrichment = self._enrichment_engine.enrich(profile, repos, orgs=orgs, readmes=readmes)

                results.append(normalize_github_candidate(profile, repos, enrichment=enrichment))

            elapsed_ms = round((time.monotonic() - started_at) * 1000, 1)
            # Full execution trace for this discover() call, per-stage, so
            # a zero-candidate result is always explainable from the logs
            # rather than a silent "no candidates found."
            logger.info(
                "github.discover.trace",
                extra={
                    "search_query": search_query,
                    "requirement_tokens": sorted(requirement_tokens),
                    "users_found": users_found,
                    "profiles_fetched": profiles_fetched,
                    "profile_fetch_failures": profile_fetch_failures,
                    "filtered_out_no_evidence": filtered_out_no_evidence,
                    "matched_semantically": matched_semantically,
                    "matched_by_fallback_tokens": matched_by_fallback_tokens,
                    "semantic_unavailable": semantic_unavailable,
                    "candidates_returned": len(results),
                    "elapsed_ms": elapsed_ms,
                    **discovery_stats,
                },
            )

            return results
        finally:
            client.close()


# --- Sprint 20A framework exposure -------------------------------------------
# Additive, same pattern as greenhouse_connector.py's own MANAGED_CONNECTOR:
# wraps the class above (untouched) so it shows up in GET /connectors,
# discovered dynamically by app/discovery/connectors/framework.py's
# discover_connectors() -- no hardcoded connector list anywhere.
from app.discovery.connectors.framework import ConnectorMetadata  # noqa: E402
from app.discovery.connectors.legacy_adapter import LegacyConnectorAdapter  # noqa: E402
from app.integrations.github.config import get_github_config_store  # noqa: E402

MANAGED_CONNECTOR = LegacyConnectorAdapter(
    wrapped=GitHubDiscoveryConnector(get_github_config_store()),
    metadata=ConnectorMetadata(
        name="github",
        version="1.0.0",
        capabilities=["candidate_search", "semantic_evidence_matching"],
        requires_auth=True,
        supported_roles=[],
        enabled=True,
    ),
)
