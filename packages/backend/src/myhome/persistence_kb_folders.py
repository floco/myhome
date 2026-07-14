# packages/backend/src/myhome/persistence_kb_folders.py
from __future__ import annotations

import uuid

from sqlalchemy import select

from .db import get_engine
from .models_kb import KBFolder
from .schema import kb_folders as kb_folders_table


def _row_to_folder(row) -> KBFolder:
    return KBFolder(id=row["id"], name=row["name"], parentId=row["parent_id"])


def list_folders(home_id: str) -> list[KBFolder]:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(kb_folders_table)
            .where(kb_folders_table.c.home_id == home_id)
            .order_by(kb_folders_table.c.name)
        ).mappings().all()
    return [_row_to_folder(r) for r in rows]


def get_folder(home_id: str, folder_id: str) -> KBFolder | None:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            select(kb_folders_table).where(
                kb_folders_table.c.home_id == home_id,
                kb_folders_table.c.id == folder_id,
            )
        ).mappings().first()
    return _row_to_folder(row) if row else None


def create_folder(home_id: str, name: str, parent_id: str | None = None) -> KBFolder:
    folder = KBFolder(id=str(uuid.uuid4()), name=name, parentId=parent_id)
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(kb_folders_table.insert(), {
            "id": folder.id, "home_id": home_id, "parent_id": folder.parentId, "name": folder.name,
        })
    return folder


def rename_folder(home_id: str, folder_id: str, name: str) -> KBFolder | None:
    folder = get_folder(home_id, folder_id)
    if folder is None:
        return None
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            kb_folders_table.update()
            .where(kb_folders_table.c.home_id == home_id, kb_folders_table.c.id == folder_id)
            .values(name=name)
        )
    folder.name = name
    return folder


def move_folder(home_id: str, folder_id: str, parent_id: str | None) -> KBFolder | None:
    folder = get_folder(home_id, folder_id)
    if folder is None:
        return None
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            kb_folders_table.update()
            .where(kb_folders_table.c.home_id == home_id, kb_folders_table.c.id == folder_id)
            .values(parent_id=parent_id)
        )
    folder.parentId = parent_id
    return folder


def delete_folder(home_id: str, folder_id: str) -> bool:
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            kb_folders_table.delete().where(
                kb_folders_table.c.home_id == home_id,
                kb_folders_table.c.id == folder_id,
            )
        )
    return result.rowcount > 0


def would_create_cycle(home_id: str, folder_id: str, new_parent_id: str) -> bool:
    """True if setting folder_id's parent to new_parent_id would create a cycle
    (new_parent_id is folder_id itself, or one of folder_id's descendants)."""
    if new_parent_id == folder_id:
        return True
    folders = {f.id: f for f in list_folders(home_id)}
    current: str | None = new_parent_id
    seen: set[str] = set()
    while current is not None:
        if current == folder_id:
            return True
        if current in seen:
            return False
        seen.add(current)
        folder = folders.get(current)
        current = folder.parentId if folder else None
    return False
