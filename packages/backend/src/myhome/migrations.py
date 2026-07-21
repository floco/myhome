# packages/backend/src/myhome/migrations.py
"""Schema-version bookkeeping for the SQLite persistence layer.

metadata.create_all() (called from db.get_engine()) handles all additive
schema changes -- new tables, and it's a no-op for tables that already
exist. This module exists for the harder case that create_all() can't
handle: column renames, type changes, backfills, or drops. Fresh installs
start at CURRENT_VERSION and skip every entry in MIGRATIONS below; only
databases created before a given migration was added actually run it.
"""
from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

CURRENT_VERSION = 3


def _drop_kb_folders_table(conn: Connection) -> None:
    conn.execute(text("DROP TABLE IF EXISTS kb_folders"))


def _add_ha_user_id_column(conn: Connection) -> None:
    conn.execute(text("ALTER TABLE users ADD COLUMN ha_user_id VARCHAR"))


MIGRATIONS: list[tuple[int, Callable[[Connection], None]]] = [
    (2, _drop_kb_folders_table),
    (3, _add_ha_user_id_column),
]


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
