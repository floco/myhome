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

from .schema import (
    consumable_categories,
    cost_categories,
    inventory_categories,
    suppliers,
    work_categories,
)

CURRENT_VERSION = 5


def _drop_kb_folders_table(conn: Connection) -> None:
    conn.execute(text("DROP TABLE IF EXISTS kb_folders"))


def _add_ha_user_id_column(conn: Connection) -> None:
    conn.execute(text("ALTER TABLE users ADD COLUMN ha_user_id VARCHAR"))


def _scope_category_tables_by_home(conn: Connection) -> None:
    # These tables were originally created with a bare `id` primary key,
    # which collides across homes since seed data reuses the same fixed
    # ids (e.g. "cat-fuel") for every home. Recreate each with the
    # (id, home_id) composite key now declared in schema.py, preserving
    # existing rows. SQLite has no ALTER TABLE for primary keys, so this
    # is a rename-recreate-copy-drop dance per table.
    for table in (cost_categories, inventory_categories, work_categories, suppliers, consumable_categories):
        name = table.name
        columns = ", ".join(c.name for c in table.columns)
        conn.execute(text(f"ALTER TABLE {name} RENAME TO {name}_old"))
        table.create(conn)
        conn.execute(text(f"INSERT INTO {name} ({columns}) SELECT {columns} FROM {name}_old"))
        conn.execute(text(f"DROP TABLE {name}_old"))


_DEFAULT_CONTACT_TYPES = [
    ("ctype-contractor", "Contractor"),
    ("ctype-supplier", "Supplier"),
    ("ctype-service", "Service Provider"),
    ("ctype-agent", "Agent"),
    ("ctype-notary", "Notary"),
    ("ctype-other", "Other"),
]


def _absorb_suppliers_into_contacts(conn: Connection) -> None:
    # cost_entries.supplier_id / works.supplier_id become contact_id, and
    # the standalone suppliers list is replaced by the new Contacts module
    # + a per-home editable Contact Types list. contact_types is a
    # brand-new table, so unlike cost_categories/work_categories/etc.
    # (whose rows already existed for any home that had ever saved
    # settings before this migration), every existing home's contact_types
    # starts genuinely empty -- it will never hit the lazy "row is None"
    # default-seed path in load_settings() again once that home already
    # has a settings row. Seed the defaults directly here so upgraded
    # homes get the same starting list a fresh home gets.
    conn.execute(text("ALTER TABLE cost_entries RENAME COLUMN supplier_id TO contact_id"))
    conn.execute(text("ALTER TABLE works RENAME COLUMN supplier_id TO contact_id"))
    conn.execute(text("DROP TABLE IF EXISTS suppliers"))
    home_ids = [r[0] for r in conn.execute(text("SELECT id FROM homes")).all()]
    for home_id in home_ids:
        for i, (type_id, name) in enumerate(_DEFAULT_CONTACT_TYPES):
            conn.execute(
                text(
                    "INSERT INTO contact_types (id, home_id, order_index, name) "
                    "VALUES (:id, :home_id, :i, :name)"
                ),
                {"id": type_id, "home_id": home_id, "i": i, "name": name},
            )


MIGRATIONS: list[tuple[int, Callable[[Connection], None]]] = [
    (2, _drop_kb_folders_table),
    (3, _add_ha_user_id_column),
    (4, _scope_category_tables_by_home),
    (5, _absorb_suppliers_into_contacts),
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
