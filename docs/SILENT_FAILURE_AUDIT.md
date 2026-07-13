# Silent Query/Candidate Loss Audit

Every place in the backend where a search query or a candidate can be discarded, filtered, defaulted, or replaced without it being visible in the API response. Ordered by severity. File paths are relative to `backend/`.

## Status: Findings #1 and #2 fixed (Sprint 20H)

**#1 (the post-discovery re-search) is fixed.** `app/discovery/orchestrator.py`'s `run()` no longer calls `self._repository.search(plan)` after connectors run. Discovery now happens exactly once, inside each connector's own `discover()` call. The final candidate set is built directly from `existing_candidates` (the one legitimate pre-discovery search) unioned with whatever `repository.upsert()` returns for every connector-discovered import — the persisted, correctly-merged `Candidate` object, previously computed and thrown away. The repository is used only for its storage/dedup/lookup role (`upsert()`, `find_potential_duplicate()`) — never again as a second, implicit search-filtering stage.

Two new regression tests in `app/discovery/tests_orchestrator.py` prove this: `test_orchestrator_returns_connector_candidate_whose_fields_dont_literally_match_the_plan` reproduces the exact bug (a connector-discovered candidate with `role="Unknown"`, `skills=["Go"]` against a plan searching `"Senior Golang Developer"`/`"Golang"` — zero literal overlap) and confirms the candidate now survives to the final response. `test_orchestrator_never_calls_repository_search_during_a_triggered_run` directly asserts `repository.search()` is never invoked during a triggered run. Both tests were verified to FAIL against the old code (confirmed by temporarily reverting the fix in a disposable copy and re-running) before being confirmed to pass against the fix — proving they actually exercise the regression, not just pass vacuously.

**#2 (the fixed-size result window) is fixed.** `_DISCOVERY_USER_LIMIT = 10` is no longer a hardcoded module constant read directly by `discover()`. It now lives as `GitHubIntelligenceConfig.max_search_results` (default `10`, unchanged behavior for every existing caller), read via `self._intelligence_config.max_search_results` and passed straight through to `GitHubClient.search_users(..., per_page=search_limit)`. Two new tests (`test_discover_honors_a_configured_max_search_results_smaller_than_default` / `..._larger_than_default`) prove the connector actually threads a non-default value through to the real HTTP request's `per_page` query parameter, in both directions — confirming this is a genuine tunable, not a disguised second hardcoded max.

Both fixes were run against the full backend regression suite from a completely fresh copy of the project files (not the working copy) via a separate Python process: **325/325 tests passing**, up from 321 before this sprint (4 new tests: 2 for each fix). As with every fix this session, this proves the logic is correctly wired against mocked-but-realistic GitHub API responses — it does **not** by itself prove the live deployed app behaves this way, since this local backend directory has not yet been pushed/deployed (see the standing git-deployment blocker documented in `GITHUB_LIVE_VALIDATION.md`). A live re-test against the deployed Railway backend, after the user pushes this code, is the only thing that would additionally confirm this in production.

Findings #3–#8 below remain open and unchanged by this sprint.

## 1. CRITICAL — the post-discovery re-search can silently undo every connector fix this session (FIXED — see status above)

**File:** `app/discovery/orchestrator.py`, line 204 (`refreshed_candidates = self._repository.search(plan)`), feeding directly into `app/routers/discovery_search.py`'s `candidates`/`count` response fields.

**File:** `app/candidate_repository/memory_repository.py`, `search()`, lines 120–137.

**What happens:** After the GitHub (or any) connector discovers, enriches, and imports real candidates, the orchestrator re-runs `repository.search(plan)` using the **same original `SearchPlan`** built by Query Understanding + the Knowledge Engine, *before* any connector ran. That `search()` method does exact, literal, case-insensitive matching:

```python
role_matches = candidate_role in normalized_terms
skill_matches = bool(candidate_skills & normalized_terms)
if role_matches or skill_matches:
    results.append(candidate)
```

`normalized_terms` comes from `plan.search_terms` — the recruiter's canonical role/skill strings. A GitHub-sourced candidate's `role` field is **never set** by the GitHub normalizer (only `headline`/`current_company`/`skills` are populated), so it defaults to `"Unknown"` in `normalize_import()`. Their `skills` field is GitHub's own repo languages (e.g. `["Go"]`), not the recruiter's literal wording (e.g. `"Golang"`).

**Consequence:** A candidate that Sprint 20E/20F/20G's connector-level fixes correctly found and imported can still be silently dropped from the final response at this last step, because `candidate.role == "Unknown"` and `{"go"} ∩ {"golang"}` is empty. This is consistent with the one live case that *did* work this session ("Java Spring Boot," 10 candidates returned) — "java" happens to be spelled identically on both sides, same coincidence that caused the original bug.

**This is the single highest-priority fix remaining.** Every fix made to the GitHub connector this session could be neutralized at this step and nobody would see an error — the response would just show fewer candidates than the connector actually found (`ConnectorRunResult.candidates_found`/`candidates_imported` would show correctly in the trace, but the final `candidates` list and `count` would not include them).

## 2. GitHub connector: fixed-size result window, invisible to the recruiter (FIXED — see status above)

**File:** `app/discovery/connectors/github_connector.py`, `_DISCOVERY_USER_LIMIT = 10`.

GitHub's Search Users API can return thousands of matches (live-confirmed: `total_count: 1729` for "golang"). Only the first 10 are ever fetched/considered. This is documented in code comments but the API response has no field indicating "10 of 1,729 candidates were examined" — a recruiter has no way to know the search was this shallow.

## 3. GitHub connector: README evidence capped at 5 repos

**File:** `app/discovery/connectors/github_connector.py`, `_README_FETCH_LIMIT = 5` — only the 5 most-starred non-fork repos get their README fetched. A real skill signal that only appears in a 6th+ repo's README is invisible to both the semantic and fallback token evidence checks. Reasonable cost/latency tradeoff, but a real coverage gap worth naming.

## 4. Greenhouse connector: single-page cap + same literal-matching class of bug as pre-fix GitHub

**File:** `app/discovery/connectors/greenhouse_connector.py`, `_DISCOVERY_PAGE_LIMIT = 100` (line 25) — only the first 100 candidates in the connected ATS are ever paged through; no continuation to a second page.

Same file, line 57: `if any(term in haystack for term in terms)` — literal substring matching between the recruiter's exact role/skill wording and each candidate's `title`/`company`/`tags` text. This is the exact same class of bug Sprint 20E found and fixed for GitHub (spelling mismatches, frameworks not appearing in a fixed field) — it has never been live-tested against a real Greenhouse account, so it's unverified whether it has the same silent-drop problem.

## 5. Matching Engine: literal scoring will systematically under-score dynamically-discovered candidates

**File:** `app/matching/engine.py`, `_score_role` (line 56) and `_score_skills` (line 68) — both use plain token-set overlap between `requirement.role`/`requirement.skills` and `candidate.role`/`candidate.skills`.

This does **not** drop candidates (every candidate is still scored — no exact-match shortcut, per the Sprint 19 rule), but it will systematically score a GitHub-sourced candidate near-zero on both the `role` and `skills` dimensions whenever their real evidence doesn't literally match the query text (the same "Golang" vs `role="Unknown"`, `skills=["Go"]` mismatch as finding #1). Combined with finding #1, a candidate that survives the re-search could still rank near the bottom and look irrelevant to a recruiter, even though Sprint 20G's semantic match correctly identified them as relevant.

## 6. Legacy `/api/v1/search` endpoint: closed 15-item skill list (not on the live recruiter path)

**File:** `app/services/query_parser.py`, `_KNOWN_SKILLS` (15 hardcoded entries). Only used by `app/services/pipeline.py` → `app/routers/search.py`'s `/api/v1/search` — confirmed via `grep` to be a separate, older pipeline that never touches the GitHub connector or `/api/search/smart`. A skill outside that list is silently absent from `must_have_skills` on this endpoint specifically. Low risk today (not the live path), but worth knowing this endpoint still exists and behaves this way if anything ever routes to it.

## 7. Orchestrator: one connector's exception removes only that connector's results (by design, and it IS surfaced)

**File:** `app/discovery/orchestrator.py`, line 149, `except Exception as exc`. Listed for completeness, not as a bug: if a connector's `discover()` raises, that connector contributes zero candidates for this request. This is intentional ("one connector failing must not fail the whole run") and is **not silent** — the error string is recorded in `ConnectorRunResult.error` and in a `DiscoveryStage` detail, both visible in the API response.

## 8. GitHub connector: per-candidate fetch failures are logged, not returned

**File:** `app/discovery/connectors/github_connector.py` — a `GitHubAPIError` on an individual candidate's profile/repo lookup increments `profile_fetch_failures` and skips that candidate. This count is written to the server-side `github.discover.trace` log line, but is **not** included anywhere in the JSON returned by `/api/search/smart` — a recruiter has no visibility into "3 of 10 matched GitHub accounts couldn't be fetched," only server operators watching logs do.

## Recommended priority order

1. ~~Fix #1 (the re-search literal filter)~~ — **done, Sprint 20H.** Until this was fixed, none of Sprint 20E/20F/20G's connector-level correctness work was guaranteed to survive to the final response.
2. ~~Fix #2 (make the search-result window configurable)~~ — **done, Sprint 20H.**
3. Surface #3, #4's caps and #8's fetch-failure count in the API response (even just in the existing `discovery.connector_results`/trace-adjacent fields) so "we only checked N of many" is visible to the recruiter, not just to server logs.
4. Consider whether Matching Engine's role/skill scoring (#5) should also consult evidence text (same semantic/dynamic approach as the connector) rather than literal tokens, so ranking reflects the same relevance judgment discovery already made.
