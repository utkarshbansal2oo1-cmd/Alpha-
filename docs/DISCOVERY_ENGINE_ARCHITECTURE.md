# Discovery Engine Architecture

Status: **Design only — no implementation in this sprint.** This document defines the data acquisition layer AlphaSource will need once retrieval moves beyond the current in-memory seed dataset (see `docs/TECH_DEBT.md`). Nothing here is approved for implementation until reviewed; per standing project convention, if any part of this conflicts with the frozen Knowledge Engine or Search Planner contracts, that is flagged explicitly below rather than silently assumed compatible.

## 1. Complete Architecture

The Discovery Engine sits between the Search Planner (already built) and a new Candidate Intelligence Database (new, this document). It does not replace the Search Planner's job of deciding *what* to search for — it owns deciding *where* to search and *how* to bring results back into one canonical shape.

```
CanonicalJobRequirement
        |
        v
   Search Planner  (existing, frozen contract — unchanged)
        |
        v
     SearchPlan  (existing contract: strict, expanded, search_terms, weights, unresolved)
        |
        v
  +---------------------------------------------------------+
  |                  DISCOVERY ENGINE (new)                  |
  |                                                           |
  |   Discovery Strategy  --decides-->  Connector Dispatcher  |
  |          |                                |               |
  |          v                                v               |
  |   Source Priority List          Connector Framework        |
  |                                  (ATS, Resume, CSV,        |
  |                                   Internal DB, Web,        |
  |                                   GitHub, LinkedIn*, ...)  |
  |                                        |                   |
  |                                        v                   |
  |                              Raw provider-shaped results   |
  |                                        |                   |
  |                                        v                   |
  |                            Candidate Normalizer            |
  |                                        |                   |
  |                                        v                   |
  |                          Deduplication Engine               |
  |                                        |                   |
  +---------------------------------------------------------+
                                           |
                                           v
                     Candidate Intelligence Database (new)
                                           |
                                           v
                   CandidateRepository interface (existing,
                   already built — search()/all() contract
                   unchanged; now backed by the CID DB instead
                   of a static JSON seed file)
```

*LinkedIn/Naukri only via user-authorized or officially compliant integration paths — see section 8.

The critical design decision: **`CandidateRepository`'s existing interface (`search(plan) -> list[Candidate]`) does not change.** The Discovery Engine, Connector Framework, Normalizer, and Dedup Engine are all new machinery that live *behind* that interface, feeding the Candidate Intelligence Database that `InMemoryCandidateRepository` will eventually be replaced by (a `DatabaseCandidateRepository`, or similar, implementing the same `CandidateRepository` ABC). This is why the brief's requirement — "allow adding new data sources without changing the Intelligence Layer" — is structurally guaranteed: the Intelligence Layer (Query Understanding, Knowledge Engine, Search Planner) has never known anything about *where* candidates come from, only that `CandidateRepository.search()` returns `Candidate` objects. Nothing above the Discovery Engine needs to change no matter how many connectors are added below it.

## 2. Component Diagram

```
┌───────────────────────────────────────────────────────────────────┐
│                         Discovery Engine                          │
│                                                                     │
│  ┌────────────────┐   ┌─────────────────┐   ┌──────────────────┐ │
│  │ Discovery       │──>│ Connector        │──>│ Connector         │ │
│  │ Strategy        │   │ Dispatcher       │   │ Registry          │ │
│  │ (routing,       │   │ (fan-out,        │   │ (which connectors │ │
│  │ prioritization,  │   │ concurrency,     │   │ exist, their      │ │
│  │ dedup-avoidance) │   │ timeout, retry)  │   │ capabilities)     │ │
│  └────────────────┘   └────────┬────────┘   └──────────────────┘ │
│                                 │                                   │
│              ┌──────────────────┼──────────────────┐               │
│              v                  v                  v               │
│      ┌───────────────┐ ┌───────────────┐ ┌───────────────┐        │
│      │ ATS Connector │ │ Web Connector │ │ GitHub Conn.  │  ...   │
│      └───────┬───────┘ └───────┬───────┘ └───────┬───────┘        │
│              │                  │                  │               │
│              └──────────────────┼──────────────────┘               │
│                                 v                                   │
│                     ┌──────────────────────┐                       │
│                     │ Candidate Normalizer │                       │
│                     └──────────┬───────────┘                       │
│                                v                                    │
│                     ┌──────────────────────┐                       │
│                     │ Deduplication Engine │                       │
│                     └──────────┬───────────┘                       │
└────────────────────────────────┼───────────────────────────────────┘
                                  v
                  ┌────────────────────────────────┐
                  │ Candidate Intelligence Database │
                  └────────────────────────────────┘
```

## 3. Sequence Diagram (single search request)

```
Recruiter        SearchPlanner      DiscoveryEngine     Connectors        Normalizer/Dedup      CID DB
   |                   |                   |                 |                  |                 |
   |--query----------->|                   |                 |                  |                 |
   |                   |--SearchPlan------>|                 |                  |                 |
   |                   |                   |--select sources->|                  |                 |
   |                   |                   |--dispatch (parallel, per-connector)->|                 |
   |                   |                   |                 |--raw results---->|                  |
   |                   |                   |                 |  (per source)     |                 |
   |                   |                   |<----------------partial/complete----|                 |
   |                   |                   |                 |                  |--normalize------>|
   |                   |                   |                 |                  |--dedup/merge---->|
   |                   |                   |                 |                  |                  |--upsert-->|
   |                   |                   |<---------------------------------- confidence-scored candidates---|
   |<--------------------------------------- Candidate[] (via existing CandidateRepository.search())----------|
```

Note: this mirrors the existing pipeline's synchronous shape (one request in, one response out) at the *API* boundary — the Discovery Engine's internal fan-out to connectors can be async/parallel without that ever being visible to `routers/search_pipeline.py`, which is precisely why this can be built without touching the frozen API contract.

## 4. Data Flow

1. **Trigger**: either a live recruiter search (real-time discovery for uncached terms) or a scheduled refresh job (background discovery, section 7).
2. **Routing**: Discovery Strategy consults the Connector Registry + Source Priority List to pick which connectors are relevant to this `SearchPlan`'s `search_terms` and `field_type`s.
3. **Dispatch**: Connector Dispatcher fans out to each selected connector concurrently, with a per-connector timeout and retry budget (section 3).
4. **Raw ingestion**: each connector returns results in its own native shape (ATS JSON, resume PDF-extracted fields, CSV rows, GitHub API JSON, etc.) — connectors do not normalize; that is a separate, single-responsibility stage (section 4), so a bug in one connector's raw format never touches the shared normalization logic.
5. **Normalization**: Candidate Normalizer maps every raw shape into one canonical `Candidate` record (existing `candidate_repository.models.Candidate`, extended per section 5).
6. **Deduplication**: Dedup Engine checks the normalized candidate against existing Candidate Intelligence Database records using the signal-based confidence merge (section 6), either creating a new record or merging into an existing one with full source attribution preserved.
7. **Persistence**: upsert into the Candidate Intelligence Database, with versioning (section 5) so every change is auditable.
8. **Read path** (unchanged): `CandidateRepository.search(plan)` reads from the Candidate Intelligence Database and returns `Candidate` objects exactly as today — the rest of the pipeline is unaware discovery ever happened.

## 5. Database Schema

Proposed core tables (illustrative column lists, not DDL — this is architecture, not a migration):

**`candidates`** (the canonical identity record)
- `candidate_id` (UUID, primary key)
- `created_at`, `updated_at`, `version` (integer, incremented on every merge/update)
- `confidence_score` (float 0-1 — overall confidence this is a single real, correctly-merged identity)
- `ai_summary` (text — generated, not authored, always labeled as such to the recruiter)

**`candidate_identity`** (1:1 with candidates)
- `full_name`, `emails` (array), `phones` (array), `location`

**`candidate_career`** (1:many — one row per role, mirrors the marketing site's `timeline` shape from Sprint 6)
- `candidate_id` (FK), `company`, `title`, `start_date`, `end_date`, `is_current`

**`candidate_skills`** (1:many)
- `candidate_id` (FK), `skill_canonical_id` (FK into the existing Knowledge Engine taxonomy — this is the integration point between Discovery and the already-frozen Knowledge Engine), `proficiency_signal` (e.g. "listed", "endorsed", "verified via assessment"), `source`

**`candidate_education`** (1:many)
- `candidate_id` (FK), `degree`, `institution`, `year`

**`candidate_projects`**, **`candidate_certifications`** (1:many, same shape pattern)

**`candidate_social_links`**
- `candidate_id` (FK), `platform` (enum: github/linkedin/portfolio/...), `url`, `verified` (bool)

**`candidate_resumes`**
- `candidate_id` (FK), `file_reference` (pointer to blob storage, not the file itself), `parsed_at`, `parser_version`

**`candidate_assessment_results`**, **`candidate_interview_history`**
- `candidate_id` (FK), `source` ("AlphaRecrewt" for the future integration mentioned in the product brief), `result_summary`, `date`

**`candidate_recruiter_notes`**
- `candidate_id` (FK), `recruiter_id`, `note_text`, `created_at` — human-authored, never AI-generated, kept in a separate table specifically so `ai_summary` (auto-generated) and recruiter notes (human-authored) are never conflatable in a query or an audit.

**`candidate_search_history`**
- `candidate_id` (FK), `search_plan_id`, `matched_at`, `why_matched` (JSON — mirrors the existing `WhyMatched` concept already built into the product)

**`candidate_source_attribution`** (critical for the Dedup Engine and for compliance/audit)
- `candidate_id` (FK), `source_connector` (e.g. "github", "ats:greenhouse", "csv:upload-2026-07-01"), `source_record_id`, `first_seen_at`, `last_confirmed_at`, `raw_payload_reference` (pointer, not inline — keeps this table lean)

**`candidate_versions`** (append-only, for auditability)
- `candidate_id` (FK), `version_number`, `changed_fields` (JSON diff), `changed_by` (connector name or "dedup-merge" or recruiter_id), `changed_at`

This schema deliberately keeps `candidate_source_attribution` and `candidate_versions` as first-class, queryable tables rather than JSON blobs on the main record — both compliance questions ("where did this data come from?") and dedup-quality questions ("why did we merge these two records?") need to be answerable without deserializing a blob.

## 6. Connector Framework

### 6.1 The interface (described, not coded)

Every connector — regardless of source type — implements one contract with exactly these responsibilities, nothing more:

- **`capabilities()`**: declares what this connector can search on (e.g. "role, skill" for a resume connector; "role, skill, github-language" for a GitHub connector) and what it returns (raw, source-native records). This is how the Discovery Strategy knows which connectors are even relevant to a given `SearchPlan` without hardcoding per-connector knowledge into the strategy layer.
- **`search(search_terms, filters) -> RawResult[]`**: takes the flattened terms from a `SearchPlan` (not the whole plan — connectors should never need to understand `StrictFilter`/`ExpandedFilter` internals, only "give me candidates matching these terms") and returns results in whatever shape is native to that source.
- **`health_check() -> ConnectorHealth`**: a cheap, fast call the Discovery Engine can use to skip a connector that's currently down rather than waiting for every search to time out against it.
- **`rate_limit_policy()`**: declares the connector's own constraints (requests/minute, concurrent connection limit) so the Dispatcher can throttle per-connector rather than globally, which matters enormously once GitHub/LinkedIn-class rate limits are in play.

### 6.2 Why this shape specifically

- **`capabilities()` before `search()`** exists so the Discovery Strategy can be a *generic* router — "which connectors declare they can search on `field_type=skill`" — rather than a growing if/elif chain of "if source is GitHub, do X; if source is CSV, do Y." This is the single design choice that makes "add a new data source without changing the Intelligence Layer" actually true rather than aspirational: a new connector is additive, never a modification to the routing logic.
- **Connectors return raw, source-native shapes, not `Candidate` objects.** This is deliberate separation of concerns: a connector author (or an auto-generated connector, eventually) only needs to know their source's API, not AlphaSource's canonical schema. The Normalizer is the *only* place that needs to know both.
- **`health_check()` and `rate_limit_policy()`** exist because the connector list explicitly includes external, rate-limited, occasionally-unreliable services (GitHub API, LinkedIn if/when permitted) alongside always-available internal ones (CSV, internal DB) — a uniform contract that pretends they're equally reliable would produce a Discovery Engine that's only as robust as its flakiest connector. Building this in from day one avoids retrofitting resilience later.

### 6.3 Connector types and their distinguishing characteristics

| Connector | Auth model | Typical latency | Rate-limited? | Compliance note |
|---|---|---|---|---|
| ATS Connector | OAuth/API key, customer-authorized | Low (internal API) | Rarely | Data already belongs to the hiring company — lowest compliance risk |
| Resume Connector | None (file upload) or internal storage | Low–medium (parsing cost) | No | Candidate-submitted; still needs retention/consent handling |
| CSV Connector | None (file upload) | Low | No | Same as resume — uploader is responsible for the data's provenance |
| Internal DB Connector | Internal | Low | No | Already-owned data (e.g. this platform's own past search history) |
| Public Web Connector | None / API key depending on target | Medium–high | Often | Must respect robots.txt/ToS per target site — see section 8 |
| GitHub Connector | OAuth or PAT | Medium | Yes (documented API limits) | Public API, compliant by design if used within GitHub's terms |
| LinkedIn Connector | Official partner API only | N/A until authorized | Yes | **Not implementable via scraping** — see section 8, this is a hard constraint, not a preference |
| Naukri Connector | Official partner/API only | N/A until authorized | Yes | Same constraint as LinkedIn |
| Wellfound Connector | Public API if available, else authorized partnership | Medium | Likely | Verify current ToS before building |
| Company Career Pages | Public Web Connector, generic HTML/structured-data parsing | High (per-site variance) | Site-dependent | Respect each site's robots.txt individually |

## 7. Discovery Strategy

Given a `SearchPlan`, the strategy answers four questions:

**Where to search.** Cross-reference `SearchPlan.search_terms`' `field_type`s against each registered connector's declared `capabilities()`. A plan searching for "GitHub, Rust" would route to the GitHub Connector and Public Web Connector but skip an ATS Connector that only indexes a company's existing applicant pool for unrelated roles — this filtering happens once, generically, not per-connector-type in a switch statement.

**How to prioritize connectors.** A simple, explainable weighting (not a black-box ranking) combining: (a) connector reliability score (rolling average from `health_check()` history), (b) historical yield for this `field_type` (a connector that rarely returns results for "skill" searches gets deprioritized for skill-heavy plans without being removed entirely), and (c) cost/latency (internal connectors before external ones, when both are equally likely to have the answer) . This mirrors the existing Knowledge Engine's own principle of weighted, explainable edges rather than an opaque score — consistency with a pattern already validated in this codebase.

**How to avoid duplicate searches.** A request-scoped and a longer-lived cache: within one recruiter query, the same `(connector, normalized_search_terms)` pair is only dispatched once even if it would satisfy multiple expanded terms. Across queries, a short-TTL cache (see section 7 on freshness — same mechanism, different name) prevents re-hitting a rate-limited external connector for a term searched five minutes ago by a different recruiter.

**How to retry failed searches.** Per-connector exponential backoff (bounded, e.g. 3 attempts) scoped to that one connector's call — one connector timing out must never block or fail the others, since the Dispatcher runs them concurrently. A connector that exhausts its retry budget contributes an empty result set plus a logged, surfaceable failure reason (mirroring the existing project convention of typed errors over silent failures, established in Sprint 5's `LLMClientError` work) rather than crashing the overall discovery request.

## 8. Candidate Normalizer

The Normalizer's only job: take one connector's raw, source-native result and produce one canonical `Candidate`-shaped record (extending the existing `candidate_repository.models.Candidate` with the richer fields from section 5's schema). Each connector type needs its own mapping function, but all of them produce the same output shape — this is what lets the Dedup Engine and the Candidate Intelligence Database remain completely connector-agnostic.

**Illustrative examples of the same canonical fields arriving in different shapes** (describing the mapping, not code):

- An **ATS Connector** might return `{"candidate_name": "...", "current_role": "...", "yrs_experience": "5.2", "skillset": "Java, Spring, AWS"}` — the Normalizer splits `skillset` on commas, trims whitespace, and maps each token through the Knowledge Engine's existing `normalize()` call so "AWS" resolves to the same canonical skill ID the rest of the platform already uses.
- A **Resume Connector** might return unstructured extracted text plus a best-effort parse: `{"name": "...", "experience_entries": [{"employer": "...", "title": "...", "dates": "Jan 2021 - Present"}]}` — the Normalizer parses the free-text date range into `start_date`/`end_date`/`is_current`, matching the `candidate_career` schema exactly.
- A **GitHub Connector** might return `{"login": "...", "public_repos": 42, "languages": {"Python": 40000, "Go": 12000}}` (bytes of code per language) — the Normalizer converts the language byte-counts into skill signals with a `proficiency_signal` of "inferred from repository activity," explicitly distinguishing this from a self-reported or verified skill.
- A **CSV Connector** has the most variable shape of all (whatever columns the uploader used) — the Normalizer requires an explicit column-mapping step (recruiter or admin maps their CSV headers to canonical fields once per upload), rather than guessing, since silently misinterpreting a CSV column is a worse failure mode than asking for one-time clarification.

In every case, the Normalizer's output includes a `source_connector` and `raw_payload_reference` tag (feeding directly into `candidate_source_attribution`), so normalization is always traceable back to its raw input — never a black-box transformation.

## 9. Deduplication Engine

### 9.1 Signals, ranked by reliability

| Signal | Reliability | Notes |
|---|---|---|
| Verified email match | Very high | Still not absolute — shared/generic emails (e.g. a company's generic careers@ inbox misfiled as a candidate email) need a sanity filter |
| GitHub URL / username match | Very high | Effectively unique per person |
| LinkedIn URL match | Very high | Same caveat as email — only usable where the URL was legitimately obtained (section 8) |
| Phone number match | High | Format-normalize before comparing (country code, spacing) |
| Resume file hash match | High | Same file uploaded twice — cheap, exact signal |
| Name + current company + location match | Medium | Common-name collisions are real (two "Rahul Sharma"s at the same company is not impossible at scale) |
| Name similarity alone | Low | Never sufficient alone — only a tiebreaker alongside at least one other medium+ signal |

### 9.2 Confidence-based merge strategy

Rather than a binary "same person / not same person," each candidate pair gets a computed **merge confidence score** as a weighted combination of whichever signals both records have available (missing signals are simply excluded from the weighted average, not treated as mismatches).

- **Score above a high threshold (e.g. two+ high-reliability signals agreeing)**: auto-merge, with a version entry recording exactly which signals drove the merge.
- **Score in a middle band (one high-reliability signal, or several medium ones agreeing)**: merge but flag the resulting record for optional human review — visible to a recruiter as "we believe these are the same person" rather than silently presented as certain.
- **Score below threshold**: kept as distinct candidate records, even if they share a name — false merges are more damaging than false separations (a wrongly-merged candidate corrupts one person's entire career history with another's), so the strategy is deliberately conservative.

Every merge is reversible: because `candidate_source_attribution` and `candidate_versions` are preserved per-source rather than overwritten, an incorrect auto-merge can be manually split back into two records without data loss — this is why those two tables are architected as append-only rather than mutable summary fields.

## 10. Data Freshness

**Refresh cadence**, tiered by how likely a field is to change and how expensive it is to re-check:
- **Career/company/title**: re-check periodically (e.g. every 30-90 days) per candidate, not per search — this is a background job, not something that happens synchronously during a recruiter's live query.
- **Skills**: lower priority for re-checking than career info; skills rarely regress, they mostly accumulate, so a missed update is lower-cost than a missed job change.
- **Contact info (email/phone)**: refresh opportunistically whenever a connector happens to re-surface the candidate (e.g. via a new search hit), not on its own dedicated schedule — not worth a standalone crawl budget for this alone.

**Avoiding unnecessary crawling**: every connector call is scoped by `last_confirmed_at` per source in `candidate_source_attribution` — a candidate already confirmed via GitHub in the last 30 days is not re-queried against GitHub again within that window, even if they resurface in an unrelated search. This is the same request-scoped/longer-lived cache concept from section 7, applied to background refresh rather than live search.

**Detecting changes**: the Normalizer compares each newly-normalized record against the existing stored version *before* triggering a merge — if nothing differs, no new `candidate_versions` row is written and no re-processing happens downstream (no unnecessary dedup re-evaluation, no wasted write). Only an actual diff triggers a version increment and a Dedup Engine pass.

## 11. Compliance

This is treated as an architectural constraint, not an afterthought:

- **The Connector Framework's `capabilities()`/interface makes compliance auditable per-connector.** Because every connector is a discrete, swappable unit, a compliance review can evaluate "is the GitHub Connector's data collection compliant with GitHub's ToS" independently of every other connector — a monolithic scraper would not offer this separability.
- **LinkedIn and Naukri connectors are explicitly scoped to official partner/API access only** in this architecture — not "scrape until blocked." If no compliant API access exists at build time, the correct outcome is that connector remains unbuilt (or built against a mock/stub for testing) rather than built against an unauthorized scraping path. This is a hard constraint carried into this document from the standing safety rules governing this project, not merely a suggestion.
- **The Public Web Connector and Company Career Pages connector must respect each target site's robots.txt and terms of service individually** — this connector type is architected to take a per-site configuration (crawl-delay, allowed paths) rather than a single global "crawl everything" policy, because compliance obligations vary site-by-site.
- **`candidate_source_attribution` is not just a dedup mechanism — it is the compliance audit trail.** Any data-subject request ("where did you get my information?") or platform policy question is answerable by querying that one table, per candidate, per source.
- **Resume and CSV connectors carry a data-retention/consent question that connectors like GitHub don't**: candidate-submitted personal data (resumes, uploaded CSVs containing personal data) needs a retention policy and, depending on jurisdiction, a consent/right-to-deletion mechanism. This is flagged here as a requirement the Candidate Intelligence Database's schema must support (e.g. a deletion that cascades correctly across `candidate_versions`, `candidate_source_attribution`, and blob storage) even though the specific legal requirements are outside this document's scope to define.

## 12. Scalability

| Scale | What changes |
|---|---|
| **100K candidates** | A single relational database (matching the schema in section 5) with standard indexing (on `candidate_id`, skill/company foreign keys, and a full-text or trigram index for name-similarity dedup checks) is sufficient. Discovery Engine can run as a single service; connector fan-out concurrency is bounded by simple worker-pool limits. |
| **1M candidates** | Read-heavy query patterns (recruiter search) benefit from a dedicated search index (e.g. a text/vector search layer) sitting alongside the relational store, rather than querying the relational schema directly for every recruiter search — the relational DB remains the source of truth, the search index is a derived, rebuildable read model. Deduplication at this scale needs blocking/candidate-pair-reduction (e.g. only compare candidates sharing at least one indexed signal, never all-pairs comparison) to stay computationally tractable. Background refresh jobs need real job scheduling/queueing (not simple cron) to spread load and respect per-connector rate limits at volume. |
| **10M candidates** | Sharding or partitioning the Candidate Intelligence Database (e.g. by region or by primary source) becomes worth considering. The Dedup Engine's signal-matching likely needs precomputed signal indexes (e.g. a separate email-hash lookup table, a phone lookup table) rather than joining through the main candidate tables for every comparison. Connector dispatch and normalization become natural candidates for a proper async job queue/worker-fleet architecture rather than in-process concurrency, since discovery volume at this scale is a sustained background workload, not just a live-search side effect. |

The common thread: nothing about crossing these thresholds requires changing the `CandidateRepository` interface the rest of the platform depends on — scale is absorbed entirely within the Discovery Engine and Candidate Intelligence Database's internals, which is the entire point of keeping that interface boundary fixed.

## 13. Future Evolution

**Search Engine (today)** — a recruiter asks, the system searches a fixed, small candidate pool and returns explainable matches. Value is in query understanding and explainability, not breadth of data.

**Talent Intelligence Platform (this document's target)** — the Discovery Engine continuously and automatically builds and enriches a persistent Candidate Intelligence Database across many sources, so recruiter queries are answered against a constantly-growing, deduplicated, versioned pool rather than a static seed file. Value shifts from "can it understand my query" (already solved) to "does it actually know about the right candidates."

**Enterprise Talent Graph (beyond this document)** — candidates, companies, skills, and roles become explicitly interconnected (e.g. "who else worked at this company during this candidate's tenure," "which skills cluster together across this candidate pool," "which companies are bleeding talent toward which others") — at that point the Candidate Intelligence Database's relational schema likely gains a genuine graph layer on top (skills-to-skills, company-to-company, candidate-to-candidate relationships), and the product's value proposition extends from "find candidates" to "understand the talent market." This document's schema is deliberately structured (explicit foreign keys, explicit source attribution, explicit versioning) so that evolution is additive — a graph layer can be built from this relational foundation without a rewrite, the same way this Discovery Engine is designed to be additive to the existing Search Planner/Knowledge Engine without a rewrite of either.

## 14. Risks

- **Connector sprawl without governance**: without a real review process for adding connectors, the registry could accumulate low-quality or non-compliant connectors over time. Mitigation: the `capabilities()`/compliance-note pattern in section 6.3 should be a mandatory part of any new connector's design review, not just documentation.
- **Over-eager auto-merge in the Dedup Engine**: a miscalibrated confidence threshold could silently corrupt candidate records by merging distinct people. Mitigation: the conservative-by-default stance in section 9.2, plus keeping merges reversible via preserved per-source attribution, is the primary safeguard — thresholds should be tuned empirically against a labeled test set before any auto-merge is trusted in production.
- **Compliance drift**: a connector compliant at build time (e.g. a public API) can have its terms change later. Mitigation: `health_check()` per connector is a natural place to also periodically re-verify terms/access are still valid, not just that the endpoint is reachable — worth designing that check to fail closed (disable the connector) rather than fail open if terms verification itself fails.
- **Normalizer fragility against upstream schema changes**: any connector's source API changing its shape silently breaks that connector's mapping. Mitigation: per-connector mapping should be tested against realistic fixtures (the same pattern already used for `FakeLLMClient` in this codebase) so a schema drift is caught by a failing test, not a silent bad normalization in production.
- **Scale assumptions baked in too early**: building 10M-candidate infrastructure (sharding, dedicated search index, job queues) before there's real data volume is its own risk (complexity cost with no corresponding benefit). Mitigation: the tiered scalability table in section 12 is intentionally sequential — build for 100K first, add the 1M-tier changes only when approaching that volume, not preemptively.

## 15. Assumptions

- The existing `Candidate` model, `CandidateRepository` interface, and Search Planner/Knowledge Engine contracts remain frozen exactly as built — this document extends the schema (section 5) but does not propose changing any existing class's public contract.
- At least one connector (internal DB, CSV, or resume) will be available from day one of implementation without requiring third-party partnership negotiations, so the Discovery Engine can be built and tested incrementally before compliant external connectors (LinkedIn, Naukri) are available, if ever.
- "AlphaRecrewt integration" fields in the schema (`candidate_assessment_results`, `candidate_interview_history`) assume that product will supply data via its own connector or direct integration at a later date — this document reserves the schema space but does not design that integration's specifics, which is out of scope here.
- Legal/compliance requirements (data retention periods, consent mechanics, right-to-deletion specifics) will be supplied by legal/compliance stakeholders before implementation of the Resume/CSV connectors' retention logic — this document identifies where that requirement plugs in (section 11) but does not invent the policy itself.

## 16. Recommended Implementation Order

1. **Candidate Intelligence Database schema** (section 5) — foundational; everything else writes to or reads from it.
2. **Connector Framework interface + one reference connector** (recommend the Internal DB or CSV connector first — no external auth/compliance complexity, fastest path to an end-to-end test of the whole pipeline).
3. **Candidate Normalizer** for that first connector, proving the canonical `Candidate` mapping end-to-end against real (if limited) data.
4. **`CandidateRepository` swap**: replace `InMemoryCandidateRepository` with a database-backed implementation of the same interface, proving the Intelligence Layer truly needs zero changes — this is the single most important validation checkpoint in the whole build, since it's the architecture's central claim.
5. **Deduplication Engine**, once there are at least two connectors feeding the same database (dedup logic is untestable meaningfully with only one source).
6. **Discovery Strategy** (routing/prioritization/retry) — only once there are 3+ connectors with genuinely different capabilities, so prioritization logic has something real to prioritize between.
7. **Additional connectors** (Resume, GitHub, then compliant-access-dependent ones like LinkedIn/Naukri only once partner access exists), each following the same Connector → Normalizer-mapping → test-fixture pattern established in step 2-3.
8. **Data Freshness / background refresh jobs** — deferred until there's enough live data volume that staleness is an observed problem, not a theoretical one.
9. **Scalability tier-1M changes** (dedicated search index, blocking-based dedup) — only once approaching real 1M-candidate volume, per the risk noted in section 14.
