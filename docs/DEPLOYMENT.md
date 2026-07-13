# Deployment Guide — AlphaSource AI

## Architecture

Three independently deployable pieces:

- **`backend/`** — FastAPI app serving the real search pipeline (`POST /api/search`: Query Understanding → Knowledge Engine → Search Planner → Candidate Repository) plus the older mock pipeline (`/api/v1/search`, untouched). In-memory candidate store — no database is required to run this today (see Known Limitations).
- **`frontend/`** — the recruiter product UI (React/Vite). Not part of this sprint's deployment scope, but deployed the same way as `marketing/` if/when needed.
- **`marketing/`** — the AlphaSource AI public launch site (React/Vite/Tailwind/Framer Motion), including Guided Demo Mode (fully offline/deterministic) and Live Pipeline mode (calls the real backend).

```
Browser ──> Vercel (marketing/, static + client-side React)
                │
                │  fetch POST /api/search  (Live Pipeline mode only)
                ▼
            Railway (backend/, FastAPI + uvicorn)
```

Guided Demo Mode never leaves the browser — it resolves against `marketing/src/data/candidates.js` and `demoScenarios.js` client-side, so the marketing site is fully functional even if the backend is down. Live Pipeline mode requires the backend to be reachable and `GEMINI_API_KEY` to be set there.

## Hosting

| Piece | Platform | Why |
|---|---|---|
| `marketing/` | **Vercel** | Native Vite support, zero-config static hosting + global CDN, instant preview deploys per branch/PR — the standard choice for this stack and what was requested. |
| `backend/` | **Railway** | Simplest path for a small FastAPI service with no infra to manage; Nixpacks auto-detects Python + `requirements.txt`, and `backend/Procfile`/`backend/railway.json` (added this sprint) make the start command explicit. As requested, and objectively reasonable here since the backend has no real database dependency yet (see below) — nothing about this app needs Railway's Postgres add-on or a heavier platform like a Kubernetes-based host. |

No case was found this sprint where a different platform would be objectively better for this specific app's current shape (single stateless FastAPI service, in-memory data, no queues/workers) — Vercel + Railway is a reasonable, low-overhead fit as specified.

## Environment variables

### Backend (Railway → Variables tab)

| Variable | Required | Notes |
|---|---|---|
| `GEMINI_API_KEY` | Yes, for Live Pipeline mode | Without it, `/api/search` returns a clean `502` (verified this sprint) rather than crashing — Guided Demo Mode on the marketing site is unaffected either way. |
| `CORS_ORIGINS` | Yes | Must include the deployed marketing site's origin, e.g. `https://alphasource-ai.vercel.app`. Comma-separated if multiple (add the Vercel preview-deploy domain pattern too if you want previews to be able to call Live Pipeline mode). |
| `DATABASE_URL` | No | Has a default in `backend/app/config.py`; nothing in the running app actually connects to it (see Known Limitations) — safe to leave unset on Railway. |
| `ENV` | No | Defaults to `development`; set to `production` for clarity in logs, no behavioral difference today. |

### Marketing (Vercel → Environment Variables)

| Variable | Required | Notes |
|---|---|---|
| `VITE_API_ROOT_URL` | Yes, for Live Pipeline mode | The backend's public Railway URL, e.g. `https://alphasource-backend.up.railway.app`. Guided Demo Mode works with this unset. |

## Deployment process

### Backend (Railway)
1. Push `backend/` (via the repo root) to GitHub — see Repository section below.
2. In Railway: New Project → Deploy from GitHub repo → select this repo → set **Root Directory** to `backend`.
3. Railway auto-detects Python via Nixpacks and installs `backend/requirements.txt`. `backend/railway.json` sets the start command explicitly: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. Add the environment variables above.
5. Deploy. Verify: `curl https://<your-railway-domain>/health` → `{"status":"ok"}`.

### Marketing (Vercel)
1. In Vercel: New Project → Import the same GitHub repo → set **Root Directory** to `marketing`.
2. Framework preset: Vite (auto-detected; `marketing/vercel.json` makes build command/output explicit).
3. Add `VITE_API_ROOT_URL` pointing at the Railway backend URL from above.
4. Deploy. Verify the homepage loads and Guided Demo Mode returns results with zero network calls (check the browser Network tab — there should be none for a Guided Demo search).
5. Update the backend's `CORS_ORIGINS` to include the resulting `*.vercel.app` domain, then redeploy the backend (env var changes require a redeploy on Railway).

## Rollback procedure

Both platforms keep every previous deployment:
- **Vercel**: Project → Deployments → find the last known-good deployment → "..." menu → **Promote to Production**. Instant, no rebuild.
- **Railway**: Project → Deployments tab → select a previous successful deployment → **Redeploy**. Takes as long as a fresh deploy (a few minutes), since Railway does not keep old build artifacts running in standby.

For a botched *code* change (not just a bad deploy), `git revert <commit>` and push — both platforms auto-deploy on push to the connected branch by default.

## Updating the application

Both Vercel and Railway are configured to auto-deploy on push to the connected branch (typically `main`). Standard flow:
```
git checkout -b my-change
# edit code
git commit -am "..."
git push origin my-change
# open a PR -> Vercel creates a preview deployment automatically
# merge to main -> both Vercel and Railway redeploy production automatically
```
No manual deploy step is required once both projects are connected to the GitHub repo.

## Known limitations (carried over from `docs/TECH_DEBT.md`, restated here for deployment context)

- The backend has no real database wired up — `backend/app/database.py` defines a SQLAlchemy engine but nothing in the running app imports or uses it. Candidate data is an in-memory JSON seed file (8 records) for the real pipeline, and a separate offline 50-record dataset for the marketing site's Guided Demo Mode. This is fine for a demo; it is not a production data layer.
- `GEMINI_API_KEY` must be a real, working Gemini API key for Live Pipeline mode to return results; Guided Demo Mode has no such dependency and is the recommended mode for any unattended or executive-facing run.
- No authentication exists on either `/api/search` or `/api/v1/search` — acceptable for an internal demo, not for a public production API long-term.
