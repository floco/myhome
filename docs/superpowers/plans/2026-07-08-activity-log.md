# Unified Activity Timeline / Audit Log Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-home, admin-only activity log capturing rich "who did what" entries (create/update/delete/complete) across Chores, Works, Costs, Inventory, Consumables, and Knowledge Base, viewable as a new Settings section.

**Architecture:** A new `persistence_activity.py` owns the log's persistence, pruning (90-day retention), and description formatting. A lightweight `get_current_user_id` dependency exposes the identity the auth middleware already resolved (no re-authentication) to route handlers, which each call `log_activity(...)` explicitly after a successful mutation — no decorator, no shared framework, mirroring this codebase's existing two independent background-scheduler loops over a generic job runner.

**Tech Stack:** FastAPI, Pydantic, pytest, Svelte 5, Vitest.

**Reference spec:** `docs/superpowers/specs/2026-07-08-activity-log-design.md`

**Scope note:** Only the primary create/update/delete actions (and chore/assignment completion) are wired for logging — attachment upload/delete, floor-plan placement changes, bulk Donetick import, and secondary deletion endpoints (chore completion records, consumable transactions) are intentionally out of scope for v1, consistent with the spec's action table.

---

## Task 1: `ActivityEntry` / `ActivityLogDocument` models

**Files:**
- Create: `packages/backend/src/myhome/models_activity.py`
- Test: `packages/backend/tests/test_activity_persistence.py` (new)

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_activity_persistence.py`:

```python
from myhome.models_activity import ActivityEntry, ActivityLogDocument


def test_activity_entry_requires_fields():
    entry = ActivityEntry(
        id="e1", timestamp="2026-07-08T12:00:00+00:00",
        userId="u1", username="alice",
        module="chores", action="complete", entityLabel="Sweep kitchen",
    )
    assert entry.refId is None


def test_activity_log_document_defaults_to_empty():
    assert ActivityLogDocument().entries == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_activity_persistence.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'myhome.models_activity'`

- [ ] **Step 3: Write minimal implementation**

Create `packages/backend/src/myhome/models_activity.py`:

```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class ActivityEntry(BaseModel):
    id: str
    timestamp: str  # ISO 8601 UTC
    userId: str
    username: str
    module: Literal["chores", "works", "costs", "inventory", "consumables", "kb"]
    action: Literal["create", "update", "delete", "complete"]
    entityLabel: str
    refId: str | None = None


class ActivityLogDocument(BaseModel):
    version: int = 1
    entries: list[ActivityEntry] = []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_activity_persistence.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/models_activity.py packages/backend/tests/test_activity_persistence.py
git commit -m "feat: add ActivityEntry and ActivityLogDocument models"
```

---

## Task 2: `persistence_activity.py` — log_activity, pruning, describe()

**Files:**
- Create: `packages/backend/src/myhome/persistence_activity.py`
- Test: `packages/backend/tests/test_activity_persistence.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_activity_persistence.py`:

```python
from datetime import datetime, timedelta, timezone

from myhome.models_auth import User, UserDocument
from myhome.persistence_activity import describe, load_activity_log, log_activity, save_activity_log
from myhome.persistence_auth import save_users


def _make_user(tmp_path, monkeypatch, user_id="u1", username="alice"):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_users(UserDocument(users=[
        User(id=user_id, username=username, role="admin", created_at="2026-01-01T00:00:00+00:00"),
    ]))


def test_log_activity_appends_entry_with_resolved_username(tmp_path, monkeypatch):
    _make_user(tmp_path, monkeypatch)
    log_activity("home-1", "u1", "chores", "complete", "Sweep kitchen", "chore-1")
    entries = load_activity_log("home-1").entries
    assert len(entries) == 1
    assert entries[0].username == "alice"
    assert entries[0].module == "chores"
    assert entries[0].action == "complete"
    assert entries[0].entityLabel == "Sweep kitchen"
    assert entries[0].refId == "chore-1"


def test_log_activity_resolves_unknown_user_gracefully(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    log_activity("home-1", "ghost", "works", "create", "Fix boiler")
    entries = load_activity_log("home-1").entries
    assert entries[0].username == "unknown"


def test_log_activity_prunes_entries_older_than_90_days(tmp_path, monkeypatch):
    _make_user(tmp_path, monkeypatch)
    old_timestamp = (datetime.now(timezone.utc) - timedelta(days=91)).isoformat()
    save_activity_log("home-1", load_activity_log("home-1").model_copy(update={
        "entries": [
            {
                "id": "old-1", "timestamp": old_timestamp, "userId": "u1", "username": "alice",
                "module": "chores", "action": "create", "entityLabel": "Old chore", "refId": None,
            }
        ]
    }))

    log_activity("home-1", "u1", "chores", "create", "New chore")

    entries = load_activity_log("home-1").entries
    assert len(entries) == 1
    assert entries[0].entityLabel == "New chore"


def test_describe_builds_expected_sentence():
    from myhome.models_activity import ActivityEntry
    entry = ActivityEntry(
        id="e1", timestamp="2026-07-08T12:00:00+00:00", userId="u1", username="alice",
        module="costs", action="create", entityLabel="Electricity",
    )
    assert describe(entry) == "added cost entry 'Electricity'"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_activity_persistence.py -v -k "log_activity or describe"`
Expected: FAIL with `ModuleNotFoundError: No module named 'myhome.persistence_activity'`

- [ ] **Step 3: Write minimal implementation**

Create `packages/backend/src/myhome/persistence_activity.py`:

```python
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models_activity import ActivityEntry, ActivityLogDocument

RETENTION_DAYS = 90

ACTION_VERBS = {"create": "added", "update": "updated", "delete": "deleted", "complete": "completed"}
MODULE_NOUNS = {
    "chores": "chore", "works": "work", "costs": "cost entry",
    "inventory": "inventory item", "consumables": "consumable", "kb": "KB article",
}


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data"))


def _home_dir(home_id: str) -> Path:
    return _data_dir() / "homes" / home_id


def _activity_file(home_id: str) -> Path:
    return _home_dir(home_id) / "activity_log.json"


def load_activity_log(home_id: str) -> ActivityLogDocument:
    path = _activity_file(home_id)
    if not path.exists():
        return ActivityLogDocument()
    with path.open() as f:
        return ActivityLogDocument.model_validate(json.load(f))


def save_activity_log(home_id: str, doc: ActivityLogDocument) -> None:
    path = _activity_file(home_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)


def _resolve_username(user_id: str) -> str:
    from .persistence_auth import load_users
    user = next((u for u in load_users().users if u.id == user_id), None)
    return user.username if user else "unknown"


def log_activity(
    home_id: str, user_id: str, module: str, action: str,
    entity_label: str, ref_id: str | None = None,
) -> None:
    doc = load_activity_log(home_id)
    doc.entries.append(ActivityEntry(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        userId=user_id,
        username=_resolve_username(user_id),
        module=module,
        action=action,
        entityLabel=entity_label,
        refId=ref_id,
    ))
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    doc.entries = [e for e in doc.entries if datetime.fromisoformat(e.timestamp) >= cutoff]
    save_activity_log(home_id, doc)


def describe(entry: ActivityEntry) -> str:
    return f"{ACTION_VERBS[entry.action]} {MODULE_NOUNS[entry.module]} '{entry.entityLabel}'"
```

Note: `log_activity`'s signature takes `user_id` only (not `username`) — it resolves the username internally via `_resolve_username`. This is a deliberate simplification over the design spec's sketch (which showed `username` as a parameter): resolving internally means every call site only needs `home_id, current_user_id, module, action, entity_label[, ref_id]`, with no risk of a caller passing a stale or mismatched username.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_activity_persistence.py -v`
Expected: PASS (6 tests total)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/persistence_activity.py packages/backend/tests/test_activity_persistence.py
git commit -m "feat: add activity log persistence, pruning, and description formatting"
```

---

## Task 3: `get_current_user_id` dependency

**Files:**
- Modify: `packages/backend/src/myhome/deps.py`
- Test: covered implicitly by Task 4's wiring tests (this dependency has no meaningful behavior to unit-test in isolation beyond "reads request.state.user", which requires a real request context)

- [ ] **Step 1: Write the implementation**

Add to `packages/backend/src/myhome/deps.py`, after `require_auth`:

```python
def get_current_user_id(request: Request) -> str:
    """Read the (user_id, role) already resolved by auth_middleware -- no re-authentication."""
    user_id, _role = request.state.user
    return user_id
```

- [ ] **Step 2: Commit**

```bash
git add packages/backend/src/myhome/deps.py
git commit -m "feat: add get_current_user_id dependency reading middleware-resolved identity"
```

---

## Task 4: Wire Chores (create, update, delete, complete_chore, complete_assignment)

**Files:**
- Modify: `packages/backend/src/myhome/routes/chores.py`
- Test: `packages/backend/tests/test_activity_wiring.py` (new)

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_activity_wiring.py`:

```python
from myhome.persistence_activity import load_activity_log


def test_creating_chore_logs_activity(client, home_id):
    client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep kitchen", "emoji": "🧹", "periodDays": 7,
        "nextDueDate": "2026-01-01T00:00:00Z",
    })
    entries = load_activity_log(home_id).entries
    assert any(e.module == "chores" and e.action == "create" and e.entityLabel == "Sweep kitchen" for e in entries)


def test_updating_chore_logs_activity(client, home_id):
    chore = client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep kitchen", "emoji": "🧹", "periodDays": 7,
        "nextDueDate": "2026-01-01T00:00:00Z",
    }).json()
    client.put(f"/api/homes/{home_id}/chores/{chore['id']}", json={"description": "Updated"})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "chores" and e.action == "update" and e.entityLabel == "Sweep kitchen" for e in entries)


def test_deleting_chore_logs_activity(client, home_id):
    chore = client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep kitchen", "emoji": "🧹", "periodDays": 7,
        "nextDueDate": "2026-01-01T00:00:00Z",
    }).json()
    client.delete(f"/api/homes/{home_id}/chores/{chore['id']}")
    entries = load_activity_log(home_id).entries
    assert any(e.module == "chores" and e.action == "delete" and e.entityLabel == "Sweep kitchen" for e in entries)


def test_completing_chore_logs_activity(client, home_id):
    chore = client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep kitchen", "emoji": "🧹", "periodDays": 7,
        "nextDueDate": "2026-01-01T00:00:00Z",
    }).json()
    client.post(f"/api/homes/{home_id}/chores/{chore['id']}/complete", json={"notes": ""})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "chores" and e.action == "complete" and e.entityLabel == "Sweep kitchen" for e in entries)


def test_completing_assignment_logs_activity(client, home_id):
    chore = client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep kitchen", "emoji": "🧹", "periodDays": 7,
        "nextDueDate": "2026-01-01T00:00:00Z",
    }).json()
    assignment = client.post(f"/api/homes/{home_id}/assignments", json={
        "choreId": chore["id"], "roomId": None, "position": None, "nextDueDate": "2026-01-01T00:00:00Z",
    }).json()
    client.post(f"/api/homes/{home_id}/assignments/{assignment['id']}/complete", json={"notes": ""})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "chores" and e.action == "complete" and e.entityLabel == "Sweep kitchen" for e in entries)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_activity_wiring.py -v -k chore`
Expected: FAIL — `load_activity_log(home_id).entries` is empty for all 5 tests

- [ ] **Step 3: Write minimal implementation**

In `packages/backend/src/myhome/routes/chores.py`, update the import lines:

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile
```

```python
from ..deps import get_current_user_id
from ..persistence_activity import log_activity
```

Update `create_chore`:

```python
@router.post("/api/homes/{home_id}/chores", response_model=Chore, status_code=201)
def create_chore(
    home_id: str, body: ChoreCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> Chore:
    doc = load_chores(home_id)
    data = body.model_dump()
    if data["frequency"] == 0:
        data["frequency"] = max(1, round(data["periodDays"]))
        data["frequencyMetadata"] = {"unit": "days"}
    chore = Chore(id=str(uuid.uuid4()), **data)
    doc.chores.append(chore)
    save_chores(home_id, doc)
    log_activity(home_id, current_user_id, "chores", "create", chore.name, chore.id)
    return chore
```

Update `update_chore`:

```python
@router.put("/api/homes/{home_id}/chores/{chore_id}", status_code=204)
def update_chore(
    home_id: str, chore_id: str, body: ChoreUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_chores(home_id)
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(chore, field, value)
    save_chores(home_id, doc)
    log_activity(home_id, current_user_id, "chores", "update", chore.name, chore.id)
```

Update `delete_chore` (this changes the 404-check from a bare `any(...)` to looking up the chore object, since we need its name before removal):

```python
@router.delete("/api/homes/{home_id}/chores/{chore_id}", status_code=204)
def delete_chore(
    home_id: str, chore_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_chores(home_id)
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    doc.chores = [c for c in doc.chores if c.id != chore_id]
    doc.assignments = [a for a in doc.assignments if a.choreId != chore_id]
    save_chores(home_id, doc)
    delete_all_attachments(home_id, chore_id)
    log_activity(home_id, current_user_id, "chores", "delete", chore.name, chore_id)
```

Update `complete_chore`:

```python
@router.post("/api/homes/{home_id}/chores/{chore_id}/complete", response_model=Chore)
def complete_chore(
    home_id: str, chore_id: str, body: CompleteRequest | None = None,
    current_user_id: str = Depends(get_current_user_id),
) -> Chore:
    doc = load_chores(home_id)
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    notes = body.notes if body else ""
    now = datetime.now(timezone.utc)
    if chore.scheduleFromDue and chore.nextDueDate:
        try:
            from_dt = datetime.fromisoformat(chore.nextDueDate.replace("Z", "+00:00"))
        except ValueError:
            from_dt = now
    else:
        from_dt = now
    next_due = next_due_from_schedule(chore, from_dt)
    next_due_str = next_due.strftime("%Y-%m-%dT%H:%M:%SZ")
    doc.completions.append(CompletionRecord(
        id=str(uuid.uuid4()),
        choreId=chore_id,
        completedAt=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        scheduledDue=chore.nextDueDate,
        notes=notes,
    ))
    for a in doc.assignments:
        if a.choreId == chore_id:
            a.nextDueDate = next_due_str
    chore.nextDueDate = next_due_str
    save_chores(home_id, doc)
    log_activity(home_id, current_user_id, "chores", "complete", chore.name, chore_id)
    return chore
```

Update `complete_assignment`:

```python
@router.post("/api/homes/{home_id}/assignments/{assignment_id}/complete", response_model=Assignment)
def complete_assignment(
    home_id: str, assignment_id: str, body: CompleteRequest | None = None,
    current_user_id: str = Depends(get_current_user_id),
) -> Assignment:
    doc = load_chores(home_id)
    assignment = next((a for a in doc.assignments if a.id == assignment_id), None)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    chore = next((c for c in doc.chores if c.id == assignment.choreId), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    notes = body.notes if body else ""
    now = datetime.now(timezone.utc)
    if chore.scheduleFromDue and assignment.nextDueDate:
        try:
            from_dt = datetime.fromisoformat(assignment.nextDueDate.replace("Z", "+00:00"))
        except ValueError:
            from_dt = now
    else:
        from_dt = now
    next_due = next_due_from_schedule(chore, from_dt)
    doc.completions.append(CompletionRecord(
        id=str(uuid.uuid4()),
        choreId=chore.id,
        assignmentId=assignment_id,
        completedAt=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        scheduledDue=assignment.nextDueDate,
        notes=notes,
    ))
    assignment.nextDueDate = next_due.strftime("%Y-%m-%dT%H:%M:%SZ")
    save_chores(home_id, doc)
    log_activity(home_id, current_user_id, "chores", "complete", chore.name, chore.id)
    return assignment
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_activity_wiring.py -v -k chore`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/chores.py packages/backend/tests/test_activity_wiring.py
git commit -m "feat: log activity for chore create/update/delete/complete"
```

---

## Task 5: Wire Works (create, update, delete)

**Files:**
- Modify: `packages/backend/src/myhome/routes/works.py`
- Test: `packages/backend/tests/test_activity_wiring.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_activity_wiring.py`:

```python
def test_creating_work_logs_activity(client, home_id):
    client.post(f"/api/homes/{home_id}/works", json={"title": "Fix boiler", "date": "2026-01-01"})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "works" and e.action == "create" and e.entityLabel == "Fix boiler" for e in entries)


def test_updating_work_logs_activity(client, home_id):
    work = client.post(f"/api/homes/{home_id}/works", json={"title": "Fix boiler", "date": "2026-01-01"}).json()
    client.put(f"/api/homes/{home_id}/works/{work['id']}", json={"status": "in_progress"})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "works" and e.action == "update" and e.entityLabel == "Fix boiler" for e in entries)


def test_deleting_work_logs_activity(client, home_id):
    work = client.post(f"/api/homes/{home_id}/works", json={"title": "Fix boiler", "date": "2026-01-01"}).json()
    client.delete(f"/api/homes/{home_id}/works/{work['id']}")
    entries = load_activity_log(home_id).entries
    assert any(e.module == "works" and e.action == "delete" and e.entityLabel == "Fix boiler" for e in entries)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_activity_wiring.py -v -k work`
Expected: FAIL — no entries logged

- [ ] **Step 3: Write minimal implementation**

In `packages/backend/src/myhome/routes/works.py`, update imports:

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile
```

```python
from ..deps import get_current_user_id
from ..persistence_activity import log_activity
```

Update `create_work`:

```python
@router.post("/api/homes/{home_id}/works", response_model=Work, status_code=201)
def create_work(
    home_id: str, body: WorkCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> Work:
    doc = load_works(home_id)
    work = Work(id=str(uuid.uuid4()), **body.model_dump())
    doc.works.append(work)
    save_works(home_id, doc)
    log_activity(home_id, current_user_id, "works", "create", work.title, work.id)
    return work
```

Update `update_work`:

```python
@router.put("/api/homes/{home_id}/works/{id}", status_code=204)
def update_work(
    home_id: str, id: str, body: WorkUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_works(home_id)
    work = next((w for w in doc.works if w.id == id), None)
    if not work:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(work, field, value)
    save_works(home_id, doc)
    log_activity(home_id, current_user_id, "works", "update", work.title, id)
```

Update `delete_work`:

```python
@router.delete("/api/homes/{home_id}/works/{id}", status_code=204)
def delete_work(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_works(home_id)
    work = next((w for w in doc.works if w.id == id), None)
    if work is None:
        raise HTTPException(status_code=404)
    doc.works = [w for w in doc.works if w.id != id]
    save_works(home_id, doc)
    delete_all_attachments(home_id, id)
    log_activity(home_id, current_user_id, "works", "delete", work.title, id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_activity_wiring.py -v -k work`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/works.py packages/backend/tests/test_activity_wiring.py
git commit -m "feat: log activity for work create/update/delete"
```

---

## Task 6: Wire Costs (create, update, delete)

**Files:**
- Modify: `packages/backend/src/myhome/routes/costs.py`
- Test: `packages/backend/tests/test_activity_wiring.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_activity_wiring.py`:

```python
def test_creating_cost_entry_logs_activity(client, home_id):
    client.post(f"/api/homes/{home_id}/costs/entries", json={
        "categoryId": "cat-1", "date": "2026-01-01", "totalAmount": 45.0, "notes": "Electricity",
    })
    entries = load_activity_log(home_id).entries
    assert any(e.module == "costs" and e.action == "create" and e.entityLabel == "Electricity" for e in entries)


def test_creating_cost_entry_without_notes_uses_amount_as_label(client, home_id):
    client.post(f"/api/homes/{home_id}/costs/entries", json={
        "categoryId": "cat-1", "date": "2026-01-01", "totalAmount": 45.5,
    })
    entries = load_activity_log(home_id).entries
    assert any(e.module == "costs" and e.action == "create" and e.entityLabel == "45.5" for e in entries)


def test_updating_cost_entry_logs_activity(client, home_id):
    entry = client.post(f"/api/homes/{home_id}/costs/entries", json={
        "categoryId": "cat-1", "date": "2026-01-01", "totalAmount": 45.0, "notes": "Electricity",
    }).json()
    client.put(f"/api/homes/{home_id}/costs/entries/{entry['id']}", json={"totalAmount": 50.0})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "costs" and e.action == "update" and e.entityLabel == "Electricity" for e in entries)


def test_deleting_cost_entry_logs_activity(client, home_id):
    entry = client.post(f"/api/homes/{home_id}/costs/entries", json={
        "categoryId": "cat-1", "date": "2026-01-01", "totalAmount": 45.0, "notes": "Electricity",
    }).json()
    client.delete(f"/api/homes/{home_id}/costs/entries/{entry['id']}")
    entries = load_activity_log(home_id).entries
    assert any(e.module == "costs" and e.action == "delete" and e.entityLabel == "Electricity" for e in entries)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_activity_wiring.py -v -k cost`
Expected: FAIL — no entries logged

- [ ] **Step 3: Write minimal implementation**

In `packages/backend/src/myhome/routes/costs.py`, update imports:

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile
```

```python
from ..deps import get_current_user_id
from ..persistence_activity import log_activity
```

Add a small local label helper (costs-specific formatting, since `CostEntry` has no name/title field):

```python
def _cost_label(entry: CostEntry) -> str:
    return entry.notes if entry.notes else f"{entry.totalAmount:g}"
```

Update `create_entry`:

```python
@router.post("/api/homes/{home_id}/costs/entries", response_model=CostEntry, status_code=201)
def create_entry(
    home_id: str, body: CostEntryCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> CostEntry:
    doc = load_costs(home_id)
    entry = CostEntry(id=str(uuid.uuid4()), **body.model_dump())
    doc.entries.append(entry)
    save_costs(home_id, doc)
    log_activity(home_id, current_user_id, "costs", "create", _cost_label(entry), entry.id)
    return entry
```

Update `update_entry`:

```python
@router.put("/api/homes/{home_id}/costs/entries/{id}", status_code=204)
def update_entry(
    home_id: str, id: str, body: CostEntryUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_costs(home_id)
    entry = next((e for e in doc.entries if e.id == id), None)
    if not entry:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    save_costs(home_id, doc)
    log_activity(home_id, current_user_id, "costs", "update", _cost_label(entry), id)
```

Update `delete_entry`:

```python
@router.delete("/api/homes/{home_id}/costs/entries/{id}", status_code=204)
def delete_entry(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_costs(home_id)
    entry = next((e for e in doc.entries if e.id == id), None)
    if entry is None:
        raise HTTPException(status_code=404)
    doc.entries = [e for e in doc.entries if e.id != id]
    save_costs(home_id, doc)
    delete_all_attachments(home_id, id)
    log_activity(home_id, current_user_id, "costs", "delete", _cost_label(entry), id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_activity_wiring.py -v -k cost`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/costs.py packages/backend/tests/test_activity_wiring.py
git commit -m "feat: log activity for cost entry create/update/delete"
```

---

## Task 7: Wire Inventory (create, update, delete)

**Files:**
- Modify: `packages/backend/src/myhome/routes/inventory.py`
- Test: `packages/backend/tests/test_activity_wiring.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_activity_wiring.py`:

```python
def test_creating_inventory_item_logs_activity(client, home_id):
    client.post(f"/api/homes/{home_id}/inventory/items", json={"name": "TV"})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "inventory" and e.action == "create" and e.entityLabel == "TV" for e in entries)


def test_updating_inventory_item_logs_activity(client, home_id):
    item = client.post(f"/api/homes/{home_id}/inventory/items", json={"name": "TV"}).json()
    client.put(f"/api/homes/{home_id}/inventory/items/{item['id']}", json={"brand": "Samsung"})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "inventory" and e.action == "update" and e.entityLabel == "TV" for e in entries)


def test_deleting_inventory_item_logs_activity(client, home_id):
    item = client.post(f"/api/homes/{home_id}/inventory/items", json={"name": "TV"}).json()
    client.delete(f"/api/homes/{home_id}/inventory/items/{item['id']}")
    entries = load_activity_log(home_id).entries
    assert any(e.module == "inventory" and e.action == "delete" and e.entityLabel == "TV" for e in entries)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_activity_wiring.py -v -k inventory`
Expected: FAIL — no entries logged

- [ ] **Step 3: Write minimal implementation**

In `packages/backend/src/myhome/routes/inventory.py`, update imports:

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile
```

```python
from ..deps import get_current_user_id
from ..persistence_activity import log_activity
```

Update `create_item`:

```python
@router.post("/api/homes/{home_id}/inventory/items", response_model=InventoryItem, status_code=201)
def create_item(
    home_id: str, body: InventoryItemCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> InventoryItem:
    doc = load_inventory(home_id)
    item = InventoryItem(id=str(uuid.uuid4()), **body.model_dump())
    doc.items.append(item)
    save_inventory(home_id, doc)
    log_activity(home_id, current_user_id, "inventory", "create", item.name, item.id)
    return item
```

Update `update_item`:

```python
@router.put("/api/homes/{home_id}/inventory/items/{id}", status_code=204)
def update_item(
    home_id: str, id: str, body: InventoryItemUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_inventory(home_id)
    item = next((i for i in doc.items if i.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    save_inventory(home_id, doc)
    log_activity(home_id, current_user_id, "inventory", "update", item.name, id)
```

Update `delete_item`:

```python
@router.delete("/api/homes/{home_id}/inventory/items/{id}", status_code=204)
def delete_item(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_inventory(home_id)
    item = next((i for i in doc.items if i.id == id), None)
    if item is None:
        raise HTTPException(status_code=404)
    doc.items = [i for i in doc.items if i.id != id]
    save_inventory(home_id, doc)
    delete_all_attachments(home_id, id)
    log_activity(home_id, current_user_id, "inventory", "delete", item.name, id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_activity_wiring.py -v -k inventory`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/inventory.py packages/backend/tests/test_activity_wiring.py
git commit -m "feat: log activity for inventory item create/update/delete"
```

---

## Task 8: Wire Consumables (create, update stock, delete)

**Files:**
- Modify: `packages/backend/src/myhome/routes/consumables.py`
- Test: `packages/backend/tests/test_activity_wiring.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_activity_wiring.py`:

```python
def test_creating_consumable_logs_activity(client, home_id):
    client.post(f"/api/homes/{home_id}/consumables", json={"name": "Salt", "quantity": 5, "minQuantity": 1})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "consumables" and e.action == "create" and e.entityLabel == "Salt" for e in entries)


def test_adjusting_consumable_stock_logs_activity(client, home_id):
    item = client.post(f"/api/homes/{home_id}/consumables", json={"name": "Salt", "quantity": 5, "minQuantity": 1}).json()
    client.post(f"/api/homes/{home_id}/consumables/{item['id']}/stock", json={"quantity": 2, "note": ""})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "consumables" and e.action == "update" and e.entityLabel == "Salt" for e in entries)


def test_deleting_consumable_logs_activity(client, home_id):
    item = client.post(f"/api/homes/{home_id}/consumables", json={"name": "Salt", "quantity": 5, "minQuantity": 1}).json()
    client.delete(f"/api/homes/{home_id}/consumables/{item['id']}")
    entries = load_activity_log(home_id).entries
    assert any(e.module == "consumables" and e.action == "delete" and e.entityLabel == "Salt" for e in entries)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_activity_wiring.py -v -k consumable`
Expected: FAIL — no entries logged

- [ ] **Step 3: Write minimal implementation**

In `packages/backend/src/myhome/routes/consumables.py`, update imports:

```python
from fastapi import APIRouter, Depends, HTTPException
```

```python
from ..deps import get_current_user_id
from ..persistence_activity import log_activity
```

Update `create_consumable`:

```python
@router.post("/api/homes/{home_id}/consumables", response_model=Consumable, status_code=201)
def create_consumable(
    home_id: str, body: ConsumableCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> Consumable:
    doc = load_consumables(home_id)
    item = Consumable(id=str(uuid.uuid4()), **body.model_dump())
    doc.consumables.append(item)
    save_consumables(home_id, doc)
    log_activity(home_id, current_user_id, "consumables", "create", item.name, item.id)
    return item
```

Update `delete_consumable`:

```python
@router.delete("/api/homes/{home_id}/consumables/{id}", status_code=204)
def delete_consumable(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_consumables(home_id)
    item = next((c for c in doc.consumables if c.id == id), None)
    if item is None:
        raise HTTPException(status_code=404)
    doc.consumables = [c for c in doc.consumables if c.id != id]
    doc.transactions = [t for t in doc.transactions if t.consumableId != id]
    save_consumables(home_id, doc)
    log_activity(home_id, current_user_id, "consumables", "delete", item.name, id)
```

Update `update_stock`:

```python
@router.post("/api/homes/{home_id}/consumables/{id}/stock", status_code=204)
def update_stock(
    home_id: str, id: str, body: StockUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_consumables(home_id)
    item = next((c for c in doc.consumables if c.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    delta = body.quantity - item.quantity
    item.quantity = body.quantity
    tx = ConsumableTransaction(
        id=str(uuid.uuid4()),
        consumableId=id,
        delta=delta,
        quantityAfter=body.quantity,
        note=body.note,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    doc.transactions.append(tx)
    save_consumables(home_id, doc)
    log_activity(home_id, current_user_id, "consumables", "update", item.name, id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_activity_wiring.py -v -k consumable`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/consumables.py packages/backend/tests/test_activity_wiring.py
git commit -m "feat: log activity for consumable create/stock-update/delete"
```

---

## Task 9: Wire Knowledge Base (create, update, delete)

**Files:**
- Modify: `packages/backend/src/myhome/routes/kb.py`
- Test: `packages/backend/tests/test_activity_wiring.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_activity_wiring.py`:

```python
def test_creating_kb_entry_logs_activity(client, home_id):
    client.post(f"/api/homes/{home_id}/kb", json={"title": "How to reset router", "content": "..."})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "kb" and e.action == "create" and e.entityLabel == "How to reset router" for e in entries)


def test_updating_kb_entry_logs_activity(client, home_id):
    entry = client.post(f"/api/homes/{home_id}/kb", json={"title": "How to reset router", "content": "..."}).json()
    client.put(f"/api/homes/{home_id}/kb/{entry['id']}", json={"content": "Updated steps"})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "kb" and e.action == "update" and e.entityLabel == "How to reset router" for e in entries)


def test_deleting_kb_entry_logs_activity(client, home_id):
    entry = client.post(f"/api/homes/{home_id}/kb", json={"title": "How to reset router", "content": "..."}).json()
    client.delete(f"/api/homes/{home_id}/kb/{entry['id']}")
    entries = load_activity_log(home_id).entries
    assert any(e.module == "kb" and e.action == "delete" and e.entityLabel == "How to reset router" for e in entries)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_activity_wiring.py -v -k kb`
Expected: FAIL — no entries logged

- [ ] **Step 3: Write minimal implementation**

In `packages/backend/src/myhome/routes/kb.py`, update imports:

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile
```

```python
from ..deps import get_current_user_id
from ..persistence_activity import log_activity
```

Update `create_entry`:

```python
@router.post("/api/homes/{home_id}/kb", response_model=KBEntry, status_code=201)
def create_entry(
    home_id: str, body: KBCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> KBEntry:
    now = _now()
    entry = KBEntry(
        id=str(uuid.uuid4()),
        title=body.title,
        content=body.content,
        createdAt=now,
        updatedAt=now,
    )
    save_entry(home_id, entry)
    log_activity(home_id, current_user_id, "kb", "create", entry.title, entry.id)
    return entry
```

Update `update_entry`:

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
    entry.updatedAt = _now()
    save_entry(home_id, entry)
    log_activity(home_id, current_user_id, "kb", "update", entry.title, id)
```

Update `delete_kb_entry`:

```python
@router.delete("/api/homes/{home_id}/kb/{id}", status_code=204)
def delete_kb_entry(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    entry = load_entry(home_id, id)
    if not entry:
        raise HTTPException(status_code=404)
    if not delete_entry(home_id, id):
        raise HTTPException(status_code=404)
    log_activity(home_id, current_user_id, "kb", "delete", entry.title, id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_activity_wiring.py -v -k kb`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/kb.py packages/backend/tests/test_activity_wiring.py
git commit -m "feat: log activity for KB entry create/update/delete"
```

---

## Task 10: `GET /api/homes/{home_id}/activity` route

**Files:**
- Create: `packages/backend/src/myhome/routes/activity.py`
- Modify: `packages/backend/src/myhome/main.py`
- Test: `packages/backend/tests/test_activity_route.py` (new)

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_activity_route.py`:

```python
def test_get_activity_requires_admin(client, home_id, ro_client):
    client.post(f"/api/homes/{home_id}/works", json={"title": "Fix boiler", "date": "2026-01-01"})
    resp = ro_client.get(f"/api/homes/{home_id}/activity")
    assert resp.status_code == 403


def test_get_activity_returns_entries_newest_first(client, home_id):
    client.post(f"/api/homes/{home_id}/works", json={"title": "First", "date": "2026-01-01"})
    client.post(f"/api/homes/{home_id}/works", json={"title": "Second", "date": "2026-01-02"})

    resp = client.get(f"/api/homes/{home_id}/activity")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert [e["entityLabel"] for e in data["entries"]] == ["Second", "First"]
    assert data["entries"][0]["description"] == "added work 'Second'"


def test_get_activity_filters_by_module(client, home_id):
    client.post(f"/api/homes/{home_id}/works", json={"title": "Fix boiler", "date": "2026-01-01"})
    client.post(f"/api/homes/{home_id}/kb", json={"title": "Router guide", "content": "..."})

    resp = client.get(f"/api/homes/{home_id}/activity?module=kb")
    entries = resp.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["module"] == "kb"


def test_get_activity_filters_by_user(client, home_id):
    client.post(f"/api/homes/{home_id}/works", json={"title": "Fix boiler", "date": "2026-01-01"})

    resp = client.get(f"/api/homes/{home_id}/activity?userId=nonexistent-user")
    assert resp.json()["entries"] == []


def test_get_activity_paginates(client, home_id):
    for i in range(3):
        client.post(f"/api/homes/{home_id}/works", json={"title": f"Work {i}", "date": "2026-01-01"})

    resp = client.get(f"/api/homes/{home_id}/activity?limit=2&offset=0")
    data = resp.json()
    assert len(data["entries"]) == 2
    assert data["total"] == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_activity_route.py -v`
Expected: FAIL with 404 (route doesn't exist)

- [ ] **Step 3: Write minimal implementation**

Create `packages/backend/src/myhome/routes/activity.py`:

```python
from fastapi import APIRouter, Query

from ..deps import require_auth
from ..persistence_activity import describe, load_activity_log

router = APIRouter()


@router.get("/api/homes/{home_id}/activity")
def get_activity(
    home_id: str,
    module: str | None = Query(default=None),
    userId: str | None = Query(default=None),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: tuple[str, str] = require_auth("admin"),
) -> dict:
    entries = load_activity_log(home_id).entries
    if module:
        entries = [e for e in entries if e.module == module]
    if userId:
        entries = [e for e in entries if e.userId == userId]
    if since:
        entries = [e for e in entries if e.timestamp >= since]
    if until:
        entries = [e for e in entries if e.timestamp <= until]
    entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)
    total = len(entries)
    page = entries[offset:offset + limit]
    return {
        "entries": [{**e.model_dump(), "description": describe(e)} for e in page],
        "total": total,
    }
```

`since`/`until` are compared as raw ISO-8601 string prefixes (no date parsing) — a shorter date-only string like `"2026-07-01"` correctly sorts before any full timestamp on that same day, so `since=2026-07-01` includes the whole day. For `until` to be inclusive of a whole day, callers should pass the end-of-day boundary (e.g. `2026-07-01T23:59:59`) — the frontend does this in Task 11.

In `packages/backend/src/myhome/main.py`, add `activity` to the routes import:

```python
from .routes import activity, auth, backup, chores, consumables, costs, ha, homes, house, inventory, kb, mcp_config, notifications, settings, svg, works
```

Register the router near the others:

```python
app.include_router(activity.router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_activity_route.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/activity.py packages/backend/src/myhome/main.py packages/backend/tests/test_activity_route.py
git commit -m "feat: add GET /api/homes/{home_id}/activity route"
```

---

## Task 11: Frontend — Activity Log section in Settings

**Files:**
- Modify: `packages/editor/src/lib/components/SettingsPage.svelte`
- Modify: `packages/editor/test/SettingsPage.test.ts`

Like the Users/MCP/SSO sections, this fetches directly in `SettingsPage.svelte` — no new store module. It reads the current home id from the `homesStore` singleton already imported in this file (`import { homesStore } from "../homesStore.svelte";`).

- [ ] **Step 1: Write the failing test**

Add to `packages/editor/test/SettingsPage.test.ts`, inside the `"SettingsPage — Backup & Restore"` describe block is the wrong place — add a **new** describe block at the end of the file (after the `"SettingsPage — Notifications"` block), since this is its own section:

```ts
describe("SettingsPage — Activity Log", () => {
  let target: HTMLDivElement;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    homesStore.setActiveHomeId("home-1");
    fetchMock = vi.fn().mockImplementation((url: string) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false, provider_name: "", issuer: "", client_id: "", client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"] }) });
      if (url.startsWith("/api/homes/home-1/activity")) {
        return Promise.resolve({ ok: true, json: async () => ({ entries: [], total: 0 }) });
      }
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    homesStore._reset();
    target.remove();
  });

  it("renders the Activity Log section for admin", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    expect(target.textContent).toContain("Activity Log");
    unmount(app);
  });

  it("does not render for non-admin", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("normal") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    expect(target.textContent).not.toContain("Activity Log");
    unmount(app);
  });

  it("renders returned entries with description", async () => {
    fetchMock.mockImplementation((url: string) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false, provider_name: "", issuer: "", client_id: "", client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"] }) });
      if (url.startsWith("/api/homes/home-1/activity")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            entries: [{
              id: "e1", timestamp: "2026-07-08T12:00:00+00:00", userId: "u1", username: "alice",
              module: "works", action: "create", entityLabel: "Fix boiler", refId: null,
              description: "added work 'Fix boiler'",
            }],
            total: 1,
          }),
        });
      }
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    expect(target.textContent).toContain("added work 'Fix boiler'");
    unmount(app);
  });

  it("applying a module filter re-fetches with the module query param", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    const moduleSelect = target.querySelector(".activity-module-filter") as HTMLSelectElement;
    moduleSelect.value = "kb";
    moduleSelect.dispatchEvent(new Event("change"));
    await new Promise((r) => setTimeout(r, 0));

    const lastCall = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
    expect(lastCall[0]).toContain("module=kb");
    unmount(app);
  });
});
```

Add the `homesStore` import to the top of `SettingsPage.test.ts` (it isn't imported there yet):

```ts
import { homesStore } from "../src/lib/homesStore.svelte";
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run SettingsPage.test.ts -t "Activity Log"`
Expected: FAIL — no "Activity Log" text, no `.activity-module-filter` element

- [ ] **Step 3: Write minimal implementation**

In `packages/editor/src/lib/components/SettingsPage.svelte`, add script state near the other admin-only sections (after the Backup & Restore scheduled-backups block, before `import { homesStore } from "../homesStore.svelte";` — note `homesStore` is already imported once in this file; do not add a duplicate import):

```ts
  // --- Activity Log (admin only) ---
  interface ActivityEntry {
    id: string;
    timestamp: string;
    userId: string;
    username: string;
    module: string;
    action: string;
    entityLabel: string;
    refId: string | null;
    description: string;
  }

  const ACTIVITY_PAGE_SIZE = 50;
  let activityEntries = $state<ActivityEntry[]>([]);
  let activityTotal = $state(0);
  let activityLoaded = $state(false);
  let activityModuleFilter = $state("");
  let activityUserFilter = $state("");
  let activitySinceFilter = $state("");
  let activityUntilFilter = $state("");
  let activityOffset = $state(0);

  function buildActivityQuery(offset: number): string {
    const params = new URLSearchParams();
    if (activityModuleFilter) params.set("module", activityModuleFilter);
    if (activityUserFilter) params.set("userId", activityUserFilter);
    if (activitySinceFilter) params.set("since", activitySinceFilter);
    if (activityUntilFilter) params.set("until", `${activityUntilFilter}T23:59:59`);
    params.set("limit", String(ACTIVITY_PAGE_SIZE));
    params.set("offset", String(offset));
    return params.toString();
  }

  async function loadActivity(reset: boolean): Promise<void> {
    if (authStore.user?.role !== "admin" || !homesStore.activeHomeId) { activityLoaded = true; return; }
    const offset = reset ? 0 : activityOffset;
    try {
      const resp = await fetch(`/api/homes/${homesStore.activeHomeId}/activity?${buildActivityQuery(offset)}`);
      if (!resp.ok) return;
      const data = await resp.json();
      activityEntries = reset ? data.entries : [...activityEntries, ...data.entries];
      activityTotal = data.total;
      activityOffset = offset + data.entries.length;
    } finally {
      activityLoaded = true;
    }
  }

  function applyActivityFilters(): void {
    loadActivity(true);
  }

  function loadMoreActivity(): void {
    loadActivity(false);
  }

  loadActivity(true);
```

Add the markup as a new `<Card>` after the "Backup & Restore" card's closing `</Card>` and before the outer `</div>`:

```svelte
    <!-- Activity Log (admin only) -->
    {#if authStore.user?.role === "admin"}
      <Card>
        <div class="section-header">
          <h2>Activity Log</h2>
        </div>
        <div class="modal-form">
          <div class="modal-field">
            <span class="modal-label">Module</span>
            <select class="activity-module-filter modal-select" bind:value={activityModuleFilter} onchange={applyActivityFilters}>
              <option value="">All modules</option>
              <option value="chores">Chores</option>
              <option value="works">Works</option>
              <option value="costs">Costs</option>
              <option value="inventory">Inventory</option>
              <option value="consumables">Consumables</option>
              <option value="kb">Knowledge Base</option>
            </select>
          </div>
          <div class="modal-field">
            <span class="modal-label">From</span>
            <Input type="date" bind:value={activitySinceFilter} />
          </div>
          <div class="modal-field">
            <span class="modal-label">To</span>
            <Input type="date" bind:value={activityUntilFilter} />
          </div>
          <div class="modal-actions">
            <Button variant="secondary" onclick={applyActivityFilters}>Filter</Button>
          </div>
        </div>
        {#if activityLoaded}
          {#if activityEntries.length === 0}
            <p class="empty-hint">No activity recorded yet.</p>
          {:else}
            <table class="token-table">
              <thead>
                <tr><th>When</th><th>Who</th><th>What</th></tr>
              </thead>
              <tbody>
                {#each activityEntries as entry (entry.id)}
                  <tr>
                    <td>{new Date(entry.timestamp).toLocaleString()}</td>
                    <td>{entry.username}</td>
                    <td>{entry.description}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
            {#if activityEntries.length < activityTotal}
              <Button variant="secondary" onclick={loadMoreActivity}>Load more</Button>
            {/if}
          {/if}
        {/if}
      </Card>
    {/if}
```

The module `<select>` uses a plain native element with its own `onchange` (matching the existing Frequency/role selects elsewhere in this file), so choosing a module re-fetches immediately. The `Input` component (used for the date fields) does not forward an `onchange`/`oninput` callback prop, so the date range instead applies via the explicit "Filter" button — clicking it calls `applyActivityFilters()`, reading whatever `activitySinceFilter`/`activityUntilFilter` are currently bound to.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run SettingsPage.test.ts`
Expected: PASS (full file, all pre-existing tests plus the 4 new Activity Log tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/SettingsPage.svelte packages/editor/test/SettingsPage.test.ts
git commit -m "feat: add Activity Log section to Settings"
```

---

## Final Verification

- [ ] Run the full backend suite: `cd packages/backend && pytest tests/ -v` — expect all green, including the ~30 new tests added across Tasks 1–10.
- [ ] Run the full frontend suite: `cd packages/editor && npx vitest run` — expect all green, including the new tests from Task 11.
- [ ] Manually verify (Playwright or browser): as admin, complete a chore, add a work, add a cost entry, edit an inventory item, adjust consumable stock, and delete a KB entry; open Settings → Activity Log and confirm all six actions appear, newest first, with correct descriptions and usernames. Confirm the module filter narrows the list, and that a non-admin user does not see the section at all.
- [ ] Update `ROADMAP.md`: move "Unified activity timeline / audit log" out of "To Be Confirmed" into "Recently Completed", linking this plan and the design spec.
