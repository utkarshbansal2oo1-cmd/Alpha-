"""POST /integrations/github/configure -- Sprint 20B, PAT verification
added Sprint 32.

Sprint 32: a submitted PAT is no longer trusted and stored blind. Before
`config_store.set()` is ever called, this endpoint makes one real call to
GitHub (`GET /user`, via GitHubClient.get_authenticated_user()) to prove
the token actually authenticates. A 401 means the token is invalid or
revoked -- nothing is persisted, and the recruiter/admin gets a clear
error instead of a search silently skipping GitHub weeks later. On
success, the token's owner (verified_username) and reported OAuth scopes
(verified_scopes -- empty for fine-grained PATs, which don't return that
header) are recorded via config_store.mark_verified().

`verify` is injected (get_github_verifier) rather than constructing
GitHubClient inline, so tests can substitute a fake verifier and never
make a real network call.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_recruiter
from app.integrations.github.client import GitHubAPIError, GitHubClient
from app.integrations.github.config import GitHubConfig, GitHubConfigStore, get_github_config_store
from app.models.recruiter import RecruiterRow

router = APIRouter(prefix="/integrations/github", tags=["github"])


class ConfigureRequest(BaseModel):
    personal_access_token: str = Field(min_length=1)
    base_url: str | None = Field(
        default=None, description="Override for GitHub Enterprise Server -- defaults to the real https://api.github.com"
    )


class ConfigureResponse(BaseModel):
    configured: bool
    base_url: str
    verified_username: str | None = None
    verified_scopes: list[str] | None = None


class DisconnectResponse(BaseModel):
    configured: bool


def get_github_verifier():
    """Returns a callable(config: GitHubConfig) -> tuple[str, list[str]]
    that makes one real GitHub API call to verify a PAT, raising
    GitHubAPIError (401 for an invalid/revoked token) if it doesn't
    authenticate. A plain provider function -- swappable via FastAPI's
    dependency_overrides in tests, same pattern as every other DI seam
    in this codebase."""

    def _verify(config: GitHubConfig) -> tuple[str, list[str]]:
        client = GitHubClient(config)
        try:
            profile, scopes = client.get_authenticated_user()
        finally:
            client.close()
        return profile.get("login"), scopes

    return _verify


@router.post("/configure", response_model=ConfigureResponse)
def configure_github(
    payload: ConfigureRequest,
    config_store: GitHubConfigStore = Depends(get_github_config_store),
    verify: callable = Depends(get_github_verifier),
    _recruiter: RecruiterRow = Depends(get_current_recruiter),
) -> ConfigureResponse:
    config = GitHubConfig(
        personal_access_token=payload.personal_access_token,
        base_url=payload.base_url or GitHubConfig.model_fields["base_url"].default,
    )

    try:
        username, scopes = verify(config)
    except GitHubAPIError as exc:
        if exc.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid GitHub Personal Access Token -- nothing was saved.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not verify the GitHub token right now: {exc}",
        ) from exc

    # Only reachable once verification succeeded -- an invalid token is
    # never persisted (see the 401 branch above).
    config_store.set(config)
    config_store.mark_verified(username, scopes)

    return ConfigureResponse(
        configured=True,
        base_url=config.base_url,
        verified_username=username,
        verified_scopes=scopes or None,
    )


@router.post("/disconnect", response_model=DisconnectResponse)
def disconnect_github(
    config_store: GitHubConfigStore = Depends(get_github_config_store),
    _recruiter: RecruiterRow = Depends(get_current_recruiter),
) -> DisconnectResponse:
    """Sprint 37: the recruiter-facing "Disconnect" action -- removes the
    stored PAT entirely (see GitHubConfigStore.clear()) so the connector
    reverts to exactly the same unconfigured state GET /integrations/
    status reports for a connector that was never connected in the first
    place. Idempotent: disconnecting when nothing was configured returns
    the same {"configured": false} rather than erroring, since the
    end state the caller cares about (GitHub is not connected) is already
    true either way."""
    config_store.clear()
    return DisconnectResponse(configured=False)
