# Autonomous Evidence Discovery System

Status: **Design only — no implementation, no connectors built in this sprint.** Builds on `docs/DISCOVERY_ENGINE_ARCHITECTURE.md` (Sprint 8) and `docs/EVIDENCE_GRAPH_ARCHITECTURE.md` (Sprint 9), both approved. Sprint 8 designed *where* to route a search. Sprint 9 redefined the destination — evidence, not candidates. This document designs the *behavior* that continuously fills the Evidence Lake without a human manually triggering each search: an AI research agent whose only output is evidence, that reasons about where evidence probably exists rather than which platform to query.

## 0. Framing

Everything below is a planning and orchestration layer sitting in front of the Connector Framework (Sprint 8, unchanged) and writing into the Evidence Lake (Sprint 9, unchanged). Nothing here proposes a new storage model or a new candidate-representation model — this document is exclusively about *what triggers discovery, what it seeks, how it prioritizes, when it stops, and how it gets smarter*. The single sentence that should be true throughout: **the system decides what evidence is worth looking for and where to look, never which named platform to depend on.**

## 1. Discovery Planner

### Input → Output

```
SearchPlan (existing, from Search Planner -- strict/expanded terms,
            weights, field_types -- unchanged contract)
        |
        v
              Discovery Planner
        |
        v
Discovery Plan:
  - evidence_goals: [{ evidence_type, target_field, justification }]
  - candidate_evidence_types_sought: e.g. "skill evidence", "employment
    evidence", "seniority-signal evidence" -- not "LinkedIn results"
  - source_candidates: ranked list of currently-registered connectors
    whose declared capabilities() (Sprint 8 section 6) can plausibly
    supply each evidence_goal
  - stopping_criteria: see section 5
  - evolution_hooks: conditions under which the plan should widen,
    narrow, or re-prioritize mid-execution (section 3)
```

### What it decides

**What evidence should we seek?** The Discovery Planner translates a `SearchPlan`'s strict and expanded terms into evidence *goals*, not queries. "Find Kubernetes-skilled Platform Engineers" becomes goals like "seek skill evidence for Kubernetes and its expansions (EKS, Docker — already known via the frozen Knowledge Engine's expansion graph)" and "seek employment-history evidence for Platform Engineer or its role-expansions." The distinction matters: a goal is a *need*, satisfiable by any evidence type/source combination; a query is a *specific instruction to one connector*. Keeping the Planner's output at the goal level is what lets new connectors slot in later without the Planner itself changing (identical reasoning to Sprint 8's `capabilities()`-first design).

**Where is that evidence likely to exist?** The Planner consults a **Source Suitability Model** — a learned/maintained mapping from evidence goal to expected-yield per registered connector (formalized in section 6). Early on, with no learned history, this falls back to static heuristics informed by evidence-type baseline confidence (Sprint 9 section 4.1) and connector capability declarations. Over time, the mapping is empirically corrected (section 6).

**How should the search evolve?** The Discovery Plan is not fire-and-forget — it carries `evolution_hooks`: conditions like "if fewer than N evidence items found for this identity cluster after the first discovery pass, broaden to lower-confidence source types" or "if a high-value evidence goal is fully satisfied early, reallocate remaining budget to a still-thin goal." This is what separates a Discovery Plan from a static search query list — it is closer to a research strategy than a fixed instruction set.

## 2. Discovery Sources — Classification

Rather than a flat list of named platforms, sources are classified along dimensions the Discovery Planner and Strategy layers actually reason about:

| Dimension | Categories |
|---|---|
| **Ownership** | Company-owned (internal HRMS, ATS, employee referrals — data the hiring org already controls) · Candidate-submitted (resume uploads, recruiter uploads) · Third-party public (GitHub, conference speaker pages, research papers, patents, government registries, portfolio sites) · Third-party restricted (platforms requiring authorized partner access — unchanged constraint from Sprint 8/9) |
| **Structure** | Structured API (GitHub API, a government registry's public API, an ATS's API) · Semi-structured (company staff pages, conference agendas) · Unstructured (resumes, blog posts, interview transcripts) |
| **Update cadence** | Real-time-ish (APIs) · Slow-changing (patents, publications, degrees) · Event-driven (a new conference talk, a new company page update) |
| **Compliance posture** | Fully compliant by ownership (internal/candidate-submitted) · Compliant public access (documented API terms, e.g. GitHub) · Requires authorization (partner APIs — LinkedIn/Naukri-class) · Not usable (anything requiring bypassing platform protections — permanently out of scope, unchanged from Sprint 8/9) |

Concretely, this sprint's source list maps onto that classification as follows: **Company-owned/structured** — internal HRMS, ATS, employee referral systems. **Candidate-submitted** — resume uploads, recruiter uploads. **Third-party public, structured** — GitHub, public APIs, government registries (where an API exists). **Third-party public, semi/unstructured** — company websites, conference speaker pages, portfolio sites, research papers, patents. **Third-party restricted** — any future connector requiring a platform partnership (LinkedIn/Naukri-class, unchanged).

This classification is what the Source Suitability Model (section 6) actually keys on — "structured, third-party-public sources tend to be high-yield for skill evidence" is a learnable, generalizable pattern; "LinkedIn is good for X" is not, because it doesn't transfer to the next new connector.

## 3. Discovery Strategies (Evidence Hunting, Not Platform Search)

| Strategy | When used | Behavior |
|---|---|---|
| **Targeted Discovery** | A specific, narrow `SearchPlan` with tight strict filters (e.g. a named skill + named location) | Discovery Planner produces a small number of high-confidence evidence goals, dispatches against the highest-suitability sources only, stops early once sufficient evidence is found (section 5) |
| **Broad Discovery** | A wide/exploratory `SearchPlan`, or an intentional market-mapping goal ("who works in DevOps in this region") | Wider evidence-goal set, deliberately includes lower-suitability-but-cheap sources to maximize identity-cluster discovery breadth over per-cluster depth |
| **Incremental Discovery** | An identity cluster already has some evidence; new discovery should fill *gaps*, not re-seek what's already well-corroborated | Discovery Plan's evidence_goals are filtered against the existing Evidence Lake state for that cluster first — this is the same principle as Sprint 9 section 7's "recalculate only what changed," applied at planning time instead of only at ingestion time |
| **Scheduled Refresh** | Time-based, tied to Sprint 8 section 7 / Sprint 9 section 4.2's freshness/decay windows | Runs as a background job, not recruiter-triggered; evidence goals are generated from "which evidence is approaching its confidence-decay threshold" rather than from any live `SearchPlan` |
| **Background Discovery** | Idle-capacity discovery not tied to any specific recruiter need — building general Evidence Lake depth ahead of demand | Lowest priority in the queue (section 4); driven by the Discovery Intelligence layer's learned sense of "what's likely to be searched for soon" (section 6) rather than a specific request |
| **Cold Start** | A brand-new deployment, or a new market/geography/role-category with no existing evidence at all | No learned Source Suitability Model data yet — falls back to the static heuristic baseline (section 1) and deliberately over-invests in Broad Discovery initially to bootstrap enough evidence for the Discovery Intelligence layer to start learning from real yield data |

## 4. Crawler Orchestration (Design, Not Implementation)

### Mission Queue

Every discovery action (one connector, one evidence goal, one identity cluster or search context) is a **Mission** — the atomic unit of work the orchestration layer schedules, tracks, retries, and reports on. A Mission carries: its originating Discovery Plan, target connector, target evidence goal, priority score (section 7), attempt count, and status.

### Priority Queue

Missions are ordered by the Priority Score (section 7), not FIFO and not strictly by strategy type — a low-priority Background Discovery mission can still outrank a Targeted Discovery mission if its evidence-value-to-cost ratio is higher (e.g. a cheap, high-yield-probability API call beats an expensive, uncertain one even if the latter came from a "more important" live search). Strategy type influences priority; it does not override it outright.

### Retry

Per-Mission, bounded exponential backoff (mirrors Sprint 8 section 3's connector-level retry, but scoped to the Mission rather than the whole search) — a failed Mission is requeued at lower priority with an incremented attempt count, up to a cap, after which it's marked `failed` and surfaced (never silently dropped, consistent with this project's standing convention of typed, visible failures over silent ones).

### Scheduling

Two scheduling classes: **reactive** (a live `SearchPlan` generates Missions immediately, dispatched as soon as capacity allows) and **proactive** (Scheduled Refresh and Background Discovery generate Missions on a cadence/idle-capacity basis, always at lower priority than reactive Missions unless the priority score genuinely says otherwise).

### Freshness

Every Mission targeting an identity cluster or evidence goal checks the Evidence Lake's current state first (per Sprint 9's `ttl`/decay fields) — a Mission that would only reproduce already-fresh, already-corroborated evidence is deprioritized or skipped entirely, directly implementing Sprint 8 section 7's "avoid unnecessary crawling" at the orchestration level.

### Rate Awareness

Per-connector rate-limit budgets (declared via Sprint 8's `rate_limit_policy()`) are tracked centrally by the orchestrator, not per-Mission — the Mission Queue holds back dispatch for a connector that's at its budget ceiling rather than letting individual Missions independently violate it. This is a shared-resource scheduling problem, solved once, centrally.

### Failure Recovery

Beyond per-Mission retry: if a connector's failure rate crosses a threshold within a time window, the orchestrator suspends new Missions to that connector entirely (not just the failing one) until its `health_check()` (Sprint 8 section 6.1) recovers — protecting the rest of the system's throughput from one degraded source.

### Source Health

A rolling per-connector health score (successful Mission rate, average latency, current rate-limit headroom) feeds directly into the Source Suitability Model (section 6) — a connector that's healthy but low-yield and one that's high-yield but currently unhealthy are prioritized very differently, and this score is the mechanism that makes that distinction computable rather than judgment-based.

## 5. Evidence Acquisition — Sufficiency and Stopping

**How much evidence is enough?** Defined per evidence goal, not globally: a goal like "confirm current employer" is satisfied by one high-confidence, unresolved-status-free evidence item; a goal like "assess overall skill breadth" has diminishing returns and no single sufficiency point — additional evidence keeps adding value, just at a decreasing rate. The Discovery Planner encodes a **sufficiency function per evidence-goal type** (binary-satisfied vs. diminishing-returns) rather than a single global threshold.

**When should discovery stop?** A Mission set for a given Discovery Plan stops when any of: (a) all binary-satisfiable goals are met at sufficient confidence, (b) diminishing-returns goals' marginal expected value (section 7) drops below the current discovery cost, (c) the discovery budget allocated to this plan is exhausted, or (d) the `evolution_hooks` (section 1) determine broadening further is not worthwhile given results so far. Stopping is a decision made continuously as Missions complete, not only checked at a fixed end — this is what allows Targeted Discovery to genuinely stop early (section 3) rather than always running to a fixed budget.

## 6. Discovery Intelligence — The Learning Planner

### The mechanism

The Source Suitability Model (introduced in section 1) is the concrete artifact that "gets smarter." It is a maintained mapping: `(evidence_goal_type, candidate_context) -> expected_yield_per_source`, updated from observed outcomes — did a Mission targeting this evidence goal via this source actually produce corroborating, high-confidence evidence, or not?

### Worked example (matching the brief's own illustration)

Recruiters frequently issue `SearchPlan`s resolving to evidence goals like "skill evidence for DevOps-adjacent terms" and "employment evidence for infrastructure-heavy roles." Over many Missions, the orchestrator observes: Missions targeting GitHub for these evidence goals produce corroborating evidence at a high rate; Missions targeting conference speaker pages produce lower volume but very high-confidence seniority signals; Missions targeting generic company blogs produce moderate volume, moderate confidence. The Source Suitability Model's weights for `(skill_evidence, devops_context) -> github` and `(seniority_evidence, devops_context) -> conference_pages` are reinforced; a source that was tried and consistently underperformed for this context (e.g. a specific portfolio-site aggregator) has its weight reduced — not removed, since context shifts (a source underperforming for DevOps roles may still be excellent for design roles).

### Why this is safe to let evolve autonomously

The Source Suitability Model only ever influences **prioritization** (section 4's Priority Queue, section 3's strategy source selection) — it never decides what counts as evidence, what confidence an item gets (Sprint 9 section 4, fixed baselines + corroboration math, unaffected by this model), or whether an identity resolution is correct. This bounds the blast radius of the learning system being wrong: a bad suitability weight makes discovery *less efficient*, it never makes the Evidence Lake *less correct*. That separation — a learning component that only affects efficiency/prioritization, never correctness/trust — is deliberate and should be treated as a hard boundary in any future implementation.

## 7. Evidence Economics

**Evidence Value Score**: a function of the evidence goal's importance to pending/likely `SearchPlan`s (reactive discovery) or to closing known Evidence Lake gaps (proactive discovery), weighted by the source-type baseline confidence it would deliver (Sprint 9 section 4.1) and whether it would corroborate existing evidence (corroboration is worth more than a first, unconfirmed data point, per Sprint 9 section 4.2).

**Discovery Cost Score**: a function of connector-specific cost (API call cost if metered, rate-limit budget consumed, compute cost of extraction/parsing, and — for AI-assisted extraction or Identity Resolution Stage 3 — the LLM call cost itself) plus latency cost (how long this Mission likely delays a live recruiter-facing result, for reactive Missions specifically).

**Priority Score**: Evidence Value Score divided by Discovery Cost Score (an ROI ratio, not a difference — this naturally favors cheap-but-useful Missions over expensive-and-marginally-useful ones regardless of absolute value, which is the correct behavior for a shared, budget-constrained queue), further adjusted by Source Health (section 4) and urgency class (reactive vs. proactive, section 4's Scheduling).

**How AlphaSource should spend its discovery budget**: reactive, live-search-driven Missions get first claim on immediate capacity (a recruiter waiting on a result should not be starved by background discovery) — but background/proactive Missions are never fully starved either, since idle capacity between reactive bursts is exactly what Background Discovery (section 3) is designed to consume. Total discovery spend (in whichever unit — API cost, compute cost, or a normalized budget currency) is capped per time period, and the Priority Queue's ROI-based ordering is what determines which Missions actually get funded within that cap — the system should always be able to answer "why was this evidence sought and this other evidence not" in ROI terms, preserving the explainability standard this whole project has held since the Knowledge Engine.

## 8. Autonomous Growth — The Four Loops

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                   │
│   Discovery Loop:                                                │
│   Discovery Planner generates Discovery Plans (reactive from     │
│   live SearchPlans, proactive from Scheduled Refresh/Background) │
│   -> Mission Queue -> Connector Framework (Sprint 8) -> raw       │
│   results -> Evidence Lake (Sprint 9)                            │
│                              |                                    │
│                              v                                    │
│   Verification Loop:                                              │
│   New evidence -> Identity Resolution (Sprint 9 section 3) ->     │
│   Confidence scoring/corroboration (Sprint 9 section 4) ->        │
│   verification_status updates                                     │
│                              |                                    │
│                              v                                    │
│   Graph Update Loop:                                               │
│   Resolved/verified evidence -> Candidate Intelligence Builder     │
│   (Sprint 9 section 5, generated view, incremental per Sprint 9    │
│   section 7) -> Talent Graph edge updates (Sprint 9 section 6),    │
│   scoped only to the affected identity cluster                     │
│                              |                                    │
│                              v                                    │
│   Learning Loop:                                                   │
│   Mission outcomes (did this Mission's evidence get accepted,      │
│   corroborated, disputed, or rejected by Identity Resolution?)     │
│   -> Source Suitability Model update (section 6) -> feeds back     │
│   into the Discovery Planner's next Discovery Plans                │
│                              |                                    │
│                              └──────────────> (back to Discovery Loop)
└─────────────────────────────────────────────────────────────────┘
```

This is the complete answer to "how does the Evidence Lake grow without manual intervention": the Discovery Loop is self-sustaining via Scheduled Refresh and Background Discovery even with zero live recruiter activity; the Learning Loop continuously improves the Discovery Loop's targeting; the Verification and Graph Update loops ensure growth in evidence *volume* is matched by growth in evidence *trustworthiness and structure*, never outpacing it. No loop requires a human to manually initiate the next cycle — human involvement is limited to the review queue for ambiguous Identity Resolution cases (Sprint 9 section 3.1, Stage 4's middle band) and to periodic oversight of the Learning Loop's weight changes, not to triggering discovery itself.

## Component Diagram

```
┌───────────────────────────────────────────────────────────────────┐
│                       Discovery Planner                            │
│  (SearchPlan / refresh trigger / idle capacity -> Discovery Plan)   │
└───────────────────────┬─────────────────────────────────────────--┘
                         v
┌───────────────────────────────────────────────────────────────────┐
│                    Discovery Strategy Selector                     │
│  Targeted | Broad | Incremental | Scheduled Refresh |               │
│  Background | Cold Start                                            │
└───────────────────────┬─────────────────────────────────────────--┘
                         v
┌───────────────────────────────────────────────────────────────────┐
│                     Crawler Orchestration                          │
│  Mission Queue -> Priority Queue -> Rate-Aware Dispatcher ->        │
│  Retry/Failure Recovery -> Source Health Tracker                    │
└───────────────────────┬─────────────────────────────────────────--┘
                         v
              Connector Framework (Sprint 8, unchanged)
                         |
                         v
                Evidence Lake (Sprint 9, unchanged)
                         |
                         v
         Identity Resolution + Candidate Builder + Talent Graph
                    (Sprint 9, unchanged)
                         |
                         v
              Mission Outcome Feedback ──────┐
                         |                    v
                         |          Source Suitability Model
                         |          (Discovery Intelligence, section 6)
                         └────────────────────┘
                    (feeds back into Discovery Planner)
```

## Sequence Diagram — Mission Flow

```
SearchPlanner    DiscoveryPlanner   StrategySelector   MissionQueue    Connector    EvidenceLake   LearningLoop
     |                 |                   |                |             |             |              |
     |--SearchPlan---->|                   |                |             |             |              |
     |                 |--evidence_goals-->|                |             |             |              |
     |                 |                   |--strategy------>|             |             |              |
     |                 |                   |  (targeted/     |             |             |              |
     |                 |                   |   broad/etc)    |             |             |              |
     |                 |                   |                |--missions-->|             |              |
     |                 |                   |                |  (priority- |             |              |
     |                 |                   |                |   ordered,  |             |              |
     |                 |                   |                |   rate-     |             |              |
     |                 |                   |                |   aware)    |             |              |
     |                 |                   |                |             |--raw------->|              |
     |                 |                   |                |             |  results    |              |
     |                 |                   |                |             |             |--store/       |
     |                 |                   |                |             |             |  resolve--->  |
     |                 |                   |                |<---------------------------outcome--------|
     |                 |                   |                |             |             |              |--update
     |                 |                   |                |             |             |              |  suitability
     |                 |<------------------------------------------------------------------------------|  model
     |                 | (next Discovery Plan benefits from updated Source Suitability Model)            |
```

## Evidence Lifecycle (Recap, Discovery-Focused)

```
Not yet sought -> Mission dispatched -> Raw result acquired ->
Evidence record created (Sprint 9 schema, unverified) ->
Identity Resolution attempted -> Confidence scored/corroborated ->
[ongoing] periodic freshness re-check per ttl -> either re-corroborated
(confidence sustained/increased) or decayed (confidence reduced) ->
eventually superseded by newer evidence, never deleted
```

## Discovery Lifecycle (This Document's Core Addition)

```
Trigger (live SearchPlan | scheduled refresh | idle background capacity)
    -> Discovery Plan generated (evidence goals, source candidates,
       stopping criteria, evolution hooks)
    -> Strategy selected
    -> Missions created and queued (priority-scored)
    -> Missions dispatched (rate-aware, retry-capable)
    -> Outcomes observed (accepted / corroborated / disputed / rejected /
       failed)
    -> Sufficiency check against stopping criteria
        -> if not sufficient and evolution hooks allow: broaden/
           re-prioritize, generate new Missions
        -> if sufficient or budget exhausted: stop
    -> Outcomes feed Source Suitability Model (Learning Loop)
```

## Cost Model

Cost is tracked at three levels, each feeding the Discovery Cost Score (section 7):

- **Per-Mission cost**: connector API cost (if metered), compute cost of parsing/extraction, and AI cost where Stage 3 Identity Resolution or LLM-assisted extraction is invoked for that Mission's result.
- **Per-connector budget**: a rate-limit-aware and (where applicable) monetary-cost-aware ceiling per time period, enforced by the Crawler Orchestration layer (section 4) — prevents any single source from consuming a disproportionate share of the discovery budget regardless of how high its individual Mission priority scores are.
- **Global discovery budget**: a top-level cap (compute + API + AI spend combined, normalized to one budget currency) allocated across reactive and proactive Missions per the split described in section 7 — this is the number a business stakeholder would actually set and monitor, everything below it is internal allocation logic.

The explicit design intent: cost is never invisible or assumed unlimited — every Mission the system chooses to run should be justifiable in Evidence-Value-to-Discovery-Cost terms, the same explainability discipline applied everywhere else in this architecture, now applied to spend.

## Scalability

Extends Sprint 8 section 12 and Sprint 9's scalability analysis with discovery-specific concerns:

| Scale | What changes |
|---|---|
| **Early stage** | Mission Queue and Priority Queue can be a single in-process or lightweight managed queue; Source Suitability Model is a small, frequently-recomputed table; Cold Start strategy dominates since most evidence goals are unprecedented. |
| **Growing volume** | Mission Queue needs to be a real distributed queue (decoupling planning from dispatch, so a burst of live `SearchPlan`s doesn't block proactive discovery entirely); Source Suitability Model needs incremental update (not full recompute) as Mission outcomes arrive continuously, mirroring Sprint 9 section 7's incremental-only principle applied to this new learned component; per-connector rate-limit tracking must be centralized and consistent across however many orchestrator workers exist (a shared rate-limit ledger, not per-worker local counters). |
< **Large scale** | Discovery becomes a genuinely continuous, always-on background process rather than something bursty and request-triggered; the Learning Loop likely needs its own dedicated evaluation cadence (batched suitability-model updates rather than per-Mission updates, to keep the model stable rather than noisy); Crawler Orchestration's Failure Recovery and Source Health tracking become critical-path reliability concerns (at this scale, a handful of connectors being silently degraded for hours represents a large amount of wasted discovery budget, not a minor inefficiency). |

## Risks

- **Technical**: the Source Suitability Model could overfit to short-term patterns (e.g. temporarily prioritizing a source that happened to look good in a small sample) — mitigation is requiring a minimum observation volume before a weight shift is trusted, and the hard boundary from section 6 (learning affects prioritization only, never correctness) limits the damage of overfitting to inefficiency, not incorrect evidence.
- **Legal**: any discovery strategy that broadens toward "third-party public, semi/unstructured" sources (section 2) must still individually respect each site's terms/robots.txt (unchanged constraint from Sprint 8 section 8) — the risk here is strategy logic becoming aggressive about *broadening* (section 3's Broad Discovery, Cold Start) without equally aggressive compliance-boundary enforcement; mitigation is treating each source's compliance posture (section 2's classification) as a hard filter applied *before* the Priority Queue ever sees a Mission targeting it, never as a soft preference.
- **Operational**: a misconfigured global discovery budget (section "Cost Model") or a Source Health miscalculation could starve reactive, recruiter-facing Missions in favor of background discovery — mitigation is the explicit priority-class floor described in section 7 (reactive Missions get first claim on immediate capacity, always).
- **Scalability**: as covered above — the main risk is under-provisioning the Mission Queue/Priority Queue infrastructure for a burst of simultaneous live searches; mitigation is treating queue depth and per-connector budget headroom as first-class monitored metrics from day one, not an afterthought added once a real incident occurs.
- **Cost**: AI-assisted extraction and Stage 3 Identity Resolution calls (Sprint 9) are the most expensive per-unit cost in this system — an autonomous Discovery Loop that over-triggers these without the Evidence Value Score properly accounting for their cost could silently run up spend; mitigation is that Discovery Cost Score (section 7) must explicitly and separately weight AI-assisted cost, not bundle it into a generic "compute cost" bucket where it could be underestimated.
- **Compliance**: an autonomous system is, by definition, making sourcing decisions without a human approving each individual Mission — this raises the bar for the compliance classification (section 2) being complete and correct at the connector-registration stage, since there is no per-Mission human check downstream of it; mitigation is treating a connector's compliance classification as an immutable, review-gated property at registration time (change requires the same review rigor Sprint 8 section 6.3 already calls for when adding any new connector), never something the autonomous system itself can alter.

## Implementation Roadmap (Two-Year View)

**Months 1-3 — Foundation**: build the Mission Queue, Priority Queue, and Crawler Orchestration primitives (section 4) against the connectors already recommended in Sprint 8/9's own roadmaps (CSV/internal DB/resume first) — prove Mission-based orchestration end-to-end before any learning component exists. Discovery Strategy at this stage is Cold Start only, static heuristics.

**Months 3-6 — Reactive Discovery**: wire the Discovery Planner to live `SearchPlan`s (Targeted + Broad strategies), with manual/static Source Suitability weights. This is the point at which the system starts behaving like "discovery driven by real recruiter need" rather than a fixed batch job.

**Months 6-9 — Proactive Discovery**: add Scheduled Refresh and Background Discovery strategies, tied to Sprint 8/9's freshness/decay mechanics — this is the first point the Evidence Lake grows meaningfully without a live search triggering it.

**Months 9-12 — Evidence Economics**: introduce the Evidence Value Score / Discovery Cost Score / Priority Score formally (section 7), replacing whatever simpler priority heuristic bootstrapped the Priority Queue in the first 9 months — this is where discovery spend becomes explainable and controllable rather than implicit.

**Year 1-1.5 — Discovery Intelligence**: introduce the Source Suitability Model and Learning Loop (section 6), only once enough Mission-outcome history exists (from the prior year's reactive+proactive activity) to learn from real data rather than guesses — this sequencing is deliberate, mirroring this project's standing preference for proving a simpler version works before adding a learned component on top of it.

**Year 1.5-2 — Multi-connector Discovery Intelligence at Scale**: expand the connector set (GitHub, then compliant-access-dependent connectors as/if partnerships are secured, unchanged constraint), stress-test the Learning Loop across genuinely different evidence-goal contexts (not just one role category), and move Crawler Orchestration's infrastructure to the "growing volume" scalability tier described above as real usage demands it — never earlier, per the same anti-premature-scaling caution carried through every architecture document in this series.

This roadmap deliberately defers the most novel, highest-risk component (Discovery Intelligence's learning loop) until the system has a full year of real operational data to learn from — an autonomous system that starts "learning" from day one, before it has trustworthy outcome history, would be optimizing against noise. Everything before that point is designed to be valuable and correct on its own, exactly as Sprint 8 and Sprint 9's own roadmaps staged foundational correctness before optimization.
