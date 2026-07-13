# Candidate Intelligence Lifecycle (Sprint 14)

**Mission:** make every imported candidate more valuable over time.
Explicitly not a search or discovery sprint -- no ranking, matching, or
Adapter SDK changes. This sprint is entirely about what happens to a
candidate record *after* it's already in AlphaSource.

## 1. Why this exists

Sprints 12-13 built the capture pipeline (browser extension + Adapter
SDK) that gets candidates into AlphaSource. But a candidate captured once
is a snapshot, not a living profile -- it doesn't get better on its own,
recruiters have no way to see how confident to be in any given field, and
there's no record of what changed or why. This sprint closes that gap
with four engines and a persistent evidence/version trail, all wired
through one orchestrator (`lifecycle.py`) so every future write path
(a real connector, a bulk CSV import, a future authorized LinkedIn
integration) gets identical behavior for free.

## 2. Architecture

```
InMemoryCandidateRepository
  ._load()  (seed bootstrap)  ──┐
  .upsert() (real capture)    ──┼──► apply_lifecycle()
                                 │      (app/candidate_intelligence/lifecycle.py)
                                 │
                                 │  1. diff_fields()          -- evidence_timeline.py
                                 │     old candidate vs incoming fields
                                 │     -> EvidenceEvent[] + per-field agreement
                                 │
                                 │  2. update_confidence()     -- confidence_engine.py
                                 │     per section touched, corroboration-aware
                                 │     -> candidate.section_confidence[section]
                                 │
                                 │  3. compute_health()        -- health_engine.py
                                 │     weighted section completeness x confidence
                                 │     -> candidate.health_score
                                 │
                                 │  4. build_snapshot()        -- versioning.py
                                 │     full-state snapshot at this version
                                 │     -> candidate.version_history[]
                                 │
                                 ▼
                        Candidate (mutated in place, same object
                        InMemoryCandidateRepository already owns)
```

Separately, on-demand (not part of the write path):

```
GET /candidate/{id}/enrichment-plan
   -> compute_health(candidate)        -- health_engine.py
   -> plan_enrichment(candidate, health) -- enrichment_planner.py
        queries enrichment_registry.py (pluggable source-type ->
        fields-it-can-supply registry) for each missing field
```

Every engine is a pure function of its inputs -- none of them import the
repository, the router, or each other's internals beyond what's passed
in. That's deliberate: it's what makes "prepare the database for millions
of continuously improving profiles" (§8 below) a matter of changing where
these functions are called from, not rewriting them.

## 3. Candidate Health Engine

`app/candidate_intelligence/health_engine.py`. Scores six fixed sections
(`app/candidate_intelligence/sections.py`):

| Section | Weight | Fields |
|---|---|---|
| identity | 15 | name, location |
| professional | 25 | role, current_company, experience |
| skills | 20 | skills |
| education | 10 | education |
| contact | 15 | public_profile_url, resume_link |
| summary | 15 | summary |

For each section: `completeness` = fraction of its fields present (a
field counts as present via `field_present()` -- `experience == 0` is
treated as *unknown*, not *zero years*, since 0 is the normalizer's
placeholder for "not captured"). `confidence` comes from
`candidate.section_confidence[section]`, defaulting to a neutral 0.5 if
the Confidence Engine hasn't touched that section yet. Overall score =
`sum(weight * completeness * confidence)`, clamped to 0-100.

## 4. Enrichment Planner + pluggable source registry

`app/candidate_intelligence/enrichment_registry.py` +
`enrichment_planner.py`. The registry is deliberately built the same way
as Sprint 13's Adapter SDK registry: a source type declares which fields
it can supply, and the planner only ever asks "who can help with field
X" -- it never special-cases a source type by name. Pre-registered
sources map directly onto the Adapter SDK's five example adapters
(`browser_extension`, `csv_import`, `resume_import`,
`career_page_listing`); adding a real future connector is one
`register_source(name, fields)` call, made once, anywhere at import time
-- no change to `enrichment_planner.py`, the endpoint, or any test.

Priority for each missing field reuses the Health Engine's own
`SECTION_WEIGHTS`, split evenly across however many fields are missing in
that section -- so "what the planner recommends first" and "what would
move the health score the most" are always the same answer, with no
separate priority scheme to keep in sync.

## 5. Confidence Engine

`app/candidate_intelligence/confidence_engine.py`. Two pure functions:

- `initial_confidence(source_confidence)` -- a section with no prior
  confidence starts at whatever the first piece of evidence's own
  confidence is.
- `update_confidence(current, incoming, agreement)` -- corroborating
  evidence (`agreement=True`) nudges confidence up, asymptotically toward
  1.0 with diminishing returns near the top; conflicting evidence
  (`agreement=False`) pulls it down proportional to how confident the
  conflicting evidence itself is. Never both directions from one event.

"Agreement" is computed per field by `evidence_timeline.py`'s
`diff_fields()`: a brand-new value for a previously-empty field is always
agreement (filling a gap isn't a conflict); a list field
(skills/education) growing is always agreement (this project's merge
strategy only ever unions/appends, never removes, so a longer list is
enrichment, not disagreement); a *scalar* field changing to a genuinely
different value is a real conflict signal.

## 6. Profile Versioning + Evidence Timeline

**Versioning** (`versioning.py`): `build_snapshot(candidate, version,
reason)` captures the candidate's current data fields (explicitly
excluding the lifecycle bookkeeping fields themselves --
`version_history`, `evidence_history`, `section_confidence`,
`health_score` -- so a snapshot never recursively grows) into a
`CandidateSnapshot`, appended to `candidate.version_history`. Append-only,
same as `capture_sources` already was.

**Evidence Timeline** (`evidence_timeline.py`): `diff_fields()` compares
old vs incoming field values and returns one `EvidenceEvent` per
informative change, each answering the exact five things recruiters need
(per the sprint brief): **what** (`field`, `old_value` → `new_value`),
**when** (`timestamp`), **why** (`reason`, `change_type`), **source**
(`source_type`, `source_url`), **confidence** (`confidence`). Appended to
`candidate.evidence_history`, never rewritten.

## 7. New endpoints

`app/routers/candidate_intelligence.py`, registered additively in
`main.py` (one new line, nothing else changed):

- `GET /candidate/{id}/health` -- HealthScore, recomputed fresh from
  current field values (not just the cached `health_score` number) so
  it's always internally consistent.
- `GET /candidate/{id}/enrichment-plan` -- EnrichmentPlan.
- `GET /candidate/{id}/evidence-timeline` -- `EvidenceEvent[]`, newest
  first.
- `GET /candidate/{id}/versions` -- `CandidateSnapshot[]`, newest first.

All four are pure reads against a new `CandidateRepository.get_by_id()`
(additive interface method); none of them write anything, and none of
them touch `/api/search`, `/api/v1/search`, or `/candidate/import`.

## 8. UI: Candidate Health panel

`marketing/src/components/demo/CandidateDrawer.jsx` gained a "Candidate
Health" section, rendered only when `candidate.health_score` is present
(true for every candidate returned by the real backend, via Live Pipeline
mode, since seed data and captures both now get a health score computed
on write). It shows: a color-coded health badge in the header (red <40,
amber 40-70, green 70+), a confidence bar per section, the profile
version + source count, and the four most recent evidence events
(field, change type, source, confidence %, reason). Guided Demo Mode's
locally-generated fictional candidates never carry `health_score`, so the
section simply doesn't render for them -- the same data-source-honesty
pattern this component already used for `education`/`timeline`.

## 9. Preparing the database for millions of continuously improving profiles

This POC keeps everything (`evidence_history`, `version_history`,
`section_confidence`) inline on the in-memory `Candidate` record, which is
fine at seed-data + demo scale but would not be fine at scale. The
production design this sprint is built to migrate into without changing
any engine's function signature:

- **Evidence as its own table**, not an inline list: `candidate_evidence
  (candidate_id, event_id, field, section, old_value, new_value,
  change_type, source_type, source_url, confidence, reason, timestamp)`,
  indexed on `(candidate_id, timestamp DESC)`. `diff_fields()` already
  returns a plain list of `EvidenceEvent` -- a real repository just
  inserts rows instead of appending to a Python list.
- **Versions as their own table**: `candidate_versions (candidate_id,
  version, timestamp, reason, fields JSONB)`, indexed on
  `(candidate_id, version DESC)`. `build_snapshot()`'s output maps
  directly onto one row.
- **Async health/confidence recomputation**: at scale, don't recompute
  `compute_health()` synchronously inside the write path for every
  candidate on every merge (fine for a POC's single-digit-millisecond
  cost per §10 below, not fine under write load at millions of
  candidates/day). Queue a `(candidate_id, reason)` message instead and
  let a worker pool call the same pure `compute_health()` /
  `update_confidence()` functions off the write path. Because every
  engine here is already a pure function with no repository/network
  access, this is a deployment change, not a rewrite.
- **Partition evidence/version tables by `candidate_id` hash or by time**,
  since both grow unboundedly and are almost always queried scoped to one
  candidate (the evidence-timeline and versions endpoints) or a recent
  time window (a future "what changed this week across all candidates"
  report).
- **`section_confidence` stays inline** on the candidate row itself (a
  small, fixed-size JSON/JSONB column) since it's read on every health
  computation and every search-adjacent display -- the one piece of
  lifecycle state worth denormalizing for read speed, unlike evidence/
  version history which are read far less often and only in detail views.

## 10. Verification performed this sprint

- `backend/app/candidate_repository/models.py`: 5 new models
  (`EvidenceEvent`, `SectionScore`, `HealthScore`, `EnrichmentPlanItem`,
  `EnrichmentPlan`, `CandidateSnapshot`) and 4 new optional `Candidate`
  fields, additive, `py_compile`-clean.
- `backend/app/candidate_intelligence/`: 7 new modules (`sections.py`,
  `health_engine.py`, `enrichment_registry.py`, `enrichment_planner.py`,
  `confidence_engine.py`, `evidence_timeline.py`, `versioning.py`,
  `lifecycle.py`), all `py_compile`-clean, no null bytes.
- `memory_repository.py`: `_load()` and `upsert()` now call
  `apply_lifecycle()`; `search()`/`all()` byte-for-byte unchanged; new
  `get_by_id()` added to both the interface and this implementation.
- `routers/candidate_intelligence.py` + one additive line in `main.py`.
- Full backend test suite: **156 passed** (127 pre-Sprint-14 +
  29 new: health engine, enrichment planner + registry, confidence
  engine, evidence-timeline diffing, versioning, the lifecycle
  orchestrator, repository integration, and all four new endpoints), run
  from a native-filesystem copy per this project's established mounted
  -filesystem mitigation.
- `marketing/`: production build (`vite build`) succeeds cleanly with the
  new Candidate Health panel in `CandidateDrawer.jsx`.

## 11. Known limitations (Proof of Concept)

- Health/confidence recomputation is synchronous, inline in
  `upsert()`/`_load()` -- fine at this POC's scale, not the production
  design (see §9).
- `section_confidence`, `evidence_history`, and `version_history` live
  inline on the in-memory `Candidate` record, unbounded -- a real
  deployment needs the separate-table design in §9 before evidence/
  version history could grow to millions of rows safely.
- The Health Engine's section weights and the drawer's health-badge color
  thresholds (`CandidateDrawer.jsx`'s `HealthBadge`) are product judgment
  calls made in this sprint, not derived from any real usage data -- worth
  revisiting once real recruiter feedback exists.
- `diff_fields()`'s conflict detection is field-level and immediate; it
  does not yet reason about *which* of two conflicting sources should
  "win" beyond the existing merge strategy's "keep the earlier value"
  rule from Sprint 12 -- a genuine confidence-weighted conflict-resolution
  policy (e.g. "prefer the higher-confidence source's value") is future
  work, not implemented here.
- No enrichment *execution* exists yet -- the Enrichment Planner tells you
  what's missing and which source types could help, but nothing in this
  sprint automatically triggers an actual capture/enrichment action from
  that plan (deliberately: that would be a discovery/automation feature,
  explicitly out of scope for this sprint).
