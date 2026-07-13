"""Confidence Engine -- maintains per-section confidence as new evidence
arrives. Pure functions only (no candidate/repository mutation here; the
orchestrator in lifecycle.py is responsible for actually writing the
result back onto `candidate.section_confidence`), so this can run inline
today and as an async batch job later without changing.

Model (deliberately simple, corroboration-aware, and conservative --
mirroring docs/EVIDENCE_GRAPH_ARCHITECTURE.md's stance that confidence
should be easy to raise with agreeing evidence and quick to lower on a
genuine conflict, never both at once):

- A section with NO prior confidence starts at whatever the first piece
  of evidence's own confidence is (see initial_confidence()).
- Corroborating evidence (the new value agrees with -- or simply fills a
  previously-empty part of -- what's already recorded) nudges confidence
  UP, asymptotically toward 1.0: bigger nudges when confidence is still
  low, diminishing returns near 1.0.
- Conflicting evidence (the new value disagrees with what's already
  recorded) pulls confidence DOWN, proportional to how confident the new,
  conflicting evidence itself is -- a low-confidence conflicting source
  barely moves an already-solid section; a high-confidence conflicting
  source moves it more.
"""
from __future__ import annotations


def initial_confidence(source_confidence: float) -> float:
    return max(0.0, min(1.0, source_confidence))


def update_confidence(current_confidence: float, incoming_confidence: float, agreement: bool) -> float:
    incoming_confidence = max(0.0, min(1.0, incoming_confidence))
    current_confidence = max(0.0, min(1.0, current_confidence))

    if agreement:
        headroom = 1.0 - current_confidence
        updated = current_confidence + headroom * incoming_confidence * 0.5
    else:
        updated = current_confidence * (1.0 - incoming_confidence * 0.5)

    return round(max(0.0, min(1.0, updated)), 4)
