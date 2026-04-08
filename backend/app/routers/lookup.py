from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import get_auth_user
from ..models import User
from ..schemas import LookupResult, LookupSearchItem
from ..services.openlibrary import download_cover, lookup_isbn, search_books
from ..services.serializers import cover_url_for

router = APIRouter(tags=["lookup"])


@router.get("/lookup", response_model=LookupResult)
async def lookup(
    isbn: str = Query(..., min_length=8),
    user: User = Depends(get_auth_user),
) -> LookupResult:
    data = await lookup_isbn(isbn)
    if not data:
        raise HTTPException(status_code=404, detail="Book not found for ISBN")

    local_filename = await download_cover(isbn)
    return LookupResult(
        title=data["title"],
        author=data["author"],
        isbn=data["isbn"],
        page_count=data.get("page_count"),
        description=data.get("description"),
        cover_image_path=local_filename,
        cover_url=cover_url_for(local_filename) or data.get("cover_url"),
    )


@router.get("/lookup/search", response_model=list[LookupSearchItem])
async def lookup_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=20),
    user: User = Depends(get_auth_user),
) -> list[LookupSearchItem]:
    results = await search_books(q, limit=limit)
    return [LookupSearchItem(**r) for r in results]
