from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..db import get_session
from ..deps import get_auth_user
from ..models import Book, Recommendation, User
from ..schemas import RecommendationItem, RecommendationsResponse
from ..services.anthropic_recs import generate_recommendations

router = APIRouter(tags=["recommendations"])

CACHE_TTL = timedelta(hours=24)
MIN_BOOKS_FOR_RECS = 5


async def _load_cached(
    session: AsyncSession,
    user_id,
    mood: str | None,
    tag_filter: str | None,
) -> list[Recommendation]:
    stmt = select(Recommendation).where(
        Recommendation.user_id == user_id,
        Recommendation.mood.is_(mood) if mood is None else Recommendation.mood == mood,
        Recommendation.tag_filter.is_(tag_filter)
        if tag_filter is None
        else Recommendation.tag_filter == tag_filter,
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _replace_cache(
    session: AsyncSession,
    user_id,
    mood: str | None,
    tag_filter: str | None,
    items: list[dict[str, str]],
) -> list[Recommendation]:
    await session.execute(
        delete(Recommendation).where(
            Recommendation.user_id == user_id,
            Recommendation.mood.is_(mood) if mood is None else Recommendation.mood == mood,
            Recommendation.tag_filter.is_(tag_filter)
            if tag_filter is None
            else Recommendation.tag_filter == tag_filter,
        )
    )
    now = datetime.now(timezone.utc)
    rows = [
        Recommendation(
            user_id=user_id,
            title=i["title"],
            author=i["author"],
            reason=i["reason"],
            mood=mood,
            tag_filter=tag_filter,
            generated_at=now,
        )
        for i in items
    ]
    session.add_all(rows)
    await session.flush()
    return rows


@router.get("/recommendations", response_model=RecommendationsResponse)
async def get_recommendations(
    count: int = Query(default=3, ge=1, le=10),
    mood: str | None = Query(default=None),
    tag: str | None = Query(default=None, alias="tag"),
    user: User = Depends(get_auth_user),
    session: AsyncSession = Depends(get_session),
) -> RecommendationsResponse:
    # Count the user's library
    books_result = await session.execute(
        select(Book)
        .where(Book.user_id == user.id)
        .options(selectinload(Book.tags))
    )
    books = list(books_result.scalars().unique().all())

    if len(books) < MIN_BOOKS_FOR_RECS:
        return RecommendationsResponse(
            available=False,
            message="Add a few more books to unlock personalized recommendations.",
            recommendations=[],
        )

    if not settings.anthropic_api_key:
        return RecommendationsResponse(
            available=False,
            message="Recommendations are not configured. Set ANTHROPIC_API_KEY on the server.",
            recommendations=[],
        )

    # Cache lookup
    cached = await _load_cached(session, user.id, mood, tag)
    if cached:
        newest = max(r.generated_at for r in cached)
        fresh_until = max(
            datetime.now(timezone.utc) - CACHE_TTL,
            user.library_updated_at,
        )
        # newest must be strictly after fresh_until threshold to be considered valid
        if newest > fresh_until and len(cached) >= count:
            return RecommendationsResponse(
                available=True,
                recommendations=[
                    RecommendationItem(title=r.title, author=r.author, reason=r.reason)
                    for r in cached[:count]
                ],
                generated_at=newest,
            )

    # Generate fresh
    items = await generate_recommendations(
        books, count=count, mood=mood, tag_filter=tag
    )
    if not items:
        return RecommendationsResponse(
            available=False,
            message="Couldn't generate recommendations right now — try again shortly.",
            recommendations=[],
        )

    rows = await _replace_cache(session, user.id, mood, tag, items)
    await session.commit()

    return RecommendationsResponse(
        available=True,
        recommendations=[
            RecommendationItem(title=r.title, author=r.author, reason=r.reason)
            for r in rows[:count]
        ],
        generated_at=rows[0].generated_at if rows else None,
    )
