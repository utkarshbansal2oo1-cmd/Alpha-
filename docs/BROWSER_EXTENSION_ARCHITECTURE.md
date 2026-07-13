# AlphaSource Browser Intelligence Extension — Proof of Concept

**Sprint 12 deliverable.** Implementation-focused, not a redesign: nothing
in the Search Planner, Query Understanding Engine, Knowledge Engine, or the
Discovery Engine / Evidence Lake architecture (Sprints 8–10) was touched.
This sprint adds exactly one new, additive write path into the existing
`CandidateRepository` and one new backend endpoint; everything downstream
(search, matching, the marketing/product UI) works on captured candidates
with zero changes, because they land in the exact same `Candidate` shape
seed data already uses.

## 1. Why a browser extension, not a scraper

Sprint 11's strategy work concluded the browser extension is the highest-
leverage, lowest-risk way to solve the "recruiter has to leave AlphaSource
to find someone on LinkedIn/Naukri" problem, because it uses the
recruiter's own, already-authenticated, already-legitimate session and
requires an explicit action every time — it is not automation and not a
Terms-of-Service risk in the way a scraper or bot would be. This is a hard,
non-negotiable constraint carried through every phase below:

- No content script runs automatically on page load. Extraction only
  happens while the popup is open, which only happens after the recruiter
  clicks the extension icon.
- No credential, password, or session cookie is ever read, stored, or
  transmitted.
- No page navigation, link-following, or multi-page crawling capability
  exists anywhere in the extension.
- Nothing is sent to the backend without an explicit "Add to AlphaSource"
  click.

## 2. Architecture

```
Browser (recruiter's own session)
   │  recruiter clicks the extension icon on a page they're viewing
   ▼
Popup (popup/popup.html + popup.js)
   │  sends {type: "extract", tabId} to the background worker
   ▼
Background Service Worker (background/service-worker.js)
   │  chrome.scripting.executeScript injects, ONLY into the active tab,
   │  ONLY for this one call:
   ▼
Content Script / Extraction Layer (content-scripts/)
   │  registry.js -> adapter registration seam
   │  adapters/generic-schema-org.js -> JSON-LD Person parsing (highest confidence)
   │  adapters/generic-heuristic.js  -> DOM/meta-tag fallback (lower confidence)
   │  extractor.js -> runs adapters in order, returns {detected, adapterUsed, fields}
   ▼
Popup renders detected fields; recruiter reviews and clicks
"Add to AlphaSource"
   │  sends {type: "capture", fields, pageUrl} to the background worker
   ▼
Background Service Worker
   │  reads backendUrl + capturedBy from chrome.storage.sync (options page)
   │  POSTs CandidateImportRequest to {backendUrl}/candidate/import
   ▼
AlphaSource Backend: POST /candidate/import (routers/candidate_import.py)
   │  1. Pydantic validation (CandidateImportRequest, import_schemas.py)
   │  2. Normalization -> Candidate (normalizer.py)
   │  3. find_potential_duplicate() -> upsert() (memory_repository.py)
   ▼
CandidateRepository (unchanged search()/all(), additive upsert()/
find_potential_duplicate()) — the SAME repository /api/search already reads
from, so the captured candidate is immediately searchable with no further
step.
```

Each module and why it's separated:

- **Content Script / Extraction Layer** — the only code that touches page
  DOM. Split into an adapter registry plus adapter files specifically so a
  future site-specific adapter (e.g. a LinkedIn-shaped adapter, if and when
  that's legally/contractually appropriate) is a new file, not a change to
  the extractor, popup, background worker, or backend.
- **Normalization Layer** — lives in the backend (`normalizer.py`), not the
  extension, so extraction stays "dumb" (best-effort raw fields) and all
  business rules (placeholder values, fallback summaries, confidence
  scoring) live in one place, testable with the rest of the backend suite.
- **Background Service Worker** — the only code with network access to the
  backend or `scripting` permission; the popup itself has neither. This
  keeps the "only acts on an explicit click" property enforceable in one
  place.
- **Candidate Repository** — extended, not replaced. `search()`'s contract
  is byte-for-byte unchanged; `upsert()`/`find_potential_duplicate()` are
  new abstract methods with one first, POC-appropriate implementation
  (`InMemoryCandidateRepository`). A future Postgres-backed repository
  implements the same interface with real persistence and real duplicate
  lookups (e.g. via an index), not a different contract.

## 3. Extraction layer: pluggable, not hardcoded

`extractor.js` has zero knowledge of any specific website. It runs every
adapter registered in `window.__AlphaSourceAdapterRegistry`, in
registration order, and uses the first one whose `detect()` returns true:

1. `generic-schema-org.js` — parses `<script type="application/ld+json">`
   `Person` records, a widely-used, platform-agnostic SEO convention.
2. `generic-heuristic.js` — a DOM/meta-tag fallback (og:type=profile,
   name-shaped title + headline/company/location class-name fragments)
   for pages without JSON-LD.

Adding a new site-specific adapter later means: write a new file
implementing `{name, detect(document), extract(document)}`, register it
via `registerAlphaSourceAdapter(...)`, and add its filename to
`ADAPTER_FILES` in `background/service-worker.js` — before the two generic
adapters in that array, so it gets first refusal on pages it recognizes.
Nothing else changes.

## 4. Normalization

`CandidateImportRequest` (import_schemas.py) is deliberately permissive —
only `name` is required, every other field defaults to `None`/empty,
matching the extraction layer's "omit what you can't find" contract.
`normalize_import()` (normalizer.py) converts that into the strict internal
`Candidate` model:

- Missing `role`/`location`/`current_company` become an explicit `"Unknown"`
  placeholder (visible and searchable-as-unknown, rather than an empty
  string that looks like a data-entry mistake).
- A missing `summary` gets a deterministic, templated fallback
  (`"{role} at {company}, captured via browser extension."`) — **not**
  LLM-generated. Sprint 12 scope stops at making captured candidates
  immediately searchable; wiring a real AI-summary pass is future work (see
  §9).
- Every capture creates a `CaptureSource` record (source type, URL,
  recruiter identity, capture time, confidence 0.7) appended to the
  candidate's `capture_sources` list — never overwritten, mirroring the
  Evidence Lake's append-only philosophy at this POC's simpler scale.

## 5. `POST /candidate/import`

`routers/candidate_import.py`, registered additively in `main.py`
alongside the existing five routers (nothing else in `main.py` changed).
Pipeline: validate → normalize → `find_potential_duplicate()` →
`upsert()` → return `{candidate_id, created, version}`.

Does **not** modify `POST /api/search` or `POST /api/v1/search` in any way
— verified by the full existing 110-test suite passing unmodified, plus a
new test asserting `/api/v1/search` still works after this router is
registered.

## 6. Deduplication / merge strategy

Implemented in `InMemoryCandidateRepository.find_potential_duplicate()` /
`.upsert()`, deliberately conservative (a false merge is worse than a false
separation — the same principle already established for the Evidence
Graph architecture in Sprint 9):

1. **Exact `public_profile_url` match** → highest-confidence signal
   available in this POC. If a URL is provided and it doesn't match
   anything, that is treated as informative on its own — the code does
   **not** fall through to the weaker name/company signal in that case,
   since two different people can share a name and employer.
2. **Name + current_company match** (only checked when no URL was
   provided) → medium-confidence fallback for captures without a profile
   URL (e.g. a resume-derived capture).
3. No match → a brand-new `Candidate` is created with a fresh UUID.

On merge: skills are unioned; scalar fields (`role`, `experience`,
`location`, `current_company`, `headline`, `summary`,
`public_profile_url`, `resume_link`) are filled in from the new capture
**only if the existing record's value is empty** — an existing, previously
-captured value is never silently overwritten by a new, possibly
lower-quality capture; education entries are appended if not already
present; `capture_sources` always gets the new entry appended;
`version` increments by 1; the existing record's `id` is always preserved.

## 7. Candidate Intelligence for captured candidates

Sprint 12 does not introduce a separate AI-summary or search-indexing step.
"Intelligence" for a captured candidate, in this POC, is:

- The templated fallback `summary` from §4, when the page had no bio text.
- Immediate searchability: the moment `/candidate/import` returns, the
  candidate is in the same in-memory pool `CandidateRepository.search()`
  already reads from — verified by
  `test_import_endpoint_candidate_is_immediately_searchable`. No indexing
  step, no delay, no separate "processing" state.
- "Why Matched" reasoning for a captured candidate works exactly the same
  way it already does for any other candidate returned by `/api/search`
  (client-side, from the `SearchPlan` returned alongside `candidates`) —
  nothing candidate-source-specific was added there, because nothing needed
  to be.

A true LLM-generated summary/intelligence pass over captured candidates is
explicitly deferred — see §9 Known Limitations.

## 8. Security constraints (recap, enforced in code)

| Constraint | Where enforced |
|---|---|
| No content script on page load | `manifest.json` declares no `content_scripts`; extraction only happens via `chrome.scripting.executeScript` triggered by an explicit popup message |
| No automatic/background capture | `background/service-worker.js`'s only listeners are `chrome.runtime.onMessage`, fired only by `popup.js` in direct response to a click |
| No credential/cookie storage | `chrome.storage.sync` only ever stores `backendUrl` and `capturedBy` (options.js) — no field for a password or token exists anywhere in the extension |
| No auth bypass | The extension has no ability to authenticate to any site; it only reads DOM the recruiter's own browser has already rendered under their own session |
| No scraping/crawling capability | No `host_permissions`, no cross-tab or cross-page navigation code anywhere in the extension |

## 9. Demo walkthrough

1. Load the unpacked extension (docs/EXTENSION_INSTALL_GUIDE.md).
2. Set the backend URL to a running AlphaSource backend and a recruiter
   identity in Settings.
3. Navigate to any page with either JSON-LD `Person` markup or an
   og:profile-shaped page (many portfolio/about pages qualify).
4. Click the AlphaSource icon → see the detected name/headline/company →
   click **Add to AlphaSource**.
5. See the success state with the candidate's ID and created/merged
   status.
6. Re-visit the same page and capture again → see `created: false` and
   `version: 2` in the response, demonstrating the merge path.
7. Confirm the captured candidate is now returned by `/api/search` for a
   query matching their role/skills (no extra step required).

## 10. Known limitations

- Detection is heuristic; the DOM-fallback adapter especially can miss or
  mis-fire. No adapter in this POC is hand-tuned to a specific real
  platform.
- `captured_by` is self-reported text, not an authenticated identity.
- `InMemoryCandidateRepository` is process-lifetime storage, same as
  before this sprint — a real deployment needs a persistent, indexed
  repository implementing the same `CandidateRepository` interface, with a
  proper (e.g. trigram or ANN-based) duplicate lookup instead of the exact/
  fallback string matches used here.
- No AI-generated summary/enrichment pass runs on captured candidates yet;
  only the deterministic template in §4.
- No automated tests exist for the extension's JavaScript itself (only
  Node syntax validation was performed, per §11) — the backend-side
  integration (import endpoint, normalizer, dedup/merge) has full pytest
  coverage (17 new tests, `app/candidate_repository/tests_import.py`), but
  there is no unit-test harness for `content-scripts/`/`popup.js`/
  `background/service-worker.js` in this POC.

## 11. Verification performed this sprint

- `backend/app/candidate_repository/models.py` and `interfaces.py`:
  additively extended, `py_compile`-clean, no null bytes.
- `memory_repository.py`: `find_potential_duplicate()`/`upsert()`
  implemented; `_load()`/`search()`/`all()` byte-for-byte unchanged.
- `import_schemas.py`, `normalizer.py`, `routers/candidate_import.py`,
  `main.py`: all `py_compile`-clean, no null bytes.
- Full backend test suite: **127 passed** (110 pre-existing + 17 new),
  run from a native-filesystem copy per the established mitigation for
  this environment's mounted-filesystem write corruption.
- Extension: every `.js` file passed `node --check`; `manifest.json`
  parses as valid JSON; every file scanned clean of null bytes; icon PNGs
  verified to open and report the correct declared dimensions.
