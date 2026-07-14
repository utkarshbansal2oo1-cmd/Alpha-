"""Tests for ConnectorCredentialStore -- Sprint 32. Runs against
in-memory SQLite, same pattern as app/auth/tests_service.py."""
from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.credentials.service import ConnectorCredentialStore
from app.database import Base
from app.models.connector_credential import ConnectorCredentialRow


@pytest.fixture(autouse=True)
def _encryption_key(monkeypatch):
    monkeypatch.setattr("app.credentials.crypto.settings.APP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    yield


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture
def store(session_factory):
    return ConnectorCredentialStore(session_factory=session_factory)


def test_get_secret_returns_none_when_unset(store):
    assert store.get_secret("github") is None


def test_set_then_get_roundtrips(store):
    store.set_secret("github", "ghp_fake_token")
    assert store.get_secret("github") == "ghp_fake_token"


def test_secret_is_encrypted_at_rest(store, session_factory):
    store.set_secret("github", "ghp_fake_token")

    with session_factory() as db:
        row = db.query(ConnectorCredentialRow).filter_by(provider="github").one()
        assert row.encrypted_secret != "ghp_fake_token"


def test_set_secret_overwrites_existing_row_not_duplicates(store, session_factory):
    store.set_secret("github", "first-token")
    store.set_secret("github", "second-token")

    with session_factory() as db:
        rows = db.query(ConnectorCredentialRow).filter_by(provider="github").all()
        assert len(rows) == 1
    assert store.get_secret("github") == "second-token"


def test_different_providers_are_independent(store):
    store.set_secret("github", "github-token")
    store.set_secret("greenhouse", "greenhouse-key")

    assert store.get_secret("github") == "github-token"
    assert store.get_secret("greenhouse") == "greenhouse-key"


def test_get_secret_survives_across_store_instances(session_factory):
    """The whole point of this sprint: a fresh ConnectorCredentialStore
    (simulating a process restart) must still see a previously-set secret."""
    store1 = ConnectorCredentialStore(session_factory=session_factory)
    store1.set_secret("github", "ghp_persisted")

    store2 = ConnectorCredentialStore(session_factory=session_factory)
    assert store2.get_secret("github") == "ghp_persisted"


def test_is_configured(store):
    assert store.is_configured("github") is False
    store.set_secret("github", "ghp_fake_token")
    assert store.is_configured("github") is True


def test_cache_avoids_second_db_hit(store, session_factory, monkeypatch):
    store.set_secret("github", "ghp_fake_token")
    store.get_secret("github")  # warms cache (set_secret already populates it too)

    original_factory = store._session_factory
    calls = {"count": 0}

    def counting_factory():
        calls["count"] += 1
        return original_factory()

    store._session_factory = counting_factory
    store.get_secret("github")
    assert calls["count"] == 0  # served from cache, no DB call
