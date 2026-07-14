"""Tests for AuthService -- Sprint 30. Runs against in-memory SQLite, same
pattern as tests_postgres_repository.py."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import AuthService
from app.database import Base


@pytest.fixture
def session_factory():
    # StaticPool -- a bare sqlite:///:memory: engine hands out a fresh,
    # empty in-memory database per connection by default, so create_all()
    # and later session_factory() calls would silently talk to different
    # databases without this.
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture
def service(session_factory):
    return AuthService(session_factory=session_factory)


def test_ensure_admin_creates_recruiter(service):
    service.ensure_admin("admin", "s3cret-password")
    token = service.authenticate("admin", "s3cret-password")
    assert token is not None


def test_ensure_admin_is_idempotent(service):
    service.ensure_admin("admin", "first-password")
    service.ensure_admin("someone-else", "second-password")  # should be a no-op -- one already exists

    assert service.authenticate("admin", "first-password") is not None
    assert service.authenticate("someone-else", "second-password") is None


def test_ensure_admin_does_nothing_without_credentials(service):
    service.ensure_admin("", "")
    assert service.authenticate("admin", "anything") is None


def test_authenticate_rejects_wrong_password(service):
    service.ensure_admin("admin", "correct-password")
    assert service.authenticate("admin", "wrong-password") is None


def test_authenticate_rejects_unknown_username(service):
    service.ensure_admin("admin", "correct-password")
    assert service.authenticate("nobody", "correct-password") is None


def test_get_recruiter_for_token_returns_recruiter(service):
    service.ensure_admin("admin", "correct-password")
    token = service.authenticate("admin", "correct-password")

    recruiter = service.get_recruiter_for_token(token)

    assert recruiter is not None
    assert recruiter.username == "admin"


def test_get_recruiter_for_token_rejects_unknown_token(service):
    assert service.get_recruiter_for_token("not-a-real-token") is None


def test_get_recruiter_for_token_rejects_expired_session(session_factory):
    from datetime import datetime, timedelta, timezone

    service = AuthService(session_factory=session_factory)
    service.ensure_admin("admin", "correct-password")
    token = service.authenticate("admin", "correct-password")

    # Manually expire the session that was just issued.
    from app.models.recruiter import SessionRow

    with session_factory() as db:
        session_row = db.get(SessionRow, token)
        session_row.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

    assert service.get_recruiter_for_token(token) is None
