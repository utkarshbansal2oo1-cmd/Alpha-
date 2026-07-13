# Evidence Graph & Talent Intelligence Architecture

Status: **Design only — no implementation in this sprint.** Builds directly on `docs/DISCOVERY_ENGINE_ARCHITECTURE.md` (Sprint 8, approved). That document answered "how do we search and route to sources." This document replaces its "Candidate Intelligence Database" (section 5 of that doc) with something more fundamental: an **Evidence Lake**, from which candidate profiles are *generated*, never *stored directly*. Everything else from Sprint 8 — the Connector Framework, Discovery Strategy shape, `CandidateRepository` interface boundary — remains valid and is extended, not replaced.

## 0. The Core Shift

Sprint 8 designed a pipeline that ends in a `candidates` table with fields written directly onto a candidate record (skills, career, education). That is a reasonable design for a system with 3-4 trusted sources. It is the wrong design for a system meant to outlive any single source.

The shift: **no fact is ever written directly onto a candidate.** Every fact discovered anywhere — a resume line, a GitHub repo, a conference talk, a recruiter's note — is stored first as an independent, immutable **Evidence** record. A candidate profile is not a row that gets updated; it is a **view computed from the current evidence graph**, regenerated whenever the underlying evidence changes. If GitHub disappears tomorrow, every candidate whose profile included GitHub-derived evidence doesn't lose their profile — they lose *one input* to a profile that's still built from everything else. This is the literal mechanism behind the brief's requirement: "the product should survive if any single connector disappears."

This is the same design principle already proven elsewhere in this codebase at smaller scale: the Knowledge Engine never lets a raw recruiter term become "truth" directly — it's normalized and expanded through an explicit, versioned, weighted graph first (`docs/KNOWLEDGE_ENGINE.md`). The Evidence Lake applies that identical philosophy — explicit, weighted, versioned, never-silently-overwritten — to candidate facts instead of taxonomy terms.

## 1. Evidence Lake

### 1.1 What it is

An append-only store of atomic, independently-sourced observations. "Append-only" is not a stylistic choice — it is the property that makes the whole architecture trustworthy: nothing is ever overwritten, so any candidate profile generated at any point in time can be explained by pointing at the exact evidence that produced it, and any evidence later found to be wrong is *superseded*, not erased, preserving the audit trail.

### 1.2 What counts as evidence

Every one of the brief's examples is treated identically at the storage layer — resume claims, GitHub repos, portfolio sites, company staff pages, conference speaker listings, patents, publications, interview transcripts, assessment results, and recruiter notes are all `Evidence` records differing only in `source_type`, `confidence`, and `parsed_fields`. This uniformity is deliberate: the Identity Resolution Engine and Candidate Intelligence Builder (sections 3, 5) operate on one shape regardless of provenance, so adding "conference speaker page" as a new evidence type later requires a new ingestion path, never a new code path through the resolution/building logic.

### 1.3 What it explicitly is not

It is not a candidate database with a `sources` audit column bolted on (that was Sprint 8's `candidate_source_attribution` table — a reasonable pattern for a source-of-truth candidate table, but insufficient here because it still treats the *candidate* as the primary stored object). Here, evidence is primary; candidates are derived. This is the same distinction as event-sourcing versus a mutable-state database: the events (evidence) are the source of truth, the current-state view (candidate profile) is a projection that can always be rebuilt from them.

## 2. Evidence Model (Schema)

Every evidence item is a single, immutable record with these fields:

| Field | Purpose |
|---|---|
| `evidence_id` | Unique, immutable identifier for this exact observation |
| `source_type` | e.g. `resume`, `github`, `portfolio`, `company_page`, `conference`, `patent`, `publication`, `interview`, `assessment`, `recruiter_note` — an open, extensible enum |
| `source_connector` | Which connector (per Sprint 8's Connector Framework) produced this — links evidence back to the Discovery Engine that found it |
| `source_url` | The exact locatable origin, where one exists (a resume upload has no URL; a GitHub profile does) |
| `discovery_time` | When AlphaSource first observed this fact (distinct from when the fact became true in the real world — a 2019 job change discovered in 2026 still has a 2026 `discovery_time`) |
| `confidence` | Initial trust score for this evidence, per the source-type baseline in section 4, before any Identity Resolution or corroboration adjustment |
| `verification_status` | `unverified` / `corroborated` (matched by another independent source) / `verified` (confirmed via an authoritative or first-party channel, e.g. an assessment result) / `disputed` (contradicted by other evidence) / `superseded` (replaced by newer evidence about the same fact) |
| `extraction_method` | How the `parsed_fields` were derived — e.g. `llm_extraction`, `structured_api`, `manual_entry`, `regex_parse` — critical for debugging when an extraction is wrong, and for weighting confidence (a structured API field is more reliable than an LLM's best-effort parse of unstructured text) |
| `raw_content_reference` | Pointer to the original raw content (blob storage), never inlined — keeps the evidence record small and lets raw content be independently retained/purged per compliance policy without touching the evidence record itself |
| `parsed_fields` | The structured extraction — e.g. `{"skill": "Kubernetes", "context": "listed under Technical Skills"}` for a resume line, or `{"company": "Acme Corp", "title": "Staff Engineer"}` for a company staff page |
| `candidate_probability` | How likely this evidence item is to belong to a *specific* candidate identity (starts unset/null at ingestion, populated by Identity Resolution — see section 3) — deliberately separate from `confidence`, because a piece of evidence can be highly confident in *what it says* (e.g. "this GitHub profile definitely uses Go") while still uncertain in *whose* profile it belongs to |
| `ttl` | Time-to-live / recommended re-verification window (section 4.2) — not a hard deletion timer, but the trigger for the freshness/re-check logic inherited from Sprint 8 section 7 |
| `version` | Monotonically incremented only if this evidence record itself is corrected (e.g. a parsing bug fixed and the record re-extracted) — distinct from superseding, which creates a *new* evidence record rather than changing this one |
| `relationships` | Links to other evidence records this one corroborates, contradicts, or supersedes — this is what lets Evidence Verification (section 4) reason about a *body* of evidence rather than each record in isolation |

Two evidence records about the same underlying fact (e.g. a resume claiming "AWS" and a GitHub repo showing AWS SDK usage) are never merged into one row — they remain two evidence records, linked via `relationships` as corroborating each other, both still fully traceable to their original source.

## 3. Identity Resolution Engine

Sprint 8's Deduplication Engine (section 9 of that document) merged already-normalized `Candidate` records. Identity Resolution is a generalization of that same signal-based-confidence idea, applied one level earlier: it decides whether *evidence items* — which may never have passed through a "candidate" shape at all — belong to the same human, before any candidate profile is built.

### 3.1 Staged approach

**Stage 1 — Strong deterministic signals.** Verified email match, verified phone match, exact GitHub username match, exact LinkedIn URL match (where legitimately present). Any one of these, if independently verified (not just self-asserted), links two evidence items to the same identity with very high confidence, largely mirroring Sprint 8 section 9.1's signal table but applied to raw evidence rather than post-normalization candidates.

**Stage 2 — Corroborating contextual signals.** Company + overlapping timeframe (two evidence items both placing this identity at "Acme Corp" in 2022), geography, and skill-set overlap. None of these alone should resolve an identity — they are used to *raise or lower* the confidence of a Stage 1 or Stage 3 match, or to surface a candidate identity link for Stage 3 review, never to unilaterally merge.

**Stage 3 — AI-assisted resolution.** For evidence pairs that Stage 1 can't resolve deterministically and Stage 2's contextual signals are ambiguous or conflicting, an LLM-backed resolution step (using the same provider-agnostic `LLMClient` interface pattern already established in `query_understanding/gemini_client.py` — this is not a new AI integration pattern, it's the existing one applied to a new problem) evaluates the full context of both evidence items and produces a confidence score plus a natural-language rationale. Crucially, this AI confidence is *one more signal*, weighted alongside Stages 1-2, never an unchallengeable final answer — consistent with this project's standing principle (established since the Query Understanding Engine) that AI output is validated and explainable, not trusted blindly.

**Stage 4 — Threshold decision**, mirroring Sprint 8 section 9.2's three-band structure exactly (auto-link above a high threshold; flag-for-review in a middle band; keep separate below threshold) — reused deliberately rather than reinvented, since that conservative-merge philosophy is exactly as valid at the evidence-identity level as it was at the candidate-record level.

### 3.2 Why this must be staged, not a single model call

A single "does this evidence belong to the same person, yes/no" model call would be an unexplainable black box exactly where explainability matters most — an incorrectly linked identity silently corrupts every downstream candidate profile built from it. Staging the resolution means every identity link can be traced to *which stage* resolved it and *which signals* it used, the same explainability requirement already enforced everywhere else in this platform (Search Planner's `WhyMatched`, Query Understanding's typed validation errors).

## 4. Evidence Verification & Confidence Scoring

### 4.1 Source-type baseline confidence

| Source type | Baseline confidence | Rationale |
|---|---|---|
| Resume (self-submitted, but structured) | 95% | Highest baseline — candidate directly asserting their own history, high specificity, but still self-reported (not independently verified) |
| Assessment result | 95% | First-party, produced by AlphaRecrewt/the platform itself — effectively verified by construction |
| GitHub | 90% | Public, structured, behaviorally-evidenced (actual code, not a claim) — very hard to fabricate at scale |
| Company website / staff page | 88% | Third-party (the employer), authoritative about employment fact, but may lag reality (stale pages) |
| Conference speaker page | 85% | Third-party, but validates expertise/seniority signal more than exact role/dates |
| Patent / publication | 85% | Strong domain-expertise signal, weaker on current role/company/skills currency |
| Interview transcript | 80% | Rich signal, but extraction-quality-dependent (NLP-derived from conversation, not structured) |
| Personal blog / portfolio | 70% | Self-authored like a resume, but typically less structured and less consistently maintained |
| Recruiter note | 65% | Valuable context, but explicitly subjective/human-opinion rather than a verifiable fact — see note below |
| Anonymous/unverified web mention | 20% | Lowest baseline — no accountable authorship, easily wrong or about a different person entirely |

Recruiter notes deserve a specific callout: they are stored as evidence (so they're versioned, attributed, and integrated into the same explainability model as everything else) but are never used by Identity Resolution as a linking signal and are never allowed to silently override a higher-confidence factual evidence item — they're context *for a human reading the profile*, not an input to automated confidence math beyond that.

### 4.2 How confidence evolves over time

- **Corroboration increases confidence.** An independent second source confirming the same fact (e.g. GitHub showing Kubernetes usage, corroborating a resume's Kubernetes claim) raises both evidence items' *effective* confidence (not their stored baseline — baseline is fixed per source type; effective confidence is a computed, evidence-relationship-aware value) without needing to re-verify either from scratch.
- **Contradiction lowers confidence and flags for review**, rather than one arbitrarily "winning" — a resume claiming "Staff Engineer" contradicted by a company page still listing "Senior Engineer" doesn't get silently resolved by source-type baseline alone; it's marked `disputed` and surfaced.
- **Age decays confidence gradually**, tied to the `ttl` field — a two-year-old unconfirmed skill claim is less trustworthy than the same claim confirmed last month, without requiring a hard expiration. This is a smooth decay function of time-since-`discovery_time` (or time-since-last-corroboration, if more recent), not a cliff-edge deletion.
- **Re-verification resets the decay**, not the evidence record itself — a fresh, independent confirmation creates a *new* evidence record (linked via `relationships` as corroborating the original), and the *candidate profile's* effective confidence for that fact is recalculated from the combined evidence, while the original record remains untouched and dated as it always was.

## 5. Candidate Intelligence Builder

```
Evidence (many records, many sources, all independently stored)
        |
        v
Identity Resolution  (groups evidence into identity clusters,
                       per section 3's staged confidence process)
        |
        v
Candidate Intelligence  (a GENERATED view: for one resolved identity
                          cluster, aggregate every linked evidence
                          item's parsed_fields into the shape the rest
                          of the platform already expects --
                          candidate_repository.models.Candidate,
                          extended per Sprint 8 section 5's richer
                          schema -- computed fresh from currently-valid
                          evidence, not stored as the source of truth)
        |
        v
CandidateRepository.search()  (existing, frozen interface --
                                completely unaware that what it reads
                                is now a generated view rather than a
                                directly-written row)
```

The critical property: **a candidate profile is a query result, not a stored object.** "Building" a candidate means: take an identity cluster, pull every still-valid (non-superseded, non-fully-decayed) evidence item linked to it, resolve any disputed fields using the confidence/corroboration rules from section 4, and assemble the result into the canonical `Candidate` shape. This can be computed on-demand (for a live search) or materialized/cached for performance (see section 7 — the cache is an optimization, never the source of truth). If the underlying evidence changes, the next build reflects it automatically — there is no separate "update the candidate record" step to forget to run.

This also directly answers "what happens if GitHub disappears": the GitHub-sourced evidence items don't vanish (they're already stored, immutably, in the Evidence Lake) — only *new* GitHub evidence stops arriving. Every existing candidate profile continues to build correctly from what's already there; it simply stops receiving that one input's updates going forward, exactly the resilience property the brief requires.

## 6. Talent Graph

The Talent Graph is the relationship layer sitting alongside (not instead of) the Evidence Lake and generated Candidate Intelligence. Where the Evidence Lake answers "what do we know and from where," the Talent Graph answers "how does everything relate."

**Node types**: Candidate (generated identity clusters), Skill (already exists as canonical entities in the frozen Knowledge Engine taxonomy — reused, not duplicated), Company, University, Certification.

**Edge types and what they represent**:
- **Candidate ↔ Skill**: weighted by evidence-derived confidence and corroboration count (a skill backed by resume + GitHub + a certification is a stronger edge than one backed by a single unverified mention) — this directly extends the Knowledge Engine's existing weighted-edge philosophy (`docs/KNOWLEDGE_ENGINE.md`) from taxonomy-to-taxonomy edges to candidate-to-taxonomy edges.
- **Candidate ↔ Company**: timestamped (start/end, from career evidence), so the graph encodes not just "worked at" but "worked at, during this window" — necessary for corroboration checks in section 3.2 (overlapping timeframe signals).
- **Candidate ↔ University**: from education evidence, generally low-decay (a degree doesn't expire) but still versioned like everything else.
- **Candidate ↔ Certification**: similar to skills but typically higher baseline confidence (certifications are third-party issued, closer to "verified" by default).
- **Company ↔ Skill**: an aggregate, derived edge (not evidence-sourced directly) — computed from "which skills are common among candidates who worked at this company," useful for market-intelligence questions ("what does Company X actually hire for") without being a new evidence type itself.
- **Skill ↔ Skill**: already exists in the Knowledge Engine as expansion/alias edges (e.g. AWS→EC2/Lambda/S3) — the Talent Graph consumes this existing structure rather than re-deriving it, keeping the Knowledge Engine as the single source of truth for skill relationships.
- **Candidate ↔ Candidate**: derived from shared company+timeframe (colleagues), shared university+timeframe (alumni), or shared project/publication co-authorship evidence — this is the edge type that enables genuinely new product capability beyond search (e.g. referral-path discovery, team-composition analysis) and is explicitly the seed of the "Enterprise Talent Graph" evolution stage (section 10).

The graph is a read-optimized structure derived from the Evidence Lake plus Identity Resolution output — like the generated Candidate Intelligence, it is rebuildable from evidence, not an independent source of truth. This matters for the same reason as everywhere else in this document: if the graph's derivation logic has a bug and produces wrong edges, the fix is "recompute from evidence," never "manually patch the graph," preserving the same auditability guarantee.

## 7. Continuous Learning (Incremental, Never Full-Rebuild)

```
New evidence arrives (via Discovery Engine, Sprint 8)
        |
        v
Evidence Lake: append new evidence record (immutable, versioned)
        |
        v
Identity Resolution: re-evaluate ONLY the affected identity cluster
        (the one this evidence's preliminary signals point toward --
         never a full re-scan of all existing clusters)
        |
        v
Confidence recalculation: re-run section 4's corroboration/decay math
        ONLY for evidence items linked to the affected identity cluster
        and any directly-relevant Talent Graph edges
        |
        v
Candidate profile cache invalidation: mark the affected candidate's
        generated profile as stale (or eagerly recompute it, depending
        on read-latency requirements) -- other candidates' cached
        profiles are entirely untouched
        |
        v
Talent Graph edge update: update only the edges touching the affected
        candidate node -- the rest of the graph is untouched
```

The mechanism that makes this genuinely incremental rather than "incremental in theory, full-scan in practice": every new evidence item arrives with enough preliminary signal (email, name, source connector context) to narrow Identity Resolution to a small candidate set *before* any expensive comparison happens — Stage 1's deterministic signals (section 3.1) are used first specifically as a fast filter, with Stages 2-3's more expensive contextual/AI evaluation reserved only for the narrowed candidate set. This mirrors the same reasoning already applied in Sprint 8's scalability section 12 (blocking-based dedup at scale) — it's the same computational-tractability principle, just applied continuously rather than in a batch dedup pass.

"No full rebuilds" specifically means: the system never needs to reprocess the entire Evidence Lake to incorporate one new fact. A candidate profile that hasn't received new evidence is never touched, recomputed, or re-verified as a side effect of unrelated activity elsewhere in the platform.

## 8. Discovery Strategy (Evidence-Oriented Reframing)

Sprint 8's Discovery Strategy answered "which connector should I search." This sprint reframes the same machinery around evidence rather than platforms:

**Discovery Strategy**: given a recruiter need (a `SearchPlan`, unchanged from the existing Search Planner) or a background enrichment goal, decide which *evidence types* are likely to be productive to seek — not "search LinkedIn," but "seek employment-history evidence and skill evidence for this profile" — then map that need to whichever currently-available connectors (per Sprint 8's Connector Framework) can supply those evidence types. If a connector for a given evidence type is unavailable (removed, rate-limited, non-compliant), the strategy simply seeks that evidence type through whichever other connectors can supply it, or accepts a lower-confidence/lower-completeness result — it never has a hardcoded dependency on one specific connector's existence.

**Evidence Discovery**: the dispatch mechanism itself is unchanged from Sprint 8's Connector Dispatcher — concurrent, per-connector timeout/retry, health-check-aware.

**Evidence Prioritization**: replaces Sprint 8's "connector prioritization" with prioritization by *expected evidence value* — a connector likely to supply a high-baseline-confidence, corroborating evidence type (section 4.1) for a currently-thin identity cluster is prioritized over one likely to supply redundant, already-well-corroborated evidence.

**Evidence Verification**: newly discovered evidence is run through section 4's confidence scoring and section 3's Identity Resolution before it's considered "settled" — nothing discovered is trusted at face value merely because it was successfully fetched.

**Evidence Merge**: not merging *candidates* (there is no candidate row to merge — section 5) but merging *identity clusters*, exactly as designed in section 3 — "merge" here means linking evidence records to the same resolved identity, never overwriting one evidence record with another.

## 9. Compliance

Directly inherits and strengthens Sprint 8 section 8's stance, now made structurally easier by the evidence-first design:

- **User-authorized integrations** (an ATS a company owns, a candidate uploading their own resume, an authorized AlphaRecrewt assessment result) map naturally to high-confidence, low-compliance-risk evidence types (section 4.1's top tier) — the architecture's own confidence model happens to align with the compliance-risk gradient, which is not a coincidence: sources with clearer authorization tend to be more structured and verifiable in the first place.
- **Company-owned data** (a company's own career page, their own ATS) is evidence about roles/companies the company itself controls and discloses — no third-party platform terms are implicated.
- **Publicly available information where permitted** (GitHub's public API within its terms, a public conference speaker page, a published patent) is treated as evidence exactly like any other source — the architecture does not distinguish "public" from "private" evidence structurally, only by `source_type` and the compliance posture that source type carries.
- **LinkedIn and Naukri remain scoped to official partner/API access only**, unchanged from Sprint 8 — this document does not revisit or soften that constraint. If such access is never obtained, those source types simply never populate the Evidence Lake; nothing else in the architecture depends on them existing.
- **The system remains valuable with any subset of connectors** precisely because of the evidence-first design: a deployment with only an ATS Connector, a Resume Connector, and a GitHub Connector still produces real, corroborated, explainable candidate intelligence — fewer evidence types per candidate on average, but no architectural degradation, no broken assumptions, no code path that only works "if LinkedIn is present." This is the concrete, structural answer to the brief's requirement that the product survive the loss of any single connector — it is not a resilience feature bolted on, it is the reason the Evidence Lake design was chosen over a direct candidate-database design in the first place.

## 10. Long-Term Vision

```
Search Engine
   (recruiter query -> Query Understanding -> Search Planner ->
    static seed data -- built, tested, live today)
        |
        v
Discovery Engine
   (Sprint 8 -- multi-connector search, normalized into a
    candidate database, still source-dependent per record)
        |
        v
Evidence Lake
   (this document -- facts stored independently of any candidate
    record; provider-independence becomes structural, not aspirational)
        |
        v
Talent Intelligence Platform
   (Identity Resolution + Candidate Intelligence Builder make
    generated, explainable, continuously-current candidate profiles
    the default way the product represents a person -- not a stored
    record but a live view over evidence)
        |
        v
Enterprise Talent Graph
   (Candidate <-> Candidate, Company <-> Skill, and market-level
    relationship queries become first-class product capability --
    "who are this candidate's likely referral paths," "what does
    this company actually hire for" -- value shifts from search to
    market intelligence)
        |
        v
AI Hiring Operating System
   (the Talent Graph plus AlphaRecrewt's assessment/interview layer
    plus the existing explainable-AI foundation combine into a single
    continuous system spanning discovery through hire -- search,
    intelligence, assessment, and decision-support unified, per the
    product's own stated future vision in the original project brief:
    "Search -> Rank -> Shortlist -> AlphaRecrewt Assessment ->
    AI Interview -> Hiring")
```

Each transition is additive, never a rewrite: Discovery Engine reused the Search Planner untouched; the Evidence Lake reuses the Connector Framework untouched; the Talent Graph reuses the Knowledge Engine's skill-edge model untouched. This document's design is only defensible as "long-term competitive advantage" because each layer strictly increases what the system can explain and survive, without ever discarding what was built before it.

## Component Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                    Evidence Lake (append-only)                   │
│  resume | github | portfolio | company_page | conference |       │
│  patent | publication | interview | assessment | recruiter_note  │
└───────────────────────────────┬────────────────────────────────--┘
                                 v
                  ┌───────────────────────────┐
                  │  Identity Resolution       │
                  │  Stage 1: deterministic     │
                  │  Stage 2: contextual         │
                  │  Stage 3: AI-assisted        │
                  │  Stage 4: threshold decision │
                  └─────────────┬─────────────┘
                                v
                  ┌───────────────────────────┐
                  │ Candidate Intelligence     │
                  │ Builder (generated view,   │
                  │ not stored source of truth)│
                  └──────┬─────────────┬───────┘
                         v             v
              ┌──────────────┐  ┌──────────────┐
              │ CandidateRepo │  │ Talent Graph  │
              │ .search()     │  │ (nodes/edges  │
              │ (existing,    │  │ derived from  │
              │ unchanged)    │  │ evidence)     │
              └──────────────┘  └──────────────┘
```

## Sequence Diagram (new evidence arriving)

```
Connector       Evidence Lake    Identity Resolution   Candidate Builder   Talent Graph
    |                |                    |                     |                |
    |--raw result--->|                    |                     |                |
    |                |--store evidence--->|                     |                |
    |                |  (append, versioned)|                     |                |
    |                |                    |--resolve identity-->|                |
    |                |                    |  (stages 1-4,        |                |
    |                |                    |   narrowed cluster   |                |
    |                |                    |   only)              |                |
    |                |                    |<--linked/flagged-----|                |
    |                |                    |                     |--invalidate/---|
    |                |                    |                     |  recompute      |
    |                |                    |                     |  ONLY this      |
    |                |                    |                     |  candidate's    |
    |                |                    |                     |  profile+edges  |
    |                |                    |                     |                |
    |                |                    |                     |<--updated------|
```

## Scalability Analysis

Extends Sprint 8 section 12's tiers with the Evidence Lake's specific characteristics:

| Scale (evidence items, not candidates -- an evidence-first system has far more rows than a candidate-first one) | What changes |
|---|---|
| **Low volume (early deployment, roughly matching Sprint 8's 100K-candidate tier)** | A single append-only evidence store (relational or a document store, either works at this volume) with indexes on `source_connector`, `discovery_time`, and whatever fields Stage 1 identity signals need (email/phone hashes). Identity Resolution and Candidate Building can run synchronously or near-synchronously. |
| **Mid volume (roughly Sprint 8's 1M-candidate tier, but now measured in evidence items which will be several-fold higher)** | Evidence storage benefits from being a genuinely append-only/log-oriented store (write-optimized) separate from the read-optimized Candidate Intelligence cache and Talent Graph store — three distinct storage concerns instead of one. Identity Resolution's Stage 1 filtering becomes mandatory (never full-cluster comparison) to keep Stage 3's AI-assisted resolution's cost bounded, since AI calls are the most expensive step and must only run on genuinely ambiguous, pre-narrowed pairs. |
| **High volume (roughly Sprint 8's 10M-candidate tier and beyond)** | The Evidence Lake likely partitions by source type or by discovery time (time-partitioned append-only logs are a well-understood pattern at this point), the Talent Graph likely needs a dedicated graph-store engine rather than relational foreign keys (to make multi-hop queries like "candidates who worked with this candidate's manager" tractable), and Continuous Learning's incremental recompute (section 7) becomes a proper event-driven pipeline (evidence arrival as an event stream triggering scoped downstream recomputation) rather than in-process function calls. |

The consistent principle carried from Sprint 8: none of this changes `CandidateRepository`'s interface or anything above the Discovery/Evidence layer — scale is entirely absorbed within this document's own components, exactly as scale was absorbed within Sprint 8's Discovery Engine without touching the Intelligence Layer.

## Implementation Roadmap

1. **Evidence schema + append-only store** (section 2) — foundational, nothing else can be built before this exists.
2. **One evidence-producing connector feeding it** (reuse Sprint 8's recommended first connector — CSV or internal DB — now writing Evidence records instead of directly-normalized Candidate records).
3. **Identity Resolution Stage 1 only** (deterministic signals) — proves the narrowing mechanism before any AI cost is introduced.
4. **Candidate Intelligence Builder, minimal version** — generates a `Candidate`-shaped view from a single connector's evidence, proving the "profile is a query, not a row" claim end-to-end before adding complexity.
5. **`CandidateRepository` swap** to read from the generated Candidate Intelligence Builder output — the same critical validation checkpoint Sprint 8 identified, now one layer deeper.
6. **Second connector + Identity Resolution Stages 2-3** — dedup/resolution logic is meaningless to build or tune with only one source, exactly as noted in Sprint 8.
7. **Confidence scoring + corroboration/decay math** (section 4) — needs at least two corroborating sources in place (step 6) to be testable against real cases.
8. **Talent Graph, Candidate↔Skill and Candidate↔Company edges first** (highest immediate product value, reuses the already-frozen Knowledge Engine skill graph directly).
9. **Continuous Learning's incremental recompute pipeline** (section 7) — deferred until steps 1-8 are stable, since premature event-driven infrastructure without real incremental-update cases to validate against is wasted complexity, mirroring Sprint 8's own caution against building for scale before the scale exists.
10. **Candidate↔Candidate edges and market-intelligence graph queries** — explicitly the last step, since this is the "Enterprise Talent Graph" evolution stage (section 10) and depends on everything before it being trustworthy first.
