"""Tests for MatchingConfig -- Sprint 35 addition: adaptive_relevance_threshold().

Solution 7's own worked example: >100 candidates -> stricter 70% cutoff,
<20 candidates -> looser 45% cutoff (a niche search shouldn't hide every
result it found), everything else -> the configured flat default (60%).
"""
from __future__ import annotations

from app.matching.config import MatchingConfig


def test_large_pool_uses_strict_threshold():
    config = MatchingConfig()
    assert config.adaptive_relevance_threshold(101) == 70.0
    assert config.adaptive_relevance_threshold(500) == 70.0


def test_small_pool_uses_loose_threshold():
    config = MatchingConfig()
    assert config.adaptive_relevance_threshold(19) == 45.0
    assert config.adaptive_relevance_threshold(0) == 45.0


def test_mid_size_pool_uses_flat_default():
    config = MatchingConfig()
    assert config.adaptive_relevance_threshold(20) == 60.0
    assert config.adaptive_relevance_threshold(100) == 60.0
    assert config.adaptive_relevance_threshold(50) == 60.0


def test_flat_default_is_configurable():
    config = MatchingConfig(min_visible_relevance_score=55.0)
    assert config.adaptive_relevance_threshold(50) == 55.0
    # The strict/loose tiers are absolute, not relative to the configured
    # default, matching Solution 7's own worked example values.
    assert config.adaptive_relevance_threshold(200) == 70.0
    assert config.adaptive_relevance_threshold(5) == 45.0
