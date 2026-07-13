"""Sprint 18: the Autonomous Talent Discovery Engine.

Everything in this package is additive on top of the existing Capture ->
Understand -> Orchestrate architecture. Nothing here modifies Query
Understanding, the Knowledge Engine, the Search Planner, the Candidate
Intelligence Lifecycle, or the Greenhouse Connector -- it only calls their
existing public seams (QueryUnderstandingService.parse(),
SearchPlanner.build_plan(), CandidateRepository.search()/upsert(), and
CandidateImportRequest -> normalize_import(), exactly like the browser
extension and Greenhouse connector already do).

Package layout:
- models.py            Pydantic models for a discovery decision/run.
- scoring.py            A requirement-match confidence heuristic, scoped
                        entirely to this package's own decision-making.
- decision_engine.py    DiscoveryDecisionEngine: is the existing result
                        set good enough, or should we go discover more?
- connectors/           One module per connected, authorized source.
- orchestrator.py       DiscoveryOrchestrator: runs connectors in
                        priority order, imports results, re-searches.
"""
