"""Tests for get_current_recruiter -- Sprint 30. Confirms the safe-default
behavior (REQUIRE_AUTH=False -> no-op, no DB touched) and real enforcement
once REQUIRE_AUTH=True, without needing a live Postgres for either case."""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_recruiter
from app.auth.service import AuthService
from app.database import Base


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_returns_anonymous_when_auth_disabled(monkeypatch):
    monkeypatch.setattr("app.auth.dependencies.settings.REQUIRE_AUTH", False)

    recruiter = get_current_recruiter(credentials=None, auth_service=AuthService())

    assert recruiter.username == "anonymous"


def test_raises_401_when_auth_enabled_and_no_credentials(monkeypatch):
    monkeypatch.setattr("app.auth.dependencies.settings.REQUIRE_AUTH", True)

    with pytest.raises(HTTPException) as exc_info:
        get_current_recruiter(credentials=None, auth_service=AuthService())

    assert exc_info.value.status_code == 401


def test_raises_401_when_auth_enabled_and_token_invalid(monkeypatch, session_factory):
    monkeypatch.setattr("app.auth.dependencies.settings.REQUIRE_AUTH", True)

    class _FakeCredentials:
        credentials = "not-a-real-token"

    with pytest.raises(HTTPException) as exc_info:
        get_current_recruiter(credentials=_FakeCredentials(), auth_service=AuthService(session_factory=session_factory))

    assert exc_info.value.status_code == 401


def test_returns_real_recruiter_when_auth_enabled_and_token_valid(monkeypatch, session_factory):
    monkeypatch.setattr("app.auth.dependencies.settings.REQUIRE_AUTH", True)

    service = AuthService(session_factory=session_factory)
    service.ensure_admin("admin", "correct-password")
    token = service.authenticate("admin", "correct-password")

    class _FakeCredentials:
        credentials = token

    recruiter = get_current_recruiter(credentials=_FakeCredentials(), auth_service=service)

    assert recruiter.username == "admin"
