# Technical Debt

Compiled during the 2026-07-07 full-project code review. This document
records known debt intentionally left in place, plus what the review fixed.
Nothing here changes architecture or adds features -- per the review's
scope, items under frozen or legacy modules were documented, not touched.

## Fixed in this review

- **Uncaught LLM provider failures** (`query_understanding/service.py`):
  any exception from `LLMClient.generate()` (missing API key, network
  error, SDK exception) previously propagated raw past the service and the
  router, producing a generic 500. Now wrapped in `LLMClientError`
  (`query_understanding/models.py`) and mapped to a clean `502` in
  `routers/search_pipeline.py`, matching the existing `ResponseParseError`
  handling. Not retried (see `service.py`'s `_call_llm` docstring for why).
- **Uncaught seed-data corruption** (`candidate_repository/memory_repository.py`):
  `_load()` only handled `FileNotFoundError`. Malformed JSON or a seed
  record that doesn't match the `Candidate` schema now raise
  `CandidateSeedDataError` with a clear message identifying the file and
  cause, instead of a raw `json.JSONDecodeError` / pydantic `ValidationError`.
- **Duplicate `FakeLLMClient`**: `query_understanding/tests.py` and
  `routers/tests_search_pipeline.py` each defined their own near-identical
  copy. Consolidated into `app/testing/fakes.py`, imported by both.
- **Dead frontend files**: `frontend/src/CandidateDetail.jsx` and
  `frontend/src/App.css` are unused since the Sprint 2 single-page/Tailwind
  rewrite (confirmed via grep -- no imports anywhere in `src`). They cannot
  be deleted from this workspace, so both now carry a header comment
  explaining they are dead and why, rather than being silently stale.

## Documented, intentionally not touched

- **Unused `Alias` model** (`backend/app/knowledge/models.py`): defined but
  never instantiated -- `TaxonomyEntry.aliases` is `list[str]`, not
  `list[Alias]`. Lives inside the Knowledge Engine, which is explicitly
  frozen per prior instruction ("No more loader improvements. No more
  engine improvements."). Left as-is; a future Knowledge Engine change
  window should either wire it in or remove it.
- **Dual pipelines**: the original mock pipeline (`app/schemas.py`,
  `app/services/*`, `app/routers/search.py` / `candidates.py` / `sources.py`,
  served at `/api/v1/search`) and the real pipeline
  (`app/query_understanding`, `app/search_planner`, `app/candidate_repository`,
  served at `/api/search`) both still exist side by side, each with its own
  "candidate" and "search request/response" shapes
  (`CandidateOut`/`CandidateDetailOut` vs. `Candidate`; `SearchRequest`/
  `SearchResponse` vs. `SearchQueryRequest`/`SearchQueryResponse`). Names do
  not actually collide, but the concepts are duplicated across two parallel
  pipelines. The old pipeline is treated as frozen legacy code per
  established project convention and was left untouched; retiring it once
  the new pipeline is feature-complete would remove this duplication.
- **`CanonicalJobRequirement` has no location/experience fields**: Query
  Understanding's output type only carries `role` and `skills`. The
  frontend's "AI understood" panel already surfaces this honestly
  ("Not captured yet" for Location/Experience) rather than inventing
  values. Extending the schema (and the Knowledge Engine taxonomy types it
  would need) is a Query Understanding + Knowledge Engine change, out of
  scope for a code-review pass.
- **In-memory-only `CandidateRepository`**: `InMemoryCandidateRepository`
  loads a static JSON seed file at process start; there is no
  database-backed implementation yet. The `CandidateRepository` interface
  is already designed to support one without changing callers
  (`app/candidate_repository/interfaces.py`), so this is a planned future
  implementation, not a design flaw.
- **Empty `app/models/` (SQLAlchemy) directory**: exists but is unused by
  either pipeline. Likely scaffolding from an earlier planning phase before
  the in-memory repository was chosen for the MVP. No immediate action
  needed; will matter once a persistent repository implementation is built.
- **Unreferenced frontend assets**: `frontend/src/assets/react.svg`,
  `vite.svg`, and `hero.png` are not imported anywhere in `frontend/src`
  (Vite/CRA scaffolding left over from project init). Binary/SVG files
  can't carry an explanatory code comment the way `.jsx`/`.css` can, and
  the workspace does not allow deletion, so they are simply noted here as
  safe-to-delete whenever the workspace restriction is lifted.

## Process note

This project's workspace-mounted files have repeatedly been corrupted
(null-byte padding / truncation) by ordinary file-edit tooling during this
project's history. Every file touched in this review was rewritten via
direct file write and verified byte-for-byte (no `\x00`, successful
`py_compile`) before being considered final. Anyone editing these files by
hand should be aware the same corruption risk exists in this environment.
