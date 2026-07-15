import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    auth,
    candidate_import,
    candidate_intelligence,
    candidates,
    connector_management,
    discovery_search,
    github_integration,
    greenhouse_integration,
    health,
    integrations_status,
    search,
    search_pipeline,
    sources,
)

# Sprint 28: uvicorn only configures its own "uvicorn"/"uvicorn.access"
# loggers, not this app's. Without a root handler at INFO or below, every
# logger.info() call across the codebase (github_connector.py's
# "github.discover.trace" -- the exact search query, users found, filter
# counts -- decision_engine's discovery reasoning, connector
# search_failed/semantic_unavailable events) is silently dropped by
# Python's default root level (WARNING). Those trace logs exist
# specifically so a zero-candidate result is explainable from the logs;
# until now they never reached Railway's log viewer at all. Level is
# configurable via LOG_LEVEL so it can be turned down in a very
# high-traffic deployment without a code change.
_STANDARD_LOG_RECORD_ATTRS = set(logging.makeLogRecord({}).__dict__)


class _ExtraFieldsFormatter(logging.Formatter):
    """A plain %(message)s format silently drops everything passed via
    logger.info(msg, extra={...}) -- those keys become LogRecord
    attributes, not part of the message. This formatter appends any
    non-standard attributes as key=value pairs, so calls like
    logger.info("github.discover.trace", extra={"search_query": ..., "users_found": ...})
    actually show the data they were written to report."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = {
            k: v for k, v in record.__dict__.items() if k not in _STANDARD_LOG_RECORD_ATTRS
        }
        if extras:
            extras_str = " ".join(f"{k}={v!r}" for k, v in extras.items())
            return f"{base} | {extras_str}"
        return base


_log_handler = logging.StreamHandler()
_log_handler.setFormatter(_ExtraFieldsFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    handlers=[_log_handler],
)

app = FastAPI(title=settings.APP_NAME, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    # Sprint 37 fix: in development, also allow ANY http://localhost:<port>
    # or http://127.0.0.1:<port> origin -- Vite hops to the next free port
    # whenever an earlier one is still held by a forgotten `npm run dev`
    # process, and that repeatedly broke CORS since cors_origins_list only
    # ever listed a few hardcoded ports. Never applied outside development
    # -- a real deployment must keep relying on explicit CORS_ORIGINS.
    allow_origin_regex=settings.LOCALHOST_CORS_REGEX if settings.ENV == "development" else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _bootstrap_admin_recruiter() -> None:
    """Sprint 30: creates the one admin recruiter account from
    ADMIN_USERNAME/ADMIN_PASSWORD if REQUIRE_AUTH is on and no recruiter
    exists yet. Guarded by REQUIRE_AUTH (default False) so this never
    touches the database -- and never requires one to be reachable -- in
    local dev or any test run that doesn't explicitly opt into real auth."""
    if not settings.REQUIRE_AUTH:
        return
    from app.auth.service import AuthService

    AuthService().ensure_admin(settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD)


app.include_router(auth.router)            # POST /auth/login
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
app.include_router(integrations_status.router)  # GET /integrations/status (Sprint 32: connector health)
