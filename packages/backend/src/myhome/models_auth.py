# packages/backend/src/myhome/models_auth.py
from __future__ import annotations
from pydantic import BaseModel


class User(BaseModel):
    id: str
    username: str
    password_hash: str | None = None
    role: str  # "admin" | "normal" | "ro"
    created_at: str  # ISO-8601
    auth_provider: str = "local"  # "local" | "oidc"


class UserDocument(BaseModel):
    version: int = 1
    users: list[User] = []


class ApiToken(BaseModel):
    id: str
    name: str
    token_hash: str  # sha256 hex of the raw token
    role: str  # "admin" | "normal" | "ro"
    owner_id: str
    created_at: str  # ISO-8601
    last_used_at: str | None = None


class TokenDocument(BaseModel):
    version: int = 1
    tokens: list[ApiToken] = []


class OidcConfig(BaseModel):
    enabled: bool = False
    provider_name: str = ""
    issuer: str = ""
    client_id: str = ""
    client_secret: str = ""
    default_role: str = "normal"  # "admin" | "normal" | "ro"
    scopes: list[str] = ["openid", "profile", "email"]


class OidcConfigDocument(BaseModel):
    version: int = 1
    config: OidcConfig = OidcConfig()
