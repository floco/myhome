# packages/backend/src/myhome/migrations.py
"""Schema-version bookkeeping for the SQLite persistence layer.

metadata.create_all() (called from db.get_engine()) handles all additive
schema changes -- new tables, and it's a no-op for tables that already
exist. This module exists for the harder case that create_all() can't
handle: column renames, type changes, backfills. MIGRATIONS is empty today
because this plan only ever adds tables; future work appends
(version, fn) pairs here as real schema alterations are needed.
"""
from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

CURRENT_VERSION = 1

MIGRATIONS: list[tuple[int, Callable[[Connection], None]]] = []


def run_migrations(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
        ))
        row = conn.execute(text("SELECT version FROM schema_version")).first()
        if row is None:
            conn.execute(
                text("INSERT INTO schema_version (version) VALUES (:v)"),
                {"v": CURRENT_VERSION},
            )
            current = CURRENT_VERSION
        else:
            current = row[0]
        for target_version, fn in MIGRATIONS:
            if target_version > current:
                fn(conn)
                conn.execute(text("UPDATE schema_version SET version = :v"), {"v": target_version})
                current = target_version
