"""GET /integrations/status -- Sprint 32.

One place for the frontend to check connector health without guessing
from a thin search result. Currently reports GitHub only (the one
connector with persisted credentials + verification as of this sprint);
structured as a dict keyed by provider name so adding Greenhouse/Lever/
etc. later is additive -- just another key, not a response-shape change.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.integrations.github.config import GitHubConfigStore, get_github_config_store

router = APIRouter(tags=["integrations"])


class ConnectorStatus(BaseModel):
    configured: bool
    status: str  # "unconfigured" | "connected" | "invalid"
    verified_username: str | None = None
    verified_scopes: list[str] | None = None
    last_verified_at: str | None = None
    last_error: str | None = None


class IntegrationsStatusResponse(BaseModel):
    github: ConnectorStatus


@router.get("/integrations/status", response_model=IntegrationsStatusResponse)
def get_integrations_status(
    github_config_store: GitHubConfigStore = Depends(get_github_config_store),
) -> IntegrationsStatusResponse:
    github_status = github_config_store.get_status()
    last_verified_at = github_status.get("last_verified_at")
    return IntegrationsStatusResponse(
        github=ConnectorStatus(
            configured=github_status["configured"],
            status=github_status["status"],
            verified_username=github_status.get("verified_username"),
            verified_scopes=github_status.get("verified_scopes"),
            last_verified_at=last_verified_at.isoformat() if last_verified_at else None,
            last_error=github_status.get("last_error"),
        )
    )
