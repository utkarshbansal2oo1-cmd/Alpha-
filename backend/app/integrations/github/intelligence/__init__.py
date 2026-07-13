"""GitHub Candidate Intelligence Engine -- Sprint 20D.

Transforms the GitHub connector from a simple profile finder into a
richer signal-extraction pipeline: repository analysis, activity
scoring, organization analysis, evidence-based skill extraction, and an
overall quality score. Everything here is additive and reads ONLY data
already available from GitHub's official REST API
(app/integrations/github/client.py) -- no new external dependency, no
scraping.

Nothing in Sprint 18-20C's frozen modules (Query Understanding, Knowledge
Engine, Search Planner, Candidate Intelligence Lifecycle, Matching
Engine, Ranking Engine, the DiscoveryConnector interface, the Connector
Intelligence Layer, the Discovery Orchestrator, the Greenhouse connector,
the Browser Extension, or the Candidate Repository's read/write
behavior) is modified. The GitHub connector's own implementation is
explicitly NOT frozen this sprint (see the Sprint 20D brief) and is
extended here to call this new package.
"""
