# packages/backend/src/myhome/schema.py
"""SQLAlchemy Core table definitions for the SQLite persistence layer.

Every persistence_x.py module's tables live here, added incrementally as
each module is converted. See the Global Constraints in
docs/superpowers/plans/2026-07-13-sqlite-persistence.md for the rules on
when a home_id/parent-id column gets a hard ForeignKey vs. stays a plain
column, and for the order_index convention.
"""
from __future__ import annotations

from sqlalchemy import MetaData

metadata = MetaData()
