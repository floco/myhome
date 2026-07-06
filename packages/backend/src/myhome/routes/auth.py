# packages/backend/src/myhome/routes/auth.py
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, HTTPException, Response
from pydantic import BaseModel

from .. import oidc
from ..deps import (
    ROLE_ORDER,
    _decode_refresh,
    create_access_token,
    create_refresh_token,
    pwd_ctx,
    require_auth,
)
from ..models_auth import ApiToken, OidcConfig, TokenDocument, User, UserDocument
from ..persistence_auth import (
    load_oidc_config,
    load_tokens,
    load_users,
    save_oidc_config,
    save_tokens,
    save_users,
)

router = APIRouter()


# ── Request / Response models ──────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    id: str
    username: str
    role: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str


class UpdateUserRequest(BaseModel):
    role: str | None = None
    password: str | None = None


class CreateTokenRequest(BaseModel):
    name: str
    role: str


class TokenInfo(BaseModel):
    id: str
    name: str
    role: str
    owner_id: str
    created_at: str
    last_used_at: str | None = None


class CreatedTokenResponse(BaseModel):
    token: str
    info: TokenInfo


class OidcStatusResponse(BaseModel):
    enabled: bool
    provider_name: str


class OidcConfigResponse(BaseModel):
    enabled: bool
    provider_name: str
    issuer: str
    client_id: str
    client_secret: str  # masked
    default_role: str
    scopes: list[str]


class OidcConfigUpdateRequest(BaseModel):
    enabled: bool
    provider_name: str
    issuer: str
    client_id: str
    client_secret: str | None = None  # omit/None keeps the existing secret
    default_role: str
    scopes: list[str] = ["openid", "profile", "email"]


# ── Core auth ─────────────────────────────────────────────────────────────

@router.post("/api/auth/login")
def login(body: LoginRequest, response: Response) -> UserInfo:
    doc = load_users()
    user = next((u for u in doc.users if u.username.lower() == body.username.lower()), None)
    if user is None or not pwd_ctx.verify(body.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password")
    _set_auth_cookies(response, user.id, user.role)
    return UserInfo(id=user.id, username=user.username, role=user.role)


@router.post("/api/auth/refresh", status_code=204)
def refresh(response: Response, myhome_refresh: str | None = Cookie(default=None)) -> None:
    if myhome_refresh is None:
        raise HTTPException(401, "No refresh token")
    payload = _decode_refresh(myhome_refresh)
    if payload is None:
        raise HTTPException(401, "Invalid or expired refresh token")
    doc = load_users()
    user = next((u for u in doc.users if u.id == payload["sub"]), None)
    if user is None:
        raise HTTPException(401, "User not found")
    response.set_cookie("myhome_access", create_access_token(user.id, user.role), httponly=True, samesite="lax")


@router.post("/api/auth/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie("myhome_access")
    response.delete_cookie("myhome_refresh")


@router.get("/api/auth/me")
def get_me(current_user: tuple[str, str] = require_auth("ro")) -> UserInfo:
    user_id, _ = current_user
    doc = load_users()
    user = next((u for u in doc.users if u.id == user_id), None)
    if user is None:
        raise HTTPException(404, "User not found")
    return UserInfo(id=user.id, username=user.username, role=user.role)


@router.put("/api/auth/me/password", status_code=204)
def change_password(
    body: ChangePasswordRequest,
    current_user: tuple[str, str] = require_auth("ro"),
) -> None:
    user_id, _ = current_user
    doc = load_users()
    user = next((u for u in doc.users if u.id == user_id), None)
    if user is None:
        raise HTTPException(404)
    if not pwd_ctx.verify(body.current_password, user.password_hash):
        raise HTTPException(400, "Current password incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(422, "Password must be at least 8 characters")
    user.password_hash = pwd_ctx.hash(body.new_password)
    save_users(doc)


# ── User management (admin only) ───────────────────────────────────────────

@router.get("/api/auth/users")
def list_users(current_user: tuple[str, str] = require_auth("admin")) -> list[UserInfo]:
    doc = load_users()
    return [UserInfo(id=u.id, username=u.username, role=u.role) for u in doc.users]


@router.post("/api/auth/users", status_code=201)
def create_user(
    body: CreateUserRequest,
    current_user: tuple[str, str] = require_auth("admin"),
) -> UserInfo:
    if body.role not in ROLE_ORDER:
        raise HTTPException(422, "Invalid role")
    if len(body.password) < 8:
        raise HTTPException(422, "Password must be at least 8 characters")
    doc = load_users()
    if any(u.username.lower() == body.username.lower() for u in doc.users):
        raise HTTPException(409, "Username already exists")
    user = User(
        id=secrets.token_hex(8),
        username=body.username,
        password_hash=pwd_ctx.hash(body.password),
        role=body.role,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    doc.users.append(user)
    save_users(doc)
    return UserInfo(id=user.id, username=user.username, role=user.role)


@router.put("/api/auth/users/{uid}", status_code=204)
def update_user(
    uid: str,
    body: UpdateUserRequest,
    current_user: tuple[str, str] = require_auth("admin"),
) -> None:
    doc = load_users()
    user = next((u for u in doc.users if u.id == uid), None)
    if user is None:
        raise HTTPException(404)
    if body.role is not None:
        if body.role not in ROLE_ORDER:
            raise HTTPException(422, "Invalid role")
        user.role = body.role
    if body.password is not None:
        if len(body.password) < 8:
            raise HTTPException(422, "Password must be at least 8 characters")
        user.password_hash = pwd_ctx.hash(body.password)
    save_users(doc)


@router.delete("/api/auth/users/{uid}", status_code=204)
def delete_user(
    uid: str,
    current_user: tuple[str, str] = require_auth("admin"),
) -> None:
    caller_id, _ = current_user
    if uid == caller_id:
        raise HTTPException(400, "Cannot delete your own account")
    doc = load_users()
    user = next((u for u in doc.users if u.id == uid), None)
    if user is None:
        raise HTTPException(404)
    doc.users = [u for u in doc.users if u.id != uid]
    save_users(doc)
    tdoc = load_tokens()
    tdoc.tokens = [t for t in tdoc.tokens if t.owner_id != uid]
    save_tokens(tdoc)


# ── API token management ───────────────────────────────────────────────────

@router.get("/api/auth/tokens")
def list_tokens(current_user: tuple[str, str] = require_auth("ro")) -> list[TokenInfo]:
    user_id, _ = current_user
    doc = load_tokens()
    return [
        TokenInfo(
            id=t.id, name=t.name, role=t.role, owner_id=t.owner_id,
            created_at=t.created_at, last_used_at=t.last_used_at,
        )
        for t in doc.tokens
        if t.owner_id == user_id
    ]


@router.post("/api/auth/tokens", status_code=201)
def create_token(
    body: CreateTokenRequest,
    current_user: tuple[str, str] = require_auth("ro"),
) -> CreatedTokenResponse:
    user_id, caller_role = current_user
    if body.role not in ROLE_ORDER:
        raise HTTPException(422, "Invalid role")
    if ROLE_ORDER[body.role] > ROLE_ORDER[caller_role]:
        raise HTTPException(422, "Token role cannot exceed your own role")
    raw_token = secrets.token_hex(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    api_token = ApiToken(
        id=secrets.token_hex(8),
        name=body.name,
        token_hash=token_hash,
        role=body.role,
        owner_id=user_id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    doc = load_tokens()
    doc.tokens.append(api_token)
    save_tokens(doc)
    info = TokenInfo(
        id=api_token.id, name=api_token.name, role=api_token.role,
        owner_id=api_token.owner_id, created_at=api_token.created_at,
    )
    return CreatedTokenResponse(token=raw_token, info=info)


@router.delete("/api/auth/tokens/{tid}", status_code=204)
def delete_token(
    tid: str,
    current_user: tuple[str, str] = require_auth("ro"),
) -> None:
    user_id, role = current_user
    doc = load_tokens()
    token = next((t for t in doc.tokens if t.id == tid), None)
    if token is None:
        raise HTTPException(404)
    if token.owner_id != user_id and role != "admin":
        raise HTTPException(403, "Cannot delete another user's token")
    doc.tokens = [t for t in doc.tokens if t.id != tid]
    save_tokens(doc)


# ── OIDC ────────────────────────────────────────────────────────────────────

def _oidc_config_response(config: OidcConfig) -> OidcConfigResponse:
    return OidcConfigResponse(
        enabled=config.enabled, provider_name=config.provider_name, issuer=config.issuer,
        client_id=config.client_id,
        client_secret="••••••••" if config.client_secret else "",
        default_role=config.default_role, scopes=config.scopes,
    )


@router.get("/api/auth/oidc/status")
def oidc_status() -> OidcStatusResponse:
    config = load_oidc_config()
    return OidcStatusResponse(enabled=config.enabled, provider_name=config.provider_name)


@router.get("/api/auth/oidc/config")
def get_oidc_config(current_user: tuple[str, str] = require_auth("admin")) -> OidcConfigResponse:
    return _oidc_config_response(load_oidc_config())


@router.put("/api/auth/oidc/config")
async def put_oidc_config(
    body: OidcConfigUpdateRequest,
    current_user: tuple[str, str] = require_auth("admin"),
) -> OidcConfigResponse:
    if body.default_role not in ROLE_ORDER:
        raise HTTPException(422, "Invalid role")
    existing = load_oidc_config()
    secret = body.client_secret if body.client_secret else existing.client_secret
    if body.enabled:
        await oidc.validate_issuer_reachable(body.issuer)
    config = OidcConfig(
        enabled=body.enabled, provider_name=body.provider_name, issuer=body.issuer,
        client_id=body.client_id, client_secret=secret,
        default_role=body.default_role, scopes=body.scopes,
    )
    save_oidc_config(config)
    oidc.clear_discovery_cache()
    return _oidc_config_response(config)


# ── Helper ─────────────────────────────────────────────────────────────────

def _set_auth_cookies(response: Response, user_id: str, role: str) -> None:
    response.set_cookie("myhome_access", create_access_token(user_id, role), httponly=True, samesite="lax")
    response.set_cookie("myhome_refresh", create_refresh_token(user_id), httponly=True, samesite="lax")
