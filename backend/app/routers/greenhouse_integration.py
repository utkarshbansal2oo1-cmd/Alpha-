"""Greenhouse ATS connector endpoints (Sprint 15) -- the first real
"Orchestrate" pillar connector (see docs/PRODUCT_PILLARS.md). Registered
additively in main.py; nothing here changes /api/search,
/candidate/import, or any other existing route.

  POST /integrations/greenhouse/configure     -- set the API key (+ base
                                                  URL override, for
                                                  pointing at a real
                                                  Greenhouse account)
  POST /integrations/greenhouse/sync          -- run a pull sync now
  GET  /integrations/greenhouse/sync-status   -- most recent sync's
                                                  summary (or full history)
  POST /integrations/greenhouse/push/{id}     -- push one AlphaSource
                                                  candidate into Greenhouse

Every write here happens through the SAME CandidateRepository (via
sync.py) the browser extension and seed data already share -- this router
does not talk to the repository directly.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.candidate_repository.interfaces import CandidateRepository
from app.candidate_repository.repository import get_candidate_repository
from app.integrations.greenhouse.client import GreenhouseAPIError, GreenhouseClient
from app.integrations.greenhouse.config import (
    GreenhouseConfig,
    GreenhouseConfigError,
    GreenhouseConfigStore,
    get_greenhouse_config_store,
)
from app.integrations.greenhouse.models import SyncRun
from app.integrations.greenhouse.sync import push_candidate, pull_sync
from app.integrations.greenhouse.sync_store import SyncRunStore, get_sync_run_store

router = APIRouter(prefix="/integrations/greenhouse", tags=["greenhouse"])


class ConfigureRequest(BaseModel):
    api_key: str = Field(min_length=1)
    base_url: str | None = Field(default=None, description="Override for testing/self-hosted setups -- defaults to the real Greenhouse Harvest API")


class ConfigureResponse(BaseModel):
    configured: bool
    base_url: str


class PushRequest(BaseModel):
    note: str | None = Field(default=None, description="Optional shortlist reasoning attached to the candidate in Greenhouse")


class PushResponse(BaseModel):
    greenhouse_candidate_id: str
    note_added: bool


def _build_client(config_store: GreenhouseConfigStore) -> GreenhouseClient:
    try:
        config = config_store.get()
    except GreenhouseConfigError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return GreenhouseClient(config)


@router.post("/configure", response_model=ConfigureResponse)
def configure_greenhouse(
    payload: ConfigureRequest,
    config_store: GreenhouseConfigStore = Depends(get_greenhouse_config_store),
) -> ConfigureResponse:
    config = GreenhouseConfig(api_key=payload.api_key, base_url=payload.base_url or GreenhouseConfig.model_fields["base_url"].default)
    config_store.set(config)
    return ConfigureResponse(configured=True, base_url=config.base_url)


@router.post("/sync", response_model=SyncRun)
def trigger_sync(
    config_store: GreenhouseConfigStore = Depends(get_greenhouse_config_store),
    repository: CandidateRepository = Depends(get_candidate_repository),
    sync_store: SyncRunStore = Depends(get_sync_run_store),
) -> SyncRun:
    client = _build_client(config_store)
    try:
        run = pull_sync(client, repository)
    finally:
        client.close()
    sync_store.record(run)
    return run


@router.get("/sync-status", response_model=list[SyncRun])
def get_sync_status(
    sync_store: SyncRunStore = Depends(get_sync_run_store),
) -> list[SyncRun]:
    # Newest first -- an admin checking sync health cares about the most
    # recent run before older history.
    return list(reversed(sync_store.all()))


@router.post("/push/{candidate_id}", response_model=PushResponse)
def push_to_greenhouse(
    candidate_id: str,
    payload: PushRequest,
    config_store: GreenhouseConfigStore = Depends(get_greenhouse_config_store),
    repository: CandidateRepository = Depends(get_candidate_repository),
) -> PushResponse:
    candidate = repository.get_by_id(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"Candidate not found: {candidate_id}")

    client = _build_client(config_store)
    try:
        created = push_candidate(client, candidate, note=payload.note)
    except GreenhouseAPIError as e:
        raise HTTPException(status_code=502, detail=f"Greenhouse push failed: {e}") from e
    finally:
        client.close()

    return PushResponse(greenhouse_candidate_id=str(created.get("id", "")), note_added=bool(payload.note))
