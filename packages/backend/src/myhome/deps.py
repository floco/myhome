# packages/backend/src/myhome/deps.py
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Cookie, Depends, Header, HTTPException, Request
from jose import JWTError, jwt
from passlib.context import CryptContext

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7
ROLE_ORDER: dict[str, int] = {"ro": 0, "normal": 1, "admin": 2}

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _get_or_create_secret() -> str:
    env_val = os.environ.get("SECRET_KEY", "")
    if env_val:
        return env_val
    key_file = Path(os.environ.get("DATA_DIR", "/data")) / "secret_key"
    if key_file.exists():
        return key_file.read_text().strip()
    key = secrets.token_hex(32)
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_text(key)
    return key


def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "role": role, "exp": expire, "iss": "myhome", "type": "access"}
    return jwt.encode(payload, _get_or_create_secret(), algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": user_id, "exp": expire, "iss": "myhome", "type": "refresh"}
    return jwt.encode(payload, _get_or_create_secret(), algorithm=ALGORITHM)


def _decode_access(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, _get_or_create_secret(), algorithms=[ALGORITHM])
        return payload if payload.get("type") == "access" else None
    except JWTError:
        return None


def _decode_refresh(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, _get_or_create_secret(), algorithms=[ALGORITHM])
        return payload if payload.get("type") == "refresh" else None
    except JWTError:
        return None


def _bearer_lookup(raw_token: str) -> tuple[str, str] | None:
    """Check opaque bearer token. Returns (user_id, role) or None."""
    from .persistence_auth import load_tokens, save_tokens

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    doc = load_tokens()
    api_token = next((t for t in doc.tokens if t.token_hash == token_hash), None)
    if api_token is None:
        return None
    api_token.last_used_at = datetime.now(timezone.utc).isoformat()
    save_tokens(doc)
    return (api_token.owner_id, api_token.role)


async def _resolve_user(
    myhome_access: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> tuple[str, str] | None:
    """Return (user_id, role) from cookie JWT or Bearer token, or None."""
    if myhome_access:
        payload = _decode_access(myhome_access)
        if payload:
            return (payload["sub"], payload["role"])
    if authorization and authorization.startswith("Bearer "):
        return _bearer_lookup(authorization[7:])
    return None


async def get_user_from_request(request: Request) -> tuple[str, str] | None:
    """Extract (user_id, role) from a raw Request for use in middleware."""
    access_token = request.cookies.get("myhome_access")
    if access_token:
        payload = _decode_access(access_token)
        if payload:
            return (payload["sub"], payload["role"])
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return _bearer_lookup(auth_header[7:])
    return None


def require_auth(min_role: str = "ro"):
    """Return a FastAPI Depends that validates auth and enforces min_role."""
    async def _dep(
        user: tuple[str, str] | None = Depends(_resolve_user),
    ) -> tuple[str, str]:
        if user is None:
            raise HTTPException(401, "Authentication required")
        _, role = user
        if ROLE_ORDER.get(role, -1) < ROLE_ORDER.get(min_role, 0):
            raise HTTPException(403, "Insufficient permissions")
        return user

    return Depends(_dep)
