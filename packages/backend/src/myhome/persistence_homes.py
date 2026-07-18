# packages/backend/src/myhome/persistence_homes.py
from __future__ import annotations

import os
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import get_engine
from .demo_data import seed_demo_home
from .ids import InvalidIdError
from .persistence_locations import seed_default_criteria
from .models_homes import (
    Home,
    HomesDocument,
    DEFAULT_EXISTING_MODULES,
    DEFAULT_PROJECT_MODULES,
    DEFAULT_DEMO_MODULES,
)
from .schema import home_modules as home_modules_table, homes as homes_table


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data"))


def _home_dir(home_id: str) -> Path:
    # Normalize lexically (no filesystem access -- Path.resolve() follows
    # symlinks and touches disk, which CodeQL's own path-injection sink set
    # flags even before any check runs) then verify containment within
    # homes_root. This is CodeQL's own recommended py/path-injection
    # sanitizer shape: os.path.normpath + startswith against a safe root.
    # Still needed here for the home's kb/ and *-attachments/ directories,
    # which remain plain files on disk.
    homes_root = os.path.normpath(os.path.join(str(_data_dir()), "homes"))
    candidate = os.path.normpath(os.path.join(homes_root, home_id))
    if not candidate.startswith(homes_root + os.sep):
        raise InvalidIdError(f"Invalid home_id: {home_id!r}")
    return Path(candidate)


def load_homes() -> HomesDocument:
    engine = get_engine()
    with engine.connect() as conn:
        home_rows = conn.execute(select(homes_table)).mappings().all()
        module_rows = conn.execute(
            select(home_modules_table).order_by(
                home_modules_table.c.home_id, home_modules_table.c.order_index
            )
        ).mappings().all()
    modules_by_home: dict[str, list[str]] = {}
    for r in module_rows:
        modules_by_home.setdefault(r["home_id"], []).append(r["module_id"])
    homes_list = [
        Home(
            id=r["id"],
            name=r["name"],
            type=r["type"],
            enabledModules=modules_by_home.get(r["id"], []),
            createdAt=r["created_at"],
        )
        for r in home_rows
    ]
    return HomesDocument(homes=homes_list)


def save_homes(doc: HomesDocument) -> None:
    # homes.id is a hard FK target from every per-home table (chores,
    # costs, ...), each written by its own save_x() at a different time
    # than this one -- so, unlike other modules' save_x(), this can't
    # blindly truncate-and-reinsert the whole table (that would transiently
    # delete every home's row and cascade-delete all of its data on every
    # single create_home/patch_home call). Instead: upsert every home in
    # the document, and only delete home ids that have genuinely been
    # removed from the document (i.e. delete_home()).
    engine = get_engine()
    with engine.begin() as conn:
        existing_ids = {row[0] for row in conn.execute(select(homes_table.c.id))}
        new_ids = {home.id for home in doc.homes}
        removed_ids = existing_ids - new_ids
        if removed_ids:
            conn.execute(homes_table.delete().where(homes_table.c.id.in_(removed_ids)))
        for home in doc.homes:
            stmt = sqlite_insert(homes_table).values(
                id=home.id, name=home.name, type=home.type, created_at=home.createdAt,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[homes_table.c.id],
                set_={"name": stmt.excluded.name, "type": stmt.excluded.type, "created_at": stmt.excluded.created_at},
            )
            conn.execute(stmt)
            conn.execute(home_modules_table.delete().where(home_modules_table.c.home_id == home.id))
            if home.enabledModules:
                conn.execute(home_modules_table.insert(), [
                    {"home_id": home.id, "module_id": module_id, "order_index": i}
                    for i, module_id in enumerate(home.enabledModules)
                ])


def create_home(name: str, home_type: str) -> Home:
    if home_type == "existing":
        modules = DEFAULT_EXISTING_MODULES[:]
    elif home_type == "demo":
        modules = DEFAULT_DEMO_MODULES[:]
    else:
        modules = DEFAULT_PROJECT_MODULES[:]
    home = Home(
        id=secrets.token_hex(8),
        name=name,
        type=home_type,
        enabledModules=modules,
        createdAt=datetime.now(timezone.utc).isoformat(),
    )
    _home_dir(home.id).mkdir(parents=True, exist_ok=True)
    doc = load_homes()
    doc.homes.append(home)
    save_homes(doc)

    if home_type == "project":
        seed_default_criteria(home.id)

    if home_type == "demo":
        try:
            seed_demo_home(home.id)
        except Exception:
            doc.homes = [h for h in doc.homes if h.id != home.id]
            save_homes(doc)
            home_dir = _home_dir(home.id)
            if home_dir.exists():
                shutil.rmtree(home_dir)
            raise

    return home


def patch_home(
    home_id: str,
    name: str | None,
    home_type: str | None,
    enabled_modules: list[str] | None,
) -> Home | None:
    doc = load_homes()
    home = next((h for h in doc.homes if h.id == home_id), None)
    if home is None:
        return None
    if name is not None:
        home.name = name
    if home_type is not None:
        home.type = home_type
    if enabled_modules is not None:
        home.enabledModules = enabled_modules
    save_homes(doc)
    return home


def delete_home(home_id: str) -> bool:
    doc = load_homes()
    before = len(doc.homes)
    doc.homes = [h for h in doc.homes if h.id != home_id]
    if len(doc.homes) == before:
        return False
    save_homes(doc)
    home_dir = _home_dir(home_id)
    if home_dir.exists():
        shutil.rmtree(home_dir)
    return True
