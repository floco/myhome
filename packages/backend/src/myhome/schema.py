# packages/backend/src/myhome/schema.py
"""SQLAlchemy Core table definitions for the SQLite persistence layer.

Every persistence_x.py module's tables live here, added incrementally as
each module is converted. See the Global Constraints in
docs/superpowers/plans/2026-07-13-sqlite-persistence.md for the rules on
when a home_id/parent-id column gets a hard ForeignKey vs. stays a plain
column, and for the order_index convention.
"""
from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, MetaData, String, Table, Text

metadata = MetaData()

homes = Table(
    "homes", metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("type", String, nullable=False),
    Column("created_at", String, nullable=False),
)

home_modules = Table(
    "home_modules", metadata,
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("module_id", String, primary_key=True),
    Column("order_index", Integer, nullable=False),
)

users = Table(
    "users", metadata,
    Column("id", String, primary_key=True),
    Column("username", String, nullable=False, unique=True),
    Column("password_hash", String),
    Column("role", String, nullable=False),
    Column("created_at", String, nullable=False),
    Column("auth_provider", String, nullable=False),
    Column("oidc_sub", String),
    Column("order_index", Integer, nullable=False),
)

# api_tokens.owner_id intentionally has no ForeignKey: users and tokens are
# saved by different, independently-timed save_x() calls (see the hard-FK
# rule in the plan's Global Constraints), so this stays a plain matched-in-
# Python string column exactly like today.
api_tokens = Table(
    "api_tokens", metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("token_hash", String, nullable=False),
    Column("role", String, nullable=False),
    Column("owner_id", String, nullable=False),
    Column("created_at", String, nullable=False),
    Column("last_used_at", String),
    Column("order_index", Integer, nullable=False),
)

oidc_config = Table(
    "oidc_config", metadata,
    Column("id", Integer, primary_key=True),
    Column("enabled", Boolean, nullable=False),
    Column("provider_name", String, nullable=False),
    Column("issuer", String, nullable=False),
    Column("client_id", String, nullable=False),
    Column("client_secret", String, nullable=False),
    Column("default_role", String, nullable=False),
    Column("scopes", Text, nullable=False),
)
