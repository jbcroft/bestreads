"""add dnf to book_status enum

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-08

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE book_status ADD VALUE IF NOT EXISTS 'dnf'")


def downgrade() -> None:
    # PostgreSQL does not support removing a value from an enum type without
    # recreating it. Reversing this migration is not supported.
    pass
