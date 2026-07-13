# Greenhouse ATS Connector (Sprint 15)

**The first real "Orchestrate" pillar connector** (see
`docs/PRODUCT_PILLARS.md`) -- and the proof point for AlphaSource's real
positioning: *"we integrate with your existing hiring stack in days, not
months, and immediately remove manual recruiter work,"* not *"we have
AI."*

This is a real connector, not a simulation. It's built directly against
Greenhouse's documented Harvest API contract
(https://developers.greenhouse.io/harvest.html). Point it at the real
`https://harvest.greenhouse.io/v1` with a real API key and every call is
real. No mock server stands in for Greenhouse anywhere in this codebase --
tests exercise the client against constructed HTTP responses shaped like
Greenhouse's real documented payloads (via `respx`), which verifies the
client speaks the real protocol correctly rather than verifying it talks
to a fake of our own design.

## Why Greenhouse first

Mature, well-documented public API. Widely used at companies large enough
to be AlphaSource's target enterprise customer. API-key auth (no OAuth
dance to build). And, most importantly: it demonstrates the Orchestrate
pillar end-to-end -- pull candidates in, dedupe against existing
intelligence, push a shortlist back out -- which is the exact workflow
compression ("Find → Click → Done" instead of "Find → Download → Upload →
ATS → Compare → Call") the business case rests on.

## Architecture

```
Greenhouse Harvest API (real, documented)
   │  GET /v1/candidates  (HTTP Basic: api_key, "")
   ▼
GreenhouseClient (client.py)
   │  follows Link: rel="next" pagination
   │  retries once on 429 + Retry-After
   ▼
normalize_greenhouse_candidate() (normalizer.py)
   │  Greenhouse candidate JSON -> CandidateImportRequest
   │  (the SAME permissive shape the browser extension's
   │  extraction layer already produces)
   ▼
normalize_import() (candidate_repository/normalizer.py, Sprint 12 -- unchanged)
   │  CandidateImportRequest -> Candidate
   ▼
CandidateRepository.find_potential_duplicate() + .upsert()
   (Sprint 12/14 -- unchanged)
   │  dedup, merge, health score, confidence, evidence timeline,
   │  version snapshot -- all for free, identical to a browser capture
   ▼
Candidate pool (immediately searchable via the existing, unmodified
                 /api/search)
```

Push-back runs the same client in the other direction:
`push_candidate()` (sync.py) builds a Greenhouse candidate payload from an
AlphaSource `Candidate`, calls `POST /v1/candidates`, and optionally
attaches a note (e.g. shortlist/match reasoning) via
`POST /v1/candidates/{id}/activity_feed/notes`.

**Nothing about `/api/search`, `/candidate/import`, the Adapter SDK, or
the Candidate Intelligence Lifecycle changed to support this.** The
connector is entirely additive: one new package
(`app/integrations/greenhouse/`), one new router registered in `main.py`,
one new registered source type (`greenhouse_ats`) in the Sprint 14
enrichment registry.

## Authentication

Greenhouse's Harvest API uses HTTP Basic Auth: the API key as the
username, an empty password. There is no OAuth flow for Harvest API keys
-- an org generates one from Greenhouse's admin settings
(Configure → Dev Center → API Credential Management) and provides it
directly. `POST /integrations/greenhouse/configure` accepts that key (and
an optional `base_url` override, unused in production but present so a
future self-hosted or regional Greenhouse variant doesn't require a code
change).

## Endpoints

- `POST /integrations/greenhouse/configure` — `{"api_key": "..."}` →
  `{"configured": true, "base_url": "..."}`
- `POST /integrations/greenhouse/sync` — runs a pull sync now, returns a
  `SyncRun` (pulled/created/merged counts, any per-candidate errors).
  Returns 400 if `/configure` hasn't been called yet.
- `GET /integrations/greenhouse/sync-status` — full sync history, newest
  first.
- `POST /integrations/greenhouse/push/{candidate_id}` —
  `{"note": "optional shortlist reasoning"}` → pushes that AlphaSource
  candidate into Greenhouse, returns the Greenhouse-assigned id.

## Demo walkthrough (against a real Greenhouse trial account)

1. Create a free Greenhouse trial account, generate a Harvest API key
   (Configure → Dev Center → API Credential Management → create a
   credential with the Harvest API type and candidate read/write
   permissions).
2. `POST /integrations/greenhouse/configure` with that key.
3. `POST /integrations/greenhouse/sync` — every candidate in that
   Greenhouse account is pulled, normalized, deduped against whatever's
   already in AlphaSource, and becomes immediately searchable via
   `/api/search`.
4. Run a search, find a strong match, note its `id`.
5. `POST /integrations/greenhouse/push/{id}` with a note explaining why
   they matched — that candidate now exists in Greenhouse (or gets a note
   on their existing record if pushed from a candidate that originated
   there) with the reasoning attached for the hiring team to see.
6. `GET /integrations/greenhouse/sync-status` to show the sync history --
   this is what an admin screen showing "connector health" would read
   from.

## Known limitations (Proof of Concept)

- **Config is in-memory, single organization.** A real deployment stores
  the API key per-organization in the database (encrypted), not in a
  module-level Python singleton. This POC's `GreenhouseConfigStore` is
  intentionally the same simplification `GreenhouseConfigStore`'s own
  docstring already flags.
- **Sync is synchronous and manual**, triggered by one API call. A
  production connector would run this on a schedule (e.g. every 15
  minutes) via a background worker, and only sync candidates
  created/updated since the last run (Greenhouse's API supports
  `updated_after` filtering) rather than re-pulling everyone every time.
- **Push-back creates a new Greenhouse candidate** rather than attaching
  to a specific job/stage — a real workflow would let the recruiter pick
  which open requisition to attach the pushed candidate to, via
  Greenhouse's `job_id`/`applications` fields on candidate creation.
- **No webhook support.** Greenhouse can push candidate/application
  change events to a webhook URL in near-real-time; this POC only
  supports pull-based sync. Webhook support would close the sync-latency
  gap without any change to `normalizer.py` or the repository-write path
  -- it's a new trigger for the same `pull_sync`-adjacent logic, not a
  new architecture.
- **Rate-limit handling retries once.** Greenhouse's real limit is
  roughly 50 requests per 10 seconds per key; a full-account sync against
  a very large candidate database could still hit it repeatedly. A
  production sync job would batch with a deliberate delay between pages,
  not just react to 429s as they occur.

## Verification performed this sprint

- `app/integrations/greenhouse/`: 6 new modules (`config.py`, `client.py`,
  `normalizer.py`, `models.py`, `sync.py`, `sync_store.py`), all
  `py_compile`-clean, no null bytes.
- `app/routers/greenhouse_integration.py` + one additive import/router
  -registration line in `main.py`.
- `enrichment_registry.py`: `greenhouse_ats` registered as a source type
  the Enrichment Planner already knows can supply name/role/company/
  skills/location/education/profile-url — zero changes to
  `enrichment_planner.py` itself.
- 19 new tests (client against respx-mocked real-shaped HTTP responses,
  normalizer, pull sync with dedup, push-back, all four endpoints). Full
  suite: **175 passed** (156 pre-Sprint-15 + 19 new), run from a native
  -filesystem copy per this project's established mounted-filesystem
  mitigation.
