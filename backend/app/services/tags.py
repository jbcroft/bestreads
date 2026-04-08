from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Tag


async def resolve_or_create_tags(
    session: AsyncSession, user_id: UUID, names: list[str]
) -> list[Tag]:
    cleaned = [n.strip() for n in names if n and n.strip()]
    if not cleaned:
        return []
    # Dedupe case-insensitively while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for n in cleaned:
        k = n.lower()
        if k not in seen:
            seen.add(k)
            unique.append(n)

    existing = await session.execute(
        select(Tag).where(Tag.user_id == user_id, Tag.name.in_(unique))
    )
    by_name: dict[str, Tag] = {t.name: t for t in existing.scalars().all()}
    result: list[Tag] = []
    for name in unique:
        tag = by_name.get(name)
        if tag is None:
            tag = Tag(user_id=user_id, name=name)
            session.add(tag)
            by_name[name] = tag
        result.append(tag)
    await session.flush()
    return result
