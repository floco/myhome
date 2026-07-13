# packages/backend/src/myhome/schema.py
"""SQLAlchemy Core table definitions for the SQLite persistence layer.

Every persistence_x.py module's tables live here, added incrementally as
each module is converted. See the Global Constraints in
docs/superpowers/plans/2026-07-13-sqlite-persistence.md for the rules on
when a home_id/parent-id column gets a hard ForeignKey vs. stays a plain
column, and for the order_index convention.
"""
from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table

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
