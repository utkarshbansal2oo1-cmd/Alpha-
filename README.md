# AlphaSource — Foundation

Read `docs/ARCHITECTURE.md`, `docs/FOLDER_STRUCTURE.md`, `docs/API_CONTRACT.md`, `docs/KNOWLEDGE_ENGINE.md`,
`docs/QUERY_UNDERSTANDING_ENGINE.md`, and `database/schema.sql` for the design. This README is just
"how do I run it."

## 1. Start Postgres
```bash
cd database
docker compose up -d
```

## 2. Backend (FastAPI)
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # already points at the docker-compose Postgres
alembic upgrade head           # applies migrations (empty baseline on Day 1)
uvicorn app.main:app --reload --port 8000
```
Check it: `curl http://localhost:8000/health` → `{"status":"ok"}`

To actually call the AI-backed search endpoint (below), also set a real Gemini key in `.env`:
```
GEMINI_API_KEY=your-real-key-here
```
Without a key, `POST /api/search` fails with a clear error at the LLM-calling step rather than
silently returning empty/fake results.

## 3. Frontend (React + Vite)
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```
Open the URL Vite prints (usually http://localhost:5173).

## 4. Run the backend test suite
```bash
cd backend
pytest app/
```
`pytest.ini` (backend/) tells pytest to also discover this project's `tests.py` / `tests_*.py` files,
not just the default `test_*.py` pattern — without it, only `app/knowledge/tests/test_*.py` would run.
104 tests currently pass across knowledge, search_planner, query_understanding, candidate_repository,
and the API layer.

## Calling the search endpoint

The first working end-to-end vertical slice: recruiter free-text in, unranked candidate list out.

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Find Product Engineers with AWS"}'
```

Response shape:
```json
{
  "candidates": [
    {
      "id": "cand-002",
      "name": "Rahul Mehta",
      "role": "Product Engineer",
      "experience": 6.0,
      "skills": ["AWS", "Docker", "Node.js"],
      "location": "Bangalore",
      "current_company": "Foo Systems",
      "source": "seed_data"
    }
  ],
  "count": 6
}
```

Pipeline behind this route: `QueryUnderstandingService.parse(query)` (Gemini call, JSON-forced,
validated, retried once on failure) → `SearchPlanner.build_plan(requirement)` (Knowledge Engine
expansion) → `CandidateRepository.search(plan)` (in-memory seed data, retrieval only). No ranking,
matching, connectors, or authentication — see `docs/` for what those look like when they're built.

Error responses: `422` if the query is empty or the LLM's response never becomes valid after one
retry attempt at parsing/shape; `502` if the LLM never returns parseable JSON at all after the retry.

The pre-existing `POST /api/v1/search` route (from the earlier architecture-phase mock pipeline) is
untouched and still works independently — see `backend/app/routers/search.py`.

## What this foundation includes
- `backend/app/config.py` — single source of truth for settings (`DATABASE_URL`, `CORS_ORIGINS`,
  `GEMINI_API_KEY`), loaded from `.env`.
- `backend/app/database.py` — SQLAlchemy engine/session/`Base` + `get_db` dependency.
- `backend/alembic/` — wired to `app.database.Base` and `app.config.settings`.
- `backend/app/routers/health.py` — `GET /health`.
- `backend/app/routers/search_pipeline.py` — `POST /api/search`, the real pipeline described above.
- `backend/app/knowledge/` — the Knowledge Engine (taxonomies, alias/expansion lookup). Frozen —
  no further changes to `loader.py`/`engine.py` without explicit approval.
- `backend/app/search_planner/` — converts a `CanonicalJobRequirement` into a `SearchPlan` using the
  Knowledge Engine.
- `backend/app/query_understanding/` — recruiter free-text → `CanonicalJobRequirement`, via a
  provider-agnostic `LLMClient` interface (Gemini implementation today).
- `backend/app/candidate_repository/` — `SearchPlan` → `Candidate[]`, in-memory/JSON-seeded today,
  swappable for a real database or connector-backed repository later.
- CORS origins come from `settings.cors_origins_list`, not a hardcoded `*`.
- `database/docker-compose.yml` — Postgres 16, credentials matching `backend/.env.example`.
- `frontend/.env` — `VITE_API_BASE_URL`, read by `frontend/src/api.js`.

## What's intentionally NOT built yet
Ranking, matching/scoring, real data source connectors (LinkedIn/Naukri/ATS/resume upload),
authentication, and a real Postgres-backed candidate store. `backend/app/models/` is intentionally
empty; real SQLAlchemy models and their Alembic migrations are still future work.
