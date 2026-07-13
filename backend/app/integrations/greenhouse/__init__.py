"""Greenhouse ATS connector (Sprint 15) -- the first "Orchestrate" pillar
connector (see docs/PRODUCT_PILLARS.md), and the proof point for
AlphaSource's real positioning: integrating with an org's existing hiring
stack, not replacing it.

This is a real connector built against Greenhouse's documented Harvest
API contract (https://developers.greenhouse.io/harvest.html) -- HTTP
Basic Auth with an API key as the username and a blank password, JSON
candidate records shaped the way Greenhouse's API actually returns them.
It is not a simulation: point `GreenhouseConfig` at
https://harvest.greenhouse.io/v1 with a real API key and it talks to the
real service. Tests exercise it against recorded/constructed HTTP
responses matching that documented shape (via `respx`, see
tests_greenhouse.py) rather than a hand-rolled fake server, so what's
being tested is "does this client speak the real API correctly," not
"does this client talk to our own mock."

- client.py     -- GreenhouseClient, the only thing that makes HTTP calls.
- normalizer.py -- Greenhouse candidate JSON -> the existing Candidate
                   model.
- sync.py       -- pull sync (Greenhouse -> AlphaSource, with dedup) and
                   push-back (AlphaSource -> Greenhouse).
- config.py     -- GreenhouseConfig (base_url, api_key) + in-memory config
                   store for this POC.
"""
