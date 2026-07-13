"""The Connector Intelligence Layer -- Sprint 20C.

Sits between the Search Planner and the Discovery Orchestrator. Nothing
upstream (Query Understanding, Knowledge Engine, Search Planner) or
downstream (Candidate Intelligence Lifecycle, Matching Engine, Ranking
Engine) is touched -- this package only reads the existing
CanonicalJobRequirement/SearchPlan and produces per-connector optimized
search strings, since a connector like GitHub responds far better to
"golang language:Go grpc" than to a literal recruiter job title like
"Senior Golang Developer".
"""
