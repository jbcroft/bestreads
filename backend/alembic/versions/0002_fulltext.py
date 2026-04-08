"""full-text search vector on books

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-08

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE books
        ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            to_tsvector(
                'english',
                coalesce(title, '') || ' ' ||
                coalesce(author, '') || ' ' ||
                coalesce(notes, '') || ' ' ||
                coalesce(description, '')
            )
        ) STORED
        """
    )
    op.execute(
        "CREATE INDEX ix_books_search_vector ON books USING GIN (search_vector)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_books_search_vector")
    op.execute("ALTER TABLE books DROP COLUMN IF EXISTS search_vector")
