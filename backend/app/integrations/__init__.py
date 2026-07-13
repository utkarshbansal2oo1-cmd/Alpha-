"""Third-party hiring-system integrations (Sprint 15 onward) -- ATS
connectors, and in the future partner/public-discovery sources. Each
integration lives in its own subpackage and speaks to
app/candidate_repository (via the same upsert()/find_potential_duplicate()
path the browser extension already uses) rather than introducing a second
candidate write path.
"""
