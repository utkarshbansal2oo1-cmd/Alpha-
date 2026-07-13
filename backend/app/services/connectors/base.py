"""The one contract every candidate data source must satisfy.

Add LinkedIn, Naukri, iimjobs, an ATS webhook, or a customer resume-upload
parser by writing a class that implements `fetch()`. Nothing else in the
system (matching engine, API, schema, frontend) needs to change.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RawCandidate:
    """Whatever a connector can scrape/pull, normalized to this common shape
    before it touches the rest of the system."""
    external_id: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    total_experience_yrs: Optional[float] = None
    skills: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    resume_url: Optional[str] = None


class SourceConnector(ABC):
    """Every data source — job board, ATS, resume upload, future partnership —
    implements this interface."""

    name: str

    @abstractmethod
    def fetch(self, requirement) -> List[RawCandidate]:
        """Return raw candidates plausibly matching the requirement.
        Broad recall is fine here; precision is the matching engine's job."""
        raise NotImplementedError
