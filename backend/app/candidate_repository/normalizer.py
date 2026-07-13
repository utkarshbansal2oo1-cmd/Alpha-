"""Maps the browser extension's permissive CandidateImportRequest into the
strict internal Candidate model.

This is the one place extraction-layer messiness (missing fields, an
extension-generated placeholder id, no source classification yet) gets
resolved into the shape every other part of AlphaSource already expects.
See docs/BROWSER_EXTENSION_ARCHITECTURE.md Phase 4.
"""
from __future__ import annotations

import uuid

from app.candidate_repository.import_schemas import CandidateImportRequest
from app.candidate_repository.models import CaptureSource, Candidate, EducationEntry

# Candidates captured with no role information still need to satisfy the
# existing, unchanged `Candidate.role` required field (role is used by
# search()'s role_matches check) -- this placeholder makes that visible
# rather than silently defaulting to an empty string that would look like
# a data-entry mistake.
_UNKNOWN_ROLE_PLACEHOLDER = "Unknown"
_UNKNOWN_LOCATION_PLACEHOLDER = "Unknown"
_UNKNOWN_COMPANY_PLACEHOLDER = "Unknown"


def normalize_import(payload: CandidateImportRequest) -> Candidate:
    """Converts a raw extension capture into a Candidate ready for
    `CandidateRepository.upsert()`. The returned Candidate always has a
    freshly-generated id -- `upsert()` is responsible for discarding it and
    keeping the existing id if this turns out to be a merge, per its own
    contract.
    """
    capture_source = CaptureSource(
        source_type=payload.source_type,
        source_url=payload.source_url,
        captured_by=payload.captured_by,
        # Confidence reflects that this is a single, unverified web capture,
        # not multi-source corroborated evidence -- see
        # docs/EVIDENCE_GRAPH_ARCHITECTURE.md's confidence-by-source-type
        # table for why a single browser capture sits in the middle of the
        # confidence range rather than at either extreme.
        confidence=0.7,
    )

    education = [
        EducationEntry(degree=e.degree, institution=e.institution, year=e.year)
        for e in payload.education
    ]

    return Candidate(
        id=str(uuid.uuid4()),
        name=payload.name.strip(),
        role=(payload.role or payload.headline or _UNKNOWN_ROLE_PLACEHOLDER).strip(),
        experience=payload.experience_years or 0,
        skills=list(payload.skills),
        location=(payload.location or _UNKNOWN_LOCATION_PLACEHOLDER).strip(),
        current_company=(payload.current_company or _UNKNOWN_COMPANY_PLACEHOLDER).strip(),
        source=payload.source_type,
        headline=payload.headline,
        summary=payload.summary or _build_fallback_summary(payload),
        education=education,
        public_profile_url=payload.public_profile_url,
        resume_link=payload.resume_link,
        capture_sources=[capture_source],
        version=1,
        # --- Sprint 20D: GitHub Candidate Intelligence Engine -----------
        # Additive passthrough only -- these fields are None/empty on
        # every payload except ones the GitHub connector builds via
        # app/integrations/github/intelligence/enrichment.py, so every
        # existing caller (browser extension, Greenhouse) is unaffected.
        github_quality_score=payload.github_quality_score,
        github_activity_score=payload.github_activity_score,
        github_repositories_analyzed=payload.github_repositories_analyzed,
        github_languages=list(payload.github_languages),
        github_topics=list(payload.github_topics),
        github_organizations=list(payload.github_organizations),
        github_skills_inferred=list(payload.github_skills_inferred),
        github_last_activity=payload.github_last_activity,
        github_profile_completeness=payload.github_profile_completeness,
    )


def _build_fallback_summary(payload: CandidateImportRequest) -> str | None:
    """Templated, deterministic one-line summary from captured fields --
    deliberately NOT LLM-generated. Sprint 12 explicitly scopes AI-generated
    summaries to the existing Candidate Intelligence pipeline being invoked
    AFTER import (Phase 7), not duplicated here in the normalizer; this
    fallback only covers the case where the page had no summary/bio text at
    all, so the candidate record isn't left with a blank summary before
    that pipeline runs.
    """
    if not payload.role and not payload.current_company:
        return None
    role_part = payload.role or payload.headline or "professional"
    company_part = f" at {payload.current_company}" if payload.current_company else ""
    return f"{role_part}{company_part}, captured via browser extension."
