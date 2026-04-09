"""Backfill short descriptions for books with description IS NULL.

Mirrors the cover backfill pattern — runs Open Library's description fetcher
against every book missing a blurb and updates the database in place. Safe
and idempotent: re-running only revisits books still missing a description.

Usage (inside the running fastapi container):

    docker compose exec fastapi python scripts/backfill_descriptions.py
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
from app.services.openlibrary import fetch_description  # noqa: E402


async def main() -> int:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Book).where(Book.description.is_(None))
        )
        books = list(result.scalars().all())
        print(f"Found {len(books)} books missing a description")
        if not books:
            return 0

        hit = 0
        for b in books:
            try:
                desc = await fetch_description(
                    title=b.title,
                    author=b.author,
                    isbn=b.isbn,
                )
            except Exception as e:
                print(f"  !!  {b.title}: {type(e).__name__}: {e}")
                continue

            if desc:
                b.description = desc
                session.add(b)
                hit += 1
                preview = desc[:80] + ("…" if len(desc) > 80 else "")
                print(f"  OK  {b.title} -> {preview}")
            else:
                print(f"  --  {b.title} (no description found)")

        await session.commit()
        print(f"Done. {hit}/{len(books)} descriptions resolved.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
