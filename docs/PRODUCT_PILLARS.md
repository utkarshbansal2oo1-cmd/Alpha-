# AlphaSource: Product Pillars

**Vision:** AlphaSource is the AI Hiring Operating Layer for enterprise
recruiting — it doesn't replace the systems an organization already uses
(LinkedIn, Naukri, ATS platforms, spreadsheets, resume databases), it
connects, understands, and automates across them.

Every architecture document in this folder implements one of three
pillars. This doc is the map from engineering names to the three words
that should appear in any customer- or investor-facing conversation.

## 1. Capture — bring talent data into AlphaSource

*"Recruiters don't lack access to candidates — they lack a system that
connects their existing sources."* Capture is how data gets in, from
whichever source it's legitimately available from. Acquisition is a
strategy with many modes, not a dependency on any one platform:

| Mode | What it is | Where it's implemented |
|---|---|---|
| Customer-owned data | ATS, resume uploads, CSV, HRMS, internal databases | `docs/ADAPTER_SDK.md` (csv-row, resume-text adapters); Sprint 15's Greenhouse connector |
| Recruiter-assisted | Browser extension, one click, recruiter's own session | `docs/BROWSER_EXTENSION_ARCHITECTURE.md`, `docs/ADAPTER_SDK.md` |
| Partner integrations | Official APIs, authorized connectors | Sprint 15 onward (Greenhouse, Lever, Workday) |
| Public discovery | Company pages, conference speakers, portfolios, GitHub | `docs/DISCOVERY_ENGINE_ARCHITECTURE.md`, `docs/AUTONOMOUS_DISCOVERY_ARCHITECTURE.md` (designed, not yet built) |
| Future | Whatever becomes legitimately available later | The Adapter SDK's pluggable registry exists precisely so this doesn't require a rewrite |

## 2. Understand — build trusted, explainable candidate intelligence

*"A candidate captured once is a snapshot. Understand is what makes it a
living, increasingly-trustworthy profile."* This is the pillar that
compounds in value the longer an organization uses AlphaSource, and the
one a competitor can't replicate just by copying the UI.

- `docs/EVIDENCE_GRAPH_ARCHITECTURE.md` — the evidence-first philosophy
  (never overwrite, always corroborate) everything else in this pillar
  follows.
- `docs/CANDIDATE_INTELLIGENCE_LIFECYCLE.md` — the implemented version:
  Candidate Health Score, Confidence Engine, Evidence Timeline, Profile
  Versioning, Enrichment Planner.
- `docs/KNOWLEDGE_ENGINE.md`, `docs/QUERY_UNDERSTANDING_ENGINE.md` — how
  a recruiter's plain-English requirement becomes a canonical,
  explainable search plan.

## 3. Orchestrate — connect hiring systems and automate recruiter workflows

*"Recruiters spend more time moving candidate data between systems than
making hiring decisions."* Orchestrate is what closes that loop: search
once across everything connected, and push decisions back out to the
systems of record.

- `docs/DISCOVERY_ENGINE_ARCHITECTURE.md`, `docs/AUTONOMOUS_DISCOVERY_ARCHITECTURE.md`
  — the designed architecture for orchestrating search across multiple
  connected sources at once (not yet implemented).
- Sprint 15's Greenhouse connector — the first real instance of
  Orchestrate: pull candidates in, dedupe against existing intelligence,
  push a shortlist back out. This is the proof point for "we integrate
  with your existing hiring stack," not "we have AI."
- `docs/ALPHASOURCE_PRODUCT_STRATEGY.md` — the business case for why
  ATS orchestration (not more search features) is where enterprise value
  concentrates first.

## Why this framing, not the engineering names

"Discovery Engine," "Evidence Lake," and "Candidate Intelligence" are
correct and precise for engineering docs — they stay as-is in this
folder. But in a pitch, a demo, or a customer conversation, three words
travel better: **Capture. Understand. Orchestrate.** Every roadmap
decision (see `docs/ALPHASOURCE_PRODUCT_STRATEGY.md`'s effort/value
scoring) should be framed as strengthening one of these three, not as a
standalone feature.
