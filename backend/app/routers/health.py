"""Liveness/readiness endpoints. Kept separate from business routers on
purpose — this is infrastructure, not a feature."""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}
