"""GitHub connector configuration endpoint -- Sprint 20B.

  POST /integrations/github/configure  -- set the Personal Access Token
                                           (+ base URL override, for
                                           GitHub Enterprise Server)

Registered additively in main.py; nothing here changes /api/search,
/api/search/smart, /candidate/import, or any other existing route.
Mirrors app/routers/greenhouse_integration.py's configure endpoint --
the GitHub connector itself has no bulk sync or push-back (Sprint 20B is
discovery-only, per the sprint brief), so this router is intentionally
just the one endpoint.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.integrations.github.config import GitHubConfig, GitHubConfigStore, get_github_config_store

router = APIRouter(prefix="/integrations/github", tags=["github"])


class ConfigureRequest(BaseModel):
    personal_access_token: str = Field(min_length=1)
    base_url: str | None = Field(
        default=None, description="Override for GitHub Enterprise Server -- defaults to the real https://api.github.com"
    )


class ConfigureResponse(BaseModel):
    configured: bool
    base_url: str


@router.post("/configure", response_model=ConfigureResponse)
def configure_github(
    payload: ConfigureRequest,
    config_store: GitHubConfigStore = Depends(get_github_config_store),
) -> ConfigureResponse:
    config = GitHubConfig(
        personal_access_token=payload.personal_access_token,
        base_url=payload.base_url or GitHubConfig.model_fields["base_url"].default,
    )
    config_store.set(config)
    return ConfigureResponse(configured=True, base_url=config.base_url)
