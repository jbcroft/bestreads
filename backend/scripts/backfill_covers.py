"""Backfill covers for books with cover_image_path IS NULL.

Runs the cover resolver cascade (cover_url → ISBN → title+author search)
against every book missing a cover and updates the database in place.
Safe and idempotent — re-running will only revisit books still missing a
cover.

Usage (inside the running fastapi container):

    docker compose exec fastapi python scripts/backfill_covers.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make the parent app/ package importable when run as a standalone script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Book  # noqa: E402
from app.services.cover_resolver import resolve_book_cover  # noqa: E402


async def main() -> int:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Book).where(Book.cover_image_path.is_(None))
        )
        books = list(result.scalars().all())
        print(f"Found {len(books)} books missing a cover")
        if not books:
            return 0

        hit = 0
        for b in books:
            fn = await resolve_book_cover(
                title=b.title,
                author=b.author,
                isbn=b.isbn,
                cover_url=None,
            )
            if fn:
                b.cover_image_path = fn
                session.add(b)
                hit += 1
                print(f"  OK  {b.title} -> {fn}")
            else:
                print(f"  --  {b.title} (no cover found)")

        await session.commit()
        print(f"Done. {hit}/{len(books)} covers resolved.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
