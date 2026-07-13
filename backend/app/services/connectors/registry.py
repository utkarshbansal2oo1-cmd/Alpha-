"""Registry of active source connectors.

To add a real source (Naukri partnership, ATS integration, customer resume
upload), implement SourceConnector in a new file and add one line here.
The rest of the system never needs to know.
"""
from __future__ import annotations

from typing import List

from .base import SourceConnector
from .mock_connector import MockConnector

_ACTIVE_CONNECTORS: List[SourceConnector] = [
    MockConnector(),
    # NaukriConnector(),        # <- future: add and nothing else changes
    # ATSConnector(config=...), # <- future
]


def get_active_connectors() -> List[SourceConnector]:
    return _ACTIVE_CONNECTORS
