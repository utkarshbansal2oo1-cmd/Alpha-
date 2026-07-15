"""Semantic evidence matching -- Sprint 20G.

Replaces literal-word overlap (Sprint 20F) as the primary candidate
relevance check with real semantic similarity: both the recruiter's
requirement text and the candidate's real GitHub evidence text are
embedded into vectors by the same embedding model, and compared by
cosine similarity. This is what lets "Computer Vision" match a candidate
whose evidence says "YOLO, OpenCV, Detectron2" -- none of those words
appear in the query, but their meanings are close in embedding space.

No predefined skill/role list is involved anywhere in this module. The
only "knowledge" here is a general-purpose embedding model (Gemini's
gemini-embedding-001, via the same `google-genai` SDK and
`settings.GEMINI_API_KEY` already used by
app/query_understanding/gemini_client.py) -- it was never trained on, or
told about, this product's specific skills or roles. It just maps
arbitrary text to a point in semantic space, for arbitrary text.

Sprint 37 fix: this previously called `text-embedding-004`, which Google
deprecated and retired server-side -- every live call was failing with a
404 ("models/text-embedding-004 is not found for API version v1beta"),
silently degrading every GitHub search to literal-token matching only
(see the fallback behavior below) with no visible error to the recruiter,
just a quieter/less precise result set. `gemini-embedding-001` is the
current supported replacement (3072-dimension vectors, vs. 768 for the
old model) -- cosine_similarity() below works unchanged for any vector
length as long as both sides come from the same model, which they always
do here.

Every comparison is still evidence-based: the "candidate" side of every
similarity check is real text GitHub returned for that candidate (repo
name, description, topics, language, README) -- nothing is fabricated or
guessed. The embedding model is used only to compare meaning between two
pieces of REAL text, never to invent a candidate's skills from nothing
(that would be exactly the hallucination this whole package has avoided
since Sprint 20D).

If the embedding API is unavailable (no API key configured, or a
transient failure), `SemanticEvidenceMatcher.is_relevant()` raises
`EmbeddingUnavailableError` so the caller can fall back to the Sprint 20F
literal-token evidence match rather than silently returning no
candidates at all -- availability must never depend on one remote call
succeeding.
"""
from __future__ import annotations

import logging
import math

from app.config import settings

logger = logging.getLogger(__name__)

# Below this cosine similarity, two pieces of text are treated as
# unrelated. 0.5 is a deliberately permissive threshold for this
# comparison -- a false negative (dropping a real, relevant candidate)
# is worse for a sourcing tool than a false positive (surfacing one
# borderline candidate a recruiter can dismiss with one glance) -- see
# docs/GITHUB_LIVE_VALIDATION.md's Sprint 20G section for the reasoning
# and the live-tunable follow-up this implies.
DEFAULT_SIMILARITY_THRESHOLD = 0.5

_EMBEDDING_MODEL = "gemini-embedding-001"


class EmbeddingUnavailableError(Exception):
    """Raised when the embedding API cannot be reached or is not
    configured -- the caller must fall back to literal evidence matching,
    not treat this as "no candidates"."""


class EmbeddingClient:
    """Provider-agnostic interface: embed one piece of text into a
    vector. Mirrors app.query_understanding.gemini_client.LLMClient's
    shape -- same reasoning: callers depend on this abstract interface,
    never on GeminiEmbeddingClient directly, so a different embedding
    provider can be swapped in later without touching this module's
    callers."""

    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class GeminiEmbeddingClient(EmbeddingClient):
    """Google Gemini embeddings via the same `google-genai` SDK and
    `settings.GEMINI_API_KEY` already used by GeminiClient (Query
    Understanding) -- one already-configured credential, reused, not a
    second integration to set up."""

    def __init__(self, api_key: str | None = None, model_name: str = _EMBEDDING_MODEL):
        self._api_key = api_key or settings.GEMINI_API_KEY
        self._model_name = model_name
        self._client = None  # constructed lazily, same pattern as GeminiClient

    def _ensure_client(self):
        if self._client is None:
            from google import genai  # local import -- see GeminiClient's docstring for why

            if not self._api_key:
                raise EmbeddingUnavailableError(
                    "GeminiEmbeddingClient requires GEMINI_API_KEY to be set (see backend/.env.example)"
                )
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def embed(self, text: str) -> list[float]:
        client = self._ensure_client()
        try:
            response = client.models.embed_content(model=self._model_name, contents=text)
        except Exception as exc:  # noqa: BLE001 -- any SDK/network failure means "unavailable", not "crash"
            raise EmbeddingUnavailableError(f"Gemini embedding call failed: {exc}") from exc

        # google-genai's embed_content response shape: response.embeddings
        # is a list (one per input); each has a `.values` float list.
        embeddings = getattr(response, "embeddings", None)
        if not embeddings:
            raise EmbeddingUnavailableError("Gemini embedding response contained no embeddings")
        values = getattr(embeddings[0], "values", None)
        if not values:
            raise EmbeddingUnavailableError("Gemini embedding response vector was empty")
        return list(values)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class SemanticEvidenceMatcher:
    """Compares a recruiter requirement's meaning against a candidate's
    real evidence text via embedding cosine similarity -- no predefined
    skill list, no literal-word requirement."""

    def __init__(
        self,
        embedding_client: EmbeddingClient | None = None,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ):
        self._client = embedding_client or GeminiEmbeddingClient()
        self._threshold = threshold

    def is_relevant(self, requirement_text: str, evidence_text: str) -> tuple[bool, float]:
        """Returns (is_relevant, similarity_score). Raises
        EmbeddingUnavailableError if the embedding call itself could not
        be completed -- callers must catch this and fall back to literal
        evidence matching, per this module's docstring."""
        if not requirement_text.strip() or not evidence_text.strip():
            return False, 0.0

        requirement_vector = self._client.embed(requirement_text)
        evidence_vector = self._client.embed(evidence_text)
        similarity = cosine_similarity(requirement_vector, evidence_vector)

        logger.info(
            "github.semantic_match",
            extra={"similarity": round(similarity, 4), "threshold": self._threshold},
        )

        return similarity >= self._threshold, similarity
