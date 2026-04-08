from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .models import User
from .security import decode_token


async def _user_from_jwt(token: str, session: AsyncSession) -> User | None:
    try:
        payload = decode_token(token)
    except ValueError:
        return None
    if payload.get("type") != "access":
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        uid = UUID(sub)
    except ValueError:
        return None
    return await session.get(User, uid)


async def _user_from_api_key(key: str, session: AsyncSession) -> User | None:
    if not key.startswith("bt_"):
        return None
    result = await session.execute(select(User).where(User.api_key == key))
    return result.scalar_one_or_none()


async def get_auth_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Authenticate via Bearer token — either a JWT access token or a bt_ API key."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1].strip()

    user: User | None = None
    if token.startswith("bt_"):
        user = await _user_from_api_key(token, session)
    else:
        user = await _user_from_jwt(token, session)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
