from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_auth_user
from ..models import Tag, User
from ..schemas import TagCreate, TagRead

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
async def list_tags(
    user: User = Depends(get_auth_user),
    session: AsyncSession = Depends(get_session),
) -> list[TagRead]:
    result = await session.execute(
        select(Tag).where(Tag.user_id == user.id).order_by(Tag.name)
    )
    return [TagRead(id=t.id, name=t.name) for t in result.scalars().all()]


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
async def create_tag(
    payload: TagCreate,
    user: User = Depends(get_auth_user),
    session: AsyncSession = Depends(get_session),
) -> TagRead:
    existing = await session.execute(
        select(Tag).where(Tag.user_id == user.id, Tag.name == payload.name)
    )
    tag = existing.scalar_one_or_none()
    if tag is not None:
        return TagRead(id=tag.id, name=tag.name)
    tag = Tag(user_id=user.id, name=payload.name)
    session.add(tag)
    await session.commit()
    await session.refresh(tag)
    return TagRead(id=tag.id, name=tag.name)


@router.delete("/{tag_id}", status_code=204)
async def delete_tag(
    tag_id: UUID,
    user: User = Depends(get_auth_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    result = await session.execute(
        select(Tag).where(Tag.id == tag_id, Tag.user_id == user.id)
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    await session.delete(tag)
    await session.commit()
