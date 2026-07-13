"""Candidate Intelligence Lifecycle (Sprint 14).

Makes every imported candidate more valuable over time, without touching
the search pipeline, the Adapter SDK, or any existing endpoint contract:

- health_engine.py       -- Candidate Health Score (per-section + overall)
- enrichment_registry.py -- pluggable source-type -> fields-it-can-supply
                             registry (adapter-registry-style pattern)
- enrichment_planner.py  -- turns missing fields into a prioritized plan
- confidence_engine.py   -- per-section confidence, corroboration-aware
- versioning.py          -- full-state snapshot history
- evidence_timeline.py   -- append-only field-level change log
- lifecycle.py           -- orchestrates all of the above; the only entry
                             point InMemoryCandidateRepository calls

See docs/CANDIDATE_INTELLIGENCE_LIFECYCLE.md for the full design.
"""
