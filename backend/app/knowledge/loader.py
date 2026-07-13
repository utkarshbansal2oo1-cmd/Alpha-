"""Reads taxonomy JSON files from disk, validates them, and returns
strongly typed Taxonomy objects. Per docs/KNOWLEDGE_ENGINE.md section 6:

  - Source of truth is JSON files in git.
  - Every file is validated on load: JSON Schema (taxonomies/_schema/),
    structural typing (Pydantic), and cross-reference integrity (duplicate
    ids, dangling target_id).
  - A failed validation hard-fails application startup (raises, does not
    return a partially-loaded result).
  - Loading happens once; this module has no notion of "reload per request".

Cross-reference validation (duplicate ids, dangling expansion targets) is
deliberately done here, across ALL loaded taxonomies together, rather than
per-file -- an expansion pointing across taxonomy types is not expected in
the current seed data, but the loader does not assume that structurally: it
resolves target_id against the full set of loaded entries from every
taxonomy, so cross-taxonomy expansion (flagged as a possibility in
KNOWLEDGE_ENGINE.md section 4.1) is not accidentally broken by an overly
narrow validation rule.
"""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from app.knowledge.exceptions import TaxonomyValidationError
from app.knowledge.models import Taxonomy, TaxonomyEntry, ValidationIssue, ValidationResult

DEFAULT_TAXONOMY_FILES = [
    "roles.json",
    "skills.json",
    "industries.json",
    "company_categories.json",
]

_SCHEMA_FILENAME_BY_TYPE = {
    "role": "role.schema.json",
    "skill": "skill.schema.json",
    "industry": "industry.schema.json",
    "company_category": "company_category.schema.json",
}


def _taxonomies_dir() -> Path:
    return Path(__file__).resolve().parent / "taxonomies"


def _schema_dir(taxonomies_dir: Path) -> Path:
    return taxonomies_dir / "_schema"


def _load_json_schema(taxonomies_dir: Path, taxonomy_type: str) -> dict | None:
    filename = _SCHEMA_FILENAME_BY_TYPE.get(taxonomy_type)
    if filename is None:
        return None
    schema_path = _schema_dir(taxonomies_dir) / filename
    if not schema_path.exists():
        return None
    return json.loads(schema_path.read_text(encoding="utf-8"))


def load_taxonomy_file(
    path: Path, taxonomies_dir: Path | None = None
) -> tuple[Taxonomy | None, list[ValidationIssue]]:
    """Parse and validate a single taxonomy JSON file: JSON Schema first,
    then Pydantic structural validation. Returns (Taxonomy, []) on success,
    or (None, issues) on failure -- never raises here, so the caller can
    accumulate issues across every file before deciding whether to
    hard-fail.
    """
    directory = taxonomies_dir or path.parent

    if not path.exists():
        return None, [ValidationIssue(message=f"Taxonomy file not found: {path}")]

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return None, [ValidationIssue(message=f"{path.name}: invalid JSON ({e})")]

    # --- JSON Schema validation (taxonomies/_schema/) -----------------
    taxonomy_type = raw.get("taxonomy_type") if isinstance(raw, dict) else None
    schema = _load_json_schema(directory, taxonomy_type) if taxonomy_type else None
    if schema is not None:
        validator = jsonschema.Draft7Validator(schema)
        schema_errors = sorted(validator.iter_errors(raw), key=lambda e: list(e.path))
        if schema_errors:
            issues = [
                ValidationIssue(
                    taxonomy_type=taxonomy_type,
                    message=f"{path.name}: JSON Schema violation at "
                    f"'{'/'.join(str(p) for p in err.path) or '<root>'}': {err.message}",
                )
                for err in schema_errors
            ]
            return None, issues

    # --- Pydantic structural validation --------------------------------
    try:
        taxonomy = Taxonomy.model_validate(raw)
    except Exception as e:  # pydantic.ValidationError, deliberately broad here
        return None, [ValidationIssue(message=f"{path.name}: schema validation failed ({e})")]

    return taxonomy, []


def validate_cross_references(taxonomies: list[Taxonomy]) -> ValidationResult:
    """Checks that hold across the whole loaded set, not one file at a time:
      - every entry id is globally unique (across all taxonomies)
      - every expansion.target_id resolves to some loaded entry
    """
    issues: list[ValidationIssue] = []

    all_ids: dict[str, str] = {}  # id -> taxonomy_type, to report duplicates with context
    for tax in taxonomies:
        for entry in tax.entries:
            if entry.id in all_ids:
                issues.append(
                    ValidationIssue(
                        taxonomy_type=tax.taxonomy_type.value,
                        entry_id=entry.id,
                        message=f"Duplicate id '{entry.id}' also defined in taxonomy "
                        f"'{all_ids[entry.id]}'",
                    )
                )
            else:
                all_ids[entry.id] = tax.taxonomy_type.value

    known_ids = set(all_ids.keys())
    for tax in taxonomies:
        for entry in tax.entries:
            for expansion in entry.expansions:
                if expansion.target_id not in known_ids:
                    issues.append(
                        ValidationIssue(
                            taxonomy_type=tax.taxonomy_type.value,
                            entry_id=entry.id,
                            message=f"Expansion target_id '{expansion.target_id}' does not "
                            f"resolve to any loaded taxonomy entry",
                        )
                    )

    return ValidationResult(is_valid=not issues, issues=issues)


def load_all_taxonomies(
    taxonomies_dir: Path | None = None,
    filenames: list[str] | None = None,
) -> list[Taxonomy]:
    """Loads every taxonomy file, validates each individually (JSON Schema +
    Pydantic) and then cross-validates the whole set. Raises
    TaxonomyValidationError (and does NOT return a partial result) if
    anything is invalid -- this is the "hard-fail application startup"
    behavior required by the design doc.
    """
    directory = taxonomies_dir or _taxonomies_dir()
    files = filenames or DEFAULT_TAXONOMY_FILES

    taxonomies: list[Taxonomy] = []
    issues: list[ValidationIssue] = []

    for filename in files:
        taxonomy, file_issues = load_taxonomy_file(directory / filename, taxonomies_dir=directory)
        issues.extend(file_issues)
        if taxonomy is not None:
            taxonomies.append(taxonomy)

    if issues:
        raise TaxonomyValidationError(
            f"Taxonomy loading failed with {len(issues)} issue(s)",
            result=ValidationResult(is_valid=False, issues=issues),
        )

    cross_ref_result = validate_cross_references(taxonomies)
    if not cross_ref_result.is_valid:
        raise TaxonomyValidationError(
            f"Taxonomy cross-reference validation failed with "
            f"{len(cross_ref_result.issues)} issue(s)",
            result=cross_ref_result,
        )

    return taxonomies
