"""FastAPI dependency for protecting endpoints -- Sprint 30.

settings.REQUIRE_AUTH (default False) gates whether this actually enforces
anything -- same safe-default pattern as Sprint 29's QUERY_PROVIDER and
Sprint 30's CANDIDATE_REPOSITORY_BACKEND: every existing test, and local
dev with no Postgres configured, gets a free pass (an anonymous stand-in
recruiter, no database touched at all) so nothing breaks without explicit
opt-in. Only when REQUIRE_AUTH=true (set once Postgres + an admin account
are actually provisioned) does a request need a valid, non-expired
Bearer session token -- see app/routers/auth.py for how one is issued.

This is the fix for the standing gap flagged before this sprint: the
publicly-deployed search endpoint had no authentication at all, so anyone
with the URL could burn your GitHub/Groq/Gemini quota or overwrite your
GitHub PAT via /integrations/github/configure.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.service import AuthService
from app.config import settings
from app.models.recruiter import RecruiterRow

_bearer_scheme = HTTPBearer(auto_error=False)

_ANONYMOUS_RECRUITER = RecruiterRow(id="anonymous", username="anonymous", password_hash="", password_salt="")


def get_auth_service() -> AuthService:
    return AuthService()


def get_current_recruiter(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> RecruiterRow:
    if not settings.REQUIRE_AUTH:
        return _ANONYMOUS_RECRUITER

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session token -- call POST /auth/login first and send the returned token as 'Authorization: Bearer <token>'.",
        )

    recruiter = auth_service.get_recruiter_for_token(credentials.credentials)
    if recruiter is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session token.")

    return recruiter
