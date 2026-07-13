import uuid

from fastapi import APIRouter

from app.schemas import SourceCreate, SourceOut
from app.services.connectors.registry import get_active_connectors

router = APIRouter(prefix="/api/v1", tags=["sources"])

# In MVP, sources are code-registered connectors. This endpoint reflects them
# and stubs registration of new ones (real version would persist to `sources` table).
_REGISTERED: list = []


@router.get("/sources", response_model=dict)
def list_sources() -> dict:
    active = [
        SourceOut(id=c.name, name=c.name, type="connector", is_active=True)
        for c in get_active_connectors()
    ]
    return {"sources": active + _REGISTERED}


@router.post("/sources", response_model=SourceOut, status_code=201)
def create_source(payload: SourceCreate) -> SourceOut:
    source = SourceOut(id=str(uuid.uuid4()), name=payload.name, type=payload.type, is_active=True)
    _REGISTERED.append(source)
    return source
