"""Sprint 20A: the Connector Management endpoints (Module 5).

New, additive router -- does not touch any existing endpoint, including
POST /api/search/smart or /integrations/greenhouse/*. Backed by the new
ManagedConnectorRegistry (app/discovery/connector_registry_v2.py), whose
connectors are loaded dynamically (Module 3), never hardcoded here.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.discovery.connector_registry_v2 import ManagedConnectorRegistry, get_managed_connector_registry

router = APIRouter(prefix="/connectors", tags=["connectors"])


class ConnectorInfo(BaseModel):
    name: str
    version: str
    capabilities: list[str]
    requires_auth: bool
    supported_roles: list[str]
    enabled: bool
    priority: int
    status: str
    health: dict


class ConfigureRequest(BaseModel):
    name: str
    config: dict = {}


class ConnectorNameRequest(BaseModel):
    name: str


def _to_info(connector) -> ConnectorInfo:
    meta = connector.metadata
    return ConnectorInfo(
        name=meta.name,
        version=meta.version,
        capabilities=meta.capabilities,
        requires_auth=meta.requires_auth,
        supported_roles=meta.supported_roles,
        enabled=meta.enabled,
        priority=connector.priority(),
        status=connector.status(),
        health=connector.health(),
    )


@router.get("", response_model=list[ConnectorInfo])
def list_connectors(
    registry: ManagedConnectorRegistry = Depends(get_managed_connector_registry),
) -> list[ConnectorInfo]:
    return [_to_info(c) for c in registry.list()]


@router.post("/configure", response_model=ConnectorInfo)
def configure_connector(
    payload: ConfigureRequest,
    registry: ManagedConnectorRegistry = Depends(get_managed_connector_registry),
) -> ConnectorInfo:
    try:
        connector = registry.configure(payload.name, payload.config)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return _to_info(connector)


@router.post("/enable", response_model=ConnectorInfo)
def enable_connector(
    payload: ConnectorNameRequest,
    registry: ManagedConnectorRegistry = Depends(get_managed_connector_registry),
) -> ConnectorInfo:
    try:
        connector = registry.enable(payload.name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return _to_info(connector)


@router.post("/disable", response_model=ConnectorInfo)
def disable_connector(
    payload: ConnectorNameRequest,
    registry: ManagedConnectorRegistry = Depends(get_managed_connector_registry),
) -> ConnectorInfo:
    try:
        connector = registry.disable(payload.name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return _to_info(connector)
