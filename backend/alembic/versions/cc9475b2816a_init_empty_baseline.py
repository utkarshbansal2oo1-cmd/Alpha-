"""init empty baseline

Revision ID: cc9475b2816a
Revises:
Create Date: 2026-07-07

This migration intentionally does nothing. It exists as a baseline revision
generated while smoke-testing the Alembic wiring during foundation setup
(confirms app.config settings -> app.database.Base -> alembic/env.py are
correctly connected end-to-end). Real tables get their own migrations once
SQLAlchemy models exist under app/models/.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "cc9475b2816a"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
