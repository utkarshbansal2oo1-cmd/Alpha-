"""Request/response contracts for the browser extension's candidate-capture
flow (POST /candidate/import). Deliberately a SEPARATE, permissive shape
from the internal `Candidate` model in models.py: this is the raw,
best-effort extraction payload the browser extension's content script sends
-- almost every field is optional because a real webpage may not expose
every field, and the extension must never block a capture just because one
field couldn't be found. Normalizing this permissive shape into the strict
internal `Candidate` model is the job of `normalizer.py`, not this file.

See docs/BROWSER_EXTENSION_ARCHITECTURE.md Phase 4 (Normalization Layer).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ImportEducationEntry(BaseModel):
    """One education entry as extracted from the page -- all fields optional,
    since extracted profile pages vary widely in what they expose."""

    degree: str | None = None
    institution: str | None = None
    year: str | None = None


class CandidateImportRequest(BaseModel):
    """The payload the browser extension's background worker POSTs to
    /candidate/import after the recruiter clicks "Add to AlphaSource" on a
    detected candidate profile page.

    Only `name` is required -- every other field is optional and defaults to
    None/empty, matching the extraction layer's contract (Phase 3): if a
    field isn't found on the page, it is omitted rather than guessed at.
    """

    name: str = Field(min_length=1, description="Candidate's full name -- the one field extraction must find to consider a page a candidate profile")
    role: str | None = None
    headline: str | None = None
    current_company: str | None = None
    experience_years: float | None = Field(default=None, ge=0)
    skills: list[str] = Field(default_factory=list)
    location: str | None = None
    summary: str | None = None
    education: list[ImportEducationEntry] = Field(default_factory=list)
    public_profile_url: str | None = None
    resume_link: str | None = None

    # --- capture provenance metadata, set by the background worker --------
    source_type: str = Field(default="browser_extension", description="Always 'browser_extension' for this endpoint in the current POC; kept as a field rather than hardcoded so future capture channels (CSV import, ATS webhook) can reuse this same schema.")
    source_url: str | None = Field(default=None, description="The URL of the page the recruiter captured this candidate from")
    captured_by: str | None = Field(default=None, description="Recruiter identity string, self-reported via the extension's options page -- not authenticated in this POC")

    # --- Sprint 20D: GitHub Candidate Intelligence Engine -------------------
    # All optional, all additive, default to None/empty so every existing
    # caller (browser extension, Greenhouse, and every pre-Sprint-20D test)
    # is unaffected. Populated only by the GitHub connector
    # (app/discovery/connectors/github_connector.py) via
    # app/integrations/github/intelligence/enrichment.py -- see that
    # package for how each value is computed and its "never hallucinate"
    # evidence requirement.
    github_quality_score: float | None = Field(default=None, ge=0.0, le=100.0)
    github_activity_score: float | None = Field(default=None, ge=0.0, le=100.0)
    github_repositories_analyzed: int | None = None
    github_languages: list[str] = Field(default_factory=list)
    github_topics: list[str] = Field(default_factory=list)
    github_organizations: list[str] = Field(default_factory=list)
    github_skills_inferred: list[str] = Field(default_factory=list)
    github_last_activity: datetime | None = None
    github_profile_completeness: float | None = Field(default=None, ge=0.0, le=100.0)


class CandidateImportResponse(BaseModel):
    """What /candidate/import returns -- enough for the extension's popup to
    show a success notification and, if the recruiter wants, a link to the
    candidate in AlphaSource."""

    candidate_id: str
    created: bool = Field(description="True if this created a new candidate record, False if it merged into an existing one")
    version: int
