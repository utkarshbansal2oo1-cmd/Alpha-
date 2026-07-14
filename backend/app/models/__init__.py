"""SQLAlchemy models package.

Imported by alembic/env.py so autogenerate can see every table. Add new
model modules here as they're created.
"""
from app.models.candidate import CandidateRow  # noqa: F401
from app.models.connector_credential import ConnectorCredentialRow  # noqa: F401
from app.models.recruiter import RecruiterRow, SessionRow  # noqa: F401
from app.models.search_session import SearchSessionCandidateRow, SearchSessionRow  # noqa: F401
