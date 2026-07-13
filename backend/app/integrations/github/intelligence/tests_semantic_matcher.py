"""Tests for semantic evidence matching -- Sprint 20G.

Uses a fake EmbeddingClient (test double) rather than mocking Gemini's
real embedding HTTP call directly -- SemanticEvidenceMatcher depends only
on the abstract EmbeddingClient interface, so these tests exercise the
real comparison/threshold/fallback logic without needing internet or
Gemini-SDK-specific HTTP mocking. GeminiEmbeddingClient's own wiring
(constructing the real SDK client, raising EmbeddingUnavailableError when
unconfigured) is covered separately below.
"""
from __future__ import annotations

import pytest

from app.integrations.github.intelligence.semantic_matcher import (
    DEFAULT_SIMILARITY_THRESHOLD,
    EmbeddingUnavailableError,
    GeminiEmbeddingClient,
    SemanticEvidenceMatcher,
    cosine_similarity,
)


class _FakeEmbeddingClient:
    """Returns a pre-programmed vector per input text, so a test can
    control exactly how "similar" two texts are without touching any
    real embedding model."""

    def __init__(self, vectors: dict[str, list[float]]):
        self._vectors = vectors

    def embed(self, text: str) -> list[float]:
        if text not in self._vectors:
            raise AssertionError(f"Unexpected embed() call for text: {text!r}")
        return self._vectors[text]


def test_cosine_similarity_identical_vectors_is_one():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors_is_zero():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_similarity_opposite_vectors_is_negative_one():
    assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


def test_cosine_similarity_handles_zero_vector_without_dividing_by_zero():
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_cosine_similarity_handles_mismatched_lengths():
    assert cosine_similarity([1.0, 0.0], [1.0]) == 0.0


def test_is_relevant_true_for_high_similarity_with_zero_shared_words():
    """The whole point of Sprint 20G: 'Computer Vision' and 'YOLO OpenCV
    Detectron2' share no literal words at all, but a real embedding model
    would place them close together in meaning -- simulated here by
    programming near-identical vectors for the two texts."""
    fake_client = _FakeEmbeddingClient(
        {
            "Computer Vision": [0.9, 0.1, 0.0],
            "YOLO OpenCV Detectron2 object detection repo": [0.88, 0.12, 0.02],
        }
    )
    matcher = SemanticEvidenceMatcher(embedding_client=fake_client)

    is_relevant, score = matcher.is_relevant(
        "Computer Vision", "YOLO OpenCV Detectron2 object detection repo"
    )

    assert is_relevant is True
    assert score > DEFAULT_SIMILARITY_THRESHOLD


def test_is_relevant_false_for_low_similarity():
    fake_client = _FakeEmbeddingClient(
        {
            "Distributed Systems": [1.0, 0.0, 0.0],
            "My personal cooking recipe blog": [0.0, 1.0, 0.0],
        }
    )
    matcher = SemanticEvidenceMatcher(embedding_client=fake_client)

    is_relevant, score = matcher.is_relevant(
        "Distributed Systems", "My personal cooking recipe blog"
    )

    assert is_relevant is False
    assert score < DEFAULT_SIMILARITY_THRESHOLD


def test_is_relevant_respects_custom_threshold():
    fake_client = _FakeEmbeddingClient({"a": [1.0, 0.0], "b": [0.7, 0.7]})
    borderline_similarity = cosine_similarity([1.0, 0.0], [0.7, 0.7])

    lenient_matcher = SemanticEvidenceMatcher(embedding_client=fake_client, threshold=borderline_similarity - 0.01)
    strict_matcher = SemanticEvidenceMatcher(embedding_client=fake_client, threshold=borderline_similarity + 0.01)

    assert lenient_matcher.is_relevant("a", "b")[0] is True
    assert strict_matcher.is_relevant("a", "b")[0] is False


def test_is_relevant_false_for_empty_text_without_calling_embedding_client():
    class _ExplodingClient:
        def embed(self, text: str) -> list[float]:
            raise AssertionError("embed() should never be called for empty text")

    matcher = SemanticEvidenceMatcher(embedding_client=_ExplodingClient())

    assert matcher.is_relevant("", "some evidence")[0] is False
    assert matcher.is_relevant("some requirement", "")[0] is False


def test_gemini_embedding_client_raises_when_no_api_key_configured():
    client = GeminiEmbeddingClient(api_key="")
    with pytest.raises(EmbeddingUnavailableError):
        client.embed("anything")


def test_gemini_embedding_client_wraps_sdk_failures_as_unavailable():
    """A real network/SDK failure must present the same way as 'not
    configured' to callers -- both mean 'fall back to token matching',
    never 'crash the whole discovery run'."""
    client = GeminiEmbeddingClient(api_key="fake-key-for-test")

    class _BrokenClient:
        class models:
            @staticmethod
            def embed_content(model, contents):
                raise RuntimeError("simulated network failure")

    client._client = _BrokenClient()  # bypass lazy SDK construction

    with pytest.raises(EmbeddingUnavailableError):
        client.embed("anything")
