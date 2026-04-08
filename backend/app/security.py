from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def _create_token(sub: str, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "type": token_type,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(sub: str) -> str:
    return _create_token(
        sub,
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
        "access",
    )


def create_refresh_token(sub: str) -> str:
    return _create_token(
        sub,
        timedelta(days=settings.jwt_refresh_token_expire_days),
        "refresh",
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise ValueError(f"invalid token: {e}") from e


def generate_api_key() -> str:
    return f"bt_{secrets.token_urlsafe(32)}"


def mask_api_key(key: str | None) -> str | None:
    if not key:
        return None
    if len(key) <= 10:
        return key
    return f"{key[:6]}…{key[-4:]}"
