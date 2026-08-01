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

import uuid
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

CURRENT_VERSION = 7


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


_DEFAULT_INSURANCE_CATEGORIES = [
    ("icat-home", "Home", "🏠"),
    ("icat-auto", "Auto", "🚗"),
    ("icat-health", "Health", "⚕️"),
    ("icat-life", "Life", "❤️"),
    ("icat-travel", "Travel", "✈️"),
    ("icat-liability", "Liability", "🛡️"),
]


def _add_insurance_support(conn: Connection) -> None:
    # insurance_categories is a brand-new table -- create_all() already
    # created it (empty) for every home before this migration runs, same
    # situation contact_types was in for migration 5. Back-fill defaults so
    # upgraded homes start with the same category list a fresh home gets;
    # load_settings()'s lazy "row is None" default-seed path won't fire
    # again for any home whose settings row already exists.
    conn.execute(text("ALTER TABLE cost_entries ADD COLUMN source_module VARCHAR"))
    conn.execute(text("ALTER TABLE cost_entries ADD COLUMN source_id VARCHAR"))
    home_ids = [r[0] for r in conn.execute(text("SELECT id FROM homes")).all()]
    for home_id in home_ids:
        for i, (cat_id, name, emoji) in enumerate(_DEFAULT_INSURANCE_CATEGORIES):
            conn.execute(
                text(
                    "INSERT INTO insurance_categories (id, home_id, order_index, name, emoji) "
                    "VALUES (:id, :home_id, :i, :name, :emoji)"
                ),
                {"id": cat_id, "home_id": home_id, "i": i, "name": name, "emoji": emoji},
            )
        existing = conn.execute(
            text("SELECT 1 FROM cost_categories WHERE home_id = :h AND id = 'cat-insurance'"),
            {"h": home_id},
        ).first()
        if existing is None:
            count = conn.execute(
                text("SELECT COUNT(*) FROM cost_categories WHERE home_id = :h"), {"h": home_id}
            ).scalar()
            conn.execute(
                text(
                    "INSERT INTO cost_categories (id, home_id, order_index, name, emoji, unit, color) "
                    "VALUES ('cat-insurance', :h, :i, 'Insurance', '🛡️', NULL, '#7a5cc4')"
                ),
                {"h": home_id, "i": count},
            )


def _add_inventory_owner_store_and_category_id(conn: Connection) -> None:
    # inventory_items.category (free-text) becomes category_id, referencing
    # inventory_categories the same way Works/Costs/Consumables already
    # reference their categories. owner_id/store_id are brand new, always
    # NULL for pre-existing rows -- see the design spec at
    # docs/superpowers/specs/2026-08-01-inventory-owner-store-design.md.
    conn.execute(text("ALTER TABLE inventory_items ADD COLUMN owner_id VARCHAR"))
    conn.execute(text("ALTER TABLE inventory_items ADD COLUMN store_id VARCHAR"))
    conn.execute(text("ALTER TABLE inventory_items ADD COLUMN category_id VARCHAR"))

    home_ids = [r[0] for r in conn.execute(text("SELECT id FROM homes")).all()]
    for home_id in home_ids:
        existing = conn.execute(
            text("SELECT id, name FROM inventory_categories WHERE home_id = :h"),
            {"h": home_id},
        ).all()
        by_name = {name.strip().lower(): cat_id for cat_id, name in existing}
        next_order = len(existing)

        rows = conn.execute(
            text("SELECT id, category FROM inventory_items WHERE home_id = :h"),
            {"h": home_id},
        ).all()
        for item_id, category_text in rows:
            text_val = (category_text or "").strip()
            if not text_val:
                continue
            key = text_val.lower()
            cat_id = by_name.get(key)
            if cat_id is None:
                cat_id = str(uuid.uuid4())
                conn.execute(
                    text(
                        "INSERT INTO inventory_categories (id, home_id, order_index, name) "
                        "VALUES (:id, :h, :i, :name)"
                    ),
                    {"id": cat_id, "h": home_id, "i": next_order, "name": text_val},
                )
                by_name[key] = cat_id
                next_order += 1
            conn.execute(
                text("UPDATE inventory_items SET category_id = :cid WHERE id = :iid"),
                {"cid": cat_id, "iid": item_id},
            )


MIGRATIONS: list[tuple[int, Callable[[Connection], None]]] = [
    (2, _drop_kb_folders_table),
    (3, _add_ha_user_id_column),
    (4, _scope_category_tables_by_home),
    (5, _absorb_suppliers_into_contacts),
    (6, _add_insurance_support),
    (7, _add_inventory_owner_store_and_category_id),
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
