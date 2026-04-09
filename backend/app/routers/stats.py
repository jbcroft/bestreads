from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_auth_user
from ..models import Book, BookStatus, Tag, User, book_tags
from ..schemas import MonthCount, StatsResponse, TagCount

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    user: User = Depends(get_auth_user),
    session: AsyncSession = Depends(get_session),
) -> StatsResponse:
    # Counts by status
    status_rows = await session.execute(
        select(Book.status, func.count())
        .where(Book.user_id == user.id)
        .group_by(Book.status)
    )
    by_status = {"want_to_read": 0, "reading": 0, "finished": 0, "dnf": 0}
    total = 0
    for s, c in status_rows.all():
        key = s.value if hasattr(s, "value") else str(s)
        by_status[key] = int(c)
        total += int(c)

    # Finished this year
    now = datetime.now(timezone.utc)
    year_start = datetime(now.year, 1, 1, tzinfo=timezone.utc)
    finished_this_year_row = await session.execute(
        select(func.count()).where(
            Book.user_id == user.id,
            Book.finished_at.is_not(None),
            Book.finished_at >= year_start,
        )
    )
    finished_this_year = int(finished_this_year_row.scalar_one())

    # Avg rating
    avg_row = await session.execute(
        select(func.avg(Book.rating)).where(
            Book.user_id == user.id, Book.rating.is_not(None)
        )
    )
    avg_rating = avg_row.scalar_one()
    avg_rating_f = float(avg_rating) if avg_rating is not None else None

    # Top tags (by usage)
    top_tag_rows = await session.execute(
        select(Tag.name, func.count(book_tags.c.book_id).label("cnt"))
        .join(book_tags, book_tags.c.tag_id == Tag.id)
        .join(Book, Book.id == book_tags.c.book_id)
        .where(Tag.user_id == user.id, Book.user_id == user.id)
        .group_by(Tag.name)
        .order_by(func.count(book_tags.c.book_id).desc())
        .limit(5)
    )
    top_tags = [TagCount(name=name, count=int(cnt)) for name, cnt in top_tag_rows.all()]

    # Finished by month — last 12 months. Use raw SQL because parameterizing
    # the to_char format string causes Postgres to treat SELECT and GROUP BY
    # expressions as different, raising a grouping error.
    month_rows = await session.execute(
        text(
            "SELECT to_char(finished_at, 'YYYY-MM') AS month, count(*) AS cnt "
            "FROM books "
            "WHERE user_id = :uid AND finished_at IS NOT NULL "
            "GROUP BY 1 ORDER BY 1"
        ),
        {"uid": user.id},
    )
    rows = {m: int(c) for m, c in month_rows.all()}

    # Build last 12 month labels ending at current month
    year = now.year
    month = now.month
    months: list[MonthCount] = []
    for _ in range(12):
        key = f"{year:04d}-{month:02d}"
        months.append(MonthCount(month=key, count=rows.get(key, 0)))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    months.reverse()

    return StatsResponse(
        total_books=total,
        by_status=by_status,
        finished_this_year=finished_this_year,
        avg_rating=avg_rating_f,
        top_tags=top_tags,
        finished_by_month=months,
    )
