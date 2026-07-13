# Autonomous Talent Discovery Engine (Sprint 18)

Status: **Implemented.** This documents what actually shipped this sprint, on top of the existing, unmodified pipeline. `docs/DISCOVERY_ENGINE_ARCHITECTURE.md` and `docs/AUTONOMOUS_DISCOVERY_ARCHITECTURE.md` were earlier design-only proposals; this is the as-built record for the version that runs today.

## What this sprint did and did not touch

Did not modify: Query Understanding, the Knowledge Engine, the Search Planner, the Candidate Intelligence Lifecycle, or the Greenhouse Connector's own modules (client, normalizer, config). `POST /api/search` is untouched and still works exactly as before. Everything below is additive: new modules under `app/discovery/`, plus one new router and one new frontend entry point.

## The workflow

```
Recruiter query
      |
      v
Query Understanding (existing, unchanged) -> CanonicalJobRequirement
      |
      v
Search Planner (existing, unchanged) -> SearchPlan
      |
      v
CandidateRepository.search(plan)  (existing, unchanged) -> candidates
      |
      v
Discovery Decision Engine.evaluate(candidates, plan)
      |
   should_discover? --- no --> return candidates as-is
      |
     yes
      |
      v
Discovery Orchestrator.run(requirement, plan, candidates)
      |  for each connector, in priority order:
      |    - skip if not is_available() (recorded, not an error)
      |    - else discover(requirement) -> CandidateImportRequest[]
      |    - normalize_import() -> Candidate
      |    - find_potential_duplicate() + repository.upsert()
      |      (upsert() automatically runs the Candidate Intelligence
      |       Lifecycle -- health score, confidence, evidence, versioning --
      |       exactly as it already did for every other capture path)
      v
CandidateRepository.search(plan) again -> refreshed candidates
      |
      v
SmartSearchResponse (requirement, search_plan, candidates, count, discovery)
```

## Discovery Decision Engine

`app/discovery/decision_engine.py`. Triggers discovery if either condition holds:

- `candidate_count < min_result_threshold` (default 5)
- `average_match_confidence < min_confidence_threshold` (default 70.0)

Both thresholds are constructor parameters, not hardcoded. `average_match_confidence` (`app/discovery/scoring.py`) is a new, purpose-built heuristic — term overlap between each candidate's role/skills and the search plan's `search_terms` — deliberately separate from two other, pre-existing "confidence" concepts it must not be confused with: `Candidate.health_score`/`section_confidence` (data-quality/provenance, from Candidate Intelligence) and the legacy `match_score` in `app/services/matching_engine.py` (belongs to the old, separate mock `/api/v1/search` pipeline).

## Discovery Orchestrator

`app/discovery/orchestrator.py`. Responsibilities, in order:

1. Ask the Decision Engine whether discovery is needed at all (stage: "Searching internal talent intelligence...").
2. If not, return the existing results untouched.
3. Otherwise, run each connector in ascending `priority` order. Unavailable connectors (`is_available() -> False`) are recorded as skipped, not errors. A connector whose `discover()` call raises is caught and isolated — one failing source cannot fail the whole run.
4. Every candidate a connector finds goes through the exact same write seam every other capture path already uses: `CandidateImportRequest -> normalize_import() -> upsert()`. `upsert()` handles dedup/merge and automatically triggers the Candidate Intelligence Lifecycle — the orchestrator never calls the lifecycle directly.
5. Re-runs `repository.search(plan)` for a refreshed result set.
6. Returns a `DiscoveryRun` (decision, per-connector `ConnectorRunResult`s, total imported, and the full `stages` list) alongside the refreshed candidates.

## Connector contract

`app/discovery/connectors/base.py` — a `Protocol`, not an ABC, so a connector needs no import-time coupling:

```python
class DiscoveryConnector(Protocol):
    name: str
    priority: int
    def is_available(self) -> bool: ...
    def discover(self, requirement: CanonicalJobRequirement) -> list[CandidateImportRequest]: ...
```

The Discovery Engine knows nothing about connector internals — it only ever calls `is_available()` and `discover()`. Per the sprint's explicit rules, a connector may only read from a source it already has legitimate, authorized access to. Nothing in this interface enables scraping, auth bypass, or anti-bot evasion; `discover()` takes a requirement and returns structured data, nothing else.

**Wired connectors** (`app/routers/discovery_search.py`), by priority:

| Priority | Connector | `is_available()` | Notes |
|---|---|---|---|
| 10 | `GreenhouseDiscoveryConnector` | reflects whether Greenhouse is actually configured | filters `list_candidates()` by keyword match against role/skills, then `normalize_greenhouse_candidate()` |
| 20 | `BrowserExtensionDiscoveryConnector` | `True` | documented no-op — browser captures already write straight into the repository via `POST /candidate/import`, so they're already part of the very first `search()` call; nothing sits in a separate queue for this connector to fetch |
| 30 | `CsvImportDiscoveryConnector` | `False` | no CSV intake endpoint exists yet |
| 40 | `ResumeImportDiscoveryConnector` | `False` | no resume-upload intake endpoint exists yet |
| 50 | `HrmsDiscoveryConnector` | `False` | no HRMS integration exists yet |

Honesty principle: stub connectors report `is_available() -> False` rather than silently returning an empty list that would look identical to "searched and found nothing." The distinction is surfaced to the recruiter via `ConnectorRunResult.configured`, because "we haven't connected your resume inbox yet" and "we checked and there's nothing there" are different, actionable facts.

## API contract

`POST /api/search/smart` (`app/routers/discovery_search.py`) — same request shape as `POST /api/search`, response is `SmartSearchResponse`:

```
requirement: CanonicalJobRequirement
search_plan: SearchPlan
candidates: list[Candidate]
count: int
discovery: DiscoveryRun   # { triggered, decision, connector_results, new_candidates_imported, stages, ran_at }
```

Same error handling as `/api/search` (422 on query validation failure, 502 on query-understanding/LLM failure).

## Frontend integration

- `marketing/src/components/demo/api.js` — added `searchCandidatesSmart(query)`, identical error-handling to the existing `searchCandidates()`, POSTs to `/api/search/smart`. The original function is untouched.
- `marketing/src/components/demo/DiscoveryStages.jsx` — new component, renders `discovery.stages` as a progress list (checkmark for completed, pulsing dot for current), the same visual idiom as `ThinkingSequence` but driven by the backend's dynamic stage list rather than a hardcoded one.
- `marketing/src/components/sections/LiveDemo.jsx` — Live Pipeline mode now calls `searchCandidatesSmart`. If `discovery.triggered` and it has stages, a new `"discovering"` status reveals them sequentially (500ms per stage) in a purple-accented panel before showing the refreshed shortlist. If, after discovery, there are still zero candidates, the empty state shows the sprint's required copy: "No suitable candidates were found across your connected talent sources." Guided Demo mode is untouched.

## Tests

13 new backend tests, full suite now 190/190 passing:

- `app/discovery/tests_decision_engine.py` (5) — triggers on too-few candidates, triggers on low confidence, does not trigger when sufficient, empty search terms means full confidence, empty candidate list means zero confidence.
- `app/discovery/tests_orchestrator.py` (5) — skip-when-sufficient, priority ordering + import counting, unavailable-connector recording, failing-connector isolation, dedup-against-existing (merges rather than duplicates).
- `app/routers/tests_discovery_search.py` (3) — triggers discovery and reports the unconfigured Greenhouse connector, skips discovery when 5+ sufficient candidates already exist, returns 502 on query-understanding failure (same as `/api/search`).

---

## Sprint 19 addition: Candidate Matching Engine + Ranking Engine

Sprint 19 sits on top of everything above without changing it. It answers a different question than Sprint 18: Sprint 18 decided *whether* to go looking for more candidates; Sprint 19 decides *how good* any given candidate actually is, for every candidate, every time -- no exact-match or first-match shortcut.

### Matching Engine (`app/matching/engine.py`)

Scores every candidate across a fixed, honest set of dimensions (`app/matching/config.py::DIMENSIONS`): role, skills, industry, experience, location, education, certifications, company preference, keyword similarity, knowledge-expansion similarity, candidate health, and confidence.

`CanonicalJobRequirement` (frozen, Query Understanding's contract) only carries `role` and `skills` -- there is no structured field for industry, education, certifications, or company preference. Rather than fabricate a score for those, the engine reports them neutrally (50.0) and lists them in `missing_fields`, and **excludes them from the overall weighted average** so a candidate is never penalized (or flattered) by data the requirement simply didn't specify. The same honesty rule applies to experience/location (scored only when the raw query contains an "N+ years" pattern or a location name) and health/confidence (scored only once `apply_lifecycle()` has actually run for that candidate).

`raw_query` powers two lightweight, best-effort heuristics scoped entirely to this new module -- they do not touch, extend, or duplicate Query Understanding's own parsing.

### Ranking Engine (`app/matching/ranking.py`)

Sorts by overall score, then confidence, then health, then most recent capture time, then candidate id as a final deterministic tie-break. Every candidate passed in gets ranked.

### Decision Engine upgrade

`DiscoveryDecisionEngine.evaluate()` now accepts an optional `match_results` argument. When supplied (as it always is from `POST /api/search/smart`), the average of the Matching Engine's `overall_score` values is used as the "Average Score" signal from Module 3, replacing Sprint 18's simpler requirement-term-overlap heuristic (`app/discovery/scoring.py`, still there, still used when `match_results` is omitted -- this is what keeps every Sprint 18 test passing unchanged).

### Connector Registry (`app/discovery/connector_registry.py`)

Replaces the inline connector list that used to live in `discovery_search.py` with a `register()`/`get_all()`/`get_available()`/`status()` registry. Connectors are still required to satisfy nothing more than the existing `DiscoveryConnector` Protocol -- the registry adds no new coupling, only lookup and priority ordering (with per-deployment override via `MatchingConfig.connector_priority`). `DiscoveryOrchestrator` accepts either a registry or a plain list (duck-typed on `get_all`), so Sprint 18's tests, which construct it with a plain list, are untouched.

### Configuration (`app/matching/config.py`)

One `MatchingConfig` dataclass holds every configurable value the sprint asked for: `min_candidate_threshold`, `min_score`, `connector_priority`, `discovery_timeout`, and `ranking_weights`. It's threaded through the Matching Engine, Decision Engine, and Connector Registry via FastAPI dependency injection (`get_matching_config()`), so tests and any future admin surface can swap in a different instance without touching engine code.

### API contract addition

`SmartSearchResponse` (unchanged fields plus): `rankings: list[RankedCandidate]` -- each returned candidate's full `MatchResult` and rank, in the same order as `candidates`.

### Frontend

`CandidateCard` now accepts an optional `match` prop (one entry from `rankings`, looked up by candidate id in `LiveDemo.jsx`). When present, it shows an "N% match" badge, Health/Confidence chips, and the Matching Engine's own `reasons` list in place of the client-side `WhyMatchedTag` computation. Guided Demo mode has no backend call and supplies no `match`, so its cards render exactly as before.

### Tests

16 new backend tests: `app/matching/tests_engine.py` (7), `app/matching/tests_ranking.py` (4), `app/discovery/tests_connector_registry.py` (5). Full suite: 206/206 passing (up from Sprint 18's 190).

---

## Sprint 20A: Universal Connector Framework

Scope note (per the sprint brief): framework only, no GitHub connector yet. Nothing about Sprint 18/19's `DiscoveryConnector` Protocol, `ConnectorRegistry`, or `DiscoveryOrchestrator` (`POST /api/search/smart`'s own connector wiring) is modified -- this is a new, parallel interface + registry + management API, built alongside the old one rather than replacing it, so every existing test keeps passing unchanged.

### The new interface (`app/discovery/connectors/framework.py`)

A `Connector` Protocol with `discover(requirement)`, `supports(requirement)`, `priority()`, `health()`, `status()`, and `configure(config)`, plus static `ConnectorMetadata` (name, version, capabilities, requires_auth, supported_roles, enabled). `priority()` is a method here (not Sprint 18's plain int attribute) so it can depend on live configuration later; existing connectors keep their original `priority` attribute untouched underneath.

### Legacy adapter (`app/discovery/connectors/legacy_adapter.py`)

`LegacyConnectorAdapter` wraps any Sprint 18 `DiscoveryConnector` (Greenhouse, and the four future-connector stubs) so it satisfies the new interface without being reimplemented. `configure({"enabled": ...})` is the one field the generic adapter understands itself -- connectors with their own richer configuration (Greenhouse's API key) keep using their existing dedicated endpoint (`POST /integrations/greenhouse/configure`); this composes with it rather than replacing it.

### Dynamic loading (Module 3)

`discover_connectors()` walks every module in `app/discovery/connectors/` and collects any module-level name matching `MANAGED_*CONNECTOR`. Adding a new connector is adding a new file (or a new name in an existing one) with that convention -- no list anywhere needs editing. `ManagedConnectorRegistry.with_dynamically_loaded_connectors()` (`app/discovery/connector_registry_v2.py`) is built this way, and is what backs the management API below.

### Management API (`app/routers/connector_management.py`)

- `GET /connectors` -- every registered connector's metadata + live status/health.
- `POST /connectors/configure` -- `{"name": ..., "config": {...}}`.
- `POST /connectors/enable` / `POST /connectors/disable` -- `{"name": ...}`.

404 on an unknown connector name for all three POST routes.

### Tests

15 new tests: `app/discovery/connectors/tests_framework.py` (6), `app/discovery/tests_connector_registry_v2.py` (6), `app/routers/tests_connector_management.py` (4, one exercising the real dynamically-loaded registry end-to-end). Full suite: 221/221 passing.

---

## Sprint 20B: GitHub Discovery Connector

The first production connector built on Sprint 20A's framework. Uses only GitHub's official REST API (https://docs.github.com/en/rest) -- no scraping, no browser automation, no bypassing authentication. Nothing about the existing architecture (Query Understanding, Knowledge Engine, Search Planner, Candidate Intelligence, Matching/Ranking Engines, the Discovery Orchestrator itself) is modified; this connector plugs into the same `ConnectorRegistry` Greenhouse already uses, on equal footing.

### Package layout (`app/integrations/github/`)

Mirrors `app/integrations/greenhouse/`'s layout:

- `config.py` -- `GitHubConfig` (personal_access_token + base_url override for GitHub Enterprise Server), `GitHubConfigStore` (in-memory, POC-scoped, same pattern as Greenhouse's).
- `client.py` -- `GitHubClient`, authenticated with `Authorization: token <PAT>`. Implements `search_users()`, `get_user()`, `list_repos()` against GitHub's documented endpoints, with the same primary-rate-limit retry-once behavior (`X-RateLimit-Remaining: 0` + `X-RateLimit-Reset`) that `GreenhouseClient` uses for its own rate limit.
- `normalizer.py` -- `infer_languages(repos)` (skills extraction: distinct, non-fork repo languages, ranked by frequency -- documented as a heuristic, not authoritative, same honesty standard as Greenhouse's `tags` field) and `normalize_github_candidate(user, repos)` -> `CandidateImportRequest`.

### Connector (`app/discovery/connectors/github_connector.py`)

`GitHubDiscoveryConnector` satisfies Sprint 18's `DiscoveryConnector` interface (`name="github"`, `priority=15`, `is_available()`, `discover()`) so it plugs straight into the existing `DiscoveryOrchestrator` via `discovery_search.py`'s `get_connector_registry()` -- one added registration line, nothing else in the orchestrator/search-pipeline touched. `discover()`: builds a GitHub user-search query from the requirement's role + skills, fetches each candidate's profile and repos (capped at 10 users per discovery pass to bound the N+1 API fan-out), infers skills via `infer_languages()`, filters out users whose inferred skills don't intersect the requirement's stated skills (when any were given), and normalizes matches into `CandidateImportRequest` objects -- the same objects every other connector produces, which then flow through `normalize_import() -> upsert()` exactly as documented in the Sprint 18 section above: Candidate Intelligence Lifecycle runs automatically, the result lands in the Repository, and the Matching/Ranking Engines score and order it on the re-search that follows. This connector calls none of those stages itself.

A `MANAGED_CONNECTOR` instance (via `LegacyConnectorAdapter`) also exposes it to Sprint 20A's framework -- it shows up in `GET /connectors` and can be enabled/disabled through the management API, picked up automatically by `discover_connectors()`, no hardcoded registration needed there either.

### Configuration endpoint (`app/routers/github_integration.py`)

`POST /integrations/github/configure` -- `{"personal_access_token": ..., "base_url": ...}` (base_url optional, for GitHub Enterprise Server). Mirrors Greenhouse's own `/configure` endpoint. No bulk sync or push-back endpoints -- Sprint 20B is discovery-only.

### Tests

18 new tests: `app/integrations/github/tests_client.py` (5, including a rate-limit-retry scenario via respx), `tests_normalizer.py` (4), `tests_config.py` (2), `app/discovery/connectors/tests_github_connector.py` (5, including a filtered-out-candidate case and a per-user-lookup-failure case), `app/routers/tests_github_integration.py` (2). Plus a fix to Sprint 20A's dynamic connector loader (`discover_connectors()`), which was accidentally importing test modules (`tests_*.py`) living in the same connectors package as if they were connectors themselves -- now explicitly excluded. Full suite: 239/239 passing (up from Sprint 20A's 221).

---

## Sprint 20C: Connector Intelligence Layer (Adaptive Connector Query Translation)

Sits between the Search Planner and the Discovery Orchestrator. Every module the sprint brief listed as frozen -- Query Understanding, Knowledge Engine, Search Planner, Candidate Intelligence Lifecycle, Matching Engine, Ranking Engine, the `DiscoveryConnector` interface itself, existing API contracts, the Browser Extension, the Greenhouse connector, and the GitHub connector's own implementation -- is untouched. This layer only decides *what search string(s) to hand a connector*, not how any connector works internally.

### Why

GitHub's user-search index responds far better to `golang`, `language:Go`, `backend go`, `go grpc` than to a literal recruiter title like "Senior Golang Developer". Greenhouse and the browser extension don't have this problem -- they already do their own keyword/role matching -- so they get a no-op passthrough instead.

### `ConnectorQuery` (`app/discovery/query_translation/models.py`)

`connector_name`, `original_query`, `connector_queries` (the ordered list of connector-native search expressions, capped by `ConnectorTranslationConfig.max_queries_per_connector`, default 8), `filters` (qualifier-style terms like `language:Go` pulled out as `{"language": "Go"}`), `metadata` (carries `strategy` name and a `passthrough` flag), `confidence`. `is_passthrough` is a convenience property reading that flag.

`ConnectorTranslationConfig`: `max_queries_per_connector` (8), `max_depth` (2 -- how many domain-term combination rounds the GitHub strategy generates), `expansion_enabled` (True), `connector_enabled` (per-connector on/off map -- disabling a connector here routes it to the generic passthrough strategy). Injected the same way `MatchingConfig` is, via `get_connector_translation_config()`.

### Strategies (`app/discovery/query_translation/strategies/`)

- **`github.py`** -- the real logic. A `SKILL_TO_GITHUB_TERMS` dict maps recruiter-facing skill words to GitHub-native terms exactly per the sprint brief's table (Python -> python, Go -> golang + language:Go, Java -> spring + java, RAG -> "retrieval augmented generation", etc.). When at least one skill/role token matches, confidence is 1.0; unmapped roles fall back to the recruiter's own significant words (stopwords like "senior"/"engineer" stripped) at confidence 0.5 -- never a fabricated technical guess. Domain-combo terms (`backend`, `grpc`, `microservices`, `kubernetes`, `docker`) are appended against the primary detected term, then the whole list is capped.
- **`greenhouse.py`** -- passthrough (`is_passthrough=True`). Returns `[original_query, role, *skills]` purely for observability; the orchestrator still calls `discover()` exactly once, with the untouched original requirement -- "No API changes," per the brief.
- **`browser_extension.py`** -- passthrough, returns `[requirement.role]` only.
- **`generic.py`** -- passthrough fallback for any connector without a dedicated strategy (future CSV/resume/HRMS connectors, or GitHub/Greenhouse themselves if disabled via config).

`ConnectorQueryTranslator.translate(connector_name, requirement, raw_query, plan)` dispatches by connector name, defaulting to `generic`.

### Orchestrator integration (`app/discovery/orchestrator.py`)

`run()` gained two new **optional** parameters, `query_translator=None` and `raw_query=None`. Omitting them (every Sprint 18/19/20B call site that doesn't pass them) reproduces the exact prior behavior byte-for-byte -- one `discover(requirement)` call per connector -- which is what keeps all 239 pre-existing tests passing unchanged.

When a translator is supplied: for each connector, get its `ConnectorQuery`. If `is_passthrough`, call `discover(requirement)` once with the **original** requirement (Greenhouse/browser extension/generic). Otherwise (GitHub today), call `discover()` once per translated search string, each against a small synthetic `CanonicalJobRequirement(role=query_text, skills=[])` -- the connector's own `discover()` method is never modified, only invoked more than once with different input. Results across all of a connector's queries are deduplicated (`app/discovery/query_translation/dedup.py`) before they reach `normalize_import()`/`upsert()`.

### Deduplication (`app/discovery/query_translation/dedup.py`)

Per the brief's "GitHub login / email / LinkedIn URL / candidate id" list: `CandidateImportRequest` has no email or id field pre-import, so the practical key priority is `public_profile_url` (covers a GitHub profile URL or LinkedIn URL alike, case-insensitive) -> `resume_link` -> `(name, current_company)` as a last resort. This runs *before* `normalize_import()`/`upsert()`, in addition to (not instead of) the existing `find_potential_duplicate()` merge logic that already runs inside `upsert()` against candidates already in the repository.

### Observability

Every connector's discovery pass now logs (`logger.info("discovery.connector_query", extra={...})`) the original recruiter query, connector name, translated search list, candidates found, duplicates removed, and elapsed time in milliseconds -- purely additive logging, no behavior or return value changes.

### Wiring (`app/routers/discovery_search.py`)

`POST /api/search/smart` now builds a `ConnectorQueryTranslator` via DI and passes it (plus the recruiter's raw query text) into `orchestrator.run()`. `POST /api/search` (the original, frozen pipeline) is untouched.

### Tests

21 new tests: `app/discovery/query_translation/tests_translator.py` (10, including all six of the sprint brief's example queries, the max-queries cap, per-connector disable, and filter extraction), `app/discovery/query_translation/tests_dedup.py` (5), `app/discovery/tests_orchestrator_query_translation.py` (3 -- explicitly proving both the backward-compatible single-call path and the new multi-query + cross-query-dedup path, plus that passthrough connectors still get exactly one call against the untouched original requirement). Full suite: 260/260 passing (up from Sprint 20B's 239) -- zero pre-existing tests modified or broken.

## Sprint 20D: GitHub Candidate Intelligence Engine

Status: **Implemented.** Transforms the GitHub connector from a simple profile finder (Sprint 20B) into a candidate intelligence engine, without touching Query Understanding, the Knowledge Engine, the Search Planner, the Candidate Intelligence Lifecycle, the Matching Engine, the Ranking Engine, the `DiscoveryConnector` interface, the Connector Intelligence Layer, the Discovery Orchestrator, existing API contracts, the Greenhouse connector, the Browser Extension, or the Candidate Repository's read paths. Everything below is additive.

### New flow

```
Recruiter Query
      |
      v
Connector Intelligence (Sprint 20C, unchanged)
      |
      v
GitHub User Search (unchanged)
      |
      v
Repository Discovery         -- client.list_repos() (existing)
      |
      v
Repository Analysis          -- app/integrations/github/intelligence/repository_analyzer.py
      |
      v
Skill Extraction             -- app/integrations/github/intelligence/skill_extractor.py
      |
      v
Activity Analysis            -- app/integrations/github/intelligence/activity_analyzer.py
      |
      v
Organization Analysis        -- app/integrations/github/intelligence/organization_analyzer.py
      |
      v
Candidate Enrichment         -- app/integrations/github/intelligence/enrichment.py
      |
      v
normalize_github_candidate(profile, repos, enrichment=...)  -- existing seam, additive param
      |
      v
normalize_import() -> Candidate (github_* fields populated)  -- existing seam, additive fields
      |
      v
Matching (unchanged) / Ranking (unchanged)
```

### `app/integrations/github/intelligence/` package

- **`config.py`** -- `GitHubIntelligenceConfig`: `max_repositories` (default 20), `max_readme_bytes` (default 20,000), and independent enable/disable flags for repository analysis, activity scoring, organization analysis, and skill extraction. `get_github_intelligence_config()` returns the shared default instance.
- **`repository_analyzer.py`** -- `RepositoryAnalyzer.analyze(raw_repos)` aggregates languages, topics, descriptions, fork status, stars/forks/watchers, license, default branch, and last update across a user's repos (capped at `max_repositories`), returning a `RepositoryAnalysis` plus the top 5 repos by stars. Forks are excluded from language/skill attribution, same reasoning as Sprint 20B's `infer_languages()`.
- **`activity_analyzer.py`** -- `ActivityAnalyzer.analyze(raw_repos)` uses each repo's `pushed_at` (the documented, honest proxy for "last commit" available from the repos-list endpoint) to compute months since last activity, active vs. inactive repo counts, and a bounded 0-100 `activity_score` (recency-weighted, breadth as a secondary factor).
- **`organization_analyzer.py`** -- `OrganizationAnalyzer.analyze(user, raw_orgs)` reads the profile's free-text `company` field plus `GET /users/{username}/orgs` (public memberships only, honestly reported as such). `verified_organization` is a conservative heuristic (org account type == "Organization"), never an authenticity guarantee.
- **`skill_extractor.py`** -- `SkillExtractor.extract(repos, readmes)` matches 21 named skills (FastAPI, Django, Flask, Spring Boot, Kafka, Redis, RabbitMQ, Docker, Terraform, Kubernetes, AWS, Azure, GCP, LangChain, LlamaIndex, RAG, OpenAI, Vector DB, ElasticSearch, PostgreSQL, MongoDB, Neo4j) against real evidence only -- repo language, topics, repo name, description, or README text, in that priority order, word-boundary matched. A skill is never reported without a specific piece of evidence attached (`SkillEvidence.evidence_type` + `source`); nothing is inferred from the role title or query.
- **`quality_scorer.py`** -- `QualityScorer.score(...)` combines repository quality, popularity, activity, followers, organization quality, and profile completeness into a weighted 0-100 `GitHubQualityScore.overall`.
- **`enrichment.py`** -- `GitHubEnrichmentEngine.enrich(user, repos, orgs, readmes)` orchestrates all four analyzers + the quality scorer, respecting each config flag (a disabled stage returns its honest empty/zero result, never a fabricated substitute), logs `github.candidate_enrichment` with repositories analyzed/skills inferred/quality score/activity score/elapsed time, and returns one `GitHubEnrichment` result.

### Client additions (`app/integrations/github/client.py`)

Two new methods, both additive: `list_orgs(username)` (`GET /users/{username}/orgs`) and `get_readme(owner, repo, max_bytes=None)` (`GET /repos/{owner}/{repo}/readme` via the `application/vnd.github.raw+json` Accept override, returning `None` on 404 rather than raising).

### Wiring into the existing capture seam

- `normalize_github_candidate(user, repos, enrichment=None)` (`app/integrations/github/normalizer.py`) gained one new optional parameter. Omitted (every pre-Sprint-20D caller), behavior is byte-identical. Provided, it populates 9 new fields on the returned `CandidateImportRequest`.
- `CandidateImportRequest` and `Candidate` (`app/candidate_repository/import_schemas.py`, `app/candidate_repository/models.py`) both gained the same 9 optional, additive fields: `github_quality_score`, `github_activity_score`, `github_repositories_analyzed`, `github_languages`, `github_topics`, `github_organizations`, `github_skills_inferred`, `github_last_activity`, `github_profile_completeness`. Every non-GitHub payload defaults these to `None`/empty.
- `normalize_import()` (`app/candidate_repository/normalizer.py`) passes these 9 fields through unchanged -- pure additive passthrough, no other behavior touched.
- `GitHubDiscoveryConnector.discover()` (`app/discovery/connectors/github_connector.py`) now, per matched candidate: fetches public orgs (`list_orgs`), fetches README text for up to 5 top-starred non-fork repos (`get_readme`, bounded by `_README_FETCH_LIMIT` and `max_readme_bytes`), runs `GitHubEnrichmentEngine.enrich(...)`, and passes the result into `normalize_github_candidate(profile, repos, enrichment=...)`. `GitHubDiscoveryConnector.__init__` gained one new optional `intelligence_config` parameter (defaults to the shared config), so `MANAGED_CONNECTOR`'s existing single-positional-arg construction is unaffected.

### Matching Engine

Deliberately **not modified**. The 9 new `github_*` fields exist on `Candidate` so the Matching Engine *can* read them in a future sprint, per the brief's explicit instruction -- this sprint only attaches the data.

### Tests

41 new tests across: `tests_repository_analyzer.py` (5), `tests_activity_analyzer.py` (5), `tests_organization_analyzer.py` (4), `tests_skill_extractor.py` (9, including explicit "no hallucination" / no-evidence and word-boundary false-positive cases), `tests_quality_scorer.py` (3), `tests_enrichment.py` (6, including each config flag disabled independently), plus additions to the existing `tests_client.py` (5 new: `list_orgs`, `get_readme` success/404/truncation/error-passthrough), `tests_normalizer.py` (2 new: enrichment omitted vs. provided), `tests_import.py` (2 new: passthrough vs. default), and `tests_github_connector.py` (extended one existing test's mocks to cover the new `/orgs` and `/readme` calls, plus new enrichment-field assertions). All mocked via `respx` -- no test requires internet. Full suite: **301/301 passing** (up from Sprint 20C's 260) -- zero pre-existing tests modified in a breaking way, zero regressions.
