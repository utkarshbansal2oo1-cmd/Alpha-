"""Tests for POST /auth/login -- Sprint 30."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_auth_service
from app.auth.service import AuthService
from app.database import Base
from app.main import app


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    service = AuthService(session_factory=session_factory)
    service.ensure_admin("admin", "correct-password")

    app.dependency_overrides[get_auth_service] = lambda: service
    yield TestClient(app)
    app.dependency_overrides.pop(get_auth_service, None)


def test_login_with_correct_credentials_returns_token(client):
    res = client.post("/auth/login", json={"username": "admin", "password": "correct-password"})

    assert res.status_code == 200
    body = res.json()
    assert body["username"] == "admin"
    assert len(body["token"]) > 20


def test_login_with_wrong_password_returns_401(client):
    res = client.post("/auth/login", json={"username": "admin", "password": "wrong-password"})
    assert res.status_code == 401


def test_login_with_unknown_username_returns_401(client):
    res = client.post("/auth/login", json={"username": "nobody", "password": "anything"})
    assert res.status_code == 401
