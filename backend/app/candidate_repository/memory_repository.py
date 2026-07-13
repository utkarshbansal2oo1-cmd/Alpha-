"""In-memory CandidateRepository implementation, backed by a JSON seed file.

Retrieval (search()/all()) is unchanged from before Sprint 12: filters the
pool by role/skill membership against a SearchPlan's flattened
search_terms, no ranking, no scoring. Swapping this for a real
database-backed repository later means implementing the same
CandidateRepository interface, not changing any caller.

Sprint 12 adds the write path -- upsert()/find_potential_duplicate() --
supporting the browser extension's candidate capture flow (see
docs/BROWSER_EXTENSION_ARCHITECTURE.md). New candidates captured via the
extension are added to this same in-memory pool, so they become
immediately searchable through the existing, unmodified search() method --
no changes to the search pipeline were needed to make captured candidates
findable.

Sprint 14 wires the Candidate Intelligence Lifecycle
(app/candidate_intelligence/lifecycle.py) into both the initial seed load
and every upsert(), so every candidate -- seed data or captured -- carries
a health score, per-section confidence, an evidence timeline, and a
version history. search()/all() remain completely untouched.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from pydantic import ValidationError

from app.candidate_intelligence.lifecycle import apply_lifecycle
from app.candidate_repository.interfaces import CandidateRepository
from app.candidate_repository.models import Candidate
from app.search_planner.models import SearchPlan

_DEFAULT_SEED_PATH = Path(__file__).resolve().parent / "data" / "candidates.json"

# Fields the lifecycle engines treat as "the candidate's data" -- same list
# app/candidate_intelligence/evidence_timeline.py diffs against. Extracted
# here as a small helper so both _load() (seed bootstrap) and upsert()
# (real captures) build this dict the same way.
_LIFECYCLE_FIELDS = [
    "name",
    "role",
    "headline",
    "current_company",
    "experience",
    "skills",
    "location",
    "summary",
    "education",
    "public_profile_url",
    "resume_link",
]


def _lifecycle_fields(candidate: Candidate) -> dict:
    return {field: getattr(candidate, field) for field in _LIFECYCLE_FIELDS}


class CandidateSeedDataError(Exception):
    """Raised when the seed data file exists but its contents are unusable --
    either not valid JSON, or valid JSON that doesn't conform to the
    Candidate model (e.g. a record missing a required field or with the
    wrong type). Distinct from FileNotFoundError (the file simply isn't
    there): this means the file IS there but is corrupted or was hand-edited
    incorrectly.

    Added during code review: previously json.JSONDecodeError and pydantic's
    ValidationError propagated raw and unexplained from _load(), giving no
    indication of which file or which record was the problem.
    """


class InMemoryCandidateRepository(CandidateRepository):
    def __init__(self, seed_path: Path | None = None):
        self._seed_path = seed_path or _DEFAULT_SEED_PATH
        self._candidates: list[Candidate] = self._load(self._seed_path)

    @staticmethod
    def _load(seed_path: Path) -> list[Candidate]:
        if not seed_path.exists():
            raise FileNotFoundError(f"Candidate seed data file not found: {seed_path}")

        raw_text = seed_path.read_text(encoding="utf-8")
        try:
            raw = json.loads(raw_text)
        except json.JSONDecodeError as e:
            raise CandidateSeedDataError(
                f"Candidate seed data file is not valid JSON: {seed_path} ({e})"
            ) from e

        try:
            candidates = [Candidate.model_validate(item) for item in raw]
        except ValidationError as e:
            raise CandidateSeedDataError(
                f"Candidate seed data file contains a record that does not match "
                f"the Candidate schema: {seed_path} ({e})"
            ) from e

        # Sprint 14: bootstrap every seed candidate through the same
        # lifecycle path a real capture goes through, so demo/seed data
        # has a populated health score, confidence, and an initial
        # evidence/version entry too -- treated as one bootstrap "capture"
        # from the seed file itself, at a fairly high (but not perfect)
        # confidence since it's curated data, not a live web capture.
        for candidate in candidates:
            apply_lifecycle(
                existing=None,
                merged=candidate,
                incoming_fields=_lifecycle_fields(candidate),
                source_type="seed_data",
                source_url=None,
                confidence=0.9,
                reason="Initial seed data load",
            )

        return candidates

    def search(self, plan: SearchPlan) -> list[Candidate]:
        if not plan.search_terms:
            return list(self._candidates)

        normalized_terms = {term.strip().lower() for term in plan.search_terms if term.strip()}

        results: list[Candidate] = []
        for candidate in self._candidates:
            candidate_role = candidate.role.strip().lower()
            candidate_skills = {skill.strip().lower() for skill in candidate.skills}

            role_matches = candidate_role in normalized_terms
            skill_matches = bool(candidate_skills & normalized_terms)

            if role_matches or skill_matches:
                results.append(candidate)

        return results

    def all(self) -> list[Candidate]:
        return list(self._candidates)

    def get_by_id(self, candidate_id: str) -> Candidate | None:
        for candidate in self._candidates:
            if candidate.id == candidate_id:
                return candidate
        return None

    # --- Sprint 12: write path for browser-extension capture -------------

    def find_potential_duplicate(self, candidate: Candidate) -> Candidate | None:
        """Conservative, signal-based duplicate detection -- see
        docs/BROWSER_EXTENSION_ARCHITECTURE.md Phase 6. Two signals, checked
        in order of reliability:

        1. Exact `public_profile_url` match -- highest-confidence signal
           available in this POC (mirrors docs/EVIDENCE_GRAPH_ARCHITECTURE.md
           section 3.1's "GitHub URL / LinkedIn URL match: very high
           reliability").
        2. Normalized name + current_company match -- a medium-reliability
           fallback for captures that don't carry a profile URL (e.g. a
           resume-derived capture). Never used alone if a URL is available
           and doesn't match -- an explicit URL mismatch is NOT overridden
           by a name/company coincidence, since two people can share both.

        No match found -> None, and the caller creates a new Candidate.
        This is deliberately conservative per the same reasoning already
        established in the approved Evidence Graph architecture: a false
        merge is more damaging than a false separation.
        """
        if candidate.public_profile_url:
            for existing in self._candidates:
                if existing.public_profile_url == candidate.public_profile_url:
                    return existing
            # An explicit URL was provided and matched nothing -- do not
            # fall through to the weaker name/company signal, since a URL
            # match failing is itself informative (this really is a
            # different profile, or a first-time capture of this one).
            return None

        normalized_name = candidate.name.strip().lower()
        normalized_company = candidate.current_company.strip().lower()
        for existing in self._candidates:
            if (
                existing.name.strip().lower() == normalized_name
                and existing.current_company.strip().lower() == normalized_company
                and normalized_name
                and normalized_company
            ):
                return existing

        return None

    def upsert(self, candidate: Candidate) -> Candidate:
        """Creates a new Candidate, or merges into an existing one found via
        find_potential_duplicate(). Merge strategy (Phase 6):

        - Skills: union of both records' skills (never dropped, never
          duplicated).
        - Scalar fields (role, experience, location, current_company,
          headline, summary, public_profile_url, resume_link): the new
          capture's value fills in only if the existing record's value is
          missing/empty -- an existing, previously-captured value is never
          silently overwritten by a new, potentially lower-quality capture.
          This mirrors the "fill unknown values, never overwrite known
          ones" principle from Phase 4 of the extension's design.
        - Education: appended if not already present (compared by degree +
          institution, to avoid exact duplicates from repeated captures of
          the same page).
        - capture_sources: the new CaptureSource is always appended -- this
          list is a provenance trail, never overwritten, matching the
          Evidence Lake's "append, never overwrite" philosophy at this
          POC's simplified scale.
        - version: incremented by 1 on every merge.
        - id: preserved from the existing record -- callers should treat
          the returned Candidate's `id` as authoritative regardless of
          what (if anything) was in the incoming record.

        Sprint 14: after the merge itself, runs the Candidate Intelligence
        Lifecycle (diff -> confidence -> health -> version snapshot) so
        every write keeps health_score/section_confidence/evidence_history/
        version_history current. The lifecycle diff always compares against
        the PRE-merge existing record and the NEWLY SUBMITTED candidate's
        fields (not the already-merged result), so "what changed" reflects
        what this specific capture actually contributed.
        """
        existing = self.find_potential_duplicate(candidate)

        incoming_source_type = candidate.capture_sources[-1].source_type if candidate.capture_sources else candidate.source
        incoming_source_url = candidate.capture_sources[-1].source_url if candidate.capture_sources else None
        incoming_confidence = candidate.capture_sources[-1].confidence if candidate.capture_sources else 0.7

        if existing is None:
            new_candidate = candidate.model_copy(update={"id": candidate.id or str(uuid.uuid4())})
            apply_lifecycle(
                existing=None,
                merged=new_candidate,
                incoming_fields=_lifecycle_fields(candidate),
                source_type=incoming_source_type,
                source_url=incoming_source_url,
                confidence=incoming_confidence,
                reason="New candidate created via capture",
            )
            self._candidates.append(new_candidate)
            return new_candidate

        merged_skills = list(dict.fromkeys([*existing.skills, *candidate.skills]))

        merged_education = list(existing.education)
        existing_education_keys = {(e.degree, e.institution) for e in existing.education}
        for entry in candidate.education:
            if (entry.degree, entry.institution) not in existing_education_keys:
                merged_education.append(entry)

        merged = existing.model_copy(
            update={
                "role": existing.role or candidate.role,
                "experience": existing.experience or candidate.experience,
                "skills": merged_skills,
                "location": existing.location or candidate.location,
                "current_company": existing.current_company or candidate.current_company,
                "headline": existing.headline or candidate.headline,
                "summary": existing.summary or candidate.summary,
                "education": merged_education,
                "resume_link": existing.resume_link or candidate.resume_link,
                "capture_sources": [*existing.capture_sources, *candidate.capture_sources],
                "version": existing.version + 1,
            }
        )

        apply_lifecycle(
            existing=existing,
            merged=merged,
            incoming_fields=_lifecycle_fields(candidate),
            source_type=incoming_source_type,
            source_url=incoming_source_url,
            confidence=incoming_confidence,
            reason="Merged new capture into existing candidate",
        )

        index = self._candidates.index(existing)
        self._candidates[index] = merged
        return merged
