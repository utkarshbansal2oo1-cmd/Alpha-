"""Typed contracts for the Candidate Repository.

Candidate is the unified, source-agnostic candidate shape every repository
implementation (in-memory today, a real database or ATS/connector-backed
repository later) must return -- callers of the repository interface never
see LinkedIn/Naukri/ATS-specific fields, only this one shape, per the
source-agnostic principle in docs/ARCHITECTURE.md.

Sprint 12 addition: the fields below `source` are all optional, additive,
and default to None/empty so every existing caller (search_pipeline.py's
response model, the 8-record seed data, all 110 pre-Sprint-12 tests)
continues to work unchanged -- nothing about the original required fields
(id, name, role, experience, skills, location, current_company, source)
was touched. These new fields exist to support the browser extension's
"Add to AlphaSource" capture flow (docs/BROWSER_EXTENSION_ARCHITECTURE.md):
richer profile data, and the provenance/confidence metadata every captured
Candidate now carries per the approved Evidence Lake philosophy
(docs/EVIDENCE_GRAPH_ARCHITECTURE.md) -- simplified for this POC to live
directly on the Candidate record rather than a separate evidence store,
since this sprint explicitly does not implement the Evidence Lake itself.

Sprint 14 addition: the Candidate Intelligence Lifecycle
(docs/CANDIDATE_INTELLIGENCE_LIFECYCLE.md) -- health scoring, per-section
confidence, evidence history, and version snapshots. All new fields below
are additive/optional with safe defaults, so every pre-Sprint-14 caller
(search_pipeline.py, the 8-record seed data, all 127 pre-Sprint-14 tests)
is unaffected. These fields are populated by
app/candidate_intelligence/lifecycle.py, called from
InMemoryCandidateRepository.upsert() and its initial seed-data bootstrap --
never from search()/all(), which remain byte-for-byte unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class EducationEntry(BaseModel):
    """One education record -- optional, only present for candidates with
    richer captured data (e.g. via the browser extension)."""

    degree: str | None = None
    institution: str | None = None
    year: str | None = None


class CaptureSource(BaseModel):
    """One capture event contributing to this candidate record. A candidate
    captured twice (e.g. once from a portfolio site, once from a career
    page) accumulates multiple CaptureSource entries rather than losing
    the earlier one -- mirrors the Evidence Lake's "never overwrite,
    always append" principle at a POC-appropriate scale (see
    docs/BROWSER_EXTENSION_ARCHITECTURE.md's Phase 6 dedup/merge strategy).
    """

    source_type: str = Field(description="e.g. 'browser_extension', 'seed_data', 'csv_import'")
    source_url: str | None = None
    captured_by: str | None = Field(default=None, description="Recruiter identity string, self-reported, not authenticated in this POC")
    capture_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


# --- Sprint 14: Candidate Intelligence Lifecycle models ---------------------

# The fixed section vocabulary the Health/Confidence engines score against.
# Kept as plain strings (not a Python enum) so the value round-trips through
# JSON/Pydantic without a custom encoder -- see
# app/candidate_intelligence/sections.py for the canonical list and the
# field-to-section mapping every engine shares.
SectionName = str


class EvidenceEvent(BaseModel):
    """One field-level change to a candidate profile -- the atomic unit of
    the Evidence Timeline. Answers, for any change: what changed, when,
    why, from which source, and at what confidence. Append-only: a
    candidate's `evidence_history` is never rewritten, only appended to,
    mirroring the same principle CaptureSource already follows.
    """

    event_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    field: str = Field(description="Dotted field path, e.g. 'current_company' or 'skills'")
    section: str = Field(description="Which profile section this field belongs to")
    old_value: str | None = Field(default=None, description="Stringified previous value, or None if the field was previously empty")
    new_value: str | None = Field(default=None, description="Stringified new value, or None if the field was cleared")
    change_type: str = Field(description="'created' | 'updated' | 'corroborated' | 'unchanged'")
    source_type: str
    source_url: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(description="Human-readable explanation, e.g. 'New capture merged from browser_extension' or 'Enrichment plan fulfilled from csv_import'")


class SectionScore(BaseModel):
    """Confidence + completeness for one profile section."""

    section: str
    confidence: float = Field(ge=0.0, le=1.0)
    complete: bool
    missing_fields: list[str] = Field(default_factory=list)
    evidence_count: int = Field(default=0, description="How many evidence events have touched this section")


class HealthScore(BaseModel):
    """The Candidate Health Engine's output -- an overall weighted score
    plus the per-section breakdown it was computed from."""

    overall: float = Field(ge=0.0, le=100.0)
    sections: list[SectionScore] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EnrichmentPlanItem(BaseModel):
    """One actionable gap the Enrichment Planner identified."""

    field: str
    section: str
    priority: float = Field(ge=0.0, le=1.0, description="Higher = more valuable to fill next")
    candidate_source_types: list[str] = Field(
        default_factory=list,
        description="Source types (from the pluggable enrichment source registry) known to be able to supply this field -- empty if no registered source can help yet.",
    )
    reason: str


class EnrichmentPlan(BaseModel):
    """The Enrichment Planner's output for one candidate."""

    candidate_id: str
    items: list[EnrichmentPlanItem] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CandidateSnapshot(BaseModel):
    """A full point-in-time snapshot of a candidate's field values, taken
    by the Profile Versioner on every meaningful change. `fields` is a
    plain dict rather than a nested Candidate to avoid recursive/self
    -referential snapshot bloat (a snapshot does not itself carry its own
    version_history/evidence_history)."""

    version: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str
    fields: dict = Field(default_factory=dict)


class Candidate(BaseModel):
    """One candidate record, in the unified shape every repository returns
    regardless of where the data originally came from.
    """

    id: str
    name: str
    role: str
    experience: float = Field(ge=0, description="Total years of experience")
    skills: list[str] = Field(default_factory=list)
    location: str
    current_company: str
    source: str = Field(
        description="Which data source this candidate record came from "
        "(e.g. 'linkedin', 'naukri', 'seed_data') -- retained for traceability, "
        "never used to change how the candidate is retrieved or scored."
    )

    # --- Sprint 12 additions: all optional, all additive ---------------

    headline: str | None = Field(default=None, description="Professional headline/tagline, as captured")
    summary: str | None = Field(default=None, description="A short profile summary -- templated from captured fields in this POC, not LLM-generated (see docs/BROWSER_EXTENSION_ARCHITECTURE.md Phase 7 for why)")
    education: list[EducationEntry] = Field(default_factory=list)
    public_profile_url: str | None = None
    resume_link: str | None = None
    capture_sources: list[CaptureSource] = Field(default_factory=list)
    version: int = Field(default=1, description="Incremented on every merge -- see Phase 6 dedup/merge strategy")

    # --- Sprint 14 additions: all optional, all additive ---------------

    health_score: float | None = Field(default=None, description="Most recently computed overall health score (0-100), or None if never computed")
    section_confidence: dict[str, float] = Field(default_factory=dict, description="section name -> confidence (0-1), maintained by the Confidence Engine")
    evidence_history: list[EvidenceEvent] = Field(default_factory=list, description="Append-only field-level change log -- the Evidence Timeline")
    version_history: list[CandidateSnapshot] = Field(default_factory=list, description="Append-only full-state snapshots, one per meaningful change -- Profile Versioning")

    # --- Sprint 20D additions: all optional, all additive ---------------
    # Populated only for candidates sourced via the GitHub connector (see
    # app/integrations/github/intelligence/). The Matching Engine is not
    # modified to read these this sprint -- they exist here so it CAN,
    # additively, in a future sprint, per the Sprint 20D brief's "add new
    # optional fields to Candidate metadata so Matching Engine
    # automatically benefits" instruction.
    github_quality_score: float | None = Field(default=None, description="0-100 overall GitHub signal quality score, or None for non-GitHub candidates / not yet enriched")
    github_activity_score: float | None = Field(default=None, description="0-100 recency/breadth-of-activity score derived from repo push timestamps")
    github_repositories_analyzed: int | None = None
    github_languages: list[str] = Field(default_factory=list, description="Distinct languages across the candidate's own (non-fork) repos, most-used first")
    github_topics: list[str] = Field(default_factory=list, description="Aggregated GitHub repo topics")
    github_organizations: list[str] = Field(default_factory=list, description="Public GitHub organization memberships")
    github_skills_inferred: list[str] = Field(default_factory=list, description="Skills inferred from real repo evidence (language/topic/name/description/README) -- never hallucinated")
    github_last_activity: datetime | None = Field(default=None, description="Most recent repo push timestamp across the candidate's analyzed repos")
    github_profile_completeness: float | None = Field(default=None, description="0-100 fraction of standard GitHub profile fields present (bio, company, location, blog, avatar, name)")
