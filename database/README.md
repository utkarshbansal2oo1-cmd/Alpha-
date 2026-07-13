# Database

```bash
cd database
docker compose up -d
```

Starts Postgres 16 on `localhost:5432` with credentials matching `backend/.env.example`
(`alphasource` / `alphasource` / db `alphasource`). Once it's up, run migrations from
`backend/`:

```bash
cd ../backend
alembic upgrade head
```

`schema.sql` in this folder is the target relational shape (candidates, sources,
candidate_source_links, searches, match_results) from the architecture doc — it is
reference/documentation, not something to run directly. Tables get created through
Alembic migrations once SQLAlchemy models for them exist (out of scope for the
Day-1 foundation task).
