# Sprint 37: GitHub Connector Onboarding Experience

## Why this sprint exists

Every search was ending in "Suggested Profiles" (seed data) no matter what
was searched for. Root cause, confirmed via `GET /integrations/status`
returning `{"github": {"configured": false}}`: no live connector had ever
been configured locally, so `good_live_count` was always 0 and seed
fallback always triggered. This is not a bug in the matching/ranking/
seed-fallback logic — those systems were never given real data to work
with. This sprint builds the missing piece: a real, production-grade way
for a recruiter/admin to connect GitHub, and for the UI to be honest about
the state of that connection at every point.

Per the explicit brief for this sprint, the ranking engine, matching
engine, and seed fallback logic were **not** touched. Everything below is
onboarding plumbing around those systems, not a change to them.

## Backend changes

**`app/credentials/service.py`** — added `ConnectorCredentialStore.clear_secret(provider)`.
Deletes the persisted, encrypted credential row entirely and evicts the
in-process cache. Idempotent: calling it when nothing was configured is a
no-op, not an error.

**`app/integrations/github/config.py`** — added `GitHubConfigStore.clear()`.
In persistent mode, delegates to `clear_secret()`; in memory mode, drops
the in-process PAT and resets status to unconfigured. Same idempotent
behavior either way.

**`app/routers/github_integration.py`** — added `POST /integrations/github/disconnect`.
Returns `{"configured": false}`. This was the one missing piece of the
connector lifecycle — configure, verify, and status already existed from
Sprint 32; disconnect did not exist anywhere in the codebase before this
sprint.

No other backend endpoint needed to change:
- `POST /integrations/github/configure` already verifies a submitted PAT
  against a real GitHub API call before persisting anything (a 401 means
  nothing is saved) — this was Sprint 32 work, reused as-is.
- `GET /integrations/status` already reports `configured` / `status` /
  `verified_username` / `verified_scopes` / `last_error` for GitHub — also
  Sprint 32, reused as-is.
- The discovery orchestrator already picks up a configured GitHub
  connector automatically on the next search — there is no separate
  "enable GitHub in discovery" step. Connecting GitHub via the new flow
  is sufficient; no code change or redeploy is needed for discovery to
  start using it, satisfying the "no code changes required after
  connecting" requirement.
- `ConnectorRunResult` (in `app/discovery/orchestrator.py`) already carries
  `source_name`, `configured`, `candidates_found`, and `error` per
  connector per search — this is what the frontend banner logic reads to
  decide whether GitHub was actually available during a given search.

No Alembic migration was needed. Disconnect only deletes an existing row
in the already-migrated `connector_credentials` table; no schema changed.

## Backend tests

- `app/credentials/tests_service.py` — 4 new tests for `clear_secret`:
  removes the row, evicts the cache, is a no-op when never configured,
  only affects its own provider.
- `app/integrations/github/tests_config.py` — 3 new tests for `clear()`:
  resets memory mode, is a no-op when never configured, delegates to the
  credential store in persistent mode.
- `app/routers/tests_github_integration.py` — 3 new tests for the
  disconnect endpoint: reverts to unconfigured after configure, is
  idempotent when never configured, and reconnecting after disconnect
  works end to end.

Full backend suite: **415 passed**, 31 deselected (pre-existing, unrelated
sandbox-only SOCKS-proxy import failures in the GitHub connector and
semantic matcher test files — not touched by this sprint).

## Frontend changes

**`frontend/src/api.js`** — added `getIntegrationsStatus()`,
`configureGithub(personalAccessToken)`, `disconnectGithub()`. All three
call the GitHub-specific PAT flow (`/integrations/github/*`,
`/integrations/status`), which is a separate system from the existing
`getConnectors()` (the older generic `/connectors` registry) — the two are
not conflated.

**`frontend/src/components/GithubConnectModal.jsx`** (new) — the complete
connection flow: PAT input, Verify & Connect (one call — the backend
verifies live before saving anything), a connected state showing the
verified GitHub username and scopes, Reconnect (re-shows the input even
when already connected), and Disconnect. Errors from the backend (invalid
token, GitHub unreachable) are shown directly, not swallowed.

**`frontend/src/App.jsx`** —
- Fetches `GET /integrations/status` once on mount.
- Header button: shows "Connect GitHub" or "GitHub connected" depending
  on real status, opens the modal.
- Results view: when a search's own `discovery.connector_results` shows
  GitHub was not configured for that run *and* `seed_fallback_used` is
  true, shows the explicit banner: *"GitHub is not connected. Showing
  suggested profiles until a live talent source is connected."* with an
  inline Connect button. This replaces any silent fallback — the
  recruiter is never left wondering why they're seeing suggested
  profiles.
- Source Group section headers (Sprint 36) already distinguish "GitHub
  Matches" from "Suggested Profiles" whenever `source_groups` is present
  — no further change needed here.

## Verification performed

- Full backend test suite (415 passed) after syncing all six modified
  backend files into a clean test run.
- Frontend: `esbuild` transform of every `.js`/`.jsx` file under `src/`
  passed with zero syntax/import errors, and — more strongly — Vite's own
  production build transformed all 1,934 modules in the real dependency
  graph twice in a row with no errors. The build's final CSS-minification
  step failed only because this sandbox's `npm install` can't extract the
  native `lightningcss`/`esbuild` binary files (`ENOENT` on the `.node`
  binaries) — a sandbox packaging limitation unrelated to the sprint's
  code, not a code defect. All application code (React components,
  `api.js`, the new modal, `App.jsx` wiring) is confirmed structurally
  sound; a final visual/interactive check in your own browser is still
  worth doing before you consider this fully signed off.

## What still needs a real PAT to confirm (objective 6)

The one thing that cannot be verified without a live GitHub Personal
Access Token: actually connecting one, confirming `GET /integrations/status`
flips to `connected`, running a real search, and watching the "GitHub
Matches" Source Group appear with real candidates while seed fallback
drops away and pagination reflects a larger real pool. This is a
one-time manual step on your end — generate a PAT from GitHub Settings →
Developer settings → Personal access tokens, click "Connect GitHub" in
the app, paste it in, and run a search.

## Not touched (by design, per this sprint's explicit constraint)

Ranking engine, matching engine, seed fallback logic. Those should be
evaluated against real GitHub data once you've connected a live token —
not redesigned ahead of that evidence.
