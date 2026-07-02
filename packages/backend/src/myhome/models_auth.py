# packages/backend/src/myhome/models_auth.py
from __future__ import annotations
from pydantic import BaseModel


class User(BaseModel):
    id: str
    username: str
    password_hash: str
    role: str  # "admin" | "normal" | "ro"
    created_at: str  # ISO-8601


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
