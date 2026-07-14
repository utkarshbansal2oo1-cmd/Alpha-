"""POST /auth/login -- Sprint 30.

The only auth endpoint that exists. No registration endpoint -- recruiter
accounts are created solely via AuthService.ensure_admin() at startup, per
this sprint's "not enterprise auth, just enough" scope (see
app/auth/service.py's own docstring).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.dependencies import get_auth_service
from app.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, auth_service: AuthService = Depends(get_auth_service)) -> LoginResponse:
    token = auth_service.authenticate(payload.username, payload.password)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
    return LoginResponse(token=token, username=payload.username)
