# AlphaSource — Architecture (MVP)

## 1. Design principle

The system must never hardcode a data source. LinkedIn, Naukri, iimjobs, an ATS, or a customer's uploaded resume CSV are all just **connectors** that produce candidates in one common shape. The AI matching engine only ever reads from the unified candidate store — it has no knowledge of where a candidate came from. Adding a new source means writing one new connector class; nothing else in the system changes.

This is enforced with three boundaries:

1. **Connector interface** (`SourceConnector` abstract base) — every source implements `fetch(query) -> list[RawCandidate]`. Naukri, an ATS webhook, a resume-upload parser, and a mock/test connector all satisfy the same interface.
2. **Normalization layer** — converts each connector's raw output into the canonical `Candidate` schema (same fields regardless of origin) and writes to Postgres.
3. **Matching engine** — operates only on canonical `Candidate` rows plus the recruiter's parsed query. It is 100% source-agnostic by construction, not by convention.

## 2. High-level flow

```
Recruiter query (plain English)
        │
        ▼
[1] Query Understanding (LLM) ──> structured JobRequirement
        │  {role, min_experience, location, must_have_skills, nice_to_have_skills}
        ▼
[2] Source Fan-out ──> SourceConnector[] (parallel)
        │  LinkedIn | Naukri | iimjobs | ATS | Resume DB | ... (pluggable)
        ▼
[3] Normalization ──> canonical Candidate rows upserted into Postgres
        ▼
[4] Deduplication ──> merge candidates appearing in >1 source (email/phone/name+company fuzzy match)
        ▼
[5] Matching Engine ──> score each candidate against JobRequirement
        │  (skills overlap, experience fit, location fit, embedding similarity)
        ▼
[6] Ranking + Explanation (LLM) ──> match_score + human-readable reasoning
        ▼
[7] API response ──> React results UI ──> Candidate detail page
        │
        ▼
[8] Shortlist ──> handoff payload to AlphaRecrewt (future)
```

## 3. Components

**Frontend (React + Vite)**
- Single search box → `POST /api/v1/search`
- Results list with match score + short reasoning
- Candidate detail page → `GET /api/v1/candidates/{id}`

**Backend (FastAPI)**
- `routers/search.py` — orchestrates steps 1–7
- `routers/candidates.py` — candidate detail/list
- `routers/sources.py` — manage connected sources (connect/disconnect a source, list what's active)
- `routers/health.py` — liveness check, unprefixed `GET /health`
- `services/query_parser.py` — free text → structured `JobRequirement`
- `services/connectors/` — one file per source, all implementing `SourceConnector`
- `services/dedup.py` — identity resolution across sources
- `services/matching_engine.py` — scoring + ranking, source-agnostic
- `config.py` — single source of truth for settings, loaded from `.env`
- `database.py` — SQLAlchemy engine/session/Base

**Data layer (Postgres, via SQLAlchemy + Alembic)**
- `candidates` — canonical profile (source-agnostic)
- `sources` — registry of connected data sources (LinkedIn, Naukri, ATS-X, "Acme Corp resume upload", …)
- `candidate_source_links` — many-to-many: which sources contributed to which canonical candidate + the raw external ID, so the same person found on LinkedIn and Naukri collapses into one row
- `searches` — every recruiter query, for history/analytics
- `match_results` — score + reasoning per (search, candidate) pair

See `database/schema.sql` for the full DDL and `docs/API_CONTRACT.md` for the REST contract.

## 4. Why this scales without rework

Tomorrow's Naukri partnership = new file `services/connectors/naukri_connector.py` implementing `fetch()`, registered in `services/connectors/registry.py`. Same for an ATS integration or a customer CSV upload parser. Zero changes to matching engine, API contract, database schema, or frontend. The `sources` table and `candidate_source_links` table already anticipate N sources per candidate.

## 5. Foundation phase (this task)

This phase is infrastructure only: folder structure, FastAPI app, React+Vite app, Postgres via Docker Compose, SQLAlchemy engine/session wiring, Alembic migrations, environment config, CORS, and a `GET /health` endpoint. No business logic, AI calls, search behavior, or connector implementations are added in this phase — those come next, one task at a time, without touching this foundation.
