# AlphaSource backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Try it:
```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Find Product Engineers with 7+ years of experience in Bangalore, skilled in AWS and Kubernetes."}'
```

MVP uses an in-memory store and a mock candidate source (`app/services/connectors/mock_connector.py`)
so the whole pipeline runs with zero external dependencies. See `app/db/schema.sql` for the real
Postgres schema this will move to, and `ARCHITECTURE.md` (repo root) for why adding new sources
(Naukri, an ATS, resume uploads) never requires touching the matching engine or API.
