from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    candidate_import,
    candidate_intelligence,
    candidates,
    connector_management,
    discovery_search,
    github_integration,
    greenhouse_integration,
    health,
    search,
    search_pipeline,
    sources,
)

app = FastAPI(title=settings.APP_NAME, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)          # GET /health -> {"status": "ok"}
app.include_router(search.router)          # POST /api/v1/search (existing mock pipeline, untouched)
app.include_router(search_pipeline.router) # POST /api/search (Query Understanding -> Search Planner -> Candidate Repository)
app.include_router(candidates.router)
app.include_router(sources.router)
app.include_router(candidate_import.router)  # POST /candidate/import (browser extension capture -> CandidateRepository)
app.include_router(candidate_intelligence.router)  # GET /candidate/{id}/health|enrichment-plan|evidence-timeline|versions
app.include_router(greenhouse_integration.router)  # /integrations/greenhouse/configure|sync|sync-status|push/{id}
app.include_router(discovery_search.router)  # POST /api/search/smart (Sprint 18: Autonomous Discovery Engine)
app.include_router(connector_management.router)  # GET/POST /connectors... (Sprint 20A: Universal Connector Framework)
app.include_router(github_integration.router)  # POST /integrations/github/configure (Sprint 20B: GitHub Discovery Connector)
