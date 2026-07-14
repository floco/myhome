# KB Folder Tree View + Card Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wrap the KB page in a `Card`, and replace its flat sidebar entry list with a hierarchical folder tree (create/rename/delete/drag-and-drop, folder-aware search) backed by a new SQLite `kb_folders` table and MCP tools.

**Architecture:** Folders are a new relational entity (`KBFolder`: id, name, parentId) stored in a new `kb_folders` SQLite table via a new `persistence_kb_folders.py` module with plain row-level CRUD functions (`create_folder`/`rename_folder`/`move_folder`/`delete_folder`/`get_folder`/`list_folders`/`would_create_cycle`), following the `create_home`/`patch_home`/`delete_home` style already used in `persistence_homes.py` (persistence layer owns id generation and mutation logic; routes are thin). KB entries keep living as markdown files (untouched by the SQLite migration); `KBEntry` just gains a `folderId` field persisted as one more frontmatter line, exactly like the existing `attachments` field. The frontend gets a new recursive `KBTree.svelte` component (using `<svelte:self>`) that renders folders+entries from flat arrays, with expand/collapse, drag-and-drop reparenting, a per-folder context menu, and search-driven auto-expand; `KBPage.svelte` wires it in and wraps the whole page in `Card`.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x Core, pytest (backend); Svelte 5 runes, TypeScript, Vitest (frontend).

## Global Constraints

- Backend tests: `cd packages/backend && python -m pytest tests/ -q` (or `-k <name>` for a single test).
- Frontend tests: `cd packages/editor && npx vitest run <file>` for a single file, or `npm run test --workspace=packages/editor` from repo root for the whole suite.
- `kb_folders` is a brand-new additive table — no entry in `migrations.py` is needed; `metadata.create_all()` (already called from `db.get_engine()`) creates it automatically, exactly like every other table already in `schema.py`.
- Folders are **not** part of the JSON-document/"clear-and-reinsert" pattern used by `persistence_consumables.py` etc. — they get individual row-level CRUD functions instead, mirroring `persistence_homes.py`'s `create_home`/`patch_home`/`delete_home` style. No `order_index` column: folders are always sorted by name (client and server), entries by `createdAt`, so there is no manual reordering to preserve.
- **Rename vs. move are always two separate functions/tools**, never one function with an optional `parent_id` that defaults to `None` — a single combined function couldn't distinguish "don't touch the parent" from "move to root" without a fragile sentinel. This applies at every layer: persistence (`rename_folder` / `move_folder`), MCP tools (`rename_kb_folder` / `move_kb_folder`, and a new `move_kb_entry` instead of overloading `update_kb_entry`). The one place this collapses back into a single call is the REST `PUT .../kb/folders/{id}` endpoint and the frontend's `store.updateFolder(id, patch)`, which use Pydantic's `model_fields_set` / a plain JS object's key presence to distinguish "key omitted" (don't touch) from "key present with value `null`" (move to root) — this works there because a real request body (JSON object / Pydantic model) can represent "key absent," unlike plain Python/TS keyword arguments.
- No activity-log entries for folder create/rename/delete/move — folders are a structural/organizational concept, like the existing category tables (`inventory_categories`, `cost_categories`, etc.), none of which log activity either.
- Folder deletion is always blocked (400/`ValueError`) when the folder has any direct entries or subfolders — never cascading, never silently reparenting children.
- Drag-and-drop in `KBTree.svelte` does not use `DragEvent.dataTransfer` to carry the dragged item's identity — that would require passing data between separate recursive component instances via the DOM, which is unreliable. Instead, `dragging: {kind, id} | null` state is lifted to `KBPage.svelte` and threaded down through every recursive `KBTree` instance as a prop, set by `onstartdrag` and read by whichever instance's row receives the `ondrop`. `dataTransfer.setData(...)` is still called (with an empty string) in `ondragstart` purely for cross-browser drag-initiation compatibility — never read back.
- Frontend drag-and-drop tests follow the existing pattern in `MediaGallery.test.ts` (`dispatchEvent(Object.assign(new Event("drop"), {...}))`) — but since this feature's `ondrop` handlers read component state/props rather than `e.dataTransfer`, tests can dispatch plain `new Event("dragstart")` / `new Event("drop")` with no faked `dataTransfer` at all.

---

### Task 1: `KBFolder` model, `kb_folders` schema table, and persistence layer

**Files:**
- Modify: `packages/backend/src/myhome/models_kb.py`
- Modify: `packages/backend/src/myhome/schema.py`
- Create: `packages/backend/src/myhome/persistence_kb_folders.py`
- Test: `packages/backend/tests/test_kb_folders.py`

**Interfaces:**
- Produces: `myhome.models_kb.KBFolder(id: str, name: str, parentId: str | None = None)`; `myhome.persistence_kb_folders.list_folders(home_id: str) -> list[KBFolder]`, `get_folder(home_id: str, folder_id: str) -> KBFolder | None`, `create_folder(home_id: str, name: str, parent_id: str | None = None) -> KBFolder`, `rename_folder(home_id: str, folder_id: str, name: str) -> KBFolder | None`, `move_folder(home_id: str, folder_id: str, parent_id: str | None) -> KBFolder | None`, `delete_folder(home_id: str, folder_id: str) -> bool`, `would_create_cycle(home_id: str, folder_id: str, new_parent_id: str) -> bool`.

- [ ] **Step 1: Add the `KBFolder` model**

Edit `packages/backend/src/myhome/models_kb.py`, insert a new class between `KBEntry` and `KBDocument`:

```python
class KBFolder(BaseModel):
    id: str
    name: str
    parentId: str | None = None
```

- [ ] **Step 2: Add the `kb_folders` table**

Edit `packages/backend/src/myhome/schema.py`, append at the end of the file:

```python

kb_folders = Table(
    "kb_folders", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("parent_id", String, ForeignKey("kb_folders.id")),
    Column("name", String, nullable=False),
)
```

- [ ] **Step 3: Write the failing tests**

Create `packages/backend/tests/test_kb_folders.py`:

```python
import pytest
from myhome.persistence_kb_folders import (
    create_folder, delete_folder, get_folder, list_folders, move_folder, rename_folder, would_create_cycle,
)


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_folder(home_id):
    folder = create_folder(home_id, "Appliances")
    folders = list_folders(home_id)
    assert len(folders) == 1
    assert folders[0].id == folder.id
    assert folders[0].name == "Appliances"
    assert folders[0].parentId is None


def test_create_subfolder(home_id):
    parent = create_folder(home_id, "Parent")
    child = create_folder(home_id, "Child", parent_id=parent.id)
    assert child.parentId == parent.id


def test_list_folders_sorted_by_name(home_id):
    create_folder(home_id, "Zebra")
    create_folder(home_id, "Apple")
    folders = list_folders(home_id)
    assert [f.name for f in folders] == ["Apple", "Zebra"]


def test_get_folder_missing_returns_none(home_id):
    assert get_folder(home_id, "nonexistent") is None


def test_rename_folder(home_id):
    folder = create_folder(home_id, "Old")
    renamed = rename_folder(home_id, folder.id, "New")
    assert renamed.name == "New"
    assert get_folder(home_id, folder.id).name == "New"


def test_rename_folder_missing_returns_none(home_id):
    assert rename_folder(home_id, "nonexistent", "New") is None


def test_move_folder(home_id):
    parent = create_folder(home_id, "Parent")
    child = create_folder(home_id, "Child")
    moved = move_folder(home_id, child.id, parent.id)
    assert moved.parentId == parent.id
    assert get_folder(home_id, child.id).parentId == parent.id


def test_move_folder_to_root(home_id):
    parent = create_folder(home_id, "Parent")
    child = create_folder(home_id, "Child", parent_id=parent.id)
    moved = move_folder(home_id, child.id, None)
    assert moved.parentId is None


def test_move_folder_missing_returns_none(home_id):
    assert move_folder(home_id, "nonexistent", None) is None


def test_delete_folder(home_id):
    folder = create_folder(home_id, "Temp")
    assert delete_folder(home_id, folder.id) is True
    assert list_folders(home_id) == []


def test_delete_folder_missing_returns_false(home_id):
    assert delete_folder(home_id, "nonexistent") is False


def test_would_create_cycle_self(home_id):
    folder = create_folder(home_id, "A")
    assert would_create_cycle(home_id, folder.id, folder.id) is True


def test_would_create_cycle_descendant(home_id):
    a = create_folder(home_id, "A")
    b = create_folder(home_id, "B", parent_id=a.id)
    c = create_folder(home_id, "C", parent_id=b.id)
    assert would_create_cycle(home_id, a.id, c.id) is True


def test_would_create_cycle_unrelated_is_false(home_id):
    a = create_folder(home_id, "A")
    b = create_folder(home_id, "B")
    assert would_create_cycle(home_id, a.id, b.id) is False
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_kb_folders.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'myhome.persistence_kb_folders'`

- [ ] **Step 5: Implement the persistence module**

Create `packages/backend/src/myhome/persistence_kb_folders.py`:

```python
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
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_kb_folders.py -q`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add packages/backend/src/myhome/models_kb.py packages/backend/src/myhome/schema.py \
  packages/backend/src/myhome/persistence_kb_folders.py packages/backend/tests/test_kb_folders.py
git commit -m "feat: add KBFolder model and SQLite-backed persistence layer"
```

---

### Task 2: `folderId` on `KBEntry` (markdown frontmatter round-trip)

**Files:**
- Modify: `packages/backend/src/myhome/models_kb.py`
- Modify: `packages/backend/src/myhome/persistence_kb.py`
- Test: `packages/backend/tests/test_kb.py`

**Interfaces:**
- Consumes: none beyond existing `KBEntry`.
- Produces: `KBEntry.folderId: str | None = None` (also added to `KBCreate`/`KBUpdate`), round-tripped through `save_entry`/`load_entry`/`load_all`.

- [ ] **Step 1: Write the failing tests**

Edit `packages/backend/tests/test_kb.py`, append at the end of the file:

```python


def test_entry_folder_id_round_trips_through_frontmatter(home_id):
    entry = make_entry()
    entry.folderId = "f1"
    save_entry(home_id, entry)
    from myhome.persistence_kb import load_entry
    loaded = load_entry(home_id, "e1")
    assert loaded.folderId == "f1"


def test_entry_without_folder_id_defaults_to_none(home_id):
    save_entry(home_id, make_entry())
    from myhome.persistence_kb import load_entry
    loaded = load_entry(home_id, "e1")
    assert loaded.folderId is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_kb.py -k folder_id -q`
Expected: FAIL with `AttributeError: 'KBEntry' object has no attribute 'folderId'` (via pydantic's extra-field rejection, or the attribute simply not existing yet)

- [ ] **Step 3: Add `folderId` to the models**

Edit `packages/backend/src/myhome/models_kb.py`, update `KBEntry`, `KBCreate`, and `KBUpdate`:

```python
class KBEntry(BaseModel):
    id: str
    title: str
    content: str = ""
    createdAt: str
    updatedAt: str
    attachments: list[str] = []
    folderId: str | None = None
```

```python
class KBCreate(BaseModel):
    title: str
    content: str = ""
    folderId: str | None = None


class KBUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    folderId: str | None = None
```

- [ ] **Step 4: Round-trip `folderId` through the markdown frontmatter**

Edit `packages/backend/src/myhome/persistence_kb.py`, in `_build_file`, add the `folderId` line after the `attachments` line:

```python
    if entry.attachments:
        lines.append(f"attachments: {','.join(entry.attachments)}")
    if entry.folderId:
        lines.append(f"folderId: {entry.folderId}")
    lines += ["---", "", entry.content]
```

In `_read_entry_file`, add `folderId` to the constructed `KBEntry`:

```python
    return KBEntry(
        id=meta["id"],
        title=meta["title"],
        content=body.lstrip("\n"),
        createdAt=meta.get("createdAt", ""),
        updatedAt=meta.get("updatedAt", ""),
        attachments=attachments,
        folderId=meta.get("folderId") or None,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_kb.py -q`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/models_kb.py packages/backend/src/myhome/persistence_kb.py \
  packages/backend/tests/test_kb.py
git commit -m "feat: add folderId to KBEntry, round-tripped through markdown frontmatter"
```

---

### Task 3: REST routes — folder CRUD + `folderId` on entry endpoints

**Files:**
- Modify: `packages/backend/src/myhome/models_kb.py`
- Modify: `packages/backend/src/myhome/routes/kb.py`
- Test: `packages/backend/tests/test_kb.py`

**Interfaces:**
- Consumes: `myhome.persistence_kb_folders.{list_folders, get_folder, create_folder, rename_folder, move_folder, delete_folder, would_create_cycle}` (Task 1); `KBEntry.folderId` (Task 2).
- Produces: `GET /api/homes/{home_id}/kb` now returns `{version, entries, folders}`; `POST /api/homes/{home_id}/kb/folders`; `PUT /api/homes/{home_id}/kb/folders/{id}`; `DELETE /api/homes/{home_id}/kb/folders/{id}`; entry create/update accept `folderId`.

- [ ] **Step 1: Add `KBFolderCreate`/`KBFolderUpdate` and extend `KBDocument`**

Edit `packages/backend/src/myhome/models_kb.py`:

```python
class KBDocument(BaseModel):
    version: int = 1
    entries: list[KBEntry] = []
    folders: list[KBFolder] = []
```

Append at the end of the file:

```python


class KBFolderCreate(BaseModel):
    name: str
    parentId: str | None = None


class KBFolderUpdate(BaseModel):
    name: str | None = None
    parentId: str | None = None
```

- [ ] **Step 2: Write the failing tests**

Edit `packages/backend/tests/test_kb.py`, append at the end of the file:

```python


def test_get_kb_includes_empty_folders_by_default(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/kb")
    assert resp.json()["folders"] == []


def test_create_kb_folder(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/kb/folders", json={"name": "Appliances"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Appliances"
    assert data["parentId"] is None
    folders = client.get(f"/api/homes/{home_id}/kb").json()["folders"]
    assert folders[0]["name"] == "Appliances"


def test_create_kb_subfolder(client, home_id):
    parent = client.post(f"/api/homes/{home_id}/kb/folders", json={"name": "Parent"}).json()
    resp = client.post(f"/api/homes/{home_id}/kb/folders", json={"name": "Child", "parentId": parent["id"]})
    assert resp.status_code == 201
    assert resp.json()["parentId"] == parent["id"]


def test_create_kb_folder_unknown_parent_404(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/kb/folders", json={"name": "X", "parentId": "nonexistent"})
    assert resp.status_code == 404


def test_rename_kb_folder(client, home_id):
    folder = client.post(f"/api/homes/{home_id}/kb/folders", json={"name": "Old"}).json()
    resp = client.put(f"/api/homes/{home_id}/kb/folders/{folder['id']}", json={"name": "New"})
    assert resp.status_code == 204
    folders = client.get(f"/api/homes/{home_id}/kb").json()["folders"]
    assert folders[0]["name"] == "New"


def test_update_kb_folder_not_found(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/kb/folders/nonexistent", json={"name": "New"})
    assert resp.status_code == 404


def test_move_kb_folder_to_root(client, home_id):
    parent = client.post(f"/api/homes/{home_id}/kb/folders", json={"name": "Parent"}).json()
    child = client.post(f"/api/homes/{home_id}/kb/folders", json={"name": "Child", "parentId": parent["id"]}).json()
    resp = client.put(f"/api/homes/{home_id}/kb/folders/{child['id']}", json={"parentId": None})
    assert resp.status_code == 204
    folders = client.get(f"/api/homes/{home_id}/kb").json()["folders"]
    moved = next(f for f in folders if f["id"] == child["id"])
    assert moved["parentId"] is None


def test_move_kb_folder_into_own_descendant_rejected(client, home_id):
    a = client.post(f"/api/homes/{home_id}/kb/folders", json={"name": "A"}).json()
    b = client.post(f"/api/homes/{home_id}/kb/folders", json={"name": "B", "parentId": a["id"]}).json()
    resp = client.put(f"/api/homes/{home_id}/kb/folders/{a['id']}", json={"parentId": b["id"]})
    assert resp.status_code == 400


def test_delete_kb_folder(client, home_id):
    folder = client.post(f"/api/homes/{home_id}/kb/folders", json={"name": "Temp"}).json()
    resp = client.delete(f"/api/homes/{home_id}/kb/folders/{folder['id']}")
    assert resp.status_code == 204
    assert client.get(f"/api/homes/{home_id}/kb").json()["folders"] == []


def test_delete_kb_folder_not_found(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/kb/folders/nonexistent")
    assert resp.status_code == 404


def test_delete_kb_folder_with_entries_blocked(client, home_id):
    folder = client.post(f"/api/homes/{home_id}/kb/folders", json={"name": "Has entries"}).json()
    client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": "", "folderId": folder["id"]})
    resp = client.delete(f"/api/homes/{home_id}/kb/folders/{folder['id']}")
    assert resp.status_code == 400


def test_delete_kb_folder_with_subfolder_blocked(client, home_id):
    parent = client.post(f"/api/homes/{home_id}/kb/folders", json={"name": "Parent"}).json()
    client.post(f"/api/homes/{home_id}/kb/folders", json={"name": "Child", "parentId": parent["id"]})
    resp = client.delete(f"/api/homes/{home_id}/kb/folders/{parent['id']}")
    assert resp.status_code == 400


def test_create_entry_with_folder_id(client, home_id):
    folder = client.post(f"/api/homes/{home_id}/kb/folders", json={"name": "Manuals"}).json()
    resp = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": "", "folderId": folder["id"]})
    assert resp.status_code == 201
    assert resp.json()["folderId"] == folder["id"]


def test_create_entry_unknown_folder_id_404(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": "", "folderId": "nonexistent"})
    assert resp.status_code == 404


def test_move_entry_to_folder(client, home_id):
    folder = client.post(f"/api/homes/{home_id}/kb/folders", json={"name": "Manuals"}).json()
    entry_id = _entry_id(client, home_id)
    resp = client.put(f"/api/homes/{home_id}/kb/{entry_id}", json={"folderId": folder["id"]})
    assert resp.status_code == 204
    entries = client.get(f"/api/homes/{home_id}/kb").json()["entries"]
    assert next(e for e in entries if e["id"] == entry_id)["folderId"] == folder["id"]


def test_move_entry_back_to_root(client, home_id):
    folder = client.post(f"/api/homes/{home_id}/kb/folders", json={"name": "Manuals"}).json()
    entry_id = _entry_id(client, home_id)
    client.put(f"/api/homes/{home_id}/kb/{entry_id}", json={"folderId": folder["id"]})
    resp = client.put(f"/api/homes/{home_id}/kb/{entry_id}", json={"folderId": None})
    assert resp.status_code == 204
    entries = client.get(f"/api/homes/{home_id}/kb").json()["entries"]
    assert next(e for e in entries if e["id"] == entry_id)["folderId"] is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_kb.py -k "folder" -q`
Expected: FAIL — `folders` key missing from `GET /kb` response, `/kb/folders` routes 404 (not registered)

- [ ] **Step 4: Implement the routes**

Edit `packages/backend/src/myhome/routes/kb.py`. Update the imports:

```python
from ..models_kb import KBCreate, KBDocument, KBEntry, KBFolder, KBFolderCreate, KBFolderUpdate, KBUpdate
from ..persistence_activity import log_activity
from ..persistence_kb import (
    get_attachment_path,
    delete_attachment,
    delete_entry,
    generate_pdf_thumbnail,
    load_all,
    load_entry,
    save_attachment,
    save_entry,
)
from ..persistence_kb_folders import (
    create_folder,
    delete_folder,
    get_folder,
    list_folders,
    move_folder,
    rename_folder,
    would_create_cycle,
)
```

Replace `get_kb`:

```python
@router.get("/api/homes/{home_id}/kb", response_model=KBDocument)
def get_kb(home_id: str) -> KBDocument:
    return KBDocument(entries=load_all(home_id), folders=list_folders(home_id))
```

Replace `create_entry` to validate and store `folderId`:

```python
@router.post("/api/homes/{home_id}/kb", response_model=KBEntry, status_code=201)
def create_entry(
    home_id: str, body: KBCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> KBEntry:
    if body.folderId is not None and get_folder(home_id, body.folderId) is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    now = _now()
    entry = KBEntry(
        id=str(uuid.uuid4()),
        title=body.title,
        content=body.content,
        folderId=body.folderId,
        createdAt=now,
        updatedAt=now,
    )
    save_entry(home_id, entry)
    log_activity(home_id, current_user_id, "kb", "create", entry.title, entry.id)
    return entry
```

Replace `update_entry` to accept `folderId` (distinguishing "omitted" from "explicit null" via `model_fields_set`):

```python
@router.put("/api/homes/{home_id}/kb/{id}", status_code=204)
def update_entry(
    home_id: str, id: str, body: KBUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    entry = load_entry(home_id, id)
    if not entry:
        raise HTTPException(status_code=404)
    if body.title is not None:
        entry.title = body.title
    if body.content is not None:
        entry.content = body.content
    if "folderId" in body.model_fields_set:
        if body.folderId is not None and get_folder(home_id, body.folderId) is None:
            raise HTTPException(status_code=404, detail="Folder not found")
        entry.folderId = body.folderId
    entry.updatedAt = _now()
    save_entry(home_id, entry)
    log_activity(home_id, current_user_id, "kb", "update", entry.title, id)
```

Add three new routes (place them after the entry routes, before the attachment routes):

```python
@router.post("/api/homes/{home_id}/kb/folders", response_model=KBFolder, status_code=201)
def create_kb_folder(home_id: str, body: KBFolderCreate) -> KBFolder:
    if body.parentId is not None and get_folder(home_id, body.parentId) is None:
        raise HTTPException(status_code=404, detail="Parent folder not found")
    return create_folder(home_id, body.name, body.parentId)


@router.put("/api/homes/{home_id}/kb/folders/{id}", status_code=204)
def update_kb_folder(home_id: str, id: str, body: KBFolderUpdate) -> None:
    if get_folder(home_id, id) is None:
        raise HTTPException(status_code=404)
    fields = body.model_fields_set
    if "name" in fields and body.name is not None:
        rename_folder(home_id, id, body.name)
    if "parentId" in fields:
        if body.parentId is not None:
            if get_folder(home_id, body.parentId) is None:
                raise HTTPException(status_code=404, detail="Parent folder not found")
            if would_create_cycle(home_id, id, body.parentId):
                raise HTTPException(status_code=400, detail="Cannot move a folder into itself or a descendant")
        move_folder(home_id, id, body.parentId)


@router.delete("/api/homes/{home_id}/kb/folders/{id}", status_code=204)
def delete_kb_folder(home_id: str, id: str) -> None:
    if get_folder(home_id, id) is None:
        raise HTTPException(status_code=404)
    has_subfolders = any(f.parentId == id for f in list_folders(home_id))
    has_entries = any(e.folderId == id for e in load_all(home_id))
    if has_subfolders or has_entries:
        raise HTTPException(status_code=400, detail="Folder must be empty before it can be deleted")
    delete_folder(home_id, id)
```

Note: the existing route below already has a function named `delete_kb_entry`/`delete_kb_attachment` etc. — the new `delete_kb_folder` name does not collide with any existing function name in this file.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_kb.py -q`
Expected: All tests PASS

- [ ] **Step 6: Run the full backend suite**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: All tests PASS (no regressions in other modules)

- [ ] **Step 7: Commit**

```bash
git add packages/backend/src/myhome/models_kb.py packages/backend/src/myhome/routes/kb.py \
  packages/backend/tests/test_kb.py
git commit -m "feat: add KB folder REST endpoints and folderId support on entry routes"
```

---

### Task 4: MCP tools for KB folders + entry `move`/`folder_id`

**Files:**
- Modify: `packages/backend/src/myhome/mcp_tools_kb.py`
- Test: `packages/backend/tests/test_mcp_tools_kb.py`

**Interfaces:**
- Consumes: `myhome.persistence_kb_folders.*` (Task 1).
- Produces: MCP tools `list_kb_folders`, `create_kb_folder`, `rename_kb_folder`, `move_kb_folder`, `delete_kb_folder`, `move_kb_entry`; `create_kb_entry` gains `folder_id`.

- [ ] **Step 1: Write the failing tests**

Edit `packages/backend/tests/test_mcp_tools_kb.py`, append at the end of the file:

```python


def test_create_and_list_folder(home_id):
    from myhome.mcp_tools_kb import _create_kb_folder_impl, _list_kb_folders_impl
    folder = _create_kb_folder_impl(home_id, "Appliances")
    doc = _list_kb_folders_impl(home_id)
    assert doc["folders"][0]["id"] == folder["id"]
    assert doc["folders"][0]["name"] == "Appliances"


def test_create_subfolder(home_id):
    from myhome.mcp_tools_kb import _create_kb_folder_impl
    parent = _create_kb_folder_impl(home_id, "Parent")
    child = _create_kb_folder_impl(home_id, "Child", parent_id=parent["id"])
    assert child["parentId"] == parent["id"]


def test_create_folder_unknown_parent_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_folder_impl
    with pytest.raises(ValueError):
        _create_kb_folder_impl(home_id, "X", parent_id="nonexistent")


def test_rename_folder(home_id):
    from myhome.mcp_tools_kb import _create_kb_folder_impl, _rename_kb_folder_impl
    folder = _create_kb_folder_impl(home_id, "Old")
    renamed = _rename_kb_folder_impl(home_id, folder["id"], "New")
    assert renamed["name"] == "New"


def test_rename_folder_unknown_id_raises(home_id):
    from myhome.mcp_tools_kb import _rename_kb_folder_impl
    with pytest.raises(ValueError):
        _rename_kb_folder_impl(home_id, "nonexistent", "New")


def test_move_folder_to_root(home_id):
    from myhome.mcp_tools_kb import _create_kb_folder_impl, _move_kb_folder_impl
    parent = _create_kb_folder_impl(home_id, "Parent")
    child = _create_kb_folder_impl(home_id, "Child", parent_id=parent["id"])
    moved = _move_kb_folder_impl(home_id, child["id"])
    assert moved["parentId"] is None


def test_move_folder_unknown_parent_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_folder_impl, _move_kb_folder_impl
    folder = _create_kb_folder_impl(home_id, "A")
    with pytest.raises(ValueError):
        _move_kb_folder_impl(home_id, folder["id"], parent_id="nonexistent")


def test_move_folder_into_own_descendant_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_folder_impl, _move_kb_folder_impl
    a = _create_kb_folder_impl(home_id, "A")
    b = _create_kb_folder_impl(home_id, "B", parent_id=a["id"])
    with pytest.raises(ValueError):
        _move_kb_folder_impl(home_id, a["id"], parent_id=b["id"])


def test_delete_folder(home_id):
    from myhome.mcp_tools_kb import _create_kb_folder_impl, _delete_kb_folder_impl, _list_kb_folders_impl
    folder = _create_kb_folder_impl(home_id, "Temp")
    _delete_kb_folder_impl(home_id, folder["id"])
    assert _list_kb_folders_impl(home_id)["folders"] == []


def test_delete_folder_with_entries_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _create_kb_folder_impl, _delete_kb_folder_impl
    folder = _create_kb_folder_impl(home_id, "Has entries")
    _create_kb_entry_impl(home_id, "X", folder_id=folder["id"])
    with pytest.raises(ValueError):
        _delete_kb_folder_impl(home_id, folder["id"])


def test_delete_folder_with_subfolder_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_folder_impl, _delete_kb_folder_impl
    parent = _create_kb_folder_impl(home_id, "Parent")
    _create_kb_folder_impl(home_id, "Child", parent_id=parent["id"])
    with pytest.raises(ValueError):
        _delete_kb_folder_impl(home_id, parent["id"])


def test_create_entry_with_folder_id(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _create_kb_folder_impl
    folder = _create_kb_folder_impl(home_id, "Manuals")
    entry = _create_kb_entry_impl(home_id, "X", folder_id=folder["id"])
    assert entry["folderId"] == folder["id"]


def test_create_entry_unknown_folder_id_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl
    with pytest.raises(ValueError):
        _create_kb_entry_impl(home_id, "X", folder_id="nonexistent")


def test_move_entry_to_folder(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _create_kb_folder_impl, _move_kb_entry_impl
    folder = _create_kb_folder_impl(home_id, "Manuals")
    entry = _create_kb_entry_impl(home_id, "X")
    moved = _move_kb_entry_impl(home_id, entry["id"], folder_id=folder["id"])
    assert moved["folderId"] == folder["id"]


def test_move_entry_unknown_folder_id_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _move_kb_entry_impl
    entry = _create_kb_entry_impl(home_id, "X")
    with pytest.raises(ValueError):
        _move_kb_entry_impl(home_id, entry["id"], folder_id="nonexistent")


def test_update_entry_does_not_touch_folder_id(home_id):
    from myhome.mcp_tools_kb import (
        _create_kb_entry_impl, _create_kb_folder_impl, _move_kb_entry_impl, _update_kb_entry_impl,
    )
    folder = _create_kb_folder_impl(home_id, "Manuals")
    entry = _create_kb_entry_impl(home_id, "X")
    _move_kb_entry_impl(home_id, entry["id"], folder_id=folder["id"])
    updated = _update_kb_entry_impl(home_id, entry["id"], title="Renamed")
    assert updated["folderId"] == folder["id"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_mcp_tools_kb.py -q`
Expected: FAIL with `ImportError` (the new `_*_impl` functions don't exist yet)

- [ ] **Step 3: Implement the impl functions and MCP tools**

Edit `packages/backend/src/myhome/mcp_tools_kb.py`, replace the whole file:

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_kb import KBEntry
from .persistence_kb import delete_entry, load_all, load_entry, save_entry
from .persistence_kb_folders import (
    create_folder,
    delete_folder,
    get_folder,
    list_folders,
    move_folder,
    rename_folder,
    would_create_cycle,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _list_kb_entries_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return {"entries": [e.model_dump() for e in load_all(resolved)]}


def _create_kb_entry_impl(
    home_id: str | None, title: str, content: str = "", folder_id: str | None = None,
) -> dict:
    resolved = _resolve_home_id(home_id)
    if folder_id is not None and get_folder(resolved, folder_id) is None:
        raise ValueError(f"Unknown folder_id {folder_id!r}")
    now = _now()
    entry = KBEntry(
        id=str(uuid.uuid4()), title=title, content=content, folderId=folder_id, createdAt=now, updatedAt=now,
    )
    save_entry(resolved, entry)
    return entry.model_dump()


def _update_kb_entry_impl(
    home_id: str | None, entry_id: str, title: str | None = None, content: str | None = None,
) -> dict:
    resolved = _resolve_home_id(home_id)
    entry = load_entry(resolved, entry_id)
    if entry is None:
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    if title is not None:
        entry.title = title
    if content is not None:
        entry.content = content
    entry.updatedAt = _now()
    save_entry(resolved, entry)
    return entry.model_dump()


def _move_kb_entry_impl(home_id: str | None, entry_id: str, folder_id: str | None = None) -> dict:
    resolved = _resolve_home_id(home_id)
    entry = load_entry(resolved, entry_id)
    if entry is None:
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    if folder_id is not None and get_folder(resolved, folder_id) is None:
        raise ValueError(f"Unknown folder_id {folder_id!r}")
    entry.folderId = folder_id
    entry.updatedAt = _now()
    save_entry(resolved, entry)
    return entry.model_dump()


def _delete_kb_entry_impl(home_id: str | None, entry_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    if not delete_entry(resolved, entry_id):
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    return {"deleted": entry_id}


def _list_kb_folders_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return {"folders": [f.model_dump() for f in list_folders(resolved)]}


def _create_kb_folder_impl(home_id: str | None, name: str, parent_id: str | None = None) -> dict:
    resolved = _resolve_home_id(home_id)
    if parent_id is not None and get_folder(resolved, parent_id) is None:
        raise ValueError(f"Unknown parent_id {parent_id!r}")
    return create_folder(resolved, name, parent_id).model_dump()


def _rename_kb_folder_impl(home_id: str | None, folder_id: str, name: str) -> dict:
    resolved = _resolve_home_id(home_id)
    folder = rename_folder(resolved, folder_id, name)
    if folder is None:
        raise ValueError(f"Unknown folder_id {folder_id!r}")
    return folder.model_dump()


def _move_kb_folder_impl(home_id: str | None, folder_id: str, parent_id: str | None = None) -> dict:
    resolved = _resolve_home_id(home_id)
    if parent_id is not None:
        if get_folder(resolved, parent_id) is None:
            raise ValueError(f"Unknown parent_id {parent_id!r}")
        if would_create_cycle(resolved, folder_id, parent_id):
            raise ValueError("Cannot move a folder into itself or a descendant")
    folder = move_folder(resolved, folder_id, parent_id)
    if folder is None:
        raise ValueError(f"Unknown folder_id {folder_id!r}")
    return folder.model_dump()


def _delete_kb_folder_impl(home_id: str | None, folder_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    subfolders = [f for f in list_folders(resolved) if f.parentId == folder_id]
    entries = [e for e in load_all(resolved) if e.folderId == folder_id]
    if subfolders or entries:
        raise ValueError("Folder must be empty before it can be deleted")
    if not delete_folder(resolved, folder_id):
        raise ValueError(f"Unknown folder_id {folder_id!r}")
    return {"deleted": folder_id}


@mcp.tool()
async def list_kb_entries(ctx: Context, home_id: str | None = None) -> dict:
    """List all knowledge base articles for a home. There is no server-side search --
    fetch the list and filter/search over titles and content yourself."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_kb_entries_impl(home_id)


@mcp.tool()
async def create_kb_entry(
    ctx: Context, title: str, home_id: str | None = None, content: str = "", folder_id: str | None = None,
) -> dict:
    """Create a knowledge base article. content supports Markdown. Optionally file it
    into an existing folder via folder_id (see list_kb_folders)."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_kb_entry_impl(home_id, title, content, folder_id)


@mcp.tool()
async def update_kb_entry(
    ctx: Context, entry_id: str, home_id: str | None = None, title: str | None = None, content: str | None = None,
) -> dict:
    """Update the title and/or content of a knowledge base article. To move it between
    folders, use move_kb_entry instead."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_kb_entry_impl(home_id, entry_id, title, content)


@mcp.tool()
async def move_kb_entry(ctx: Context, entry_id: str, home_id: str | None = None, folder_id: str | None = None) -> dict:
    """Move a knowledge base article into folder_id, or to the top level if folder_id is omitted."""
    await _require_role(ctx.request_context.request, "normal")
    return _move_kb_entry_impl(home_id, entry_id, folder_id)


@mcp.tool()
async def delete_kb_entry(ctx: Context, entry_id: str, home_id: str | None = None) -> dict:
    """Delete a knowledge base article."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_kb_entry_impl(home_id, entry_id)


@mcp.tool()
async def list_kb_folders(ctx: Context, home_id: str | None = None) -> dict:
    """List all knowledge base folders for a home."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_kb_folders_impl(home_id)


@mcp.tool()
async def create_kb_folder(ctx: Context, name: str, home_id: str | None = None, parent_id: str | None = None) -> dict:
    """Create a knowledge base folder, optionally nested under parent_id (see list_kb_folders)."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_kb_folder_impl(home_id, name, parent_id)


@mcp.tool()
async def rename_kb_folder(ctx: Context, folder_id: str, name: str, home_id: str | None = None) -> dict:
    """Rename a knowledge base folder."""
    await _require_role(ctx.request_context.request, "normal")
    return _rename_kb_folder_impl(home_id, folder_id, name)


@mcp.tool()
async def move_kb_folder(ctx: Context, folder_id: str, home_id: str | None = None, parent_id: str | None = None) -> dict:
    """Move a knowledge base folder under parent_id, or to the top level if parent_id is omitted."""
    await _require_role(ctx.request_context.request, "normal")
    return _move_kb_folder_impl(home_id, folder_id, parent_id)


@mcp.tool()
async def delete_kb_folder(ctx: Context, folder_id: str, home_id: str | None = None) -> dict:
    """Delete an empty knowledge base folder (it must contain no entries or subfolders)."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_kb_folder_impl(home_id, folder_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_mcp_tools_kb.py -q`
Expected: All tests PASS

- [ ] **Step 5: Run the full backend suite**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_kb.py packages/backend/tests/test_mcp_tools_kb.py
git commit -m "feat: add MCP tools for KB folder management and entry moves"
```

---

### Task 5: `kbStore.svelte.ts` — folders state and CRUD

**Files:**
- Modify: `packages/editor/src/lib/kbStore.svelte.ts`
- Test: `packages/editor/test/kbStore.test.ts`

**Interfaces:**
- Produces: `KBFolder` interface; `store.folders: KBFolder[]`; `store.createFolder({name, parentId?}) -> Promise<KBFolder>`; `store.updateFolder(id, {name?, parentId?}) -> Promise<void>`; `store.deleteFolder(id) -> Promise<void>`; `store.createEntry` gains optional `folderId`; `store.updateEntry`'s patch type gains `folderId?: string | null`.

- [ ] **Step 1: Write the failing tests**

Edit `packages/editor/test/kbStore.test.ts`. Change the existing import line

```ts
import type { KBEntry } from "../src/lib/kbStore.svelte";
```

to also import `KBFolder`:

```ts
import type { KBEntry, KBFolder } from "../src/lib/kbStore.svelte";
```

Add a `makeFolder` helper after the existing `makeEntry` function:

```ts
function makeFolder(overrides: Partial<KBFolder> = {}): KBFolder {
  return { id: "f1", name: "Appliances", parentId: null, ...overrides };
}
```

Append at the end of the file:

```ts

describe("kbStore — folders init", () => {
  it("loads folders from API alongside entries", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, entries: [], folders: [makeFolder()] }));
    const store = createKBStore(getHomeId);
    await tick();
    expect(store.folders.length).toBe(1);
    expect(store.folders[0].name).toBe("Appliances");
  });
});

describe("kbStore — createFolder", () => {
  it("POSTs to /api/homes/{homeId}/kb/folders, returns new folder, and refreshes", async () => {
    const created = makeFolder({ id: "f2", name: "New folder" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [] }) })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => created })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [created] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    const folder = await store.createFolder({ name: "New folder" });
    await tick();
    expect(folder.id).toBe("f2");
    expect(store.folders.length).toBe(1);
    const [, postCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(postCall[0]).toBe(`/api/homes/${HOME}/kb/folders`);
    expect(JSON.parse(postCall[1].body as string)).toEqual({ name: "New folder", parentId: null });
  });

  it("throws on HTTP error", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [] }) })
      .mockResolvedValueOnce({ ok: false, status: 404, json: async () => null });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await expect(store.createFolder({ name: "x" })).rejects.toThrow("HTTP 404");
  });
});

describe("kbStore — updateFolder", () => {
  it("PUTs to /api/homes/{homeId}/kb/folders/{id} and refreshes", async () => {
    const folder = makeFolder();
    const renamed = makeFolder({ name: "Renamed" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [folder] }) })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [renamed] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.updateFolder("f1", { name: "Renamed" });
    await tick();
    expect(store.folders[0].name).toBe("Renamed");
    const [, putCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(putCall[0]).toBe(`/api/homes/${HOME}/kb/folders/f1`);
    expect(JSON.parse(putCall[1].body as string)).toEqual({ name: "Renamed" });
  });

  it("sends an explicit null parentId when moving to root", async () => {
    const folder = makeFolder({ parentId: "parent1" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [folder] }) })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [{ ...folder, parentId: null }] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.updateFolder("f1", { parentId: null });
    await tick();
    const [, putCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(JSON.parse(putCall[1].body as string)).toEqual({ parentId: null });
  });

  it("throws on HTTP error", async () => {
    const folder = makeFolder();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [folder] }) })
      .mockResolvedValueOnce({ ok: false, status: 404, json: async () => null });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await expect(store.updateFolder("f1", { name: "x" })).rejects.toThrow("HTTP 404");
  });
});

describe("kbStore — deleteFolder", () => {
  it("DELETEs /api/homes/{homeId}/kb/folders/{id} and refreshes", async () => {
    const folder = makeFolder();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [folder] }) })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.deleteFolder("f1");
    await tick();
    expect(store.folders.length).toBe(0);
    const [, delCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(delCall[0]).toBe(`/api/homes/${HOME}/kb/folders/f1`);
    expect(delCall[1].method).toBe("DELETE");
  });
});

describe("kbStore — createEntry with folderId", () => {
  it("includes folderId in the POST body only when provided", async () => {
    const created = makeEntry({ id: "e2", folderId: "f1" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => created })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [created] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.createEntry({ title: "New entry", content: "", folderId: "f1" });
    const [, postCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(JSON.parse(postCall[1].body as string)).toEqual({ title: "New entry", content: "", folderId: "f1" });
  });
});

describe("kbStore — updateEntry with folderId", () => {
  it("includes folderId in the PUT body when provided", async () => {
    const entry = makeEntry();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [{ ...entry, folderId: "f1" }] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.updateEntry("e1", { folderId: "f1" });
    await tick();
    const [, putCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(JSON.parse(putCall[1].body as string)).toEqual({ folderId: "f1" });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/kbStore.test.ts`
Expected: FAIL — `store.folders` is undefined, `store.createFolder` is not a function

- [ ] **Step 3: Implement the store changes**

Edit `packages/editor/src/lib/kbStore.svelte.ts`. Add the `KBFolder` interface and extend `KBDocument` near the top:

```ts
export interface KBFolder {
  id: string;
  name: string;
  parentId: string | null;
}

export interface KBDocument {
  version: number;
  entries: KBEntry[];
  folders: KBFolder[];
}
```

Update the `KBEntry` interface to include `folderId`:

```ts
export interface KBEntry {
  id: string;
  title: string;
  content: string;
  createdAt: string;
  updatedAt: string;
  attachments: string[];
  folderId: string | null;
}
```

Inside `createKBStore`, add `folders` state next to `entries`:

```ts
  const entries = $state<KBEntry[]>([]);
  const folders = $state<KBFolder[]>([]);
```

Update `init()` to populate `folders` and default `folderId` on loaded entries:

```ts
  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) { loaded = true; return; }
    try {
      loadError = null;
      const resp = await fetch(`/api/homes/${homeId}/kb`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: KBDocument = await resp.json();
      entries.length = 0;
      for (const e of doc.entries) entries.push({ attachments: [], folderId: null, ...e });
      folders.length = 0;
      for (const f of doc.folders ?? []) folders.push(f);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }
```

Update `createEntry` to accept optional `folderId`, sent only when provided:

```ts
  async function createEntry(
    data: { title: string; content: string; folderId?: string | null },
  ): Promise<KBEntry> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const payload: Record<string, unknown> = { title: data.title, content: data.content };
    if (data.folderId !== undefined) payload.folderId = data.folderId;
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
```

Update `updateEntry`'s patch type:

```ts
  async function updateEntry(
    id: string,
    patch: { title?: string; content?: string; folderId?: string | null },
  ): Promise<void> {
```

(the body of `updateEntry` is unchanged — `JSON.stringify(patch)` already serializes whatever keys are present.)

Add folder CRUD functions (place them after `deleteAttachment`, before `init()` is called):

```ts
  async function createFolder(data: { name: string; parentId?: string | null }): Promise<KBFolder> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/folders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: data.name, parentId: data.parentId ?? null }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const folder: KBFolder = await resp.json();
    await init();
    return folder;
  }

  async function updateFolder(
    id: string,
    patch: { name?: string; parentId?: string | null },
  ): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/folders/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteFolder(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/folders/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }
```

Update the returned object to expose `folders` and the new functions:

```ts
  return {
    get entries() { return entries as KBEntry[]; },
    get folders() { return folders as KBFolder[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    createEntry,
    updateEntry,
    deleteEntry,
    uploadAttachment,
    deleteAttachment,
    createFolder,
    updateFolder,
    deleteFolder,
    reload: init,
  };
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/kbStore.test.ts`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/kbStore.svelte.ts packages/editor/test/kbStore.test.ts
git commit -m "feat: add folders state and CRUD to kbStore"
```

---

### Task 6: `KBTree.svelte` — recursive folder/entry tree component

**Files:**
- Create: `packages/editor/src/lib/components/ui/KBTree.svelte`
- Test: `packages/editor/test/KBTree.test.ts`

**Interfaces:**
- Consumes: `KBEntry`, `KBFolder` from `../../kbStore.svelte` (Task 5).
- Produces: `KBTree.svelte` with props `{folders, entries, parentId?, depth?, selectedId, searchQuery, collapsedIds, renamingFolderId, dragging, onselectentry, ontogglefolder, oncreatesubfolder, oncreateentryin, onstartrename, oncommitrename, oncancelrename, ondeletefolder, onstartdrag, onenddrag, ondropon}`.

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/KBTree.test.ts`:

```ts
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import KBTree from "../src/lib/components/ui/KBTree.svelte";
import type { KBEntry, KBFolder } from "../src/lib/kbStore.svelte";

function makeFolder(overrides: Partial<KBFolder> = {}): KBFolder {
  return { id: "f1", name: "Appliances", parentId: null, ...overrides };
}

function makeEntry(overrides: Partial<KBEntry> = {}): KBEntry {
  return {
    id: "e1", title: "How to paint", content: "", createdAt: "2026-06-28T10:00:00Z",
    updatedAt: "2026-06-28T10:00:00Z", attachments: [], folderId: null, ...overrides,
  };
}

function baseProps(overrides: Record<string, unknown> = {}) {
  return {
    folders: [] as KBFolder[],
    entries: [] as KBEntry[],
    selectedId: null,
    searchQuery: "",
    collapsedIds: new Set<string>(),
    renamingFolderId: null,
    dragging: null,
    onselectentry: vi.fn(),
    ontogglefolder: vi.fn(),
    oncreatesubfolder: vi.fn(),
    oncreateentryin: vi.fn(),
    onstartrename: vi.fn(),
    oncommitrename: vi.fn(),
    oncancelrename: vi.fn(),
    ondeletefolder: vi.fn(),
    onstartdrag: vi.fn(),
    onenddrag: vi.fn(),
    ondropon: vi.fn(),
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
  it("renders root-level folders and entries", () => {
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1", name: "Manuals" })],
      entries: [makeEntry({ id: "e1", title: "Wifi password", folderId: null })],
    });
    expect(target.querySelector(".folder-name")?.textContent).toBe("Manuals");
    expect(target.querySelector(".entry-title")?.textContent).toBe("Wifi password");
    unmount(comp);
    target.remove();
  });

  it("shows 'No entries yet.' when the tree is empty", () => {
    const { target, comp } = setup();
    expect(target.querySelector(".list-empty")?.textContent).toContain("No entries yet.");
    unmount(comp);
    target.remove();
  });

  it("nests entries under their folder, not at the root", () => {
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1", name: "Manuals" })],
      entries: [makeEntry({ id: "e1", title: "Nested entry", folderId: "f1" })],
    });
    const allEntryRows = target.querySelectorAll(".entry-row");
    expect(allEntryRows.length).toBe(1);
    expect(allEntryRows[0].textContent).toContain("Nested entry");
    unmount(comp);
    target.remove();
  });
});

describe("KBTree — expand/collapse", () => {
  it("clicking the disclosure calls ontogglefolder with the folder id", () => {
    const ontogglefolder = vi.fn();
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1", name: "Manuals" })],
      ontogglefolder,
    });
    (target.querySelector(".disclosure") as HTMLElement).click();
    expect(ontogglefolder).toHaveBeenCalledWith("f1");
    unmount(comp);
    target.remove();
  });

  it("hides nested entries when the folder id is in collapsedIds", () => {
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1", name: "Manuals" })],
      entries: [makeEntry({ id: "e1", folderId: "f1" })],
      collapsedIds: new Set(["f1"]),
    });
    expect(target.querySelector(".entry-row")).toBeNull();
    unmount(comp);
    target.remove();
  });
});

describe("KBTree — search filter", () => {
  it("hides folders with no matching descendants", () => {
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1", name: "Manuals" }), makeFolder({ id: "f2", name: "Warranties" })],
      entries: [makeEntry({ id: "e1", title: "Wifi password", folderId: "f1" })],
      searchQuery: "wifi",
    });
    const names = Array.from(target.querySelectorAll(".folder-name")).map((n) => n.textContent);
    expect(names).toEqual(["Manuals"]);
    unmount(comp);
    target.remove();
  });

  it("auto-expands a folder containing a match even if collapsed", () => {
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1", name: "Manuals" })],
      entries: [makeEntry({ id: "e1", title: "Wifi password", folderId: "f1" })],
      collapsedIds: new Set(["f1"]),
      searchQuery: "wifi",
    });
    expect(target.querySelector(".entry-title")?.textContent).toBe("Wifi password");
    unmount(comp);
    target.remove();
  });

  it("shows 'No matching entries.' when nothing matches", () => {
    const { target, comp } = setup({
      entries: [makeEntry({ id: "e1", title: "Wifi password" })],
      searchQuery: "zzz",
    });
    expect(target.querySelector(".list-empty")?.textContent).toContain("No matching entries.");
    unmount(comp);
    target.remove();
  });
});

describe("KBTree — folder context menu", () => {
  function openMenu(target: HTMLElement) {
    (target.querySelector(".menu-trigger") as HTMLElement).click();
    flushSync();
  }

  it("New subfolder calls oncreatesubfolder with the folder id", () => {
    const oncreatesubfolder = vi.fn();
    const { target, comp } = setup({ folders: [makeFolder({ id: "f1" })], oncreatesubfolder });
    openMenu(target);
    const btn = Array.from(target.querySelectorAll(".folder-menu button"))
      .find((b) => b.textContent === "New subfolder") as HTMLButtonElement;
    btn.click();
    expect(oncreatesubfolder).toHaveBeenCalledWith("f1");
    unmount(comp);
    target.remove();
  });

  it("New entry here calls oncreateentryin with the folder id", () => {
    const oncreateentryin = vi.fn();
    const { target, comp } = setup({ folders: [makeFolder({ id: "f1" })], oncreateentryin });
    openMenu(target);
    const btn = Array.from(target.querySelectorAll(".folder-menu button"))
      .find((b) => b.textContent === "New entry here") as HTMLButtonElement;
    btn.click();
    expect(oncreateentryin).toHaveBeenCalledWith("f1");
    unmount(comp);
    target.remove();
  });

  it("Rename calls onstartrename with the folder id", () => {
    const onstartrename = vi.fn();
    const { target, comp } = setup({ folders: [makeFolder({ id: "f1" })], onstartrename });
    openMenu(target);
    const btn = Array.from(target.querySelectorAll(".folder-menu button"))
      .find((b) => b.textContent === "Rename") as HTMLButtonElement;
    btn.click();
    expect(onstartrename).toHaveBeenCalledWith("f1");
    unmount(comp);
    target.remove();
  });

  it("Delete is disabled when the folder has entries", () => {
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1" })],
      entries: [makeEntry({ id: "e1", folderId: "f1" })],
    });
    openMenu(target);
    const btn = Array.from(target.querySelectorAll(".folder-menu button"))
      .find((b) => b.textContent === "Delete") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    unmount(comp);
    target.remove();
  });

  it("Delete calls ondeletefolder when the folder is empty", () => {
    const ondeletefolder = vi.fn();
    const { target, comp } = setup({ folders: [makeFolder({ id: "f1" })], ondeletefolder });
    openMenu(target);
    const btn = Array.from(target.querySelectorAll(".folder-menu button"))
      .find((b) => b.textContent === "Delete") as HTMLButtonElement;
    btn.click();
    expect(ondeletefolder).toHaveBeenCalledWith("f1");
    unmount(comp);
    target.remove();
  });
});

describe("KBTree — inline rename", () => {
  it("shows a text input for the folder being renamed and commits on Enter", () => {
    const oncommitrename = vi.fn();
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1", name: "Old name" })],
      renamingFolderId: "f1",
      oncommitrename,
    });
    const input = target.querySelector(".rename-input") as HTMLInputElement;
    expect(input).not.toBeNull();
    input.value = "New name";
    input.dispatchEvent(new Event("input"));
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    expect(oncommitrename).toHaveBeenCalledWith("f1", "New name");
    unmount(comp);
    target.remove();
  });

  it("Escape cancels the rename", () => {
    const oncancelrename = vi.fn();
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1", name: "Old name" })],
      renamingFolderId: "f1",
      oncancelrename,
    });
    const input = target.querySelector(".rename-input") as HTMLInputElement;
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(oncancelrename).toHaveBeenCalled();
    unmount(comp);
    target.remove();
  });
});

describe("KBTree — drag and drop", () => {
  it("dragstart on an entry calls onstartdrag with kind entry", () => {
    const onstartdrag = vi.fn();
    const { target, comp } = setup({ entries: [makeEntry({ id: "e1" })], onstartdrag });
    (target.querySelector(".entry-row") as HTMLElement).dispatchEvent(new Event("dragstart"));
    expect(onstartdrag).toHaveBeenCalledWith("entry", "e1");
    unmount(comp);
    target.remove();
  });

  it("dropping on a folder calls ondropon with the folder id", () => {
    const ondropon = vi.fn();
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1" })],
      dragging: { kind: "entry", id: "e1" },
      ondropon,
    });
    (target.querySelector(".folder-row") as HTMLElement).dispatchEvent(new Event("drop"));
    expect(ondropon).toHaveBeenCalledWith("f1");
    unmount(comp);
    target.remove();
  });

  it("does not allow dropping a folder onto its own descendant", () => {
    const ondropon = vi.fn();
    const { target, comp } = setup({
      folders: [
        makeFolder({ id: "f1", name: "Parent" }),
        makeFolder({ id: "f2", name: "Child", parentId: "f1" }),
      ],
      dragging: { kind: "folder", id: "f1" },
      ondropon,
    });
    const rows = target.querySelectorAll(".folder-row");
    (rows[1] as HTMLElement).dispatchEvent(new Event("drop"));
    expect(ondropon).not.toHaveBeenCalled();
    unmount(comp);
    target.remove();
  });

  it("shows the root drop zone only while dragging", () => {
    const { target: idle, comp: idleComp } = setup();
    expect(idle.querySelector(".root-dropzone")).toBeNull();
    unmount(idleComp);
    idle.remove();

    const { target, comp } = setup({ dragging: { kind: "entry", id: "e1" } });
    expect(target.querySelector(".root-dropzone")).not.toBeNull();
    unmount(comp);
    target.remove();
  });

  it("dropping on the root zone calls ondropon with null", () => {
    const ondropon = vi.fn();
    const { target, comp } = setup({ dragging: { kind: "entry", id: "e1" }, ondropon });
    (target.querySelector(".root-dropzone") as HTMLElement).dispatchEvent(new Event("drop"));
    expect(ondropon).toHaveBeenCalledWith(null);
    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/KBTree.test.ts`
Expected: FAIL — cannot find module `../src/lib/components/ui/KBTree.svelte`

- [ ] **Step 3: Implement the component**

Create `packages/editor/src/lib/components/ui/KBTree.svelte`:

```svelte
<!-- packages/editor/src/lib/components/ui/KBTree.svelte -->
<script lang="ts">
  import type { KBEntry, KBFolder } from "../../kbStore.svelte";

  interface Dragging {
    kind: "entry" | "folder";
    id: string;
  }

  interface Props {
    folders: KBFolder[];
    entries: KBEntry[];
    parentId?: string | null;
    depth?: number;
    selectedId: string | null;
    searchQuery: string;
    collapsedIds: Set<string>;
    renamingFolderId: string | null;
    dragging: Dragging | null;
    onselectentry: (entry: KBEntry) => void;
    ontogglefolder: (folderId: string) => void;
    oncreatesubfolder: (parentId: string) => void;
    oncreateentryin: (folderId: string) => void;
    onstartrename: (folderId: string) => void;
    oncommitrename: (folderId: string, name: string) => void;
    oncancelrename: () => void;
    ondeletefolder: (folderId: string) => void;
    onstartdrag: (kind: "entry" | "folder", id: string) => void;
    onenddrag: () => void;
    ondropon: (targetFolderId: string | null) => void;
  }

  let {
    folders, entries, parentId = null, depth = 0, selectedId, searchQuery, collapsedIds,
    renamingFolderId, dragging,
    onselectentry, ontogglefolder, oncreatesubfolder, oncreateentryin,
    onstartrename, oncommitrename, oncancelrename, ondeletefolder,
    onstartdrag, onenddrag, ondropon,
  }: Props = $props();

  let renameDraft = $state("");
  let menuOpenFor = $state<string | null>(null);
  let dragOverId = $state<string | null>(null);

  function matches(text: string): boolean {
    const q = searchQuery.trim().toLowerCase();
    return !q || text.toLowerCase().includes(q);
  }

  const visibleFolderIds = $derived.by(() => {
    const q = searchQuery.trim();
    if (!q) return null;
    const childFoldersOf = new Map<string | null, KBFolder[]>();
    for (const f of folders) {
      const list = childFoldersOf.get(f.parentId) ?? [];
      list.push(f);
      childFoldersOf.set(f.parentId, list);
    }
    const childEntriesOf = new Map<string | null, KBEntry[]>();
    for (const e of entries) {
      const list = childEntriesOf.get(e.folderId) ?? [];
      list.push(e);
      childEntriesOf.set(e.folderId, list);
    }
    const visible = new Set<string>();
    function visit(folder: KBFolder): boolean {
      const ownMatch = matches(folder.name);
      const hasMatchingEntry = (childEntriesOf.get(folder.id) ?? []).some((e) => matches(e.title));
      const hasMatchingChild = (childFoldersOf.get(folder.id) ?? []).map(visit).some(Boolean);
      const keep = ownMatch || hasMatchingEntry || hasMatchingChild;
      if (keep) visible.add(folder.id);
      return keep;
    }
    for (const f of childFoldersOf.get(null) ?? []) visit(f);
    return visible;
  });

  const childFolders = $derived(
    folders
      .filter((f) => f.parentId === parentId)
      .filter((f) => visibleFolderIds === null || visibleFolderIds.has(f.id))
      .slice()
      .sort((a, b) => a.name.localeCompare(b.name)),
  );
  const childEntries = $derived(
    entries
      .filter((e) => e.folderId === parentId)
      .filter((e) => matches(e.title))
      .slice()
      .sort((a, b) => a.createdAt.localeCompare(b.createdAt)),
  );

  function isOpen(folderId: string): boolean {
    return searchQuery.trim() !== "" || !collapsedIds.has(folderId);
  }

  function hasChildren(folderId: string): boolean {
    return folders.some((f) => f.parentId === folderId) || entries.some((e) => e.folderId === folderId);
  }

  function fmtDate(iso: string): string {
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }

  function startRename(folder: KBFolder): void {
    renameDraft = folder.name;
    menuOpenFor = null;
    onstartrename(folder.id);
  }

  function commitRename(folderId: string): void {
    const name = renameDraft.trim();
    if (name) oncommitrename(folderId, name);
    else oncancelrename();
  }

  function wouldCreateCycle(folderId: string, targetId: string): boolean {
    if (folderId === targetId) return true;
    let current: string | null = targetId;
    const seen = new Set<string>();
    while (current !== null) {
      if (current === folderId) return true;
      if (seen.has(current)) return false;
      seen.add(current);
      const f = folders.find((x) => x.id === current);
      current = f ? f.parentId : null;
    }
    return false;
  }

  function canDropOnFolder(targetId: string): boolean {
    if (!dragging) return false;
    if (dragging.kind === "folder" && wouldCreateCycle(dragging.id, targetId)) return false;
    return true;
  }
</script>

<ul class="kb-tree" class:root={depth === 0}>
  {#each childFolders as folder (folder.id)}
    <li>
      <div
        class="tree-row folder-row"
        class:drop-target={dragOverId === folder.id}
        draggable="true"
        role="treeitem"
        aria-expanded={isOpen(folder.id)}
        tabindex="0"
        ondragstart={(e) => { e.dataTransfer?.setData("text/plain", ""); onstartdrag("folder", folder.id); }}
        ondragend={onenddrag}
        ondragover={(e) => { if (canDropOnFolder(folder.id)) { e.preventDefault(); dragOverId = folder.id; } }}
        ondragleave={() => { if (dragOverId === folder.id) dragOverId = null; }}
        ondrop={(e) => {
          e.preventDefault();
          dragOverId = null;
          if (canDropOnFolder(folder.id)) ondropon(folder.id);
        }}
      >
        <button
          class="disclosure"
          onclick={() => ontogglefolder(folder.id)}
          aria-label={isOpen(folder.id) ? "Collapse folder" : "Expand folder"}
        >{isOpen(folder.id) ? "▾" : "▸"}</button>
        <span class="folder-icon">📁</span>
        {#if renamingFolderId === folder.id}
          <input
            class="rename-input"
            bind:value={renameDraft}
            onblur={() => commitRename(folder.id)}
            onkeydown={(e) => {
              if (e.key === "Enter") commitRename(folder.id);
              if (e.key === "Escape") oncancelrename();
            }}
          />
        {:else}
          <span class="folder-name">{folder.name}</span>
        {/if}
        <button
          class="menu-trigger"
          title="Folder actions"
          onclick={() => { menuOpenFor = menuOpenFor === folder.id ? null : folder.id; }}
        >⋯</button>
        {#if menuOpenFor === folder.id}
          <div class="folder-menu" role="menu">
            <button role="menuitem" onclick={() => { oncreatesubfolder(folder.id); menuOpenFor = null; }}>New subfolder</button>
            <button role="menuitem" onclick={() => { oncreateentryin(folder.id); menuOpenFor = null; }}>New entry here</button>
            <button role="menuitem" onclick={() => startRename(folder)}>Rename</button>
            <button
              role="menuitem"
              class="danger"
              disabled={hasChildren(folder.id)}
              title={hasChildren(folder.id) ? "Folder must be empty" : undefined}
              onclick={() => { ondeletefolder(folder.id); menuOpenFor = null; }}
            >Delete</button>
          </div>
        {/if}
      </div>
      {#if isOpen(folder.id)}
        <svelte:self
          {folders} {entries} parentId={folder.id} depth={depth + 1}
          {selectedId} {searchQuery} {collapsedIds} {renamingFolderId} {dragging}
          {onselectentry} {ontogglefolder} {oncreatesubfolder} {oncreateentryin}
          {onstartrename} {oncommitrename} {oncancelrename} {ondeletefolder}
          {onstartdrag} {onenddrag} {ondropon}
        />
      {/if}
    </li>
  {/each}
  {#each childEntries as entry (entry.id)}
    <li>
      <div
        role="button"
        tabindex="0"
        class="tree-row entry-row"
        class:active={entry.id === selectedId}
        draggable="true"
        ondragstart={(e) => { e.dataTransfer?.setData("text/plain", ""); onstartdrag("entry", entry.id); }}
        ondragend={onenddrag}
        onclick={() => onselectentry(entry)}
        onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") onselectentry(entry); }}
      >
        <span class="entry-title">{entry.title}</span>
        <span class="entry-date">{fmtDate(entry.updatedAt)}</span>
      </div>
    </li>
  {/each}
  {#if depth === 0 && childFolders.length === 0 && childEntries.length === 0}
    <li class="list-empty">
      {searchQuery.trim() ? "No matching entries." : "No entries yet."}
    </li>
  {/if}
</ul>

{#if depth === 0 && dragging}
  <div
    class="root-dropzone"
    class:drop-target={dragOverId === "__root__"}
    ondragover={(e) => { e.preventDefault(); dragOverId = "__root__"; }}
    ondragleave={() => { if (dragOverId === "__root__") dragOverId = null; }}
    ondrop={(e) => { e.preventDefault(); dragOverId = null; ondropon(null); }}
  >⬆ Move to top level</div>
{/if}

<style>
  .kb-tree { list-style: none; margin: 0; padding: 0; }
  .kb-tree:not(.root) { padding-left: 16px; }

  .tree-row {
    display: flex; align-items: center; gap: 6px;
    padding: 6px 8px; border-radius: var(--radius-md);
    cursor: pointer; position: relative;
  }
  .tree-row:hover { background: var(--surface-hover); }
  .tree-row.drop-target { outline: 2px solid var(--accent); outline-offset: -2px; }

  .folder-row { cursor: default; }
  .disclosure {
    background: none; border: none; padding: 0; width: 14px; flex-shrink: 0;
    color: var(--text-faint); font-size: 10px; cursor: pointer;
  }
  .folder-icon { flex-shrink: 0; font-size: 13px; }
  .folder-name {
    flex: 1; min-width: 0; font-size: 13px; color: var(--text); font-weight: 500;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .rename-input {
    flex: 1; min-width: 0; font-size: 13px; font-family: var(--font-sans);
    background: var(--surface-alt); border: 1px solid var(--accent);
    border-radius: var(--radius-sm); padding: 2px 6px; color: var(--text);
  }
  .rename-input:focus { outline: none; }

  .menu-trigger {
    background: none; border: none; padding: 2px 4px; color: var(--text-faint);
    cursor: pointer; font-size: 13px; opacity: 0; flex-shrink: 0;
  }
  .tree-row:hover .menu-trigger, .menu-trigger:focus { opacity: 1; }

  .folder-menu {
    position: absolute; top: 100%; right: 0; z-index: 10;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); box-shadow: var(--shadow-md);
    display: flex; flex-direction: column; min-width: 150px; padding: 4px;
  }
  .folder-menu button {
    background: none; border: none; text-align: left; padding: 6px 10px;
    font-size: 12px; color: var(--text); border-radius: var(--radius-sm); cursor: pointer;
  }
  .folder-menu button:hover:not(:disabled) { background: var(--surface-hover); }
  .folder-menu button:disabled { color: var(--text-faint); cursor: default; }
  .folder-menu button.danger { color: var(--danger); }

  .entry-row { padding: 8px 10px 8px 26px; border-left: 3px solid transparent; border-radius: var(--radius-md); }
  .entry-row.active { background: var(--surface-alt); border-left-color: var(--accent); }
  .entry-title {
    font-size: 13px; color: var(--text); font-weight: 500; flex: 1; min-width: 0;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .entry-date { font-size: 11px; color: var(--text-faint); flex-shrink: 0; }

  .list-empty { font-size: 12px; color: var(--text-faint); text-align: center; padding: 20px 0; list-style: none; }

  .root-dropzone {
    margin: 4px 8px; padding: 10px; border: 2px dashed var(--border); border-radius: var(--radius-md);
    text-align: center; font-size: 11px; color: var(--text-faint);
  }
  .root-dropzone.drop-target { border-color: var(--accent); color: var(--accent); }
</style>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/KBTree.test.ts`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/KBTree.svelte packages/editor/test/KBTree.test.ts
git commit -m "feat: add recursive KBTree component for folder/entry navigation"
```

---

### Task 7: `KBPage.svelte` — Card wrap + wire in `KBTree`

**Files:**
- Modify: `packages/editor/src/lib/components/KBPage.svelte`
- Test: `packages/editor/test/KBPage.test.ts`

**Interfaces:**
- Consumes: `KBTree.svelte` (Task 6); `store.folders`/`createFolder`/`updateFolder`/`deleteFolder` (Task 5).
- Produces: KB page wrapped in `Card`, sidebar renders `KBTree` instead of a flat list, toolbar gains a "＋ Folder" button.

- [ ] **Step 1: Update the test mock store and add new tests**

Edit `packages/editor/test/KBPage.test.ts`. Change the existing import line

```ts
import type { KBEntry } from "../src/lib/kbStore.svelte";
```

to also import `KBFolder`:

```ts
import type { KBEntry, KBFolder } from "../src/lib/kbStore.svelte";
```

Add a `makeFolder` helper near the top (after `makeEntry`):

```ts
function makeFolder(overrides: Partial<KBFolder> = {}): KBFolder {
  return { id: "f1", name: "Manuals", parentId: null, ...overrides };
}
```

Update `makeStore` to include folders and the new store methods:

```ts
function makeStore(entries: KBEntry[] = [], overrides: Partial<ReturnType<typeof makeStore>> = {}) {
  return {
    entries,
    folders: [] as KBFolder[],
    loaded: true,
    loadError: null as string | null,
    createEntry: vi.fn().mockResolvedValue(
      makeEntry({ id: "new1", title: "New entry", content: "" }),
    ),
    updateEntry: vi.fn().mockResolvedValue(undefined),
    deleteEntry: vi.fn().mockResolvedValue(undefined),
    uploadAttachment: vi.fn().mockResolvedValue("file.jpg"),
    deleteAttachment: vi.fn().mockResolvedValue(undefined),
    createFolder: vi.fn().mockResolvedValue(makeFolder({ id: "newf1", name: "New folder" })),
    updateFolder: vi.fn().mockResolvedValue(undefined),
    deleteFolder: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}
```

Append new test suites at the end of the file:

```ts

describe("KBPage — Card wrapper", () => {
  it("wraps the page content in a Card", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(KBPage, { target, props: { store: makeStore([]) } });
    flushSync();
    expect(target.querySelector(".ui-card")).not.toBeNull();
    unmount(app);
    target.remove();
  });
});

describe("KBPage — folders", () => {
  it("＋ Folder button calls store.createFolder with a root-level folder", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    const btn = Array.from(target.querySelectorAll("button")).find(
      (b) => b.textContent?.trim() === "＋ Folder",
    ) as HTMLButtonElement;
    btn.click();
    await tick();
    flushSync();
    expect(store.createFolder).toHaveBeenCalledWith({ name: "New folder", parentId: null });
    unmount(app);
    target.remove();
  });

  it("renders folders from the store in the tree", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([], { folders: [makeFolder({ id: "f1", name: "Manuals" })] });
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    expect(target.querySelector(".folder-name")?.textContent).toBe("Manuals");
    unmount(app);
    target.remove();
  });

  it("selecting an entry nested in a folder shows its content", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore(
      [makeEntry({ id: "e1", title: "Nested", folderId: "f1" })],
      { folders: [makeFolder({ id: "f1", name: "Manuals" })] },
    );
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    expect(target.querySelector(".content-title")?.textContent?.trim()).toBe("Nested");
    unmount(app);
    target.remove();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/KBPage.test.ts`
Expected: FAIL — `.ui-card` not found, "＋ Folder" button not found, `.folder-name` not found

- [ ] **Step 3: Implement the integration**

Edit `packages/editor/src/lib/components/KBPage.svelte`. Update the imports:

```ts
  import type { createKBStore, KBEntry } from "../kbStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import MarkdownEditor from "./ui/MarkdownEditor.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import Card from "./ui/Card.svelte";
  import KBTree from "./ui/KBTree.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";
```

Add new state (place it alongside the existing `let searchQuery = $state("");` etc.):

```ts
  let collapsedIds = $state<Set<string>>(new Set());
  let renamingFolderId = $state<string | null>(null);
  let dragging = $state<{ kind: "entry" | "folder"; id: string } | null>(null);
```

Remove the now-unused `filteredEntries` derived (search filtering moves into `KBTree`):

```ts
  const filteredEntries = $derived(
    store.entries.filter((e) =>
      e.title.toLowerCase().includes(searchQuery.toLowerCase()),
    ),
  );
```

Add the new handler functions (place them after `handleDeleteAttachment`, before `handleItemClick`):

```ts
  function toggleFolder(folderId: string): void {
    const next = new Set(collapsedIds);
    if (next.has(folderId)) next.delete(folderId); else next.add(folderId);
    collapsedIds = next;
  }

  async function handleCreateFolder(parentId: string | null): Promise<void> {
    try {
      const folder = await store.createFolder({ name: "New folder", parentId });
      if (parentId) {
        const next = new Set(collapsedIds);
        next.delete(parentId);
        collapsedIds = next;
      }
      renamingFolderId = folder.id;
    } catch (e) {
      error = e instanceof Error ? e.message : "Create folder failed";
    }
  }

  async function handleCreateEntryIn(folderId: string): Promise<void> {
    try {
      const entry = await store.createEntry({ title: "New entry", content: "", folderId });
      selectEntry(entry);
      editing = true;
    } catch (e) {
      error = e instanceof Error ? e.message : "Create failed";
    }
  }

  async function handleRenameFolder(folderId: string, name: string): Promise<void> {
    try {
      await store.updateFolder(folderId, { name });
    } catch (e) {
      error = e instanceof Error ? e.message : "Rename failed";
    } finally {
      renamingFolderId = null;
    }
  }

  function handleCancelRename(): void {
    renamingFolderId = null;
  }

  async function handleDeleteFolder(folderId: string): Promise<void> {
    try {
      await store.deleteFolder(folderId);
    } catch (e) {
      error = e instanceof Error ? e.message : "Delete folder failed";
    }
  }

  function handleStartDrag(kind: "entry" | "folder", id: string): void {
    dragging = { kind, id };
  }

  function handleEndDrag(): void {
    dragging = null;
  }

  async function handleDropOn(targetFolderId: string | null): Promise<void> {
    const active = dragging;
    dragging = null;
    if (!active) return;
    try {
      if (active.kind === "entry") {
        await store.updateEntry(active.id, { folderId: targetFolderId });
      } else if (active.id !== targetFolderId) {
        await store.updateFolder(active.id, { parentId: targetFolderId });
      }
    } catch (e) {
      error = e instanceof Error ? e.message : "Move failed";
    }
  }
```

Replace the top-level markup. The old structure was:

```svelte
<div class="kb-page">
  <div class="kb-sidebar">
    <div class="sidebar-toolbar">
      <Input placeholder="🔍 Search…" bind:value={searchQuery} />
      <Button onclick={handleNew}>＋ New</Button>
    </div>
    <div class="entry-list">
      {#each filteredEntries as entry (entry.id)}
        ...
      {:else}
        <div class="list-empty">
          {searchQuery ? "No matching entries." : "No entries yet."}
        </div>
      {/each}
    </div>
  </div>

  <div class="kb-content">
    ...
  </div>
</div>
```

Replace it with:

```svelte
<Card style="display:flex; padding:0; overflow:hidden; height:100%; font-family: var(--font-sans);">
  <div class="kb-sidebar">
    <div class="sidebar-toolbar">
      <Input placeholder="🔍 Search…" bind:value={searchQuery} />
      <Button onclick={handleNew}>＋ New</Button>
      <Button variant="secondary" onclick={() => handleCreateFolder(null)}>＋ Folder</Button>
    </div>
    <div class="entry-list">
      <KBTree
        folders={store.folders}
        entries={store.entries}
        {selectedId}
        {searchQuery}
        {collapsedIds}
        {renamingFolderId}
        {dragging}
        onselectentry={selectEntry}
        ontogglefolder={toggleFolder}
        oncreatesubfolder={handleCreateFolder}
        oncreateentryin={handleCreateEntryIn}
        onstartrename={(id) => { renamingFolderId = id; }}
        oncommitrename={handleRenameFolder}
        oncancelrename={handleCancelRename}
        ondeletefolder={handleDeleteFolder}
        onstartdrag={handleStartDrag}
        onenddrag={handleEndDrag}
        ondropon={handleDropOn}
      />
    </div>
  </div>

  <div class="kb-content">
    ...
  </div>
</Card>
```

(the `.kb-content` block's own contents are unchanged — only its enclosing tag changes from `</div>` [closing `.kb-page`] to `</Card>`.)

Update the `<style>` block:
- Remove the `.kb-page { ... }` rule entirely (replaced by the `Card` + inline `style`).
- Remove `.entry-row`, `.entry-row:hover`, `.entry-row.active`, `.entry-title`, `.entry-date`, and `.list-empty` — these elements now render inside `KBTree.svelte`, and Svelte's scoped CSS only applies within the component that renders the markup, so leaving them in `KBPage.svelte` would just be dead CSS.

The remaining `.kb-sidebar`, `.sidebar-toolbar`, `.entry-list`, `.kb-content`, and all `.content-*` rules are unchanged.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/KBPage.test.ts`
Expected: All tests PASS

- [ ] **Step 5: Run the full frontend suite**

Run: `cd packages/editor && npx vitest run`
Expected: All tests PASS (no regressions in other components)

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/KBPage.svelte packages/editor/test/KBPage.test.ts
git commit -m "feat: wrap KB page in Card and wire in the KBTree folder view"
```

---

## Manual verification (after all tasks)

- [ ] Start the app, open the KB module, confirm the page now renders inside a card with rounded corners/shadow.
- [ ] Create a folder via "＋ Folder", confirm it appears with an inline rename box already active; type a name and press Enter.
- [ ] Right-click-equivalent (click "⋯") on the folder, use "New subfolder" and "New entry here"; confirm both land inside the folder and the folder auto-expands.
- [ ] Drag an existing entry onto a folder; confirm it moves (disappears from root, appears nested).
- [ ] Drag a folder onto its own child; confirm nothing happens (no cycle).
- [ ] Try deleting a non-empty folder; confirm the Delete menu item is disabled with a tooltip.
- [ ] Delete all its contents, then delete the empty folder; confirm it disappears.
- [ ] Type a search query matching only a deeply nested entry; confirm the ancestor folders auto-expand and unrelated folders disappear; clear the search and confirm prior collapse state returns.
