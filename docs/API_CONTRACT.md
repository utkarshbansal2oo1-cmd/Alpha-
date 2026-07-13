# AlphaSource API Contract (v1)

Base URL: `http://localhost:8000/api/v1` (health check is unprefixed: `GET /health`)

## POST /search
Recruiter submits a plain-English requirement. Runs the full pipeline (parse → fetch from all active sources → normalize → dedupe → match → rank → explain) and returns ranked candidates.

**Request**
```json
{ "query": "Find Product Engineers with 7+ years of experience in Bangalore, skilled in AWS and Kubernetes." }
```

**Response 200**
```json
{
  "search_id": "b7e1...",
  "parsed_requirement": {
    "role": "Product Engineer",
    "min_experience_yrs": 7,
    "location": "Bangalore",
    "must_have_skills": ["AWS", "Kubernetes"],
    "nice_to_have_skills": []
  },
  "results": [
    {
      "candidate_id": "c9f2...",
      "full_name": "Asha Rao",
      "current_title": "Senior Product Engineer",
      "current_company": "Acme Cloud",
      "location": "Bangalore",
      "total_experience_yrs": 8.5,
      "match_score": 92.5,
      "reasoning": "8.5 years experience exceeds the 7-year bar; direct AWS + Kubernetes overlap; based in Bangalore.",
      "sources": ["linkedin", "naukri"]
    }
  ],
  "count": 1
}
```

## GET /candidates/{candidate_id}
Full candidate detail page.

**Response 200**
```json
{
  "candidate_id": "c9f2...",
  "full_name": "Asha Rao",
  "email": "asha.rao@example.com",
  "phone": "+91...",
  "location": "Bangalore",
  "current_title": "Senior Product Engineer",
  "current_company": "Acme Cloud",
  "total_experience_yrs": 8.5,
  "skills": ["AWS", "Kubernetes", "Python", "React"],
  "summary": "...",
  "resume_url": "https://...",
  "sources": [
    { "name": "linkedin", "external_id": "...", "fetched_at": "2026-07-05T10:00:00Z" },
    { "name": "naukri", "external_id": "...", "fetched_at": "2026-07-06T09:00:00Z" }
  ]
}
```

## GET /sources
List connected data sources and their status.

**Response 200**
```json
{ "sources": [ { "id": "...", "name": "mock", "type": "mock", "is_active": true } ] }
```

## POST /sources
Register/connect a new source. Body shape is intentionally generic so any connector type fits.

```json
{ "name": "naukri", "type": "job_board", "config": { "api_key_ref": "NAUKRI_API_KEY" } }
```

## POST /candidates/{candidate_id}/shortlist
Send a candidate into AlphaRecrewt for assessment/interview (future integration point — stubbed).

```json
{ "search_id": "b7e1..." }
```

**Response 202**
```json
{ "status": "queued", "candidate_id": "c9f2...", "target": "alpharecrewt" }
```

## GET /health
Liveness check, unprefixed (not under `/api/v1`).
```json
{ "status": "ok" }
```
