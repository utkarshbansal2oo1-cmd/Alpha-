"""Greenhouse connector configuration. Deliberately minimal for this POC:
one API key + base URL, held in memory (not persisted across restarts).
A real deployment would store this per-organization in the database, but
the storage mechanism is not the point of this sprint -- the connector
logic behind it is.

Greenhouse's Harvest API (https://developers.greenhouse.io/harvest.html)
authenticates with HTTP Basic Auth: the API key as the username, an empty
password. There is no OAuth flow for Harvest API keys -- an org generates
one from their Greenhouse admin settings and gives it to whatever
integration needs it. That's a real, documented fact about how this API
works, not a simplification made for this POC.
"""
from __future__ import annotations

from pydantic import BaseModel

DEFAULT_BASE_URL = "https://harvest.greenhouse.io/v1"


class GreenhouseConfig(BaseModel):
    api_key: str
    base_url: str = DEFAULT_BASE_URL


class GreenhouseConfigError(Exception):
    """Raised when a Greenhouse-dependent operation is attempted before
    the connector has been configured (see POST /integrations/greenhouse/configure)."""


class GreenhouseConfigStore:
    """In-memory holder for the active GreenhouseConfig. Not thread-safe
    beyond Python's GIL-level guarantees -- fine for this POC's single
    -process deployment; a real multi-worker deployment would move this
    into the database alongside per-organization settings."""

    def __init__(self):
        self._config: GreenhouseConfig | None = None

    def set(self, config: GreenhouseConfig) -> None:
        self._config = config

    def get(self) -> GreenhouseConfig:
        if self._config is None:
            raise GreenhouseConfigError(
                "Greenhouse is not configured yet -- call POST /integrations/greenhouse/configure with an api_key first."
            )
        return self._config

    def is_configured(self) -> bool:
        return self._config is not None


_store = GreenhouseConfigStore()


def get_greenhouse_config_store() -> GreenhouseConfigStore:
    return _store
