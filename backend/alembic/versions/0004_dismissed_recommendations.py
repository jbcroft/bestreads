"""add dismissed_recommendations table

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dismissed_recommendations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("author", sa.String(512), nullable=False),
        sa.Column(
            "dismissed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id", "title", "author", name="uq_dismissed_user_title_author"
        ),
    )
    op.create_index(
        "ix_dismissed_recommendations_user_id",
        "dismissed_recommendations",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_dismissed_recommendations_user_id", table_name="dismissed_recommendations"
    )
    op.drop_table("dismissed_recommendations")
