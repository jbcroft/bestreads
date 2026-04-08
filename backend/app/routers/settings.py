from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_auth_user
from ..models import User
from ..schemas import ApiKeyMasked, ApiKeyPlain
from ..security import generate_api_key, mask_api_key

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/api-key", response_model=ApiKeyMasked)
async def view_api_key(user: User = Depends(get_auth_user)) -> ApiKeyMasked:
    return ApiKeyMasked(api_key=mask_api_key(user.api_key))


@router.post("/api-key/regenerate", response_model=ApiKeyPlain)
async def regenerate_api_key(
    user: User = Depends(get_auth_user),
    session: AsyncSession = Depends(get_session),
) -> ApiKeyPlain:
    new_key = generate_api_key()
    user.api_key = new_key
    session.add(user)
    await session.commit()
    return ApiKeyPlain(api_key=new_key)
