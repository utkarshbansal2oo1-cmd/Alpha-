"""Version management for taxonomies.

Per docs/KNOWLEDGE_ENGINE.md section 7:
  - Every taxonomy file carries its own independent version string.
  - Every JobRequirement (future work, not this module) should be able to
    record which taxonomy versions were active when it was produced -- this
    module exposes that as a simple version snapshot.
  - Changelog diffing between two versions of the same taxonomy should be
    possible, so taxonomy edits are reviewable in a PR the way code is.
  - Deprecation, not deletion: entries with status=deprecated stay resolvable
    (this module doesn't enforce that directly -- engine.py's lookup indices
    do -- but the diff logic here treats a status change to "deprecated" as
    its own kind of change, not a removal).

This module is deliberately pure/stateless: it takes Taxonomy objects in and
returns data out. It does not read files or hold engine state -- that's
loader.py's and engine.py's job respectively.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.knowledge.models import Taxonomy, TaxonomyEntry


@dataclass
class VersionSnapshot:
    """taxonomy_type -> version, suitable for embedding into any future
    JobRequirement's `knowledge_versions` meta field (see
    docs/KNOWLEDGE_ENGINE.md section 7.1)."""

    versions: dict[str, str] = field(default_factory=dict)


def snapshot_versions(taxonomies: list[Taxonomy]) -> VersionSnapshot:
    return VersionSnapshot(versions={t.taxonomy_type.value: t.version for t in taxonomies})


@dataclass
class ChangelogEntry:
    kind: str  # "entry_added" | "entry_removed" | "entry_deprecated" | "alias_added" |
    #            "alias_removed" | "expansion_added" | "expansion_removed" | "expansion_weight_changed"
    entry_id: str
    detail: str


def diff_taxonomies(old: Taxonomy, new: Taxonomy) -> list[ChangelogEntry]:
    """Produces a human-readable changelog between two versions of the SAME
    taxonomy (same taxonomy_type). This is what makes a taxonomy PR
    reviewable -- a raw JSON diff of a large file is not, per
    docs/KNOWLEDGE_ENGINE.md section 7.3.
    """
    if old.taxonomy_type != new.taxonomy_type:
        raise ValueError(
            f"Cannot diff different taxonomy types: {old.taxonomy_type} vs {new.taxonomy_type}"
        )

    changelog: list[ChangelogEntry] = []

    old_by_id: dict[str, TaxonomyEntry] = {e.id: e for e in old.entries}
    new_by_id: dict[str, TaxonomyEntry] = {e.id: e for e in new.entries}

    for entry_id, new_entry in new_by_id.items():
        if entry_id not in old_by_id:
            changelog.append(
                ChangelogEntry(
                    kind="entry_added",
                    entry_id=entry_id,
                    detail=f"added new entry '{new_entry.canonical}'",
                )
            )
            continue

        old_entry = old_by_id[entry_id]

        if old_entry.status != new_entry.status and new_entry.status.value == "deprecated":
            changelog.append(
                ChangelogEntry(
                    kind="entry_deprecated",
                    entry_id=entry_id,
                    detail=f"'{new_entry.canonical}' marked deprecated",
                )
            )

        old_aliases = set(old_entry.aliases)
        new_aliases = set(new_entry.aliases)
        for added in new_aliases - old_aliases:
            changelog.append(
                ChangelogEntry(
                    kind="alias_added",
                    entry_id=entry_id,
                    detail=f"added alias '{added}' -> {new_entry.canonical}",
                )
            )
        for removed in old_aliases - new_aliases:
            changelog.append(
                ChangelogEntry(
                    kind="alias_removed",
                    entry_id=entry_id,
                    detail=f"removed alias '{removed}' -> {new_entry.canonical}",
                )
            )

        old_expansions = {e.target_id: e for e in old_entry.expansions}
        new_expansions = {e.target_id: e for e in new_entry.expansions}
        for target_id, exp in new_expansions.items():
            if target_id not in old_expansions:
                changelog.append(
                    ChangelogEntry(
                        kind="expansion_added",
                        entry_id=entry_id,
                        detail=f"added expansion {entry_id} -> {target_id} "
                        f"(weight {exp.weight})",
                    )
                )
            elif old_expansions[target_id].weight != exp.weight:
                changelog.append(
                    ChangelogEntry(
                        kind="expansion_weight_changed",
                        entry_id=entry_id,
                        detail=f"expansion {entry_id} -> {target_id} weight changed "
                        f"{old_expansions[target_id].weight} -> {exp.weight}",
                    )
                )
        for target_id in old_expansions:
            if target_id not in new_expansions:
                changelog.append(
                    ChangelogEntry(
                        kind="expansion_removed",
                        entry_id=entry_id,
                        detail=f"removed expansion {entry_id} -> {target_id}",
                    )
                )

    for entry_id, old_entry in old_by_id.items():
        if entry_id not in new_by_id:
            changelog.append(
                ChangelogEntry(
                    kind="entry_removed",
                    entry_id=entry_id,
                    detail=f"'{old_entry.canonical}' no longer present in file "
                    f"(should normally be deprecated instead of removed -- see "
                    f"docs/KNOWLEDGE_ENGINE.md section 7)",
                )
            )

    return changelog
