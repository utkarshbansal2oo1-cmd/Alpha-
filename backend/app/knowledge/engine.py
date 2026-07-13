"""KnowledgeEngine: the single entry point every other module (Query
Understanding, Matching Engine, and anything future) uses to normalize
recruiter/candidate terminology and expand canonical values into searchable
equivalents.

Per docs/KNOWLEDGE_ENGINE.md:
  - Loaded once at startup, in-memory singleton (section 6.3).
  - normalize()/get_entry()/expand() are O(1) lookups via prebuilt indices
    (section "PERFORMANCE" in the implementation brief).
  - suggest_canonical() is a fuzzy search over the whole vocabulary and is
    NOT O(1) by nature -- it is a search/ranking operation, documented as
    such rather than mis-sold as constant time.
  - The LLM never generates synonyms; it only ever picks among the
    candidates suggest_canonical() returns (section 8). This engine performs
    all actual expansion.
"""
from __future__ import annotations

import difflib
from pathlib import Path

from app.knowledge.exceptions import KnowledgeEngineError
from app.knowledge.loader import load_all_taxonomies
from app.knowledge.models import Expansion, Taxonomy, TaxonomyEntry
from app.knowledge.versioning import VersionSnapshot, snapshot_versions


class ExpansionResult:
    """One expanded-to entry plus the weight/notes of the edge that produced
    it -- returned by expand() so callers (eventually the Matching Engine)
    have the weight available for scoring, per
    docs/KNOWLEDGE_ENGINE.md section 8.
    """

    __slots__ = ("entry", "weight", "notes")

    def __init__(self, entry: TaxonomyEntry, weight: float, notes: str):
        self.entry = entry
        self.weight = weight
        self.notes = notes

    def __repr__(self) -> str:  # pragma: no cover - debug convenience only
        return f"ExpansionResult(entry={self.entry.id!r}, weight={self.weight})"


class SuggestionResult:
    """One candidate canonical entry suggested for a raw recruiter term,
    with a similarity score in [0, 1] -- this is what gets handed to the LLM
    as grounding context per docs/KNOWLEDGE_ENGINE.md section 8 ("narrows a
    huge taxonomy down to a handful of plausible candidates").
    """

    __slots__ = ("entry", "score")

    def __init__(self, entry: TaxonomyEntry, score: float):
        self.entry = entry
        self.score = score

    def __repr__(self) -> str:  # pragma: no cover
        return f"SuggestionResult(entry={self.entry.id!r}, score={self.score:.2f})"


class KnowledgeEngine:
    """Loads all taxonomies once and serves O(1) normalize/expand/get_entry
    lookups for the lifetime of the process. Construct one instance (a
    module-level singleton, see get_knowledge_engine() below) and reuse it --
    do not construct a new KnowledgeEngine per request.
    """

    def __init__(self, taxonomies_dir: Path | None = None, filenames: list[str] | None = None):
        self._taxonomies_dir = taxonomies_dir
        self._filenames = filenames
        self._taxonomies: list[Taxonomy] = []
        self._entry_by_id: dict[str, TaxonomyEntry] = {}
        self._canonical_by_alias: dict[str, str] = {}  # normalized alias/canonical text -> entry id
        self._version_snapshot: VersionSnapshot = VersionSnapshot()
        self._loaded = False

    # --- lifecycle -----------------------------------------------------

    def load(self) -> None:
        """Loads and validates every taxonomy file, then builds the O(1)
        lookup indices. Raises TaxonomyValidationError (uncaught, on
        purpose) if anything is invalid -- application startup must fail
        loudly rather than run with a partially-loaded engine.
        """
        taxonomies = load_all_taxonomies(
            taxonomies_dir=self._taxonomies_dir, filenames=self._filenames
        )
        self._install(taxonomies)
        self._loaded = True

    def reload(self) -> None:
        """Re-reads taxonomy files from disk and atomically replaces the
        in-memory state. Per docs/KNOWLEDGE_ENGINE.md section 6.5, this is a
        development-time convenience (e.g. a file-watcher calling it) -- in
        production the engine is loaded once at startup and a new taxonomy
        version requires a redeploy, so that the active version is always
        tied to a specific deployed build.
        """
        taxonomies = load_all_taxonomies(
            taxonomies_dir=self._taxonomies_dir, filenames=self._filenames
        )
        self._install(taxonomies)

    def _install(self, taxonomies: list[Taxonomy]) -> None:
        entry_by_id: dict[str, TaxonomyEntry] = {}
        canonical_by_alias: dict[str, str] = {}

        for taxonomy in taxonomies:
            for entry in taxonomy.entries:
                entry_by_id[entry.id] = entry
                canonical_by_alias[self._normalize_text(entry.canonical)] = entry.id
                for alias in entry.aliases:
                    canonical_by_alias[self._normalize_text(alias)] = entry.id

        # Assigned together so a failure above never leaves the engine
        # half-updated (old state stays fully intact until this point).
        self._taxonomies = taxonomies
        self._entry_by_id = entry_by_id
        self._canonical_by_alias = canonical_by_alias
        self._version_snapshot = snapshot_versions(taxonomies)

    @staticmethod
    def _normalize_text(text: str) -> str:
        return text.strip().lower()

    def _require_loaded(self) -> None:
        if not self._loaded:
            raise KnowledgeEngineError(
                "KnowledgeEngine.load() must be called before use "
                "(it is not loaded implicitly, so startup failures are explicit)"
            )

    # --- lookups (O(1)) -------------------------------------------------

    def normalize(self, term: str) -> str | None:
        """Resolves a raw alias OR canonical string to its canonical entry
        id. Returns None if the term is not recognized at all (see
        docs/KNOWLEDGE_ENGINE.md section 8 -- an unrecognized term is logged
        as an "unresolved term" by the caller, not guessed at here).
        O(1): single dict lookup after normalizing case/whitespace.
        """
        self._require_loaded()
        if term is None:
            return None
        return self._canonical_by_alias.get(self._normalize_text(term))

    def get_entry(self, entry_id: str) -> TaxonomyEntry | None:
        """O(1) lookup of a TaxonomyEntry by its id."""
        self._require_loaded()
        return self._entry_by_id.get(entry_id)

    def expand(self, canonical_term_or_id: str) -> list[ExpansionResult]:
        """Given a canonical value OR an entry id, returns every entry it
        expands to, with weight/notes. This is the ONLY place expansion
        happens in the system -- per docs/KNOWLEDGE_ENGINE.md, the LLM must
        never generate these. Returns [] for an unrecognized term (not an
        error -- an entry with no expansions is a completely normal, valid
        state, e.g. 'EC2' in the seed data).
        O(1) index lookup + O(k) where k = number of expansions on that
        entry (proportional to output size, not dataset size).
        """
        self._require_loaded()

        entry = self._entry_by_id.get(canonical_term_or_id)
        if entry is None:
            resolved_id = self._canonical_by_alias.get(self._normalize_text(canonical_term_or_id))
            entry = self._entry_by_id.get(resolved_id) if resolved_id else None

        if entry is None:
            return []

        results: list[ExpansionResult] = []
        for expansion in entry.expansions:
            target_entry = self._entry_by_id.get(expansion.target_id)
            if target_entry is None:
                # Should be impossible -- loader.py validates every target_id
                # at load time -- but defensive rather than silently wrong.
                continue
            results.append(ExpansionResult(target_entry, expansion.weight, expansion.notes))
        return results

    def get_version(self) -> dict[str, str]:
        """Returns the currently loaded version string per taxonomy_type,
        e.g. {'role': '2026.07.1', 'skill': '2026.07.1', ...} -- suitable
        for embedding into a future JobRequirement's knowledge_versions
        meta field per docs/KNOWLEDGE_ENGINE.md section 7.1.
        """
        self._require_loaded()
        return dict(self._version_snapshot.versions)

    # --- fuzzy search (NOT O(1) -- see class docstring) ------------------

    def suggest_canonical(self, term: str, limit: int = 5, min_score: float = 0.5) -> list[SuggestionResult]:
        """Fuzzy-matches a raw term against every known canonical value and
        alias, returning the top candidates. This is what narrows the full
        taxonomy down to a short list the LLM is asked to choose from,
        per docs/KNOWLEDGE_ENGINE.md section 8 -- the LLM picks from these
        candidates, it never invents its own.

        Deliberately O(n) over the vocabulary size (a search, not a lookup)
        using difflib's SequenceMatcher ratio; taxonomy sizes are in the
        thousands of entries (per docs/KNOWLEDGE_ENGINE.md section 6.1),
        so this is fast enough without needing a dedicated search index in
        this first implementation. Swapping in a smarter/faster string-
        similarity index later is a pure internal change -- see "Future
        Improvements" in the accompanying implementation notes.
        """
        self._require_loaded()
        if not term or not term.strip():
            return []

        normalized_term = self._normalize_text(term)

        best_score_by_entry_id: dict[str, float] = {}
        for text, entry_id in self._canonical_by_alias.items():
            score = difflib.SequenceMatcher(None, normalized_term, text).ratio()
            if score > best_score_by_entry_id.get(entry_id, -1.0):
                best_score_by_entry_id[entry_id] = score

        ranked = sorted(best_score_by_entry_id.items(), key=lambda kv: kv[1], reverse=True)

        results: list[SuggestionResult] = []
        for entry_id, score in ranked:
            if score < min_score:
                break
            entry = self._entry_by_id.get(entry_id)
            if entry is not None:
                results.append(SuggestionResult(entry, score))
            if len(results) >= limit:
                break
        return results


# --- module-level singleton -------------------------------------------------

_engine_instance: KnowledgeEngine | None = None


def get_knowledge_engine() -> KnowledgeEngine:
    """Returns the process-wide KnowledgeEngine singleton, loading it on
    first access. Mirrors how services/connectors/registry.py builds its
    connector list once and is reused -- this function (not a fresh
    KnowledgeEngine()) is what every future consumer (Query Understanding,
    Matching Engine) should import.
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = KnowledgeEngine()
        _engine_instance.load()
    return _engine_instance
