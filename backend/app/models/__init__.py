"""SQLAlchemy models package.

Intentionally empty on Day 1 (foundation-only task). Real tables (candidates,
sources, candidate_source_links, searches, match_results — see
database/schema.sql for the target shape) get added here as their own
modules, then imported below so Alembic's autogenerate can see them:

    from app.models.candidate import Candidate
    from app.models.source import Source
"""
