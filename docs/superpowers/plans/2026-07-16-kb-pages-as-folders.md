# KB Pages-as-Folders Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the KB module's separate `kb_folders` data type with unified pages that can contain child pages (Notion-style), add a per-page icon, live-updating child-page links, and cascading soft-delete with a Trash view.

**Architecture:** `KBEntry` (still file-based markdown+frontmatter) gains `parentId`, `icon`, `order`, `deletedAt`. `kb_folders` (SQLite) and all folder-specific code are deleted. The frontend tree (`KBTree.svelte`) collapses folders and entries into one recursive "page" concept. `MarkdownEditor` gains live child-page link rendering and a `/page` slash command. Routing gains `#/kb/<id>` deep links.

**Tech Stack:** FastAPI + Pydantic + markdown-frontmatter files (backend), Svelte 5 runes + vitest (frontend). No new dependencies.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-16-kb-pages-as-folders-design.md` — every requirement below traces back to a section there.
- No migration of existing `kb_folders` data (fresh start); existing KB entries keep their content and become top-level (`parentId: null`).
- KB pages remain markdown files on disk — explicitly not moving to SQLite this pass.
- Trash purge is manual only (no auto-expiry background job).
- Child-page links (`#/kb/<id>`) are live references: displayed text is resolved from the current page title/icon at render time, not frozen into the stored markdown.
- Follow existing code style: this codebase does not use docstrings/comments except where a non-obvious constraint needs explaining (see `_home_dir`'s path-injection comment in `persistence_kb.py` as the bar).

---

## Task 1: Backend data model + persistence layer

**Files:**
- Modify: `packages/backend/src/myhome/schema.py:313-319` (remove `kb_folders` table)
- Modify: `packages/backend/src/myhome/migrations.py` (drop `kb_folders` table for upgrading installs)
- Modify: `packages/backend/src/myhome/models_kb.py` (full rewrite)
- Modify: `packages/backend/src/myhome/persistence_kb.py` (full rewrite)
- Delete: `packages/backend/src/myhome/persistence_kb_folders.py`
- Modify: `packages/backend/tests/test_kb_persistence.py` (add new tests, remove none — all existing tests still pass unchanged)
- Delete: `packages/backend/tests/test_kb_folders.py`
- (`packages/backend/tests/test_kb.py` is not touched in this task — Task 2 replaces it wholesale)

**Interfaces:**
- Produces (used by Task 2's routes and Task 3's MCP tools):
  - `KBEntry(id, title, content, createdAt, updatedAt, attachments, parentId, icon, order, deletedAt)` — pydantic model, `icon: str = "📄"`, `order: int = 0`, `parentId: str | None = None`, `deletedAt: str | None = None`.
  - `KBDocument(version, entries)`, `KBCreate(title, content, parentId, icon)`, `KBUpdate(title, content, parentId, icon)` — all `str | None = None` except `content: str = ""`, `icon: str = "📄"` on `KBCreate`.
  - `load_all(home_id, include_deleted=False) -> list[KBEntry]`
  - `load_entry(home_id, id) -> KBEntry | None`
  - `save_entry(home_id, entry) -> None`
  - `delete_entry(home_id, id) -> bool` (hard delete: unlinks file + attachments dir — used only for permanent trash deletion from Task 2 onward)
  - `soft_delete_subtree(home_id, id) -> list[str]` (returns affected ids, id + all live descendants)
  - `restore_subtree(home_id, id) -> list[str]` (returns restored ids)
  - `list_trash(home_id) -> list[KBEntry]`
  - `empty_trash(home_id) -> list[str]`
  - `would_create_cycle(home_id, entry_id, new_parent_id) -> bool`
  - `next_order(home_id, parent_id) -> int`
  - `reorder_siblings(home_id, parent_id, ordered_ids) -> None`
  - `get_attachment_path`, `save_attachment`, `delete_attachment`, `generate_pdf_thumbnail` — unchanged signatures, unchanged behavior.

- [ ] **Step 1: Write the failing tests**

Add to `packages/backend/tests/test_kb_persistence.py` (append after the existing `test_title_with_colon_round_trips` test — the existing tests above it are untouched):

```python
from myhome.persistence_kb import (
    descendant_ids,
    empty_trash,
    list_trash,
    next_order,
    reorder_siblings,
    restore_subtree,
    soft_delete_subtree,
    would_create_cycle,
)


def test_icon_defaults_to_page_emoji(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_entry(HOME_ID, make_entry())
    assert load_entry(HOME_ID, "e1").icon == "📄"


def test_custom_icon_round_trips(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    entry = make_entry()
    entry.icon = "🔧"
    save_entry(HOME_ID, entry)
    assert load_entry(HOME_ID, "e1").icon == "🔧"


def test_parent_id_round_trips(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_entry(HOME_ID, make_entry())
    child = make_entry()
    child.id = "child"
    child.parentId = "e1"
    save_entry(HOME_ID, child)
    assert load_entry(HOME_ID, "child").parentId == "e1"


def test_entry_without_parent_id_defaults_to_none(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_entry(HOME_ID, make_entry())
    assert load_entry(HOME_ID, "e1").parentId is None


def test_legacy_folder_id_frontmatter_ignored_on_read(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    kb_dir = tmp_path / "homes" / HOME_ID / "kb"
    kb_dir.mkdir(parents=True, exist_ok=True)
    (kb_dir / "legacy.md").write_text(
        "---\nid: legacy\ntitle: Old entry\ncreatedAt: 2026-01-01T00:00:00Z\n"
        "updatedAt: 2026-01-01T00:00:00Z\nfolderId: some-old-folder\n---\n\nBody text",
        encoding="utf-8",
    )
    entry = load_entry(HOME_ID, "legacy")
    assert entry is not None
    assert entry.parentId is None


def test_missing_order_migrated_sequentially_by_created_at(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    kb_dir = tmp_path / "homes" / HOME_ID / "kb"
    kb_dir.mkdir(parents=True, exist_ok=True)
    for id_, created in [("a", "2026-01-02T00:00:00Z"), ("b", "2026-01-01T00:00:00Z")]:
        (kb_dir / f"{id_}.md").write_text(
            f"---\nid: {id_}\ntitle: {id_}\ncreatedAt: {created}\nupdatedAt: {created}\n---\n\n",
            encoding="utf-8",
        )
    entries = load_all(HOME_ID)
    by_id = {e.id: e for e in entries}
    assert by_id["b"].order < by_id["a"].order
    assert load_entry(HOME_ID, "b").order == by_id["b"].order


def test_deleted_entries_excluded_by_default(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_entry(HOME_ID, make_entry())
    soft_delete_subtree(HOME_ID, "e1")
    assert load_all(HOME_ID) == []
    assert len(load_all(HOME_ID, include_deleted=True)) == 1


def test_soft_delete_cascades_to_descendants(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    p = make_entry(); p.id = "p"
    c1 = make_entry(); c1.id = "c1"; c1.parentId = "p"
    c2 = make_entry(); c2.id = "c2"; c2.parentId = "c1"
    save_entry(HOME_ID, p); save_entry(HOME_ID, c1); save_entry(HOME_ID, c2)
    affected = soft_delete_subtree(HOME_ID, "p")
    assert set(affected) == {"p", "c1", "c2"}
    assert load_all(HOME_ID) == []


def test_descendant_ids_finds_grandchildren(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    p = make_entry(); p.id = "p"
    c1 = make_entry(); c1.id = "c1"; c1.parentId = "p"
    c2 = make_entry(); c2.id = "c2"; c2.parentId = "c1"
    save_entry(HOME_ID, p); save_entry(HOME_ID, c1); save_entry(HOME_ID, c2)
    assert set(descendant_ids(HOME_ID, "p")) == {"c1", "c2"}


def test_restore_brings_back_cascaded_descendants(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    p = make_entry(); p.id = "p"
    c1 = make_entry(); c1.id = "c1"; c1.parentId = "p"
    save_entry(HOME_ID, p); save_entry(HOME_ID, c1)
    soft_delete_subtree(HOME_ID, "p")
    restored = restore_subtree(HOME_ID, "p")
    assert set(restored) == {"p", "c1"}
    assert {e.id for e in load_all(HOME_ID)} == {"p", "c1"}


def test_restore_does_not_touch_already_live_descendant(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    p = make_entry(); p.id = "p"
    c1 = make_entry(); c1.id = "c1"; c1.parentId = "p"
    save_entry(HOME_ID, p); save_entry(HOME_ID, c1)
    soft_delete_subtree(HOME_ID, "p")
    restore_subtree(HOME_ID, "c1")
    restored = restore_subtree(HOME_ID, "p")
    assert "c1" not in restored
    assert "p" in restored


def test_list_trash_returns_only_deleted(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    a = make_entry(); a.id = "a"
    b = make_entry(); b.id = "b"
    save_entry(HOME_ID, a); save_entry(HOME_ID, b)
    soft_delete_subtree(HOME_ID, "a")
    assert [e.id for e in list_trash(HOME_ID)] == ["a"]


def test_empty_trash_permanently_removes_files(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_entry(HOME_ID, make_entry())
    soft_delete_subtree(HOME_ID, "e1")
    deleted = empty_trash(HOME_ID)
    assert deleted == ["e1"]
    assert not (tmp_path / "homes" / HOME_ID / "kb" / "e1.md").exists()


def test_would_create_cycle_detects_self(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_entry(HOME_ID, make_entry())
    assert would_create_cycle(HOME_ID, "e1", "e1") is True


def test_would_create_cycle_detects_descendant(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    a = make_entry(); a.id = "a"
    b = make_entry(); b.id = "b"; b.parentId = "a"
    save_entry(HOME_ID, a); save_entry(HOME_ID, b)
    assert would_create_cycle(HOME_ID, "a", "b") is True


def test_would_create_cycle_false_for_unrelated(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    a = make_entry(); a.id = "a"
    b = make_entry(); b.id = "b"
    save_entry(HOME_ID, a); save_entry(HOME_ID, b)
    assert would_create_cycle(HOME_ID, "a", "b") is False


def test_next_order_appends_after_existing_siblings(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    a = make_entry(); a.id = "a"; a.order = 0
    b = make_entry(); b.id = "b"; b.order = 1
    save_entry(HOME_ID, a); save_entry(HOME_ID, b)
    assert next_order(HOME_ID, None) == 2


def test_next_order_zero_for_empty_parent(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert next_order(HOME_ID, None) == 0


def test_reorder_siblings_sets_sequential_order(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    a = make_entry(); a.id = "a"; a.order = 0
    b = make_entry(); b.id = "b"; b.order = 1
    c = make_entry(); c.id = "c"; c.order = 2
    save_entry(HOME_ID, a); save_entry(HOME_ID, b); save_entry(HOME_ID, c)
    reorder_siblings(HOME_ID, None, ["c", "a", "b"])
    orders = {e.id: e.order for e in load_all(HOME_ID)}
    assert orders == {"c": 0, "a": 1, "b": 2}
```

Leave `packages/backend/tests/test_kb.py` untouched in this task — it still references the old `folderId`/`KBFolder` API and will fail once `models_kb.py` changes below, but Task 2 replaces its full contents wholesale (including dropping the two now-redundant `folderId` round-trip tests duplicated by the persistence-level tests above), so editing it here would just be overwritten. Do not run `test_kb.py` until Task 2.

Delete `packages/backend/tests/test_kb_folders.py` entirely (its 14 tests exercise `persistence_kb_folders.py`, which this task deletes).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_kb_persistence.py -v`
Expected: FAIL — `ImportError: cannot import name 'descendant_ids' from 'myhome.persistence_kb'` (and similar for the other new names).

- [ ] **Step 3: Remove `kb_folders` from schema.py**

In `packages/backend/src/myhome/schema.py`, delete lines 313-319:

```python
kb_folders = Table(
    "kb_folders", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("parent_id", String, ForeignKey("kb_folders.id")),
    Column("name", String, nullable=False),
)
```

- [ ] **Step 4: Add the schema migration**

Replace the full contents of `packages/backend/src/myhome/migrations.py`:

```python
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

CURRENT_VERSION = 2


def _drop_kb_folders_table(conn: Connection) -> None:
    conn.execute(text("DROP TABLE IF EXISTS kb_folders"))


MIGRATIONS: list[tuple[int, Callable[[Connection], None]]] = [
    (2, _drop_kb_folders_table),
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
```

- [ ] **Step 5: Rewrite models_kb.py**

Replace the full contents of `packages/backend/src/myhome/models_kb.py`:

```python
from __future__ import annotations
from pydantic import BaseModel


class KBEntry(BaseModel):
    id: str
    title: str
    content: str = ""
    createdAt: str
    updatedAt: str
    attachments: list[str] = []
    parentId: str | None = None
    icon: str = "📄"
    order: int = 0
    deletedAt: str | None = None


class KBDocument(BaseModel):
    version: int = 1
    entries: list[KBEntry] = []


class KBTrashDocument(BaseModel):
    entries: list[KBEntry] = []


class KBCreate(BaseModel):
    title: str
    content: str = ""
    parentId: str | None = None
    icon: str = "📄"


class KBUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    parentId: str | None = None
    icon: str | None = None


class KBReorder(BaseModel):
    parentId: str | None = None
    orderedIds: list[str]
```

- [ ] **Step 6: Rewrite persistence_kb.py**

Replace the full contents of `packages/backend/src/myhome/persistence_kb.py`:

```python
from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .ids import InvalidIdError
from .models_kb import KBEntry

_log = logging.getLogger(__name__)

_MISSING_ORDER = -1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _home_dir(home_id: str) -> Path:
    # Normalize lexically (no filesystem access -- Path.resolve() follows
    # symlinks and touches disk, which CodeQL's own path-injection sink set
    # flags even before any check runs) then verify containment within
    # homes_root. This is CodeQL's own recommended py/path-injection
    # sanitizer shape: os.path.normpath + startswith against a safe root.
    homes_root = os.path.normpath(os.path.join(os.environ.get("DATA_DIR", "/data"), "homes"))
    candidate = os.path.normpath(os.path.join(homes_root, home_id))
    if not candidate.startswith(homes_root + os.sep):
        raise InvalidIdError(f"Invalid home_id: {home_id!r}")
    return Path(candidate)


def _kb_dir(home_id: str) -> Path:
    return _home_dir(home_id) / "kb"


def _entry_path(home_id: str, id: str) -> Path:
    base = os.path.normpath(str(_kb_dir(home_id)))
    candidate = os.path.normpath(os.path.join(base, f"{id}.md"))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid id: {id!r}")
    return Path(candidate)


def _attachments_dir(home_id: str, entry_id: str) -> Path:
    # Same inline lexical-normalize-then-verify-containment shape as
    # _home_dir() above -- entry_id is validated at the route layer too, but
    # CodeQL's taint tracker doesn't credit a separate validator function as
    # sanitizing the value used here.
    base = os.path.normpath(str(_home_dir(home_id) / "kb-attachments"))
    candidate = os.path.normpath(os.path.join(base, entry_id))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid entry_id: {entry_id!r}")
    return Path(candidate)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    meta: dict = {}
    for line in text[4:end].splitlines():
        if ": " in line:
            key, _, val = line.partition(": ")
            meta[key.strip()] = val.strip()
    body = text[end + 5:]
    return meta, body


def _build_file(entry: KBEntry) -> str:
    title = entry.title.replace("\n", " ")
    lines = [
        "---",
        f"id: {entry.id}",
        f"title: {title}",
        f"createdAt: {entry.createdAt}",
        f"updatedAt: {entry.updatedAt}",
        f"icon: {entry.icon}",
        f"order: {entry.order}",
    ]
    if entry.attachments:
        lines.append(f"attachments: {','.join(entry.attachments)}")
    if entry.parentId:
        lines.append(f"parentId: {entry.parentId}")
    if entry.deletedAt:
        lines.append(f"deletedAt: {entry.deletedAt}")
    lines += ["---", "", entry.content]
    return "\n".join(lines)


def _read_entry_file(path: Path) -> KBEntry | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    meta, body = _parse_frontmatter(text)
    if not meta.get("id") or not meta.get("title"):
        return None
    att_str = meta.get("attachments", "")
    attachments = [a for a in att_str.split(",") if a] if att_str else []
    order_raw = meta.get("order")
    return KBEntry(
        id=meta["id"],
        title=meta["title"],
        content=body.lstrip("\n"),
        createdAt=meta.get("createdAt", ""),
        updatedAt=meta.get("updatedAt", ""),
        attachments=attachments,
        parentId=meta.get("parentId") or None,
        icon=meta.get("icon") or "📄",
        order=int(order_raw) if order_raw not in (None, "") else _MISSING_ORDER,
        deletedAt=meta.get("deletedAt") or None,
    )


def _migrate_missing_order(home_id: str, entries: list[KBEntry]) -> None:
    missing = [e for e in entries if e.order == _MISSING_ORDER]
    if not missing:
        return
    missing.sort(key=lambda e: e.createdAt)
    by_parent_max: dict[str | None, int] = {}
    for e in entries:
        if e.order != _MISSING_ORDER:
            by_parent_max[e.parentId] = max(by_parent_max.get(e.parentId, -1), e.order)
    for e in missing:
        next_val = by_parent_max.get(e.parentId, -1) + 1
        by_parent_max[e.parentId] = next_val
        e.order = next_val
        save_entry(home_id, e)


def load_all(home_id: str, include_deleted: bool = False) -> list[KBEntry]:
    d = _kb_dir(home_id)
    if not d.exists():
        return []
    entries = [e for path in d.glob("*.md") if (e := _read_entry_file(path))]
    _migrate_missing_order(home_id, entries)
    if not include_deleted:
        entries = [e for e in entries if e.deletedAt is None]
    entries.sort(key=lambda e: (e.parentId or "", e.order))
    return entries


def load_entry(home_id: str, id: str) -> KBEntry | None:
    return _read_entry_file(_entry_path(home_id, id))


def save_entry(home_id: str, entry: KBEntry) -> None:
    d = _kb_dir(home_id)
    d.mkdir(parents=True, exist_ok=True)
    path = _entry_path(home_id, entry.id)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(_build_file(entry), encoding="utf-8")
    tmp.replace(path)


def delete_entry(home_id: str, id: str) -> bool:
    path = _entry_path(home_id, id)
    if not path.exists():
        return False
    path.unlink()
    att_dir = _attachments_dir(home_id, id)
    if att_dir.exists():
        shutil.rmtree(att_dir)
    return True


def _children_map(entries: list[KBEntry]) -> dict[str | None, list[KBEntry]]:
    m: dict[str | None, list[KBEntry]] = {}
    for e in entries:
        m.setdefault(e.parentId, []).append(e)
    return m


def descendant_ids(home_id: str, id: str) -> list[str]:
    entries = load_all(home_id, include_deleted=True)
    children = _children_map(entries)
    result: list[str] = []
    stack = [id]
    while stack:
        current = stack.pop()
        for child in children.get(current, []):
            result.append(child.id)
            stack.append(child.id)
    return result


def soft_delete_subtree(home_id: str, id: str) -> list[str]:
    if load_entry(home_id, id) is None:
        return []
    ids = [id] + descendant_ids(home_id, id)
    now = _now()
    affected: list[str] = []
    for eid in ids:
        e = load_entry(home_id, eid)
        if e is not None and e.deletedAt is None:
            e.deletedAt = now
            save_entry(home_id, e)
            affected.append(eid)
    return affected


def restore_subtree(home_id: str, id: str) -> list[str]:
    if load_entry(home_id, id) is None:
        return []
    ids = [id] + descendant_ids(home_id, id)
    restored: list[str] = []
    for eid in ids:
        e = load_entry(home_id, eid)
        if e is not None and e.deletedAt is not None:
            e.deletedAt = None
            save_entry(home_id, e)
            restored.append(eid)
    return restored


def list_trash(home_id: str) -> list[KBEntry]:
    return [e for e in load_all(home_id, include_deleted=True) if e.deletedAt is not None]


def empty_trash(home_id: str) -> list[str]:
    deleted: list[str] = []
    for e in list_trash(home_id):
        if delete_entry(home_id, e.id):
            deleted.append(e.id)
    return deleted


def would_create_cycle(home_id: str, entry_id: str, new_parent_id: str) -> bool:
    """True if setting entry_id's parent to new_parent_id would create a cycle
    (new_parent_id is entry_id itself, or one of entry_id's descendants)."""
    if new_parent_id == entry_id:
        return True
    entries = {e.id: e for e in load_all(home_id, include_deleted=True)}
    current: str | None = new_parent_id
    seen: set[str] = set()
    while current is not None:
        if current == entry_id:
            return True
        if current in seen:
            return False
        seen.add(current)
        e = entries.get(current)
        current = e.parentId if e else None
    return False


def next_order(home_id: str, parent_id: str | None) -> int:
    siblings = [e for e in load_all(home_id) if e.parentId == parent_id]
    return max((e.order for e in siblings), default=-1) + 1


def reorder_siblings(home_id: str, parent_id: str | None, ordered_ids: list[str]) -> None:
    siblings = {e.id: e for e in load_all(home_id) if e.parentId == parent_id}
    for index, eid in enumerate(ordered_ids):
        e = siblings.get(eid)
        if e is not None:
            e.order = index
            save_entry(home_id, e)


def get_attachment_path(home_id: str, entry_id: str, filename: str) -> Path:
    base = os.path.normpath(str(_attachments_dir(home_id, entry_id)))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    return Path(candidate)


def save_attachment(home_id: str, entry_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(home_id, entry_id)
    base = os.path.normpath(str(path))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    path.mkdir(parents=True, exist_ok=True)
    Path(candidate).write_bytes(data)


def delete_attachment(home_id: str, entry_id: str, filename: str) -> bool:
    base = os.path.normpath(str(_attachments_dir(home_id, entry_id)))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    path = Path(candidate)
    if not path.exists():
        return False
    path.unlink()
    thumb = path.with_name(path.name + ".thumb.jpg")
    if thumb.exists():
        thumb.unlink()
    return True


def generate_pdf_thumbnail(pdf_path: Path, thumb_path: Path) -> None:
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        page = doc[0]
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat)
        pix.save(str(thumb_path))
    except Exception as exc:
        _log.warning("PDF thumbnail generation failed for %s: %s", pdf_path, exc)
```

- [ ] **Step 7: Delete persistence_kb_folders.py and test_kb_folders.py**

```bash
rm packages/backend/src/myhome/persistence_kb_folders.py
rm packages/backend/tests/test_kb_folders.py
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_kb_persistence.py -v`
Expected: PASS (all tests, including the pre-existing ones which are untouched by the rewrite).

Note: `test_kb.py` will still fail at this point (it imports `KBFolder` and hits `/kb/folders` routes that Task 2 removes) — that's expected and fixed in Task 2. Do not run the full test suite yet.

- [ ] **Step 9: Commit**

```bash
git add packages/backend/src/myhome/schema.py packages/backend/src/myhome/migrations.py \
  packages/backend/src/myhome/models_kb.py packages/backend/src/myhome/persistence_kb.py \
  packages/backend/tests/test_kb_persistence.py
git rm packages/backend/src/myhome/persistence_kb_folders.py packages/backend/tests/test_kb_folders.py
git commit -m "feat(kb): add parentId/icon/order/deletedAt to KBEntry, drop kb_folders"
```

---

## Task 2: Backend API routes

Depends on Task 1 (`models_kb.py`, `persistence_kb.py`).

**Files:**
- Modify: `packages/backend/src/myhome/routes/kb.py` (full rewrite)
- Modify: `packages/backend/tests/test_kb.py` (full rewrite of the folder-related tests; attachment tests at lines 68-153 of the current file are unchanged and stay as-is)

**Interfaces:**
- Consumes: everything listed under Task 1's Produces.
- Produces (used by Task 8's frontend `kbStore.svelte.ts` via HTTP, and indirectly by Task 3's MCP layer which stays independent):
  - `GET /api/homes/{home_id}/kb` → `KBDocument{entries}` (trashed excluded)
  - `POST /api/homes/{home_id}/kb` body `KBCreate` → `KBEntry`, 201
  - `PUT /api/homes/{home_id}/kb/{id}` body `KBUpdate` → 204
  - `PUT /api/homes/{home_id}/kb/reorder` body `KBReorder` → 204
  - `DELETE /api/homes/{home_id}/kb/{id}` → `{"deletedCount": int}`, 200 (soft delete, cascades)
  - `GET /api/homes/{home_id}/kb/trash` → `KBTrashDocument{entries}`
  - `POST /api/homes/{home_id}/kb/trash/{id}/restore` → `{"restoredCount": int}`, 200
  - `DELETE /api/homes/{home_id}/kb/trash/{id}` → 204 (permanent)
  - `POST /api/homes/{home_id}/kb/trash/empty` → `{"deletedCount": int}`, 200
  - Attachment routes unchanged: `POST/GET/DELETE /api/homes/{home_id}/kb/{id}/attachments...`

- [ ] **Step 1: Write the failing tests**

Replace the full contents of `packages/backend/tests/test_kb.py`:

```python
import pytest
from myhome.models_kb import KBEntry
from myhome.persistence_kb import save_entry


def make_entry() -> KBEntry:
    return KBEntry(
        id="e1",
        title="How to paint",
        content="# Painting",
        createdAt="2026-06-28T10:00:00Z",
        updatedAt="2026-06-28T10:00:00Z",
    )


def test_get_kb_empty_when_no_dir(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/kb")
    assert resp.status_code == 200
    assert resp.json()["entries"] == []


def test_get_kb_returns_saved_data(client, home_id):
    save_entry(home_id, make_entry())
    resp = client.get(f"/api/homes/{home_id}/kb")
    assert resp.status_code == 200
    assert resp.json()["entries"][0]["id"] == "e1"


def test_create_entry(client, home_id):
    payload = {"title": "How to paint", "content": "# Painting"}
    resp = client.post(f"/api/homes/{home_id}/kb", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "How to paint"
    assert data["content"] == "# Painting"
    assert data["icon"] == "📄"
    assert data["parentId"] is None
    assert data["order"] == 0
    assert "id" in data
    assert "createdAt" in data
    assert "updatedAt" in data


def test_create_entry_with_custom_icon(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": "", "icon": "🔧"})
    assert resp.json()["icon"] == "🔧"


def test_create_child_page(client, home_id):
    parent = client.post(f"/api/homes/{home_id}/kb", json={"title": "Parent", "content": ""}).json()
    resp = client.post(f"/api/homes/{home_id}/kb", json={"title": "Child", "content": "", "parentId": parent["id"]})
    assert resp.status_code == 201
    assert resp.json()["parentId"] == parent["id"]
    assert resp.json()["order"] == 0


def test_create_second_child_gets_next_order(client, home_id):
    parent = client.post(f"/api/homes/{home_id}/kb", json={"title": "Parent", "content": ""}).json()
    client.post(f"/api/homes/{home_id}/kb", json={"title": "C1", "content": "", "parentId": parent["id"]})
    resp = client.post(f"/api/homes/{home_id}/kb", json={"title": "C2", "content": "", "parentId": parent["id"]})
    assert resp.json()["order"] == 1


def test_create_child_unknown_parent_404(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": "", "parentId": "nonexistent"})
    assert resp.status_code == 404


def test_create_child_under_trashed_parent_404(client, home_id):
    parent = client.post(f"/api/homes/{home_id}/kb", json={"title": "Parent", "content": ""}).json()
    client.delete(f"/api/homes/{home_id}/kb/{parent['id']}")
    resp = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": "", "parentId": parent["id"]})
    assert resp.status_code == 404


def test_update_entry(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/kb", json={"title": "Old title", "content": ""})
    entry_id = resp.json()["id"]
    resp = client.put(f"/api/homes/{home_id}/kb/{entry_id}", json={"title": "New title"})
    assert resp.status_code == 204
    entries = client.get(f"/api/homes/{home_id}/kb").json()["entries"]
    assert entries[0]["title"] == "New title"


def test_update_entry_not_found(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/kb/nonexistent", json={"title": "x"})
    assert resp.status_code == 404


def test_update_entry_icon(client, home_id):
    entry_id = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": ""}).json()["id"]
    resp = client.put(f"/api/homes/{home_id}/kb/{entry_id}", json={"icon": "🔧"})
    assert resp.status_code == 204
    entries = client.get(f"/api/homes/{home_id}/kb").json()["entries"]
    assert entries[0]["icon"] == "🔧"


def test_move_entry_to_new_parent(client, home_id):
    parent = client.post(f"/api/homes/{home_id}/kb", json={"title": "Parent", "content": ""}).json()
    entry_id = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": ""}).json()["id"]
    resp = client.put(f"/api/homes/{home_id}/kb/{entry_id}", json={"parentId": parent["id"]})
    assert resp.status_code == 204
    entries = client.get(f"/api/homes/{home_id}/kb").json()["entries"]
    assert next(e for e in entries if e["id"] == entry_id)["parentId"] == parent["id"]


def test_move_entry_back_to_root(client, home_id):
    parent = client.post(f"/api/homes/{home_id}/kb", json={"title": "Parent", "content": ""}).json()
    entry_id = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": "", "parentId": parent["id"]}).json()["id"]
    resp = client.put(f"/api/homes/{home_id}/kb/{entry_id}", json={"parentId": None})
    assert resp.status_code == 204
    entries = client.get(f"/api/homes/{home_id}/kb").json()["entries"]
    assert next(e for e in entries if e["id"] == entry_id)["parentId"] is None


def test_move_entry_unknown_parent_404(client, home_id):
    entry_id = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": ""}).json()["id"]
    resp = client.put(f"/api/homes/{home_id}/kb/{entry_id}", json={"parentId": "nonexistent"})
    assert resp.status_code == 404


def test_move_entry_into_own_descendant_rejected(client, home_id):
    a = client.post(f"/api/homes/{home_id}/kb", json={"title": "A", "content": ""}).json()
    b = client.post(f"/api/homes/{home_id}/kb", json={"title": "B", "content": "", "parentId": a["id"]}).json()
    resp = client.put(f"/api/homes/{home_id}/kb/{a['id']}", json={"parentId": b["id"]})
    assert resp.status_code == 400


def test_move_entry_into_self_rejected(client, home_id):
    a = client.post(f"/api/homes/{home_id}/kb", json={"title": "A", "content": ""}).json()
    resp = client.put(f"/api/homes/{home_id}/kb/{a['id']}", json={"parentId": a["id"]})
    assert resp.status_code == 400


def test_reorder_siblings(client, home_id):
    a = client.post(f"/api/homes/{home_id}/kb", json={"title": "A", "content": ""}).json()
    b = client.post(f"/api/homes/{home_id}/kb", json={"title": "B", "content": ""}).json()
    c = client.post(f"/api/homes/{home_id}/kb", json={"title": "C", "content": ""}).json()
    resp = client.put(f"/api/homes/{home_id}/kb/reorder", json={"parentId": None, "orderedIds": [c["id"], a["id"], b["id"]]})
    assert resp.status_code == 204
    entries = client.get(f"/api/homes/{home_id}/kb").json()["entries"]
    order = {e["id"]: e["order"] for e in entries}
    assert order[c["id"]] < order[a["id"]] < order[b["id"]]


def test_reorder_siblings_mismatched_ids_rejected(client, home_id):
    a = client.post(f"/api/homes/{home_id}/kb", json={"title": "A", "content": ""}).json()
    resp = client.put(f"/api/homes/{home_id}/kb/reorder", json={"parentId": None, "orderedIds": [a["id"], "bogus"]})
    assert resp.status_code == 400


def test_delete_entry(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/kb", json={"title": "To delete", "content": ""})
    entry_id = resp.json()["id"]
    resp = client.delete(f"/api/homes/{home_id}/kb/{entry_id}")
    assert resp.status_code == 200
    assert resp.json() == {"deletedCount": 1}
    assert client.get(f"/api/homes/{home_id}/kb").json()["entries"] == []


def test_delete_entry_not_found(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/kb/nonexistent")
    assert resp.status_code == 404


def test_delete_entry_cascades_to_children(client, home_id):
    parent = client.post(f"/api/homes/{home_id}/kb", json={"title": "Parent", "content": ""}).json()
    client.post(f"/api/homes/{home_id}/kb", json={"title": "Child", "content": "", "parentId": parent["id"]})
    resp = client.delete(f"/api/homes/{home_id}/kb/{parent['id']}")
    assert resp.json() == {"deletedCount": 2}
    assert client.get(f"/api/homes/{home_id}/kb").json()["entries"] == []


def test_deleted_entry_appears_in_trash(client, home_id):
    entry_id = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": ""}).json()["id"]
    client.delete(f"/api/homes/{home_id}/kb/{entry_id}")
    trash = client.get(f"/api/homes/{home_id}/kb/trash").json()["entries"]
    assert trash[0]["id"] == entry_id


def test_restore_entry(client, home_id):
    entry_id = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": ""}).json()["id"]
    client.delete(f"/api/homes/{home_id}/kb/{entry_id}")
    resp = client.post(f"/api/homes/{home_id}/kb/trash/{entry_id}/restore")
    assert resp.status_code == 200
    assert resp.json() == {"restoredCount": 1}
    assert client.get(f"/api/homes/{home_id}/kb").json()["entries"][0]["id"] == entry_id
    assert client.get(f"/api/homes/{home_id}/kb/trash").json()["entries"] == []


def test_restore_cascades_to_trashed_descendants(client, home_id):
    parent = client.post(f"/api/homes/{home_id}/kb", json={"title": "Parent", "content": ""}).json()
    client.post(f"/api/homes/{home_id}/kb", json={"title": "Child", "content": "", "parentId": parent["id"]})
    client.delete(f"/api/homes/{home_id}/kb/{parent['id']}")
    resp = client.post(f"/api/homes/{home_id}/kb/trash/{parent['id']}/restore")
    assert resp.json() == {"restoredCount": 2}
    assert len(client.get(f"/api/homes/{home_id}/kb").json()["entries"]) == 2


def test_restore_not_found_for_live_entry(client, home_id):
    entry_id = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": ""}).json()["id"]
    resp = client.post(f"/api/homes/{home_id}/kb/trash/{entry_id}/restore")
    assert resp.status_code == 404


def test_permanently_delete_from_trash(client, tmp_path, home_id):
    entry_id = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": ""}).json()["id"]
    client.delete(f"/api/homes/{home_id}/kb/{entry_id}")
    resp = client.delete(f"/api/homes/{home_id}/kb/trash/{entry_id}")
    assert resp.status_code == 204
    assert client.get(f"/api/homes/{home_id}/kb/trash").json()["entries"] == []
    assert not (tmp_path / "homes" / home_id / "kb" / f"{entry_id}.md").exists()


def test_permanently_delete_live_entry_rejected(client, home_id):
    entry_id = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": ""}).json()["id"]
    resp = client.delete(f"/api/homes/{home_id}/kb/trash/{entry_id}")
    assert resp.status_code == 404
    assert client.get(f"/api/homes/{home_id}/kb").json()["entries"][0]["id"] == entry_id


def test_empty_trash(client, home_id):
    a = client.post(f"/api/homes/{home_id}/kb", json={"title": "A", "content": ""}).json()["id"]
    b = client.post(f"/api/homes/{home_id}/kb", json={"title": "B", "content": ""}).json()["id"]
    client.delete(f"/api/homes/{home_id}/kb/{a}")
    client.delete(f"/api/homes/{home_id}/kb/{b}")
    resp = client.post(f"/api/homes/{home_id}/kb/trash/empty")
    assert resp.status_code == 200
    assert resp.json() == {"deletedCount": 2}
    assert client.get(f"/api/homes/{home_id}/kb/trash").json()["entries"] == []


def _make_valid_pdf() -> bytes:
    import fitz
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    return doc.write()


def _entry_id(client, home_id) -> str:
    resp = client.post(f"/api/homes/{home_id}/kb", json={"title": "Test entry", "content": "Hello"})
    return resp.json()["id"]


def test_kb_attachments_empty_by_default(client, home_id):
    eid = _entry_id(client, home_id)
    entry = next(e for e in client.get(f"/api/homes/{home_id}/kb").json()["entries"] if e["id"] == eid)
    assert entry["attachments"] == []


def test_kb_upload_jpeg_accepted(client, home_id):
    eid = _entry_id(client, home_id)
    resp = client.post(
        f"/api/homes/{home_id}/kb/{eid}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "photo.jpg"
    entry = next(e for e in client.get(f"/api/homes/{home_id}/kb").json()["entries"] if e["id"] == eid)
    assert "photo.jpg" in entry["attachments"]


def test_kb_upload_unsupported_rejected(client, home_id):
    eid = _entry_id(client, home_id)
    resp = client.post(
        f"/api/homes/{home_id}/kb/{eid}/attachments",
        files={"file": ("x.docx", b"\x00" * 50, "application/vnd.openxmlformats")},
    )
    assert resp.status_code == 400


def test_kb_upload_pdf_creates_thumbnail(client, tmp_path, home_id):
    eid = _entry_id(client, home_id)
    resp = client.post(
        f"/api/homes/{home_id}/kb/{eid}/attachments",
        files={"file": ("note.pdf", _make_valid_pdf(), "application/pdf")},
    )
    assert resp.status_code == 201
    thumb = tmp_path / "homes" / home_id / "kb-attachments" / eid / "note.pdf.thumb.jpg"
    assert thumb.exists()


def test_kb_delete_attachment_removes_thumb(client, tmp_path, home_id):
    eid = _entry_id(client, home_id)
    client.post(f"/api/homes/{home_id}/kb/{eid}/attachments",
        files={"file": ("note.pdf", _make_valid_pdf(), "application/pdf")})
    thumb = tmp_path / "homes" / home_id / "kb-attachments" / eid / "note.pdf.thumb.jpg"
    assert thumb.exists()
    client.delete(f"/api/homes/{home_id}/kb/{eid}/attachments/note.pdf")
    assert not thumb.exists()


def test_kb_get_jpeg_returns_image_content_type(client, home_id):
    eid = _entry_id(client, home_id)
    client.post(f"/api/homes/{home_id}/kb/{eid}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")})
    resp = client.get(f"/api/homes/{home_id}/kb/{eid}/attachments/photo.jpg")
    assert resp.status_code == 200
    assert "image/jpeg" in resp.headers["content-type"]


def test_kb_attachments_persist_after_entry_update(client, home_id):
    eid = _entry_id(client, home_id)
    client.post(f"/api/homes/{home_id}/kb/{eid}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")})
    client.put(f"/api/homes/{home_id}/kb/{eid}", json={"title": "Updated title"})
    entry = next(e for e in client.get(f"/api/homes/{home_id}/kb").json()["entries"] if e["id"] == eid)
    assert "photo.jpg" in entry["attachments"]


def test_kb_delete_entry_removes_attachment_dir(client, tmp_path, home_id):
    eid = _entry_id(client, home_id)
    client.post(f"/api/homes/{home_id}/kb/{eid}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")})
    att_dir = tmp_path / "homes" / home_id / "kb-attachments" / eid
    assert att_dir.exists()
    # DELETE on the live entry is a soft delete now -- the attachment dir survives
    # until the entry is permanently deleted from Trash.
    client.delete(f"/api/homes/{home_id}/kb/{eid}")
    assert att_dir.exists()
    client.delete(f"/api/homes/{home_id}/kb/trash/{eid}")
    assert not att_dir.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_kb.py -v`
Expected: FAIL — e.g. `assert 201 == 404` on `test_create_entry` isn't right; actually expect import/route errors: `KeyError: 'icon'` or 404s since `/kb/reorder` and `/kb/trash*` routes don't exist yet, and `create_entry` still requires `folderId`-shaped validation. The old `routes/kb.py` still imports `KBFolder` from `models_kb`, which Task 1 already removed, so this will actually fail at collection time with `ImportError: cannot import name 'KBFolder'`.

- [ ] **Step 3: Rewrite routes/kb.py**

Replace the full contents of `packages/backend/src/myhome/routes/kb.py`:

```python
import mimetypes
import os
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..deps import get_current_user_id
from ..models_kb import KBCreate, KBDocument, KBEntry, KBReorder, KBTrashDocument, KBUpdate
from ..persistence_activity import log_activity
from ..persistence_kb import (
    delete_attachment,
    delete_entry,
    empty_trash,
    generate_pdf_thumbnail,
    get_attachment_path,
    list_trash,
    load_all,
    load_entry,
    next_order,
    reorder_siblings,
    restore_subtree,
    save_attachment,
    save_entry,
    soft_delete_subtree,
    would_create_cycle,
)

router = APIRouter()

_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_id(entry_id: str) -> None:
    if not _ID_RE.fullmatch(entry_id):
        raise HTTPException(status_code=400, detail="Invalid id")


def _validate_filename(filename: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", filename) or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")


def _sanitise_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name or "attachment"


def _live_entry(home_id: str, id: str) -> KBEntry | None:
    entry = load_entry(home_id, id)
    if entry is None or entry.deletedAt is not None:
        return None
    return entry


@router.get("/api/homes/{home_id}/kb", response_model=KBDocument)
def get_kb(home_id: str) -> KBDocument:
    return KBDocument(entries=load_all(home_id))


@router.post("/api/homes/{home_id}/kb", response_model=KBEntry, status_code=201)
def create_entry(
    home_id: str, body: KBCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> KBEntry:
    if body.parentId is not None and _live_entry(home_id, body.parentId) is None:
        raise HTTPException(status_code=404, detail="Parent page not found")
    now = _now()
    entry = KBEntry(
        id=str(uuid.uuid4()),
        title=body.title,
        content=body.content,
        parentId=body.parentId,
        icon=body.icon,
        order=next_order(home_id, body.parentId),
        createdAt=now,
        updatedAt=now,
    )
    save_entry(home_id, entry)
    log_activity(home_id, current_user_id, "kb", "create", entry.title, entry.id)
    return entry


@router.put("/api/homes/{home_id}/kb/reorder", status_code=204)
def reorder_kb_entries(
    home_id: str, body: KBReorder,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    siblings = [e for e in load_all(home_id) if e.parentId == body.parentId]
    if {e.id for e in siblings} != set(body.orderedIds):
        raise HTTPException(status_code=400, detail="orderedIds must match current siblings exactly")
    reorder_siblings(home_id, body.parentId, body.orderedIds)


@router.put("/api/homes/{home_id}/kb/{id}", status_code=204)
def update_entry(
    home_id: str, id: str, body: KBUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    entry = _live_entry(home_id, id)
    if not entry:
        raise HTTPException(status_code=404)
    if body.title is not None:
        entry.title = body.title
    if body.content is not None:
        entry.content = body.content
    if body.icon is not None:
        entry.icon = body.icon
    if "parentId" in body.model_fields_set:
        if body.parentId is not None:
            if _live_entry(home_id, body.parentId) is None:
                raise HTTPException(status_code=404, detail="Parent page not found")
            if would_create_cycle(home_id, id, body.parentId):
                raise HTTPException(status_code=400, detail="Cannot move a page into itself or a descendant")
        entry.parentId = body.parentId
        entry.order = next_order(home_id, body.parentId)
    entry.updatedAt = _now()
    save_entry(home_id, entry)
    log_activity(home_id, current_user_id, "kb", "update", entry.title, id)


@router.delete("/api/homes/{home_id}/kb/{id}", status_code=200)
def delete_kb_entry(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    entry = _live_entry(home_id, id)
    if not entry:
        raise HTTPException(status_code=404)
    deleted_ids = soft_delete_subtree(home_id, id)
    log_activity(home_id, current_user_id, "kb", "delete", entry.title, id)
    return {"deletedCount": len(deleted_ids)}


@router.get("/api/homes/{home_id}/kb/trash", response_model=KBTrashDocument)
def get_kb_trash(home_id: str) -> KBTrashDocument:
    return KBTrashDocument(entries=list_trash(home_id))


@router.post("/api/homes/{home_id}/kb/trash/{id}/restore", status_code=200)
def restore_kb_entry(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    entry = load_entry(home_id, id)
    if entry is None or entry.deletedAt is None:
        raise HTTPException(status_code=404)
    restored_ids = restore_subtree(home_id, id)
    log_activity(home_id, current_user_id, "kb", "restore", entry.title, id)
    return {"restoredCount": len(restored_ids)}


@router.delete("/api/homes/{home_id}/kb/trash/{id}", status_code=204)
def permanently_delete_kb_entry(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    entry = load_entry(home_id, id)
    if entry is None or entry.deletedAt is None:
        raise HTTPException(status_code=404)
    delete_entry(home_id, id)
    log_activity(home_id, current_user_id, "kb", "delete_forever", entry.title, id)


@router.post("/api/homes/{home_id}/kb/trash/empty", status_code=200)
def empty_kb_trash(
    home_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    deleted_ids = empty_trash(home_id)
    log_activity(home_id, current_user_id, "kb", "empty_trash", f"{len(deleted_ids)} pages", None)
    return {"deletedCount": len(deleted_ids)}


@router.post("/api/homes/{home_id}/kb/{id}/attachments", status_code=201)
async def upload_kb_attachment(home_id: str, id: str, file: UploadFile) -> dict:
    _validate_id(id)
    entry = load_entry(home_id, id)
    if not entry:
        raise HTTPException(status_code=404)
    original = file.filename or ""
    ext = os.path.splitext(original.lower())[1]
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not supported")
    filename = _sanitise_filename(original)
    data = await file.read()
    save_attachment(home_id, id, filename, data)
    if ext == ".pdf":
        pdf_path = get_attachment_path(home_id, id, filename)
        thumb_path = pdf_path.with_name(pdf_path.name + ".thumb.jpg")
        generate_pdf_thumbnail(pdf_path, thumb_path)
    if filename not in entry.attachments:
        entry.attachments.append(filename)
    entry.updatedAt = _now()
    save_entry(home_id, entry)
    return {"filename": filename}


@router.get("/api/homes/{home_id}/kb/{id}/attachments/{filename}")
def get_kb_attachment(home_id: str, id: str, filename: str) -> FileResponse:
    _validate_id(id)
    _validate_filename(filename)
    path = get_attachment_path(home_id, id, filename)
    if not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", content_disposition_type="inline")


@router.delete("/api/homes/{home_id}/kb/{id}/attachments/{filename}", status_code=204)
def delete_kb_attachment(home_id: str, id: str, filename: str) -> None:
    _validate_id(id)
    _validate_filename(filename)
    entry = load_entry(home_id, id)
    if not entry:
        raise HTTPException(status_code=404)
    if not delete_attachment(home_id, id, filename):
        raise HTTPException(status_code=404)
    entry.attachments = [a for a in entry.attachments if a != filename]
    entry.updatedAt = _now()
    save_entry(home_id, entry)
```

Note the route ordering: `PUT /kb/reorder` is declared before `PUT /kb/{id}` so FastAPI matches the literal `/reorder` path before the `{id}` wildcard would otherwise swallow it.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_kb.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Run the full backend suite**

Run: `cd packages/backend && python -m pytest -q`
Expected: PASS. (`test_mcp_tools_kb.py` will fail here — that's expected and fixed in Task 3; if the runner supports it, run `python -m pytest -q --ignore=tests/test_mcp_tools_kb.py` instead to confirm everything else is green before moving on.)

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/routes/kb.py packages/backend/tests/test_kb.py
git commit -m "feat(kb): rewrite KB routes for page nesting, reorder, and trash"
```

---

## Task 3: Backend MCP tools

Depends on Task 1. Independent of Task 2 (separate call path into the same persistence layer).

**Files:**
- Modify: `packages/backend/src/myhome/mcp_tools_kb.py` (full rewrite)
- Modify: `packages/backend/tests/test_mcp_tools_kb.py` (full rewrite)

**Interfaces:**
- Consumes: Task 1's persistence functions directly (not Task 2's HTTP routes — this is a separate call path into the same `persistence_kb.py`).
- Produces: MCP tools `list_kb_entries`, `create_kb_entry`, `update_kb_entry`, `move_kb_entry`, `delete_kb_entry`, `list_kb_trash`, `restore_kb_entry`, `permanently_delete_kb_entry`, `empty_kb_trash` — all folder-specific tools (`list_kb_folders`, `create_kb_folder`, `rename_kb_folder`, `move_kb_folder`, `delete_kb_folder`) are removed.

- [ ] **Step 1: Write the failing tests**

Replace the full contents of `packages/backend/tests/test_mcp_tools_kb.py`:

```python
import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_entry(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _list_kb_entries_impl
    entry = _create_kb_entry_impl(home_id, "Wifi Password", content="It's on the router")
    doc = _list_kb_entries_impl(home_id)
    assert doc["entries"][0]["id"] == entry["id"]
    assert doc["entries"][0]["title"] == "Wifi Password"
    assert doc["entries"][0]["icon"] == "📄"
    assert doc["entries"][0]["parentId"] is None


def test_create_entry_with_custom_icon(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl
    entry = _create_kb_entry_impl(home_id, "Boiler", icon="🔧")
    assert entry["icon"] == "🔧"


def test_create_child_entry(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl
    parent = _create_kb_entry_impl(home_id, "Appliances")
    child = _create_kb_entry_impl(home_id, "Boiler", parent_id=parent["id"])
    assert child["parentId"] == parent["id"]


def test_create_entry_unknown_parent_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl
    with pytest.raises(ValueError):
        _create_kb_entry_impl(home_id, "X", parent_id="nonexistent")


def test_update_entry_bumps_updated_at(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _update_kb_entry_impl
    entry = _create_kb_entry_impl(home_id, "Boiler Manual")
    updated = _update_kb_entry_impl(home_id, entry["id"], content="Reset button is on the side")
    assert updated["content"] == "Reset button is on the side"
    assert updated["updatedAt"] >= entry["updatedAt"]


def test_update_entry_icon(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _update_kb_entry_impl
    entry = _create_kb_entry_impl(home_id, "Boiler")
    updated = _update_kb_entry_impl(home_id, entry["id"], icon="🔧")
    assert updated["icon"] == "🔧"


def test_update_entry_unknown_id_raises(home_id):
    from myhome.mcp_tools_kb import _update_kb_entry_impl
    with pytest.raises(ValueError):
        _update_kb_entry_impl(home_id, "nonexistent", title="X")


def test_move_entry(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _move_kb_entry_impl
    parent = _create_kb_entry_impl(home_id, "Appliances")
    entry = _create_kb_entry_impl(home_id, "Boiler")
    moved = _move_kb_entry_impl(home_id, entry["id"], parent["id"])
    assert moved["parentId"] == parent["id"]


def test_move_entry_to_root(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _move_kb_entry_impl
    parent = _create_kb_entry_impl(home_id, "Appliances")
    entry = _create_kb_entry_impl(home_id, "Boiler", parent_id=parent["id"])
    moved = _move_kb_entry_impl(home_id, entry["id"], None)
    assert moved["parentId"] is None


def test_move_entry_into_own_descendant_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _move_kb_entry_impl
    a = _create_kb_entry_impl(home_id, "A")
    b = _create_kb_entry_impl(home_id, "B", parent_id=a["id"])
    with pytest.raises(ValueError):
        _move_kb_entry_impl(home_id, a["id"], b["id"])


def test_delete_entry(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _delete_kb_entry_impl, _list_kb_entries_impl
    entry = _create_kb_entry_impl(home_id, "Old Note")
    result = _delete_kb_entry_impl(home_id, entry["id"])
    assert result["deletedCount"] == 1
    assert _list_kb_entries_impl(home_id)["entries"] == []


def test_delete_entry_cascades_to_children(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _delete_kb_entry_impl
    parent = _create_kb_entry_impl(home_id, "Parent")
    _create_kb_entry_impl(home_id, "Child", parent_id=parent["id"])
    result = _delete_kb_entry_impl(home_id, parent["id"])
    assert result["deletedCount"] == 2


def test_delete_entry_unknown_id_raises(home_id):
    from myhome.mcp_tools_kb import _delete_kb_entry_impl
    with pytest.raises(ValueError):
        _delete_kb_entry_impl(home_id, "nonexistent")


def test_list_kb_trash(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _delete_kb_entry_impl, _list_kb_trash_impl
    entry = _create_kb_entry_impl(home_id, "Old Note")
    _delete_kb_entry_impl(home_id, entry["id"])
    trash = _list_kb_trash_impl(home_id)
    assert trash["entries"][0]["id"] == entry["id"]


def test_restore_kb_entry(home_id):
    from myhome.mcp_tools_kb import (
        _create_kb_entry_impl, _delete_kb_entry_impl, _list_kb_entries_impl, _restore_kb_entry_impl,
    )
    entry = _create_kb_entry_impl(home_id, "Old Note")
    _delete_kb_entry_impl(home_id, entry["id"])
    result = _restore_kb_entry_impl(home_id, entry["id"])
    assert result["restoredCount"] == 1
    assert _list_kb_entries_impl(home_id)["entries"][0]["id"] == entry["id"]


def test_restore_kb_entry_not_trashed_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _restore_kb_entry_impl
    entry = _create_kb_entry_impl(home_id, "Live Note")
    with pytest.raises(ValueError):
        _restore_kb_entry_impl(home_id, entry["id"])


def test_permanently_delete_kb_entry(home_id):
    from myhome.mcp_tools_kb import (
        _create_kb_entry_impl, _delete_kb_entry_impl, _list_kb_trash_impl, _permanently_delete_kb_entry_impl,
    )
    entry = _create_kb_entry_impl(home_id, "Old Note")
    _delete_kb_entry_impl(home_id, entry["id"])
    _permanently_delete_kb_entry_impl(home_id, entry["id"])
    assert _list_kb_trash_impl(home_id)["entries"] == []


def test_permanently_delete_live_entry_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _permanently_delete_kb_entry_impl
    entry = _create_kb_entry_impl(home_id, "Live Note")
    with pytest.raises(ValueError):
        _permanently_delete_kb_entry_impl(home_id, entry["id"])


def test_empty_kb_trash(home_id):
    from myhome.mcp_tools_kb import (
        _create_kb_entry_impl, _delete_kb_entry_impl, _empty_kb_trash_impl, _list_kb_trash_impl,
    )
    a = _create_kb_entry_impl(home_id, "A")
    b = _create_kb_entry_impl(home_id, "B")
    _delete_kb_entry_impl(home_id, a["id"])
    _delete_kb_entry_impl(home_id, b["id"])
    result = _empty_kb_trash_impl(home_id)
    assert result["deletedCount"] == 2
    assert _list_kb_trash_impl(home_id)["entries"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_mcp_tools_kb.py -v`
Expected: FAIL — `ImportError: cannot import name '_create_kb_entry_impl'` signature mismatch (old one takes `folder_id`, not `parent_id`) and missing `_list_kb_trash_impl`/`_restore_kb_entry_impl`/etc.

- [ ] **Step 3: Rewrite mcp_tools_kb.py**

Replace the full contents of `packages/backend/src/myhome/mcp_tools_kb.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_kb import KBEntry
from .persistence_kb import (
    delete_entry,
    empty_trash,
    list_trash,
    load_all,
    load_entry,
    next_order,
    restore_subtree,
    save_entry,
    soft_delete_subtree,
    would_create_cycle,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _live_entry(home_id: str, entry_id: str) -> KBEntry | None:
    entry = load_entry(home_id, entry_id)
    if entry is None or entry.deletedAt is not None:
        return None
    return entry


def _list_kb_entries_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return {"entries": [e.model_dump() for e in load_all(resolved)]}


def _create_kb_entry_impl(
    home_id: str | None, title: str, content: str = "", parent_id: str | None = None, icon: str = "📄",
) -> dict:
    resolved = _resolve_home_id(home_id)
    if parent_id is not None and _live_entry(resolved, parent_id) is None:
        raise ValueError(f"Unknown parent_id {parent_id!r}")
    now = _now()
    entry = KBEntry(
        id=str(uuid.uuid4()), title=title, content=content, parentId=parent_id, icon=icon,
        order=next_order(resolved, parent_id), createdAt=now, updatedAt=now,
    )
    save_entry(resolved, entry)
    return entry.model_dump()


def _update_kb_entry_impl(
    home_id: str | None, entry_id: str, title: str | None = None, content: str | None = None,
    icon: str | None = None,
) -> dict:
    resolved = _resolve_home_id(home_id)
    entry = _live_entry(resolved, entry_id)
    if entry is None:
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    if title is not None:
        entry.title = title
    if content is not None:
        entry.content = content
    if icon is not None:
        entry.icon = icon
    entry.updatedAt = _now()
    save_entry(resolved, entry)
    return entry.model_dump()


def _move_kb_entry_impl(home_id: str | None, entry_id: str, parent_id: str | None = None) -> dict:
    resolved = _resolve_home_id(home_id)
    entry = _live_entry(resolved, entry_id)
    if entry is None:
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    if parent_id is not None:
        if _live_entry(resolved, parent_id) is None:
            raise ValueError(f"Unknown parent_id {parent_id!r}")
        if would_create_cycle(resolved, entry_id, parent_id):
            raise ValueError("Cannot move a page into itself or a descendant")
    entry.parentId = parent_id
    entry.order = next_order(resolved, parent_id)
    entry.updatedAt = _now()
    save_entry(resolved, entry)
    return entry.model_dump()


def _delete_kb_entry_impl(home_id: str | None, entry_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    if _live_entry(resolved, entry_id) is None:
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    deleted_ids = soft_delete_subtree(resolved, entry_id)
    return {"deleted": entry_id, "deletedCount": len(deleted_ids)}


def _list_kb_trash_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return {"entries": [e.model_dump() for e in list_trash(resolved)]}


def _restore_kb_entry_impl(home_id: str | None, entry_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    entry = load_entry(resolved, entry_id)
    if entry is None or entry.deletedAt is None:
        raise ValueError(f"Unknown trashed entry_id {entry_id!r}")
    restored_ids = restore_subtree(resolved, entry_id)
    return {"restored": entry_id, "restoredCount": len(restored_ids)}


def _permanently_delete_kb_entry_impl(home_id: str | None, entry_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    entry = load_entry(resolved, entry_id)
    if entry is None or entry.deletedAt is None:
        raise ValueError(f"Unknown trashed entry_id {entry_id!r}")
    delete_entry(resolved, entry_id)
    return {"deleted": entry_id}


def _empty_kb_trash_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    deleted_ids = empty_trash(resolved)
    return {"deletedCount": len(deleted_ids)}


@mcp.tool()
async def list_kb_entries(ctx: Context, home_id: str | None = None) -> dict:
    """List all knowledge base pages for a home. There is no server-side search --
    fetch the list and filter/search over titles and content yourself. Each page
    has a parent_id; pages with children display as folders in the UI."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_kb_entries_impl(home_id)


@mcp.tool()
async def create_kb_entry(
    ctx: Context, title: str, home_id: str | None = None, content: str = "",
    parent_id: str | None = None, icon: str = "📄",
) -> dict:
    """Create a knowledge base page. content supports Markdown. Optionally nest it
    under an existing page via parent_id (see list_kb_entries) -- the parent then
    displays as a folder in the UI."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_kb_entry_impl(home_id, title, content, parent_id, icon)


@mcp.tool()
async def update_kb_entry(
    ctx: Context, entry_id: str, home_id: str | None = None,
    title: str | None = None, content: str | None = None, icon: str | None = None,
) -> dict:
    """Update the title, content, and/or icon of a knowledge base page. To move it
    between parents, use move_kb_entry instead."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_kb_entry_impl(home_id, entry_id, title, content, icon)


@mcp.tool()
async def move_kb_entry(ctx: Context, entry_id: str, home_id: str | None = None, parent_id: str | None = None) -> dict:
    """Move a knowledge base page under parent_id, or to the top level if parent_id is omitted."""
    await _require_role(ctx.request_context.request, "normal")
    return _move_kb_entry_impl(home_id, entry_id, parent_id)


@mcp.tool()
async def delete_kb_entry(ctx: Context, entry_id: str, home_id: str | None = None) -> dict:
    """Delete a knowledge base page. This is a soft delete: the page and any child
    pages nested under it move to Trash and can be restored with restore_kb_entry
    until someone empties the trash."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_kb_entry_impl(home_id, entry_id)


@mcp.tool()
async def list_kb_trash(ctx: Context, home_id: str | None = None) -> dict:
    """List knowledge base pages currently in Trash."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_kb_trash_impl(home_id)


@mcp.tool()
async def restore_kb_entry(ctx: Context, entry_id: str, home_id: str | None = None) -> dict:
    """Restore a knowledge base page from Trash, along with any child pages that
    were trashed in the same delete."""
    await _require_role(ctx.request_context.request, "normal")
    return _restore_kb_entry_impl(home_id, entry_id)


@mcp.tool()
async def permanently_delete_kb_entry(ctx: Context, entry_id: str, home_id: str | None = None) -> dict:
    """Permanently delete a single knowledge base page from Trash. This cannot be undone."""
    await _require_role(ctx.request_context.request, "normal")
    return _permanently_delete_kb_entry_impl(home_id, entry_id)


@mcp.tool()
async def empty_kb_trash(ctx: Context, home_id: str | None = None) -> dict:
    """Permanently delete every knowledge base page currently in Trash. This cannot be undone."""
    await _require_role(ctx.request_context.request, "normal")
    return _empty_kb_trash_impl(home_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_mcp_tools_kb.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Run the full backend suite**

Run: `cd packages/backend && python -m pytest -q`
Expected: PASS, all tests green. This confirms Tasks 1-3 are fully consistent together.

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_kb.py packages/backend/tests/test_mcp_tools_kb.py
git commit -m "feat(kb): rewrite KB MCP tools for page nesting and trash"
```

---

## Task 4: Frontend kbStore.svelte.ts

Depends on Task 2 (matches the HTTP contract it defines). Independent of Tasks 5-9 until they're wired together in Task 8.

**Files:**
- Modify: `packages/editor/src/lib/kbStore.svelte.ts` (full rewrite)
- Modify: `packages/editor/test/kbStore.test.ts` (full rewrite)

**Interfaces:**
- Produces (used by Tasks 5, 6, 8, 9):
  - `interface KBEntry { id, title, content, createdAt, updatedAt, attachments, parentId, icon, order, deletedAt? }`
  - `createKBStore(getHomeId) -> { entries, trash, loaded, loadError, createEntry, updateEntry, reorderSiblings, deleteEntry, uploadAttachment, deleteAttachment, loadTrash, restoreEntry, permanentlyDeleteEntry, emptyTrash, reload }`
  - `createEntry(data: { title, content, parentId?, icon? }) -> Promise<KBEntry>`
  - `updateEntry(id, patch: { title?, content?, parentId?, icon? }) -> Promise<void>`
  - `reorderSiblings(parentId: string | null, orderedIds: string[]) -> Promise<void>`
  - `deleteEntry(id) -> Promise<number>` (returns `deletedCount`)
  - `loadTrash() -> Promise<void>`, `restoreEntry(id) -> Promise<void>`, `permanentlyDeleteEntry(id) -> Promise<void>`, `emptyTrash() -> Promise<void>`

- [ ] **Step 1: Write the failing tests**

Replace the full contents of `packages/editor/test/kbStore.test.ts`:

```typescript
import { describe, it, expect, afterEach, vi } from "vitest";
import { createKBStore } from "../src/lib/kbStore.svelte";
import type { KBEntry } from "../src/lib/kbStore.svelte";

const HOME = "home-123";
const getHomeId = () => HOME;

function makeFetch(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => vi.unstubAllGlobals());

function makeEntry(overrides: Partial<KBEntry> = {}): KBEntry {
  return {
    id: "e1",
    title: "How to paint",
    content: "# Painting\n\nUse good brushes.",
    createdAt: "2026-06-28T10:00:00Z",
    updatedAt: "2026-06-28T10:00:00Z",
    attachments: [],
    parentId: null,
    icon: "📄",
    order: 0,
    ...overrides,
  };
}

const emptyDoc = { version: 1, entries: [] };

describe("kbStore — init", () => {
  it("loads entries from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, entries: [makeEntry()] }));
    const store = createKBStore(getHomeId);
    await tick();
    expect(store.entries.length).toBe(1);
    expect(store.entries[0].id).toBe("e1");
    expect(store.entries[0].icon).toBe("📄");
    expect(store.loaded).toBe(true);
  });

  it("marks loaded and sets loadError on network failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("net fail")));
    const store = createKBStore(getHomeId);
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("net fail");
  });

  it("marks loaded and sets loadError on HTTP error", async () => {
    vi.stubGlobal("fetch", makeFetch(500));
    const store = createKBStore(getHomeId);
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("HTTP 500");
  });

  it("does not fetch when no homeId provided", async () => {
    const fetchFn = vi.fn();
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore();
    await tick();
    expect(fetchFn).not.toHaveBeenCalled();
    expect(store.loaded).toBe(true);
  });
});

describe("kbStore — createEntry", () => {
  it("POSTs to /api/homes/{homeId}/kb, returns new entry, and refreshes", async () => {
    const created = makeEntry({ id: "e2", title: "New page", content: "" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => created })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [created] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    const entry = await store.createEntry({ title: "New page", content: "" });
    await tick();
    expect(entry.id).toBe("e2");
    expect(store.entries.length).toBe(1);
    const [, postCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(postCall[0]).toBe(`/api/homes/${HOME}/kb`);
    expect(postCall[1].method).toBe("POST");
    expect(JSON.parse(postCall[1].body as string)).toEqual({ title: "New page", content: "" });
  });

  it("includes parentId and icon in the POST body only when provided", async () => {
    const created = makeEntry({ id: "e2", parentId: "p1", icon: "🔧" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => created })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [created] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.createEntry({ title: "New page", content: "", parentId: "p1", icon: "🔧" });
    const [, postCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(JSON.parse(postCall[1].body as string)).toEqual({
      title: "New page", content: "", parentId: "p1", icon: "🔧",
    });
  });

  it("throws on HTTP error", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: false, status: 422, json: async () => null });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await expect(store.createEntry({ title: "x", content: "" })).rejects.toThrow("HTTP 422");
  });
});

describe("kbStore — updateEntry", () => {
  it("PUTs to /api/homes/{homeId}/kb/{id} and refreshes", async () => {
    const entry = makeEntry();
    const updated = makeEntry({ title: "Updated title" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [updated] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.updateEntry("e1", { title: "Updated title" });
    await tick();
    expect(store.entries[0].title).toBe("Updated title");
    const [, putCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(putCall[0]).toBe(`/api/homes/${HOME}/kb/e1`);
    expect(putCall[1].method).toBe("PUT");
  });

  it("includes parentId and icon in the PUT body when provided", async () => {
    const entry = makeEntry();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [{ ...entry, parentId: "p1" }] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.updateEntry("e1", { parentId: "p1", icon: "🔧" });
    const [, putCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(JSON.parse(putCall[1].body as string)).toEqual({ parentId: "p1", icon: "🔧" });
  });

  it("throws on HTTP error", async () => {
    const entry = makeEntry();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: false, status: 404, json: async () => null });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await expect(store.updateEntry("e1", { title: "x" })).rejects.toThrow("HTTP 404");
  });
});

describe("kbStore — reorderSiblings", () => {
  it("PUTs to /api/homes/{homeId}/kb/reorder and refreshes", async () => {
    const a = makeEntry({ id: "a", order: 0 });
    const b = makeEntry({ id: "b", order: 1 });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [a, b] }) })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [{ ...b, order: 0 }, { ...a, order: 1 }] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.reorderSiblings(null, ["b", "a"]);
    await tick();
    const [, putCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(putCall[0]).toBe(`/api/homes/${HOME}/kb/reorder`);
    expect(JSON.parse(putCall[1].body as string)).toEqual({ parentId: null, orderedIds: ["b", "a"] });
    expect(store.entries[0].id).toBe("b");
  });
});

describe("kbStore — deleteEntry", () => {
  it("DELETEs /api/homes/{homeId}/kb/{id}, returns deletedCount, and refreshes", async () => {
    const entry = makeEntry();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ deletedCount: 3 }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    expect(store.entries.length).toBe(1);
    const count = await store.deleteEntry("e1");
    await tick();
    expect(count).toBe(3);
    expect(store.entries.length).toBe(0);
    const [, delCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(delCall[0]).toBe(`/api/homes/${HOME}/kb/e1`);
    expect(delCall[1].method).toBe("DELETE");
  });

  it("throws on HTTP error", async () => {
    const entry = makeEntry();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: false, status: 404, json: async () => null });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await expect(store.deleteEntry("e1")).rejects.toThrow("HTTP 404");
  });
});

describe("kbStore — trash", () => {
  it("loadTrash GETs /kb/trash and populates trash", async () => {
    const trashed = makeEntry({ id: "t1", deletedAt: "2026-07-01T00:00:00Z" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ entries: [trashed] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.loadTrash();
    expect(store.trash.length).toBe(1);
    expect(store.trash[0].id).toBe("t1");
    const [, trashCall] = fetchFn.mock.calls as [unknown, [string]][];
    expect(trashCall[0]).toBe(`/api/homes/${HOME}/kb/trash`);
  });

  it("restoreEntry POSTs to /kb/trash/{id}/restore, then refreshes entries and trash", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ restoredCount: 1 }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [makeEntry()] }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ entries: [] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.restoreEntry("e1");
    const [, restoreCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(restoreCall[0]).toBe(`/api/homes/${HOME}/kb/trash/e1/restore`);
    expect(restoreCall[1].method).toBe("POST");
    expect(store.entries.length).toBe(1);
  });

  it("permanentlyDeleteEntry DELETEs /kb/trash/{id}, then refreshes trash", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ entries: [] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.permanentlyDeleteEntry("t1");
    const [, delCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(delCall[0]).toBe(`/api/homes/${HOME}/kb/trash/t1`);
    expect(delCall[1].method).toBe("DELETE");
  });

  it("emptyTrash POSTs to /kb/trash/empty, then refreshes trash", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ deletedCount: 2 }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ entries: [] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.emptyTrash();
    const [, emptyCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(emptyCall[0]).toBe(`/api/homes/${HOME}/kb/trash/empty`);
    expect(emptyCall[1].method).toBe("POST");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/kbStore.test.ts`
Expected: FAIL — `store.reorderSiblings is not a function`, `store.trash` is `undefined`, etc.

- [ ] **Step 3: Rewrite kbStore.svelte.ts**

Replace the full contents of `packages/editor/src/lib/kbStore.svelte.ts`:

```typescript
export interface KBEntry {
  id: string;
  title: string;
  content: string;
  createdAt: string;
  updatedAt: string;
  attachments: string[];
  parentId: string | null;
  icon: string;
  order: number;
  deletedAt?: string | null;
}

export interface KBDocument {
  version: number;
  entries: KBEntry[];
}

export interface KBTrashDocument {
  entries: KBEntry[];
}

export function createKBStore(getHomeId: () => string | null = () => null) {
  const entries = $state<KBEntry[]>([]);
  const trash = $state<KBEntry[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) { loaded = true; return; }
    try {
      loadError = null;
      const resp = await fetch(`/api/homes/${homeId}/kb`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: KBDocument = await resp.json();
      entries.length = 0;
      for (const e of doc.entries) entries.push({ attachments: [], parentId: null, icon: "📄", order: 0, ...e });
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function createEntry(
    data: { title: string; content: string; parentId?: string | null; icon?: string },
  ): Promise<KBEntry> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const payload: Record<string, unknown> = { title: data.title, content: data.content };
    if (data.parentId !== undefined) payload.parentId = data.parentId;
    if (data.icon !== undefined) payload.icon = data.icon;
    const resp = await fetch(`/api/homes/${homeId}/kb`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const entry: KBEntry = await resp.json();
    await init();
    return entry;
  }

  async function updateEntry(
    id: string,
    patch: { title?: string; content?: string; parentId?: string | null; icon?: string },
  ): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function reorderSiblings(parentId: string | null, orderedIds: string[]): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/reorder`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ parentId, orderedIds }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteEntry(id: string): Promise<number> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const result = await resp.json();
    await init();
    return result.deletedCount as number;
  }

  async function uploadAttachment(id: string, file: File): Promise<string> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch(`/api/homes/${homeId}/kb/${id}/attachments`, { method: "POST", body: form });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const result = await resp.json();
    await init();
    return result.filename as string;
  }

  async function deleteAttachment(id: string, filename: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/${id}/attachments/${filename}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function loadTrash(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) return;
    const resp = await fetch(`/api/homes/${homeId}/kb/trash`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const doc: KBTrashDocument = await resp.json();
    trash.length = 0;
    for (const e of doc.entries) trash.push(e);
  }

  async function restoreEntry(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/trash/${id}/restore`, { method: "POST" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
    await loadTrash();
  }

  async function permanentlyDeleteEntry(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/trash/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await loadTrash();
  }

  async function emptyTrash(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/trash/empty`, { method: "POST" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await loadTrash();
  }

  init();

  return {
    get entries() { return entries as KBEntry[]; },
    get trash() { return trash as KBEntry[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    createEntry,
    updateEntry,
    reorderSiblings,
    deleteEntry,
    uploadAttachment,
    deleteAttachment,
    loadTrash,
    restoreEntry,
    permanentlyDeleteEntry,
    emptyTrash,
    reload: init,
  };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/kbStore.test.ts`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/kbStore.svelte.ts packages/editor/test/kbStore.test.ts
git commit -m "feat(kb): rewrite kbStore for page nesting, reorder, and trash"
```

---

## Task 5: Frontend KBTree.svelte (unified page tree)

Depends on Task 4 (`KBEntry` type).

**Files:**
- Modify: `packages/editor/src/lib/components/ui/KBTree.svelte` (full rewrite)
- Modify: `packages/editor/test/KBTree.test.ts` (full rewrite)

**Interfaces:**
- Consumes: `KBEntry` from `../../kbStore.svelte` (Task 4).
- Produces (used by Task 8's `KBPage.svelte`):
  - Props: `{ entries, parentId?, depth?, selectedId, searchQuery, collapsedIds, renamingId, dragging, onselect, ontoggle, oncreatechild, onstartrename, oncommitrename, oncancelrename, ondelete, onstartdrag, onenddrag, ondrop }`
  - `ondrop: (draggedId: string, targetParentId: string | null, orderedIds: string[] | null) => void` — `orderedIds` is `null` for a pure nest ("drop inside", append at end of new parent's children); non-null (a full sibling id list including the dragged id at its new position) for a "drop before/after" reorder, which may also imply a parent change.
  - Rendering rule: an entry whose `parentId` does not match any other live entry's `id` renders as if it were top-level (handles both `parentId === null` and "parent was trashed/deleted" per the spec's rendering rule).

- [ ] **Step 1: Write the failing tests**

Replace the full contents of `packages/editor/test/KBTree.test.ts`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import KBTree from "../src/lib/components/ui/KBTree.svelte";
import type { KBEntry } from "../src/lib/kbStore.svelte";

function makeEntry(overrides: Partial<KBEntry> = {}): KBEntry {
  return {
    id: "e1", title: "How to paint", content: "", createdAt: "2026-06-28T10:00:00Z",
    updatedAt: "2026-06-28T10:00:00Z", attachments: [], parentId: null, icon: "📄", order: 0,
    ...overrides,
  };
}

function baseProps(overrides: Record<string, unknown> = {}) {
  return {
    entries: [] as KBEntry[],
    selectedId: null,
    searchQuery: "",
    collapsedIds: new Set<string>(),
    renamingId: null,
    dragging: null,
    onselect: vi.fn(),
    ontoggle: vi.fn(),
    oncreatechild: vi.fn(),
    onstartrename: vi.fn(),
    oncommitrename: vi.fn(),
    oncancelrename: vi.fn(),
    ondelete: vi.fn(),
    onstartdrag: vi.fn(),
    onenddrag: vi.fn(),
    ondrop: vi.fn(),
    ...overrides,
  };
}

function setup(overrides: Record<string, unknown> = {}) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const props = baseProps(overrides);
  const comp = mount(KBTree, { target, props });
  flushSync();
  return { target, comp, props };
}

describe("KBTree — rendering", () => {
  it("renders root-level pages sorted by order", () => {
    const { target, comp } = setup({
      entries: [makeEntry({ id: "b", title: "B", order: 1 }), makeEntry({ id: "a", title: "A", order: 0 })],
    });
    const titles = Array.from(target.querySelectorAll(".page-title")).map((n) => n.textContent);
    expect(titles).toEqual(["A", "B"]);
    unmount(comp); target.remove();
  });

  it("shows the page's icon, defaulting to 📄", () => {
    const { target, comp } = setup({
      entries: [makeEntry({ icon: "🔧" }), makeEntry({ id: "e2", icon: "", order: 1 })],
    });
    const icons = Array.from(target.querySelectorAll(".page-icon")).map((n) => n.textContent);
    expect(icons).toContain("🔧");
    expect(icons).toContain("📄");
    unmount(comp); target.remove();
  });

  it("shows a disclosure triangle only for pages with children", () => {
    const { target, comp } = setup({
      entries: [makeEntry({ id: "p" }), makeEntry({ id: "c", parentId: "p", order: 0 })],
    });
    expect(target.querySelectorAll(".disclosure").length).toBe(1);
    expect(target.querySelectorAll(".disclosure-spacer").length).toBe(1);
    unmount(comp); target.remove();
  });

  it("renders a live page whose parent no longer exists as top-level", () => {
    const { target, comp } = setup({
      entries: [makeEntry({ id: "orphan", parentId: "trashed-parent" })],
    });
    expect(target.querySelectorAll(".tree-row").length).toBe(1);
    expect(target.querySelector(".page-title")?.textContent).toBe("How to paint");
    unmount(comp); target.remove();
  });

  it("does not render children of a collapsed page", () => {
    const { target, comp } = setup({
      entries: [makeEntry({ id: "p" }), makeEntry({ id: "c", parentId: "p", order: 0 })],
      collapsedIds: new Set(["p"]),
    });
    expect(target.querySelectorAll(".tree-row").length).toBe(1);
    unmount(comp); target.remove();
  });

  it("shows empty state when there are no pages", () => {
    const { target, comp } = setup();
    expect(target.textContent).toContain("No pages yet.");
    unmount(comp); target.remove();
  });
});

describe("KBTree — selection", () => {
  it("clicking a row calls onselect with the entry", () => {
    const onselect = vi.fn();
    const { target, comp } = setup({ entries: [makeEntry()], onselect });
    (target.querySelector(".tree-row") as HTMLElement).click();
    expect(onselect).toHaveBeenCalledWith(expect.objectContaining({ id: "e1" }));
    unmount(comp); target.remove();
  });

  it("marks the selected row active", () => {
    const { target, comp } = setup({ entries: [makeEntry()], selectedId: "e1" });
    expect(target.querySelector(".tree-row")?.className).toContain("active");
    unmount(comp); target.remove();
  });

  it("clicking the disclosure triangle toggles without selecting", () => {
    const onselect = vi.fn();
    const ontoggle = vi.fn();
    const { target, comp } = setup({
      entries: [makeEntry({ id: "p" }), makeEntry({ id: "c", parentId: "p", order: 0 })],
      onselect, ontoggle,
    });
    (target.querySelector(".disclosure") as HTMLElement).click();
    expect(ontoggle).toHaveBeenCalledWith("p");
    expect(onselect).not.toHaveBeenCalled();
    unmount(comp); target.remove();
  });
});

describe("KBTree — search filtering", () => {
  it("keeps a page visible if its own title matches", () => {
    const { target, comp } = setup({
      entries: [makeEntry({ id: "a", title: "Alpha" }), makeEntry({ id: "b", title: "Beta", order: 1 })],
      searchQuery: "alp",
    });
    expect(target.querySelectorAll(".page-title").length).toBe(1);
    unmount(comp); target.remove();
  });

  it("keeps a parent visible (and auto-expanded) if a descendant matches", () => {
    const { target, comp } = setup({
      entries: [makeEntry({ id: "p", title: "Parent" }), makeEntry({ id: "c", title: "Matching child", parentId: "p", order: 0 })],
      collapsedIds: new Set(["p"]),
      searchQuery: "matching",
    });
    const titles = Array.from(target.querySelectorAll(".page-title")).map((n) => n.textContent);
    expect(titles).toEqual(["Parent", "Matching child"]);
    unmount(comp); target.remove();
  });
});

describe("KBTree — creation and rename", () => {
  it("clicking add-child calls oncreatechild with the page id", () => {
    const oncreatechild = vi.fn();
    const { target, comp } = setup({ entries: [makeEntry()], oncreatechild });
    (target.querySelector(".add-child") as HTMLElement).click();
    expect(oncreatechild).toHaveBeenCalledWith("e1");
    unmount(comp); target.remove();
  });

  it("shows a rename input when renamingId matches, and commits on Enter", () => {
    const oncommitrename = vi.fn();
    const { target, comp } = setup({ entries: [makeEntry()], renamingId: "e1", oncommitrename });
    const input = target.querySelector(".rename-input") as HTMLInputElement;
    expect(input).not.toBeNull();
    input.value = "Renamed title";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(oncommitrename).toHaveBeenCalledWith("e1", "Renamed title");
    unmount(comp); target.remove();
  });
});

describe("KBTree — drag and drop", () => {
  it("dropping in the middle band of a row calls ondrop with orderedIds null (nest)", () => {
    const ondrop = vi.fn();
    const { target, comp } = setup({
      entries: [makeEntry({ id: "a" }), makeEntry({ id: "b", order: 1 })],
      dragging: "a", ondrop,
    });
    const rows = target.querySelectorAll(".tree-row");
    const targetRow = rows[1] as HTMLElement;
    vi.spyOn(targetRow, "getBoundingClientRect").mockReturnValue({ top: 0, height: 20 } as DOMRect);
    targetRow.dispatchEvent(new MouseEvent("dragover", { bubbles: true, clientY: 10 }));
    targetRow.dispatchEvent(new MouseEvent("drop", { bubbles: true, clientY: 10 }));
    expect(ondrop).toHaveBeenCalledWith("a", "b", null);
    unmount(comp); target.remove();
  });

  it("dropping in the top band of a row calls ondrop with a before-reordered sibling list", () => {
    const ondrop = vi.fn();
    const { target, comp } = setup({
      entries: [makeEntry({ id: "a" }), makeEntry({ id: "b", order: 1 }), makeEntry({ id: "c", order: 2 })],
      dragging: "c", ondrop,
    });
    const rows = target.querySelectorAll(".tree-row");
    const targetRow = rows[0] as HTMLElement;
    vi.spyOn(targetRow, "getBoundingClientRect").mockReturnValue({ top: 0, height: 20 } as DOMRect);
    targetRow.dispatchEvent(new MouseEvent("dragover", { bubbles: true, clientY: 1 }));
    targetRow.dispatchEvent(new MouseEvent("drop", { bubbles: true, clientY: 1 }));
    expect(ondrop).toHaveBeenCalledWith("c", null, ["c", "a", "b"]);
    unmount(comp); target.remove();
  });

  it("does not call ondrop when dropping a page onto its own descendant", () => {
    const ondrop = vi.fn();
    const { target, comp } = setup({
      entries: [makeEntry({ id: "p" }), makeEntry({ id: "c", parentId: "p", order: 0 })],
      dragging: "p", ondrop,
    });
    const rows = target.querySelectorAll(".tree-row");
    const childRow = rows[1] as HTMLElement;
    vi.spyOn(childRow, "getBoundingClientRect").mockReturnValue({ top: 0, height: 20 } as DOMRect);
    childRow.dispatchEvent(new MouseEvent("dragover", { bubbles: true, clientY: 10 }));
    childRow.dispatchEvent(new MouseEvent("drop", { bubbles: true, clientY: 10 }));
    expect(ondrop).not.toHaveBeenCalled();
    unmount(comp); target.remove();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/KBTree.test.ts`
Expected: FAIL — `KBFolder` import doesn't exist yet in the old component's expectations, `.page-title`/`.page-icon`/`.add-child` selectors don't exist in the old folder/entry-split markup.

- [ ] **Step 3: Rewrite KBTree.svelte**

Replace the full contents of `packages/editor/src/lib/components/ui/KBTree.svelte`:

```svelte
<!-- packages/editor/src/lib/components/ui/KBTree.svelte -->
<script lang="ts">
  import type { KBEntry } from "../../kbStore.svelte";
  import Self from "./KBTree.svelte";

  interface DropIndicator {
    id: string;
    position: "before" | "after" | "inside";
  }

  interface Props {
    entries: KBEntry[];
    parentId?: string | null;
    depth?: number;
    selectedId: string | null;
    searchQuery: string;
    collapsedIds: Set<string>;
    renamingId: string | null;
    dragging: string | null;
    onselect: (entry: KBEntry) => void;
    ontoggle: (id: string) => void;
    oncreatechild: (parentId: string) => void;
    onstartrename: (id: string) => void;
    oncommitrename: (id: string, title: string) => void;
    oncancelrename: () => void;
    ondelete: (id: string) => void;
    onstartdrag: (id: string) => void;
    onenddrag: () => void;
    ondrop: (draggedId: string, targetParentId: string | null, orderedIds: string[] | null) => void;
  }

  let {
    entries, parentId = null, depth = 0, selectedId, searchQuery, collapsedIds,
    renamingId, dragging,
    onselect, ontoggle, oncreatechild, onstartrename, oncommitrename, oncancelrename, ondelete,
    onstartdrag, onenddrag, ondrop,
  }: Props = $props();

  let renameDraft = $state("");
  let menuOpenFor = $state<string | null>(null);
  let dropIndicator = $state<DropIndicator | null>(null);

  function matches(text: string): boolean {
    const q = searchQuery.trim().toLowerCase();
    return !q || text.toLowerCase().includes(q);
  }

  // A live page whose parentId doesn't match any other live page (null, or
  // pointing at a page that's been trashed/deleted) renders as top-level.
  function isRootLevel(entry: KBEntry): boolean {
    return entry.parentId === null || !entries.some((p) => p.id === entry.parentId);
  }

  const visibleIds = $derived.by(() => {
    const q = searchQuery.trim();
    if (!q) return null;
    const childrenOf = new Map<string | null, KBEntry[]>();
    for (const e of entries) {
      const key = isRootLevel(e) ? null : e.parentId;
      const list = childrenOf.get(key) ?? [];
      list.push(e);
      childrenOf.set(key, list);
    }
    const visible = new Set<string>();
    function visit(entry: KBEntry): boolean {
      const ownMatch = matches(entry.title);
      const hasMatchingChild = (childrenOf.get(entry.id) ?? []).map(visit).some(Boolean);
      const keep = ownMatch || hasMatchingChild;
      if (keep) visible.add(entry.id);
      return keep;
    }
    for (const e of childrenOf.get(null) ?? []) visit(e);
    return visible;
  });

  const childEntries = $derived(
    entries
      .filter((e) => (parentId === null ? isRootLevel(e) : e.parentId === parentId))
      .filter((e) => visibleIds === null || visibleIds.has(e.id))
      .slice()
      .sort((a, b) => a.order - b.order),
  );

  function isOpen(id: string): boolean {
    return searchQuery.trim() !== "" || !collapsedIds.has(id);
  }

  function hasChildren(id: string): boolean {
    return entries.some((e) => e.parentId === id);
  }

  function startRename(entry: KBEntry): void {
    renameDraft = entry.title;
    menuOpenFor = null;
    onstartrename(entry.id);
  }

  function commitRename(id: string): void {
    const title = renameDraft.trim();
    if (title) oncommitrename(id, title);
    else oncancelrename();
  }

  function wouldCreateCycle(draggedId: string, targetId: string): boolean {
    if (draggedId === targetId) return true;
    let current: string | null = targetId;
    const seen = new Set<string>();
    while (current !== null) {
      if (current === draggedId) return true;
      if (seen.has(current)) return false;
      seen.add(current);
      const e = entries.find((x) => x.id === current);
      current = e ? e.parentId : null;
    }
    return false;
  }

  function handleDragOver(e: DragEvent, entry: KBEntry): void {
    if (!dragging || dragging === entry.id || wouldCreateCycle(dragging, entry.id)) return;
    e.preventDefault();
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const ratio = (e.clientY - rect.top) / rect.height;
    const position = ratio < 0.25 ? "before" : ratio > 0.75 ? "after" : "inside";
    dropIndicator = { id: entry.id, position };
  }

  function handleDrop(e: DragEvent, entry: KBEntry): void {
    e.preventDefault();
    const indicator = dropIndicator;
    dropIndicator = null;
    if (!dragging || dragging === entry.id || wouldCreateCycle(dragging, entry.id) || !indicator) return;
    if (indicator.position === "inside") {
      ondrop(dragging, entry.id, null);
      return;
    }
    const siblings = entries
      .filter((s) => s.parentId === entry.parentId && s.id !== dragging)
      .sort((a, b) => a.order - b.order);
    const targetIndex = siblings.findIndex((s) => s.id === entry.id);
    const insertAt = indicator.position === "before" ? targetIndex : targetIndex + 1;
    const orderedIds = siblings.map((s) => s.id);
    orderedIds.splice(insertAt, 0, dragging);
    ondrop(dragging, entry.parentId, orderedIds);
  }
</script>

<ul class="kb-tree" class:root={depth === 0}>
  {#each childEntries as entry (entry.id)}
    <li>
      <div
        role="button"
        tabindex="0"
        class="tree-row"
        class:active={entry.id === selectedId}
        class:drop-before={dropIndicator?.id === entry.id && dropIndicator.position === "before"}
        class:drop-after={dropIndicator?.id === entry.id && dropIndicator.position === "after"}
        class:drop-inside={dropIndicator?.id === entry.id && dropIndicator.position === "inside"}
        draggable="true"
        ondragstart={(e) => { e.dataTransfer?.setData("text/plain", ""); onstartdrag(entry.id); }}
        ondragend={() => { dropIndicator = null; onenddrag(); }}
        ondragover={(e) => handleDragOver(e, entry)}
        ondragleave={() => { if (dropIndicator?.id === entry.id) dropIndicator = null; }}
        ondrop={(e) => handleDrop(e, entry)}
        onclick={() => onselect(entry)}
        onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") onselect(entry); }}
      >
        {#if hasChildren(entry.id)}
          <button
            class="disclosure"
            onclick={(e) => { e.stopPropagation(); ontoggle(entry.id); }}
            aria-label={isOpen(entry.id) ? "Collapse" : "Expand"}
          >{isOpen(entry.id) ? "▾" : "▸"}</button>
        {:else}
          <span class="disclosure-spacer"></span>
        {/if}
        <span class="page-icon">{entry.icon || "📄"}</span>
        {#if renamingId === entry.id}
          <input
            class="rename-input"
            bind:value={renameDraft}
            onclick={(e) => e.stopPropagation()}
            onblur={() => commitRename(entry.id)}
            onkeydown={(e) => {
              if (e.key === "Enter") commitRename(entry.id);
              if (e.key === "Escape") oncancelrename();
            }}
          />
        {:else}
          <span class="page-title">{entry.title}</span>
        {/if}
        <button
          class="add-child"
          title="Add child page"
          onclick={(e) => { e.stopPropagation(); oncreatechild(entry.id); }}
        >＋</button>
        <button
          class="menu-trigger"
          title="Page actions"
          onclick={(e) => { e.stopPropagation(); menuOpenFor = menuOpenFor === entry.id ? null : entry.id; }}
        >⋯</button>
        {#if menuOpenFor === entry.id}
          <div class="page-menu" role="menu">
            <button role="menuitem" onclick={(e) => { e.stopPropagation(); oncreatechild(entry.id); menuOpenFor = null; }}>Add child page</button>
            <button role="menuitem" onclick={(e) => { e.stopPropagation(); startRename(entry); }}>Rename</button>
            <button role="menuitem" class="danger" onclick={(e) => { e.stopPropagation(); ondelete(entry.id); menuOpenFor = null; }}>Delete</button>
          </div>
        {/if}
      </div>
      {#if hasChildren(entry.id) && isOpen(entry.id)}
        <Self
          {entries} parentId={entry.id} depth={depth + 1}
          {selectedId} {searchQuery} {collapsedIds} {renamingId} {dragging}
          {onselect} {ontoggle} {oncreatechild} {onstartrename} {oncommitrename} {oncancelrename} {ondelete}
          {onstartdrag} {onenddrag} {ondrop}
        />
      {/if}
    </li>
  {/each}
  {#if depth === 0 && childEntries.length === 0}
    <li class="list-empty">
      {searchQuery.trim() ? "No matching pages." : "No pages yet."}
    </li>
  {/if}
</ul>

<style>
  .kb-tree { list-style: none; margin: 0; padding: 0; }
  .kb-tree:not(.root) { padding-left: 16px; }

  .tree-row {
    display: flex; align-items: center; gap: 6px;
    padding: 6px 8px; border-radius: var(--radius-md);
    cursor: pointer; position: relative;
    border-left: 3px solid transparent;
  }
  .tree-row:hover { background: var(--surface-hover); }
  .tree-row.active { background: var(--surface-alt); border-left-color: var(--accent); }
  .tree-row.drop-inside { outline: 2px solid var(--accent); outline-offset: -2px; }
  .tree-row.drop-before { box-shadow: inset 0 2px 0 var(--accent); }
  .tree-row.drop-after { box-shadow: inset 0 -2px 0 var(--accent); }

  .disclosure {
    background: none; border: none; padding: 0; width: 14px; flex-shrink: 0;
    color: var(--text-faint); font-size: 10px; cursor: pointer;
  }
  .disclosure-spacer { width: 14px; flex-shrink: 0; }
  .page-icon { flex-shrink: 0; font-size: 13px; }
  .page-title {
    flex: 1; min-width: 0; font-size: 13px; color: var(--text); font-weight: 500;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .rename-input {
    flex: 1; min-width: 0; font-size: 13px; font-family: var(--font-sans);
    background: var(--surface-alt); border: 1px solid var(--accent);
    border-radius: var(--radius-sm); padding: 2px 6px; color: var(--text);
  }
  .rename-input:focus { outline: none; }

  .add-child, .menu-trigger {
    background: none; border: none; padding: 2px 4px; color: var(--text-faint);
    cursor: pointer; font-size: 13px; opacity: 0; flex-shrink: 0;
  }
  .tree-row:hover .add-child, .tree-row:hover .menu-trigger,
  .add-child:focus, .menu-trigger:focus { opacity: 1; }

  .page-menu {
    position: absolute; top: 100%; right: 0; z-index: 10;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); box-shadow: var(--shadow-md);
    display: flex; flex-direction: column; min-width: 150px; padding: 4px;
  }
  .page-menu button {
    background: none; border: none; text-align: left; padding: 6px 10px;
    font-size: 12px; color: var(--text); border-radius: var(--radius-sm); cursor: pointer;
  }
  .page-menu button:hover { background: var(--surface-hover); }
  .page-menu button.danger { color: var(--danger); }

  .list-empty { font-size: 12px; color: var(--text-faint); text-align: center; padding: 20px 0; list-style: none; }
</style>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/KBTree.test.ts`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/KBTree.svelte packages/editor/test/KBTree.test.ts
git commit -m "feat(kb): unify KBTree into a single recursive page tree"
```

---

## Task 6: Frontend KBTrash.svelte (new component)

Depends on Task 4 (`KBEntry` type). Independent of Task 5.

**Files:**
- Create: `packages/editor/src/lib/components/ui/KBTrash.svelte`
- Create: `packages/editor/test/KBTrash.test.ts`

**Interfaces:**
- Consumes: `KBEntry` from `../../kbStore.svelte` (Task 4), `Button` from `./Button.svelte` (existing, unchanged — `variant` values `secondary`/`danger`/`ghost` already used elsewhere in this codebase).
- Produces (used by Task 8's `KBPage.svelte`):
  - Props: `{ entries: KBEntry[]; onrestore: (id: string) => void; ondeleteforever: (id: string) => void; onemptytrash: () => void }`

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/KBTrash.test.ts`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import KBTrash from "../src/lib/components/ui/KBTrash.svelte";
import type { KBEntry } from "../src/lib/kbStore.svelte";

function makeEntry(overrides: Partial<KBEntry> = {}): KBEntry {
  return {
    id: "e1", title: "Old note", content: "", createdAt: "2026-06-28T10:00:00Z",
    updatedAt: "2026-06-28T10:00:00Z", attachments: [], parentId: null, icon: "📄", order: 0,
    deletedAt: "2026-07-01T00:00:00Z",
    ...overrides,
  };
}

function setup(overrides: Record<string, unknown> = {}) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const props = {
    entries: [] as KBEntry[],
    onrestore: vi.fn(),
    ondeleteforever: vi.fn(),
    onemptytrash: vi.fn(),
    ...overrides,
  };
  const comp = mount(KBTrash, { target, props });
  flushSync();
  return { target, comp, props };
}

describe("KBTrash", () => {
  it("shows empty state when trash is empty", () => {
    const { target, comp } = setup();
    expect(target.textContent).toContain("Trash is empty.");
    unmount(comp); target.remove();
  });

  it("lists each trashed page with its title and icon", () => {
    const { target, comp } = setup({ entries: [makeEntry({ icon: "🔧" })] });
    expect(target.querySelector(".trash-title")?.textContent).toBe("Old note");
    expect(target.querySelector(".trash-icon")?.textContent).toBe("🔧");
    unmount(comp); target.remove();
  });

  it("clicking Restore calls onrestore with the entry id", () => {
    const onrestore = vi.fn();
    const { target, comp } = setup({ entries: [makeEntry()], onrestore });
    const restoreBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Restore") as HTMLElement;
    restoreBtn.click();
    expect(onrestore).toHaveBeenCalledWith("e1");
    unmount(comp); target.remove();
  });

  it("delete forever requires confirmation before calling ondeleteforever", () => {
    const ondeleteforever = vi.fn();
    const { target, comp } = setup({ entries: [makeEntry()], ondeleteforever });
    (target.querySelector('[title="Delete forever"]') as HTMLElement).click();
    flushSync();
    expect(ondeleteforever).not.toHaveBeenCalled();
    const confirmBtn = target.querySelector(".trash-actions button.ui-button-danger") as HTMLElement;
    confirmBtn.click();
    expect(ondeleteforever).toHaveBeenCalledWith("e1");
    unmount(comp); target.remove();
  });

  it("does not show Empty Trash button when trash is empty", () => {
    const { target, comp } = setup();
    const emptyBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Empty Trash");
    expect(emptyBtn).toBeUndefined();
    unmount(comp); target.remove();
  });

  it("Empty Trash requires confirmation before calling onemptytrash", () => {
    const onemptytrash = vi.fn();
    const { target, comp } = setup({ entries: [makeEntry()], onemptytrash });
    const emptyBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Empty Trash") as HTMLElement;
    emptyBtn.click();
    flushSync();
    expect(onemptytrash).not.toHaveBeenCalled();
    const confirmBtn = target.querySelector(".trash-header button.ui-button-danger") as HTMLElement;
    confirmBtn.click();
    expect(onemptytrash).toHaveBeenCalled();
    unmount(comp); target.remove();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/KBTrash.test.ts`
Expected: FAIL — `Failed to resolve import "../src/lib/components/ui/KBTrash.svelte"`.

- [ ] **Step 3: Create KBTrash.svelte**

Create `packages/editor/src/lib/components/ui/KBTrash.svelte`:

```svelte
<!-- packages/editor/src/lib/components/ui/KBTrash.svelte -->
<script lang="ts">
  import type { KBEntry } from "../../kbStore.svelte";
  import Button from "./Button.svelte";

  interface Props {
    entries: KBEntry[];
    onrestore: (id: string) => void;
    ondeleteforever: (id: string) => void;
    onemptytrash: () => void;
  }
  let { entries, onrestore, ondeleteforever, onemptytrash }: Props = $props();

  let confirmEmptyAll = $state(false);
  let confirmDeleteId = $state<string | null>(null);

  function fmtDate(iso: string | null | undefined): string {
    return iso ? new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "";
  }
</script>

<div class="kb-trash">
  <div class="trash-header">
    <h2>Trash</h2>
    {#if entries.length > 0}
      {#if confirmEmptyAll}
        <span class="confirm-text">Permanently delete all {entries.length} pages?</span>
        <Button variant="danger" onclick={() => { onemptytrash(); confirmEmptyAll = false; }}>✓</Button>
        <Button variant="ghost" onclick={() => { confirmEmptyAll = false; }}>✕</Button>
      {:else}
        <Button variant="secondary" onclick={() => { confirmEmptyAll = true; }}>Empty Trash</Button>
      {/if}
    {/if}
  </div>
  {#if entries.length === 0}
    <div class="trash-empty">Trash is empty.</div>
  {:else}
    <ul class="trash-list">
      {#each entries as entry (entry.id)}
        <li class="trash-row">
          <span class="trash-icon">{entry.icon || "📄"}</span>
          <span class="trash-title">{entry.title}</span>
          <span class="trash-date">Deleted {fmtDate(entry.deletedAt)}</span>
          <div class="trash-actions">
            <Button variant="secondary" onclick={() => onrestore(entry.id)}>Restore</Button>
            {#if confirmDeleteId === entry.id}
              <Button variant="danger" onclick={() => { ondeleteforever(entry.id); confirmDeleteId = null; }}>✓</Button>
              <Button variant="ghost" onclick={() => { confirmDeleteId = null; }}>✕</Button>
            {:else}
              <Button variant="ghost" onclick={() => { confirmDeleteId = entry.id; }} title="Delete forever">🗑</Button>
            {/if}
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .kb-trash { padding: var(--space-4); flex: 1; overflow-y: auto; }
  .trash-header { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-3); }
  .trash-header h2 { font-size: 16px; font-weight: 600; color: var(--text); margin: 0; flex: 1; }
  .confirm-text { font-size: 11px; color: var(--danger); }
  .trash-empty { color: var(--text-faint); font-size: 13px; }
  .trash-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  .trash-row {
    display: flex; align-items: center; gap: 8px; padding: 8px 10px;
    border: 1px solid var(--border); border-radius: var(--radius-md);
  }
  .trash-icon { font-size: 14px; flex-shrink: 0; }
  .trash-title { flex: 1; min-width: 0; font-size: 13px; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .trash-date { font-size: 11px; color: var(--text-faint); flex-shrink: 0; }
  .trash-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
</style>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/KBTrash.test.ts`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/KBTrash.svelte packages/editor/test/KBTrash.test.ts
git commit -m "feat(kb): add KBTrash view for restoring/purging deleted pages"
```

---

## Task 7: MarkdownEditor live KB links + `/page` slash command

Independent of Tasks 4-6 (touches a different, generic shared component). Its new props are additive and optional, so every other consumer of `MarkdownEditor` (Costs, Works, Inventory, Consumables, Chores, KB itself) is unaffected when they don't pass them.

**Files:**
- Modify: `packages/editor/src/lib/components/ui/MarkdownEditor.svelte`
- Modify: `packages/editor/test/MarkdownEditor.test.ts` (append new test blocks; every existing test in this file is untouched)

**Interfaces:**
- Produces (used by Task 8's `KBPage.svelte`):
  - New prop `resolveKbLink?: (id: string) => { title: string; icon: string } | null` — when provided, any rendered `<a href="#/kb/<id>">` in the preview has its visible text replaced with `"{icon} {title}"` from a live lookup (ignoring whatever text was in the markdown source), or becomes a greyed-out non-clickable "Page deleted" chip if the lookup returns `null`.
  - New prop `onSlashPage?: () => Promise<{ id: string; title: string } | null>` — when the user types exactly `/page` at the start of the current line while editing, it's replaced with `[{title}](#/kb/{id})` from the resolved promise (or left as literal text if the promise resolves to `null`, e.g. because no page is open yet to parent under).

- [ ] **Step 1: Write the failing tests**

Append to `packages/editor/test/MarkdownEditor.test.ts` (new `describe` blocks, added after the file's existing content):

```typescript
describe("MarkdownEditor — resolveKbLink", () => {
  it("replaces the link text with the live title and icon when resolvable", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: {
        value: "See [stale text](#/kb/p1) for details",
        editing: false,
        resolveKbLink: (id: string) => (id === "p1" ? { title: "Current Title", icon: "🔧" } : null),
      },
    });
    flushSync();
    const link = target.querySelector("a.kb-link");
    expect(link).not.toBeNull();
    expect(link?.textContent).toBe("🔧 Current Title");
    unmount(app);
    target.remove();
  });

  it("renders a Page deleted chip when the link cannot be resolved", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: {
        value: "See [old link](#/kb/gone) for details",
        editing: false,
        resolveKbLink: () => null,
      },
    });
    flushSync();
    const chip = target.querySelector("a.kb-link-deleted");
    expect(chip).not.toBeNull();
    expect(chip?.textContent).toBe("Page deleted");
    expect(chip?.hasAttribute("href")).toBe(false);
    unmount(app);
    target.remove();
  });

  it("leaves non-kb links untouched", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: {
        value: "[External](https://example.com)",
        editing: false,
        resolveKbLink: () => null,
      },
    });
    flushSync();
    const link = target.querySelector("a[href='https://example.com']");
    expect(link?.textContent).toBe("External");
    unmount(app);
    target.remove();
  });

  it("does not alter kb links when resolveKbLink is not provided", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "[Some text](#/kb/p1)", editing: false },
    });
    flushSync();
    const link = target.querySelector("a[href='#/kb/p1']");
    expect(link?.textContent).toBe("Some text");
    unmount(app);
    target.remove();
  });
});

describe("MarkdownEditor — /page slash command", () => {
  it("replaces /page with a link to the created child page", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onSlashPage = async () => ({ id: "new-child", title: "New page" });
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, onSlashPage },
    });
    flushSync();
    const textarea = target.querySelector(".md-editor") as HTMLTextAreaElement;
    textarea.value = "/page";
    textarea.selectionStart = 5;
    textarea.selectionEnd = 5;
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(textarea.value).toBe("[New page](#/kb/new-child)");
    unmount(app);
    target.remove();
  });

  it("does nothing when onSlashPage is not provided", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true },
    });
    flushSync();
    const textarea = target.querySelector(".md-editor") as HTMLTextAreaElement;
    textarea.value = "/page";
    textarea.selectionStart = 5;
    textarea.selectionEnd = 5;
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(textarea.value).toBe("/page");
    unmount(app);
    target.remove();
  });

  it("does nothing when onSlashPage resolves to null", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onSlashPage = async () => null;
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, onSlashPage },
    });
    flushSync();
    const textarea = target.querySelector(".md-editor") as HTMLTextAreaElement;
    textarea.value = "/page";
    textarea.selectionStart = 5;
    textarea.selectionEnd = 5;
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(textarea.value).toBe("/page");
    unmount(app);
    target.remove();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/MarkdownEditor.test.ts`
Expected: FAIL — `resolveKbLink`/`onSlashPage` props are unused by the current component, so links keep their literal text and `/page` is never intercepted.

- [ ] **Step 3: Add the props and behavior to MarkdownEditor.svelte**

In `packages/editor/src/lib/components/ui/MarkdownEditor.svelte`, update the `Props` interface (currently lines 9-16) to add the two new optional fields:

```typescript
  interface Props {
    value: string;
    editing: boolean;
    placeholder?: string;
    minHeight?: string;
    mediaItems?: MediaItem[];
    clickToEdit?: boolean;
    resolveKbLink?: (id: string) => { title: string; icon: string } | null;
    onSlashPage?: () => Promise<{ id: string; title: string } | null>;
  }
```

Update the destructuring (currently lines 18-25) to include the new props:

```typescript
  let {
    value = $bindable(),
    editing = $bindable(),
    placeholder = "Click to add markdown content…",
    minHeight = "200px",
    mediaItems = [],
    clickToEdit = true,
    resolveKbLink,
    onSlashPage,
  }: Props = $props();
```

Replace the `renderedHtml` derivation (currently lines 42-44):

```typescript
  function resolveKbLinksInHtml(html: string): string {
    if (!resolveKbLink) return html;
    const template = document.createElement("template");
    template.innerHTML = html;
    template.content.querySelectorAll("a[href^='#/kb/']").forEach((node) => {
      const a = node as HTMLAnchorElement;
      const href = a.getAttribute("href") ?? "";
      const id = decodeURIComponent(href.slice("#/kb/".length));
      const target = resolveKbLink!(id);
      if (target) {
        a.textContent = `${target.icon} ${target.title}`;
        a.classList.add("kb-link");
      } else {
        a.removeAttribute("href");
        a.textContent = "Page deleted";
        a.classList.add("kb-link-deleted");
      }
    });
    return template.innerHTML;
  }

  // marked() is sync here (no async extensions); cast to string is safe.
  const renderedHtml = $derived(
    value.trim() ? resolveKbLinksInHtml(DOMPurify.sanitize(marked(value) as string)) : "",
  );
```

Add the slash-command handler after the existing `linePrefix` function (currently ending at line 66):

```typescript
  async function handleTextareaInput(): Promise<void> {
    if (!onSlashPage || !textareaEl) return;
    const cursor = textareaEl.selectionStart;
    const lineStart = value.lastIndexOf("\n", cursor - 1) + 1;
    if (value.slice(lineStart, cursor) !== "/page") return;
    const result = await onSlashPage();
    if (!result || !textareaEl) return;
    const link = `[${result.title}](#/kb/${result.id})`;
    value = value.slice(0, lineStart) + link + value.slice(cursor);
    const ns = lineStart + link.length;
    setTimeout(() => { if (textareaEl) { textareaEl.focus(); textareaEl.setSelectionRange(ns, ns); } }, 0);
  }
```

Add `oninput={handleTextareaInput}` to the `<textarea>` element (currently lines 146-152) — it coexists with the existing `bind:value`:

```svelte
  <textarea
    class="md-editor"
    style:min-height={minHeight}
    bind:this={textareaEl}
    bind:value
    oninput={handleTextareaInput}
    placeholder="Write in Markdown…"
  ></textarea>
```

Add CSS for the new link states, appended inside the existing `<style>` block near the other `.md-preview :global(a)` rule (currently line 264):

```css
  .md-preview :global(a.kb-link) { font-weight: 500; }
  .md-preview :global(a.kb-link-deleted) {
    color: var(--text-faint); text-decoration: line-through; cursor: default;
  }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/MarkdownEditor.test.ts`
Expected: PASS (all tests, including every pre-existing test in the file — the new props are purely additive).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/MarkdownEditor.svelte packages/editor/test/MarkdownEditor.test.ts
git commit -m "feat(kb): live-resolve KB page links and add /page slash command in MarkdownEditor"
```

---

## Task 8: KBPage.svelte (wire everything together)

Depends on Tasks 4, 5, 6, 7 (uses `kbStore`, `KBTree`, `KBTrash`, and the new `MarkdownEditor` props).

**Files:**
- Modify: `packages/editor/src/lib/components/KBPage.svelte` (full rewrite)
- Modify: `packages/editor/test/KBPage.test.ts` (full rewrite)

**Interfaces:**
- Consumes: `createKBStore`/`KBEntry` (Task 4), `KBTree` (Task 5), `KBTrash` (Task 6), `MarkdownEditor`'s `resolveKbLink`/`onSlashPage` (Task 7), existing `Button`/`Input`/`Card`/`MediaGallery`/`Lightbox`/`EmojiPicker` (unchanged).
- Produces (used by Task 9's `App.svelte`):
  - Props: `{ store: KBStore; selectedItemId?: string | null; onnavigate?: (id: string) => void }` — note `onclearselection` is removed; selection is now driven by the URL (`selectedItemId`) rather than a clear-once external signal.
  - `onnavigate` fires with a page id whenever the page changes via in-app interaction (tree click, new-page/child-page creation) so the parent can update the URL hash. Native anchor clicks on live KB links inside rendered content navigate via the browser's own hashchange handling and don't call `onnavigate`.

- [ ] **Step 1: Write the failing tests**

Replace the full contents of `packages/editor/test/KBPage.test.ts`. First inspect the current file's imports and helper setup so the rewrite matches this codebase's `createKBStore`-based mount pattern:

```bash
sed -n '1,40p' packages/editor/test/KBPage.test.ts
```

Then write the new file (base it on that same `mount`/`vi.stubGlobal("fetch", ...)` pattern used throughout this codebase's Svelte 5 component tests — see `KBTree.test.ts`/`KBTrash.test.ts` above for the `mount`/`unmount`/`flushSync` shape, and `kbStore.test.ts` for the `vi.stubGlobal("fetch", ...)` shape):

```typescript
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import KBPage from "../src/lib/components/KBPage.svelte";
import { createKBStore } from "../src/lib/kbStore.svelte";
import type { KBEntry } from "../src/lib/kbStore.svelte";

const HOME = "home-1";

afterEach(() => vi.unstubAllGlobals());

function makeEntry(overrides: Partial<KBEntry> = {}): KBEntry {
  return {
    id: "e1", title: "How to paint", content: "# Painting", createdAt: "2026-06-28T10:00:00Z",
    updatedAt: "2026-06-28T10:00:00Z", attachments: [], parentId: null, icon: "📄", order: 0,
    ...overrides,
  };
}

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

// A minimal in-memory fake of the Task 2 backend. Several KBPage flows
// (create-child-then-append-link, cascade delete, restore, reorder) mutate
// state across multiple fetch calls within a single interaction, so a
// stateless canned response can't exercise them -- this fake mirrors just
// enough of routes/kb.py's behavior (soft delete + cascade, next-order
// append, restore) to make those flows observable in a component test.
function createFakeKbBackend(initial: KBEntry[]) {
  let entries: KBEntry[] = initial.map((e) => ({ ...e }));
  let nextId = 100;

  function live(): KBEntry[] { return entries.filter((e) => !e.deletedAt); }
  function trashed(): KBEntry[] { return entries.filter((e) => e.deletedAt); }

  function descendantIds(id: string): string[] {
    const result: string[] = [];
    const stack = [id];
    while (stack.length) {
      const current = stack.pop() as string;
      for (const e of entries) {
        if (e.parentId === current) { result.push(e.id); stack.push(e.id); }
      }
    }
    return result;
  }

  async function handle(url: string, init?: RequestInit) {
    const method = init?.method ?? "GET";
    const body = init?.body ? JSON.parse(init.body as string) : undefined;

    if (url.endsWith("/kb") && method === "GET") {
      return { ok: true, status: 200, json: async () => ({ version: 1, entries: live() }) };
    }
    if (url.endsWith("/kb") && method === "POST") {
      const parentId = body.parentId ?? null;
      const siblings = live().filter((e) => e.parentId === parentId);
      const order = siblings.length ? Math.max(...siblings.map((s) => s.order)) + 1 : 0;
      const entry: KBEntry = {
        id: `new-${nextId++}`, title: body.title, content: body.content ?? "",
        createdAt: "2026-07-16T00:00:00Z", updatedAt: "2026-07-16T00:00:00Z",
        attachments: [], parentId, icon: body.icon ?? "📄", order,
      };
      entries.push(entry);
      return { ok: true, status: 201, json: async () => entry };
    }
    if (url.endsWith("/kb/trash") && method === "GET") {
      return { ok: true, status: 200, json: async () => ({ entries: trashed() }) };
    }
    if (url.endsWith("/trash/empty") && method === "POST") {
      const ids = trashed().map((e) => e.id);
      entries = live();
      return { ok: true, status: 200, json: async () => ({ deletedCount: ids.length }) };
    }
    const restoreMatch = url.match(/\/kb\/trash\/([^/]+)\/restore$/);
    if (restoreMatch && method === "POST") {
      const ids = new Set([restoreMatch[1], ...descendantIds(restoreMatch[1])]);
      let count = 0;
      for (const e of entries) if (ids.has(e.id) && e.deletedAt) { e.deletedAt = null; count += 1; }
      return { ok: true, status: 200, json: async () => ({ restoredCount: count }) };
    }
    const permDeleteMatch = url.match(/\/kb\/trash\/([^/]+)$/);
    if (permDeleteMatch && method === "DELETE") {
      entries = entries.filter((e) => e.id !== permDeleteMatch[1]);
      return { ok: true, status: 204, json: async () => null };
    }
    if (url.endsWith("/kb/reorder") && method === "PUT") {
      (body.orderedIds as string[]).forEach((id, index) => {
        const e = entries.find((x) => x.id === id);
        if (e) e.order = index;
      });
      return { ok: true, status: 204, json: async () => null };
    }
    if (method === "PUT") {
      const id = (url.match(/\/kb\/([^/]+)$/) as RegExpMatchArray)[1];
      const e = entries.find((x) => x.id === id);
      if (e) {
        if (body.title !== undefined) e.title = body.title;
        if (body.content !== undefined) e.content = body.content;
        if (body.icon !== undefined) e.icon = body.icon;
        if ("parentId" in body) e.parentId = body.parentId;
      }
      return { ok: true, status: 204, json: async () => null };
    }
    if (method === "DELETE") {
      const id = (url.match(/\/kb\/([^/]+)$/) as RegExpMatchArray)[1];
      const ids = new Set([id, ...descendantIds(id)]);
      let count = 0;
      for (const e of entries) if (ids.has(e.id) && !e.deletedAt) { e.deletedAt = "2026-07-16T00:00:00Z"; count += 1; }
      return { ok: true, status: 200, json: async () => ({ deletedCount: count }) };
    }
    return { ok: true, status: 200, json: async () => ({ version: 1, entries: live() }) };
  }

  return { handle };
}

async function setup(initialEntries: KBEntry[] = [], props: Record<string, unknown> = {}) {
  const backend = createFakeKbBackend(initialEntries);
  vi.stubGlobal("fetch", vi.fn((url: string, init?: RequestInit) => backend.handle(url, init)));
  const store = createKBStore(() => HOME);
  await tick();
  const target = document.createElement("div");
  document.body.appendChild(target);
  const comp = mount(KBPage, { target, props: { store, ...props } });
  flushSync();
  await tick();
  flushSync();
  return { target, comp, store };
}

describe("KBPage — empty state", () => {
  it("shows an empty-content placeholder when nothing is selected", async () => {
    const { target, comp } = await setup([]);
    expect(target.textContent).toContain("Select a page or create one");
    unmount(comp); target.remove();
  });

  it("toolbar has a single New Page button (no separate Folder button)", async () => {
    const { target, comp } = await setup([]);
    const buttons = Array.from(target.querySelectorAll("button")).map((b) => b.textContent?.trim());
    expect(buttons).toContain("＋ New Page");
    expect(buttons).not.toContain("＋ Folder");
    unmount(comp); target.remove();
  });
});

describe("KBPage — selection and deep links", () => {
  it("selects the page named by selectedItemId on mount", async () => {
    const { target, comp } = await setup([makeEntry()], { selectedItemId: "e1" });
    expect(target.querySelector(".content-title")?.textContent).toBe("How to paint");
    unmount(comp); target.remove();
  });

  it("calls onnavigate with the new page id when a tree row is clicked", async () => {
    const onnavigate = vi.fn();
    const entries = [makeEntry(), makeEntry({ id: "e2", title: "Second page", order: 1 })];
    const { target, comp } = await setup(entries, { onnavigate });
    const rows = target.querySelectorAll(".tree-row");
    (rows[1] as HTMLElement).click();
    expect(onnavigate).toHaveBeenCalledWith("e2");
    unmount(comp); target.remove();
  });
});

describe("KBPage — child page creation", () => {
  it("clicking add-child on a tree row creates and selects a child page", async () => {
    const entries = [makeEntry()];
    const { target, comp, store } = await setup(entries);
    (target.querySelector(".add-child") as HTMLElement).click();
    await tick(); flushSync(); await tick(); flushSync();
    const created = store.entries.find((e) => e.parentId === "e1");
    expect(created).toBeDefined();
    expect(target.querySelector(".title-input")).not.toBeNull();
    unmount(comp); target.remove();
  });
});

describe("KBPage — delete with cascade confirmation", () => {
  it("shows the sub-page count in the delete confirmation for a page with children", async () => {
    const entries = [makeEntry(), makeEntry({ id: "e2", title: "Child", parentId: "e1", order: 0 })];
    const { target, comp } = await setup(entries, { selectedItemId: "e1" });
    (target.querySelector('[title="Delete page"]') as HTMLElement).click();
    flushSync();
    expect(target.textContent).toContain("sub-page");
    unmount(comp); target.remove();
  });

  it("clears selection after confirming delete of the selected page", async () => {
    const entries = [makeEntry()];
    const { target, comp } = await setup(entries, { selectedItemId: "e1" });
    (target.querySelector('[title="Delete page"]') as HTMLElement).click();
    flushSync();
    const confirmBtn = Array.from(target.querySelectorAll(".header-actions button")).find((b) => b.textContent === "✓") as HTMLElement;
    confirmBtn.click();
    await tick(); flushSync(); await tick(); flushSync();
    expect(target.textContent).toContain("Select a page or create one");
    unmount(comp); target.remove();
  });
});

describe("KBPage — trash", () => {
  it("clicking the Trash link switches the content pane to the trash view", async () => {
    const { target, comp } = await setup([]);
    const trashLink = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Trash")) as HTMLElement;
    trashLink.click();
    await tick(); flushSync();
    expect(target.textContent).toContain("Trash is empty.");
    unmount(comp); target.remove();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/KBPage.test.ts`
Expected: FAIL — old `KBPage.svelte` still renders `＋ Folder`, has no `.add-child`/Trash link, and its delete flow has no cascade-count messaging.

- [ ] **Step 3: Rewrite KBPage.svelte**

Replace the full contents of `packages/editor/src/lib/components/KBPage.svelte`:

```svelte
<script lang="ts">
  import type { createKBStore, KBEntry } from "../kbStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import { apiUrl } from "../apiUrl";
  import MarkdownEditor from "./ui/MarkdownEditor.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import Card from "./ui/Card.svelte";
  import KBTree from "./ui/KBTree.svelte";
  import KBTrash from "./ui/KBTrash.svelte";
  import EmojiPicker from "./ui/EmojiPicker.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";

  type KBStore = ReturnType<typeof createKBStore>;
  interface Props {
    store: KBStore;
    selectedItemId?: string | null;
    onnavigate?: (id: string) => void;
  }
  let { store, selectedItemId = null, onnavigate }: Props = $props();

  let selectedId = $state<string | null>(null);
  let contentMode = $state<"page" | "trash">("page");
  let contentTab = $state<"content" | "media">("content");
  let editing = $state(false);
  let draftTitle = $state("");
  let draftContent = $state("");
  let draftIcon = $state("📄");
  let confirmDelete = $state<{ count: number } | null>(null);
  let pendingDeleteId = $state<string | null>(null);
  let saving = $state(false);
  let error = $state<string | null>(null);
  let searchQuery = $state("");
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);
  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);
  let collapsedIds = $state<Set<string>>(new Set());
  let renamingId = $state<string | null>(null);
  let dragging = $state<string | null>(null);

  const selectedEntry = $derived(
    selectedId ? (store.entries.find((e) => e.id === selectedId) ?? null) : null,
  );

  const mediaItems = $derived<MediaItem[]>(
    (selectedEntry?.attachments ?? []).map(fname => {
      const url = apiUrl(`/api/kb/${selectedId}/attachments/${fname}`);
      const isPdf = fname.toLowerCase().endsWith(".pdf");
      return { id: fname, name: fname, url, thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url, type: isPdf ? "document" : "image" };
    })
  );

  function selectEntry(entry: KBEntry): void {
    selectedId = entry.id;
    draftTitle = entry.title;
    draftContent = entry.content;
    draftIcon = entry.icon;
    editing = false;
    confirmDelete = null;
    pendingDeleteId = null;
    contentTab = "content";
    contentMode = "page";
    error = null;
  }

  function handleTreeSelect(entry: KBEntry): void {
    selectEntry(entry);
    onnavigate?.(entry.id);
  }

  $effect(() => {
    if (selectedItemId && selectedItemId !== selectedId) {
      const found = store.entries.find((e) => e.id === selectedItemId);
      if (found) selectEntry(found);
    }
  });

  function resolveKbLink(id: string): { title: string; icon: string } | null {
    const found = store.entries.find((e) => e.id === id);
    return found ? { title: found.title, icon: found.icon } : null;
  }

  async function handleNewPage(): Promise<void> {
    try {
      const entry = await store.createEntry({ title: "New page", content: "" });
      selectEntry(entry);
      editing = true;
      onnavigate?.(entry.id);
    } catch (e) {
      error = e instanceof Error ? e.message : "Create failed";
    }
  }

  async function handleCreateChild(parentId: string): Promise<void> {
    try {
      const parent = store.entries.find((e) => e.id === parentId);
      const entry = await store.createEntry({ title: "New page", content: "", parentId });
      if (parent) {
        const link = `[${entry.title}](#/kb/${entry.id})`;
        await store.updateEntry(parentId, { content: `${parent.content}\n\n${link}\n` });
      }
      const next = new Set(collapsedIds);
      next.delete(parentId);
      collapsedIds = next;
      selectEntry(entry);
      editing = true;
      onnavigate?.(entry.id);
    } catch (e) {
      error = e instanceof Error ? e.message : "Create failed";
    }
  }

  async function handleSlashPage(): Promise<{ id: string; title: string } | null> {
    if (!selectedId) return null;
    try {
      const entry = await store.createEntry({ title: "New page", content: "", parentId: selectedId });
      const next = new Set(collapsedIds);
      next.delete(selectedId);
      collapsedIds = next;
      return { id: entry.id, title: entry.title };
    } catch (e) {
      error = e instanceof Error ? e.message : "Create failed";
      return null;
    }
  }

  async function handleSave(): Promise<void> {
    if (!selectedId) return;
    if (!draftTitle.trim()) { error = "Title cannot be empty"; return; }
    saving = true;
    error = null;
    try {
      await store.updateEntry(selectedId, {
        title: draftTitle.trim(),
        content: draftContent,
      });
      editing = false;
    } catch (e) {
      error = e instanceof Error ? e.message : "Save failed";
    } finally {
      saving = false;
    }
  }

  function handleCancel(): void {
    if (selectedEntry) {
      draftTitle = selectedEntry.title;
      draftContent = selectedEntry.content;
    }
    editing = false;
    error = null;
  }

  async function handleIconChange(icon: string): Promise<void> {
    if (!selectedId) return;
    try {
      await store.updateEntry(selectedId, { icon });
    } catch (e) {
      error = e instanceof Error ? e.message : "Icon update failed";
    }
  }

  function childCount(id: string): number {
    let count = 0;
    const stack = [id];
    while (stack.length) {
      const current = stack.pop()!;
      for (const e of store.entries) {
        if (e.parentId === current) { count += 1; stack.push(e.id); }
      }
    }
    return count;
  }

  function handleAskDelete(id: string): void {
    pendingDeleteId = id;
    confirmDelete = { count: childCount(id) + 1 };
  }

  async function handleConfirmDelete(): Promise<void> {
    const id = pendingDeleteId;
    if (!id) return;
    try {
      await store.deleteEntry(id);
      if (selectedId && !store.entries.some((e) => e.id === selectedId)) {
        selectedId = null;
        editing = false;
      }
    } catch (e) {
      error = e instanceof Error ? e.message : "Delete failed";
    } finally {
      confirmDelete = null;
      pendingDeleteId = null;
    }
  }

  async function handleUpload(files: File[]): Promise<void> {
    if (!selectedId) return;
    uploading = true; uploadError = null;
    try { for (const file of files) await store.uploadAttachment(selectedId, file); }
    catch (err) { uploadError = err instanceof Error ? err.message : "Upload failed"; }
    finally { uploading = false; }
  }

  async function handleDeleteAttachment(id: string): Promise<void> {
    if (!selectedId) return;
    try { await store.deleteAttachment(selectedId, id); }
    catch (err) { uploadError = err instanceof Error ? err.message : "Delete failed"; }
  }

  function handleItemClick(index: number): void { lightboxIndex = index; lightboxOpen = true; }

  function toggleTree(id: string): void {
    const next = new Set(collapsedIds);
    if (next.has(id)) next.delete(id); else next.add(id);
    collapsedIds = next;
  }

  async function handleRenamePage(id: string, title: string): Promise<void> {
    try {
      await store.updateEntry(id, { title });
      if (id === selectedId) draftTitle = title;
    } catch (e) {
      error = e instanceof Error ? e.message : "Rename failed";
    } finally {
      renamingId = null;
    }
  }

  function handleCancelRename(): void {
    renamingId = null;
  }

  function handleStartDrag(id: string): void {
    dragging = id;
  }

  function handleEndDrag(): void {
    dragging = null;
  }

  async function handleTreeDrop(
    draggedId: string, targetParentId: string | null, orderedIds: string[] | null,
  ): Promise<void> {
    try {
      const dragged = store.entries.find((e) => e.id === draggedId);
      if (dragged && dragged.parentId !== targetParentId) {
        await store.updateEntry(draggedId, { parentId: targetParentId });
      }
      if (orderedIds) {
        await store.reorderSiblings(targetParentId, orderedIds);
      }
    } catch (e) {
      error = e instanceof Error ? e.message : "Move failed";
    }
  }

  async function openTrash(): Promise<void> {
    contentMode = "trash";
    selectedId = null;
    try { await store.loadTrash(); }
    catch (e) { error = e instanceof Error ? e.message : "Failed to load trash"; }
  }

  async function handleRestore(id: string): Promise<void> {
    try { await store.restoreEntry(id); }
    catch (e) { error = e instanceof Error ? e.message : "Restore failed"; }
  }

  async function handlePermanentDelete(id: string): Promise<void> {
    try { await store.permanentlyDeleteEntry(id); }
    catch (e) { error = e instanceof Error ? e.message : "Delete failed"; }
  }

  async function handleEmptyTrash(): Promise<void> {
    try { await store.emptyTrash(); }
    catch (e) { error = e instanceof Error ? e.message : "Empty trash failed"; }
  }
</script>

<div class="page">
<Card style="display:flex; padding:0; overflow:hidden; flex:1; min-height:0; font-family: var(--font-sans);">
  <div class="kb-sidebar">
    <div class="sidebar-toolbar">
      <Input placeholder="🔍 Search…" bind:value={searchQuery} />
      <Button onclick={handleNewPage}>＋ New Page</Button>
    </div>
    <div class="entry-list">
      <KBTree
        entries={store.entries}
        {selectedId}
        {searchQuery}
        {collapsedIds}
        {renamingId}
        {dragging}
        onselect={handleTreeSelect}
        ontoggle={toggleTree}
        oncreatechild={handleCreateChild}
        onstartrename={(id) => { renamingId = id; }}
        oncommitrename={handleRenamePage}
        oncancelrename={handleCancelRename}
        ondelete={handleAskDelete}
        onstartdrag={handleStartDrag}
        onenddrag={handleEndDrag}
        ondrop={handleTreeDrop}
      />
    </div>
    <button class="trash-link" onclick={openTrash}>
      🗑 Trash{store.trash.length > 0 ? ` (${store.trash.length})` : ""}
    </button>
  </div>

  <div class="kb-content">
    {#if contentMode === "trash"}
      <KBTrash
        entries={store.trash}
        onrestore={handleRestore}
        ondeleteforever={handlePermanentDelete}
        onemptytrash={handleEmptyTrash}
      />
    {:else if !selectedEntry}
      <div class="content-empty">Select a page or create one</div>
    {:else}
      <div class="content-header">
        <div class="content-header-left">
          <div class="title-row">
            <EmojiPicker bind:value={draftIcon} onchange={handleIconChange} />
            {#if editing}
              <input class="title-input" bind:value={draftTitle} placeholder="Page title" />
            {:else}
              <h1 class="content-title">{selectedEntry.title}</h1>
            {/if}
          </div>
          <div class="content-tab-bar">
            <button class="content-tab" class:active={contentTab === "content"}
              onclick={() => { contentTab = "content"; }}>Content</button>
            <button class="content-tab" class:active={contentTab === "media"}
              onclick={() => { contentTab = "media"; editing = false; }}>
              Media{(selectedEntry.attachments?.length ?? 0) > 0 ? ` (${selectedEntry.attachments.length})` : ""}
            </button>
          </div>
        </div>
        <div class="header-actions">
          {#if contentTab === "content" && !editing}
            <Button variant="secondary" onclick={() => { editing = true; }}>Edit</Button>
          {/if}
          {#if confirmDelete && pendingDeleteId === selectedEntry.id}
            <span class="confirm-text">
              Delete{confirmDelete.count > 1 ? ` this and ${confirmDelete.count - 1} sub-page${confirmDelete.count > 2 ? "s" : ""}` : ""}?
            </span>
            <Button variant="danger" onclick={handleConfirmDelete}>✓</Button>
            <Button variant="ghost" onclick={() => { confirmDelete = null; pendingDeleteId = null; }}>✕</Button>
          {:else}
            <Button variant="ghost" onclick={() => handleAskDelete(selectedEntry.id)} title="Delete page">🗑</Button>
          {/if}
        </div>
      </div>

      <div class="content-body">
        {#if contentTab === "content"}
          <MarkdownEditor
            bind:value={draftContent}
            bind:editing
            mediaItems={contentTab === "content" ? mediaItems : []}
            clickToEdit={false}
            placeholder="Start writing in Markdown… (type /page to create a linked child page)"
            {resolveKbLink}
            onSlashPage={handleSlashPage}
          />
        {:else}
          <MediaGallery
            items={mediaItems}
            {uploading}
            {uploadError}
            onUpload={handleUpload}
            onDelete={handleDeleteAttachment}
            onItemClick={handleItemClick}
          />
        {/if}
      </div>

      {#if error}
        <div class="content-error">{error}</div>
      {/if}

      {#if editing && contentTab === "content"}
        <div class="content-footer">
          <Button variant="primary" disabled={saving} onclick={handleSave}>
            {saving ? "Saving…" : "Save"}
          </Button>
          <Button variant="secondary" onclick={handleCancel}>Cancel</Button>
        </div>
      {/if}
    {/if}
  </div>
</Card>
</div>

{#if lightboxOpen && mediaItems.length > 0}
  <Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />
{/if}

<style>
  .page {
    display: flex; height: 100%; box-sizing: border-box;
    padding: var(--space-4); background: var(--bg);
  }

  .kb-sidebar {
    width: 260px; flex-shrink: 0;
    display: flex; flex-direction: column;
    border-right: 1px solid var(--border);
  }
  .sidebar-toolbar {
    display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3);
    background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .sidebar-toolbar :global(.ui-input) { flex: 1; }

  .entry-list {
    flex: 1; overflow-y: auto; padding: var(--space-2);
    display: flex; flex-direction: column; gap: 2px;
  }

  .trash-link {
    flex-shrink: 0; text-align: left; padding: 8px 12px;
    background: none; border: none; border-top: 1px solid var(--border);
    color: var(--text-muted); font-size: 12px; cursor: pointer; font-family: var(--font-sans);
  }
  .trash-link:hover { background: var(--surface-hover); color: var(--text); }

  .kb-content { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
  .content-empty {
    flex: 1; display: flex; align-items: center; justify-content: center;
    color: var(--text-faint); font-size: 13px;
  }

  .content-header {
    display: flex; align-items: flex-start; gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .content-header-left { flex: 1; min-width: 0; }
  .title-row { display: flex; align-items: center; gap: var(--space-2); margin-bottom: 6px; }
  .content-title { font-size: 18px; font-weight: 600; color: var(--text); margin: 0; }
  .title-input {
    flex: 1; min-width: 0; background: var(--surface-alt); border: 1px solid var(--accent);
    border-radius: var(--radius-md); color: var(--text); box-sizing: border-box;
    font-size: 16px; font-weight: 600; padding: 6px 10px; font-family: var(--font-sans);
  }
  .title-input:focus { outline: none; }
  .content-tab-bar { display: flex; }
  .content-tab {
    padding: 4px 12px; background: none; border: none; border-bottom: 2px solid transparent;
    color: var(--text-muted); font-size: 11px; cursor: pointer; font-family: var(--font-sans);
  }
  .content-tab:hover { color: var(--text); }
  .content-tab.active { border-bottom-color: var(--accent); color: var(--text); }
  .header-actions { display: flex; align-items: center; gap: var(--space-1); flex-shrink: 0; }
  .confirm-text { font-size: 11px; color: var(--danger); }

  .content-body {
    flex: 1; overflow: hidden; padding: var(--space-4);
    display: flex; flex-direction: column;
  }
  .content-body :global(.md-preview),
  .content-body :global(.md-editor) { flex: 1; }

  .content-error { padding: 0 var(--space-4); font-size: 11px; color: var(--danger); }
  .content-footer {
    display: flex; gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
    border-top: 1px solid var(--border); flex-shrink: 0;
  }
</style>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/KBPage.test.ts`
Expected: PASS (all tests).

- [ ] **Step 5: Run the full frontend suite**

Run: `cd packages/editor && npx vitest run`
Expected: PASS for every KB-related file (`kbStore.test.ts`, `KBTree.test.ts`, `KBTrash.test.ts`, `MarkdownEditor.test.ts`, `KBPage.test.ts`). `App.test.ts` or any test asserting on `#/kb` routing/search behavior may still fail here — that's expected and fixed in Task 9.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/KBPage.svelte packages/editor/test/KBPage.test.ts
git commit -m "feat(kb): wire unified page tree, icons, trash, and live links into KBPage"
```

---

## Task 9: App.svelte routing + searchIndex.ts

Depends on Task 8 (`KBPage`'s new `onnavigate` prop and `selectedItemId` semantics) and Task 4 (`KBEntry.icon`).

**Files:**
- Modify: `packages/editor/src/App.svelte`
- Modify: `packages/editor/src/lib/searchIndex.ts`

**Interfaces:**
- Consumes: `KBPage`'s `{ store, selectedItemId, onnavigate }` props (Task 8), `KBEntry.icon` (Task 4).
- Produces: `#/kb/<id>` is now a real route; global search and notification navigation for KB entries route through it.

No test file exists for `App.svelte`'s routing or for `searchIndex.ts`'s KB icon field (confirmed by grep — neither `selectedKBEntryId` nor `#/kb` appear in any file under `packages/editor/test/`), so this task is verified by keeping the full frontend suite green plus the manual browser check in Step 4.

- [ ] **Step 1: Update searchIndex.ts**

In `packages/editor/src/lib/searchIndex.ts`, change line 130 from:

```typescript
      icon: "📄",
```

to:

```typescript
      icon: entry.icon,
```

(This is the only change in this file — `KBEntry` already gained the `icon` field in Task 4, so `entry.icon` is valid; `buildSearchIndex` no longer needs a hardcoded fallback since every entry now always has a real icon value from `kbStore`.)

- [ ] **Step 2: Update App.svelte routing**

In `packages/editor/src/App.svelte`, remove the `selectedKBEntryId` state declaration at line 122:

```typescript
  let selectedKBEntryId = $state<string | null>(null);
```

At line 135, change the KB branch of `handleSearchSelect` from:

```typescript
    else if (result.module === "kb") { selectedKBEntryId = result.id; window.location.hash = "#/kb"; }
```

to:

```typescript
    else if (result.module === "kb") { window.location.hash = "#/kb/" + encodeURIComponent(result.id); }
```

After the existing `const isHome = $derived(currentRoute === "#/" || currentRoute === "");` line (currently line 334), add a new derived value for the KB route id:

```typescript
  const kbRouteId = $derived(
    currentRoute.startsWith("#/kb/") ? decodeURIComponent(currentRoute.slice("#/kb/".length)) : null,
  );
```

Replace the KB route branch (currently lines 1252-1253):

```svelte
      {:else if currentRoute === "#/kb"}
        <KBPage store={kbStore} selectedItemId={selectedKBEntryId} onclearselection={() => { selectedKBEntryId = null; }} />
```

with:

```svelte
      {:else if currentRoute === "#/kb" || currentRoute.startsWith("#/kb/")}
        <KBPage store={kbStore} selectedItemId={kbRouteId} onnavigate={(id) => { window.location.hash = "#/kb/" + encodeURIComponent(id); }} />
```

- [ ] **Step 3: Run the full frontend suite**

Run: `cd packages/editor && npx vitest run`
Expected: PASS, every test file green — this confirms Tasks 4-9 are fully consistent together and no other component referenced the now-removed `selectedKBEntryId` or `onclearselection` prop.

Then run: `cd packages/editor && npm run typecheck` (runs `svelte-check`)
Expected: PASS with no type errors, confirming `KBPage`'s prop signature change didn't break its one caller in `App.svelte`.

- [ ] **Step 4: Manual verification in the browser**

Start the dev stack per this repo's normal run instructions and in a browser:

1. Open the Knowledge Base page. Create a page, confirm it gets the default 📄 icon and appears in the tree.
2. Click the icon next to the title, pick a different emoji, confirm it updates in both the header and the tree row.
3. Hover a tree row, click "＋" to add a child page — confirm the new child appears nested under the parent with a disclosure triangle now showing on the parent, and that a `[New page](#/kb/...)` link was appended to the parent's content.
4. Open the parent page (not editing) and click the child-page link in the rendered content — confirm it navigates to the child and the URL becomes `#/kb/<child-id>`. Reload the browser at that URL — confirm it lands directly on the child page (deep link works).
5. Rename the child page, navigate back to the parent, confirm the link's displayed text updated to the new title without editing the parent's content.
6. Drag a page onto another page — confirm it nests. Drag a page between two siblings — confirm it reorders without changing its parent.
7. Delete a page that has children — confirm the confirmation message mentions the sub-page count, and after confirming, both parent and child disappear from the tree.
8. Click "Trash" at the bottom of the sidebar — confirm the deleted pages appear, click Restore on the parent — confirm both parent and child reappear in the tree.
9. Delete a page again, open Trash, click the 🗑 on that row, confirm, and confirm the page permanently disappears from Trash.
10. In the editor, type `/page` at the start of a line while editing a page's content — confirm it's replaced with a link to a newly created child page.
11. Use the global search (command palette) to find a KB page, select it — confirm it navigates via `#/kb/<id>` and opens correctly.

If any step fails, fix the relevant Task's code before proceeding — do not report this plan complete until all 11 steps behave as described.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/src/lib/searchIndex.ts
git commit -m "feat(kb): add #/kb/<id> deep links and wire KB search/notifications through them"
```

---

## Final verification

- [ ] Run the full backend suite: `cd packages/backend && python -m pytest -q` — expect all green.
- [ ] Run the full frontend suite: `cd packages/editor && npx vitest run` — expect all green.
- [ ] Confirm no leftover references to the old folder API: `grep -rn "kb_folders\|KBFolder\|folderId" packages/ --include="*.py" --include="*.ts" --include="*.svelte"` — expect no output (only historical mentions in `docs/superpowers/` are acceptable, if any).
- [ ] Re-read `docs/superpowers/specs/2026-07-16-kb-pages-as-folders-design.md` once more against the finished code and confirm every section (data model, API surface, tree UI, content linking, migration/scope) has a corresponding implemented piece.
