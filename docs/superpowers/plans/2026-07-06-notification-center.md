# Notification Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-home notification center surfacing chores due soon, low-stock consumables, and expiring inventory warranties, shown via a topbar bell/dropdown and an optional daily HA push digest.

**Architecture:** A new backend module (`notifications.py`) computes the full notification list from existing chore/consumable/inventory JSON documents plus new per-home settings; a new `GET /api/homes/{home_id}/notifications` endpoint exposes it to the frontend, and a new `asyncio` background task (the first scheduler in this codebase) calls the same function directly to build a once-daily HA `notify` service digest. Chores and low-stock are computed live/stateless; warranty notifications fire once per item per expiry date, tracked in a small new per-home state file.

**Tech Stack:** FastAPI, Pydantic, httpx, pytest + respx (HTTP mocking), Svelte 5, Vitest.

**Reference spec:** `docs/superpowers/specs/2026-07-06-notification-center-design.md`

---

## Task 1: `NotificationSettings` model + `SettingsDocument` field

**Files:**
- Modify: `packages/backend/src/myhome/models_settings.py`
- Test: `packages/backend/tests/test_settings.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_settings.py`:

```python
def test_get_settings_returns_default_notification_settings(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/settings")
    assert resp.status_code == 200
    notif = resp.json()["notifications"]
    assert notif["enabled"] is True
    assert notif["choresDueSoonThreshold"] == 0.25
    assert notif["warrantyDaysThreshold"] == 30
    assert notif["haPushEnabled"] is False
    assert notif["haNotifyService"] is None
    assert notif["haPushTime"] == "08:00"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_settings.py -v -k default_notification_settings`
Expected: FAIL with a `KeyError: 'notifications'`

- [ ] **Step 3: Write minimal implementation**

In `packages/backend/src/myhome/models_settings.py`, add after `ConsumableCategory` (before `_default_consumable_units`):

```python
class NotificationSettings(BaseModel):
    enabled: bool = True
    choresDueSoonThreshold: float = 0.25
    warrantyDaysThreshold: int = 30
    haPushEnabled: bool = False
    haNotifyService: str | None = None
    haPushTime: str = "08:00"
```

And add a field to `SettingsDocument`:

```python
class SettingsDocument(BaseModel):
    version: int = 1
    costCategories: list[CostCategory] = []
    inventoryCategories: list[InventoryCategory] = []
    workCategories: list[WorkCategory] = []
    suppliers: list[Supplier] = []
    consumableUnits: list[str] = []
    consumableCategories: list[ConsumableCategory] = []
    notifications: NotificationSettings = NotificationSettings()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_settings.py -v -k default_notification_settings`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/models_settings.py packages/backend/tests/test_settings.py
git commit -m "feat: add NotificationSettings to SettingsDocument"
```

---

## Task 2: `PUT /settings/notifications` route

**Files:**
- Modify: `packages/backend/src/myhome/routes/settings.py`
- Test: `packages/backend/tests/test_settings.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_settings.py`:

```python
def test_put_notification_settings(client, home_id):
    body = {
        "enabled": True,
        "choresDueSoonThreshold": 0.4,
        "warrantyDaysThreshold": 45,
        "haPushEnabled": True,
        "haNotifyService": "notify.mobile_app_pixel",
        "haPushTime": "09:30",
    }
    resp = client.put(f"/api/homes/{home_id}/settings/notifications", json=body)
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/settings").json()["notifications"]
    assert data["choresDueSoonThreshold"] == 0.4
    assert data["haNotifyService"] == "notify.mobile_app_pixel"
    assert data["haPushTime"] == "09:30"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_settings.py -v -k put_notification_settings`
Expected: FAIL with 404 (no such route)

- [ ] **Step 3: Write minimal implementation**

In `packages/backend/src/myhome/routes/settings.py`, add `NotificationSettings` to the import from `..models_settings`, and add a route at the end of the file:

```python
from ..models_settings import (
    ConsumableCategory,
    CostCategory,
    CostCategoryPlacement,
    InventoryCategory,
    NotificationSettings,
    WorkCategory,
    Supplier,
    SettingsDocument,
)
```

```python
@router.put("/api/homes/{home_id}/settings/notifications", status_code=204)
def put_notification_settings(home_id: str, body: NotificationSettings) -> None:
    doc = load_settings(home_id)
    doc.notifications = body
    save_settings(home_id, doc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_settings.py -v -k put_notification_settings`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/settings.py packages/backend/tests/test_settings.py
git commit -m "feat: add PUT settings/notifications route"
```

---

## Task 3: Notification state model + persistence

**Files:**
- Create: `packages/backend/src/myhome/models_notifications.py`
- Create: `packages/backend/src/myhome/persistence_notifications.py`
- Test: `packages/backend/tests/test_notifications_persistence.py`

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_notifications_persistence.py`:

```python
import os

from myhome.models_notifications import NotificationState
from myhome.persistence_notifications import load_notification_state, save_notification_state


def test_load_notification_state_returns_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    state = load_notification_state("home-1")
    assert state.warrantyNotified == {}
    assert state.lastPushDigestDate is None


def test_save_and_load_notification_state_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_notification_state("home-1", NotificationState(
        warrantyNotified={"item-1": "2026-08-01T00:00:00Z"},
        lastPushDigestDate="2026-07-06",
    ))
    state = load_notification_state("home-1")
    assert state.warrantyNotified == {"item-1": "2026-08-01T00:00:00Z"}
    assert state.lastPushDigestDate == "2026-07-06"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_notifications_persistence.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'myhome.models_notifications'`

- [ ] **Step 3: Write minimal implementation**

Create `packages/backend/src/myhome/models_notifications.py`:

```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class Notification(BaseModel):
    type: Literal["chore", "low_stock", "warranty"]
    refId: str
    title: str
    detail: str
    severity: Literal["info", "warning", "critical"]


class NotificationState(BaseModel):
    version: int = 1
    warrantyNotified: dict[str, str] = {}
    lastPushDigestDate: str | None = None
```

Create `packages/backend/src/myhome/persistence_notifications.py`:

```python
import json
import os
from pathlib import Path

from .models_notifications import NotificationState


def _home_dir(home_id: str) -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "homes" / home_id


def _state_file(home_id: str) -> Path:
    return _home_dir(home_id) / "notifications_state.json"


def load_notification_state(home_id: str) -> NotificationState:
    path = _state_file(home_id)
    if not path.exists():
        return NotificationState()
    with path.open() as f:
        return NotificationState.model_validate(json.load(f))


def save_notification_state(home_id: str, state: NotificationState) -> None:
    path = _state_file(home_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(state.model_dump(), f, indent=2)
    tmp.replace(path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_notifications_persistence.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/models_notifications.py packages/backend/src/myhome/persistence_notifications.py packages/backend/tests/test_notifications_persistence.py
git commit -m "feat: add notification state model and persistence"
```

---

## Task 4: `compute_notifications` — chore due-soon/overdue

**Files:**
- Create: `packages/backend/src/myhome/notifications.py`
- Test: `packages/backend/tests/test_notifications.py`

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_notifications.py`:

```python
from datetime import datetime, timedelta, timezone

from myhome.models_chores import Assignment, Chore, ChoreDocument
from myhome.notifications import _chore_notifications


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_chore_notifications_includes_assignment_within_threshold():
    now = datetime.now(timezone.utc)
    doc = ChoreDocument(
        chores=[Chore(id="c1", name="Sweep", emoji="🧹", periodDays=10, nextDueDate=_iso(now))],
        assignments=[Assignment(id="a1", choreId="c1", nextDueDate=_iso(now + timedelta(days=2)))],
    )
    results = _chore_notifications(doc, threshold=0.25)
    assert len(results) == 1
    assert results[0].type == "chore"
    assert results[0].refId == "c1"
    assert results[0].severity == "warning"


def test_chore_notifications_excludes_assignment_outside_threshold():
    now = datetime.now(timezone.utc)
    doc = ChoreDocument(
        chores=[Chore(id="c1", name="Sweep", emoji="🧹", periodDays=10, nextDueDate=_iso(now))],
        assignments=[Assignment(id="a1", choreId="c1", nextDueDate=_iso(now + timedelta(days=9)))],
    )
    results = _chore_notifications(doc, threshold=0.25)
    assert results == []


def test_chore_notifications_marks_overdue_as_critical():
    now = datetime.now(timezone.utc)
    doc = ChoreDocument(
        chores=[Chore(id="c1", name="Sweep", emoji="🧹", periodDays=10, nextDueDate=_iso(now))],
        assignments=[Assignment(id="a1", choreId="c1", nextDueDate=_iso(now - timedelta(days=1)))],
    )
    results = _chore_notifications(doc, threshold=0.25)
    assert len(results) == 1
    assert results[0].severity == "critical"
    assert "overdue" in results[0].detail


def test_chore_notifications_dedupes_by_chore_keeping_most_urgent():
    now = datetime.now(timezone.utc)
    doc = ChoreDocument(
        chores=[Chore(id="c1", name="Sweep", emoji="🧹", periodDays=10, nextDueDate=_iso(now))],
        assignments=[
            Assignment(id="a1", choreId="c1", nextDueDate=_iso(now + timedelta(days=8))),
            Assignment(id="a2", choreId="c1", nextDueDate=_iso(now - timedelta(days=1))),
        ],
    )
    results = _chore_notifications(doc, threshold=0.25)
    assert len(results) == 1
    assert results[0].severity == "critical"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_notifications.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'myhome.notifications'`

- [ ] **Step 3: Write minimal implementation**

Create `packages/backend/src/myhome/notifications.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone

from .models_chores import ChoreDocument
from .models_consumables import ConsumableDocument
from .models_inventory import InventoryDocument
from .models_notifications import Notification, NotificationState


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _format_due(now: datetime, due: datetime) -> str:
    days = (due.date() - now.date()).days
    if days < 0:
        return f"{-days}d overdue"
    if days == 0:
        return "Due today"
    if days == 1:
        return "Due tomorrow"
    return f"In {days}d"


def _chore_notifications(doc: ChoreDocument, threshold: float) -> list[Notification]:
    now = datetime.now(timezone.utc)
    best: dict[str, tuple[float, datetime]] = {}
    for a in doc.assignments:
        if not a.nextDueDate:
            continue
        chore = next((c for c in doc.chores if c.id == a.choreId), None)
        if chore is None or chore.periodDays <= 0:
            continue
        due = _parse_iso(a.nextDueDate)
        period_seconds = chore.periodDays * 86400
        pct = max(0.0, min(1.0, (due - now).total_seconds() / period_seconds))
        if chore.id not in best or pct < best[chore.id][0]:
            best[chore.id] = (pct, due)

    results: list[Notification] = []
    for chore in doc.chores:
        entry = best.get(chore.id)
        if entry is None or entry[0] > threshold:
            continue
        pct, due = entry
        overdue = due < now
        results.append(Notification(
            type="chore",
            refId=chore.id,
            title=chore.name,
            detail=_format_due(now, due),
            severity="critical" if overdue else "warning",
        ))
    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_notifications.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/notifications.py packages/backend/tests/test_notifications.py
git commit -m "feat: compute chore due-soon/overdue notifications"
```

---

## Task 5: `compute_notifications` — low stock

**Files:**
- Modify: `packages/backend/src/myhome/notifications.py`
- Test: `packages/backend/tests/test_notifications.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_notifications.py`:

```python
from myhome.models_consumables import Consumable, ConsumableDocument
from myhome.notifications import _low_stock_notifications


def test_low_stock_notifications_flags_low_and_empty_but_not_ok():
    doc = ConsumableDocument(consumables=[
        Consumable(id="co1", name="Soap", quantity=5, minQuantity=1),
        Consumable(id="co2", name="Salt", quantity=1, minQuantity=2),
        Consumable(id="co3", name="Sugar", quantity=0, minQuantity=1),
    ])
    results = _low_stock_notifications(doc)
    ids = {n.refId for n in results}
    assert ids == {"co2", "co3"}
    empty = next(n for n in results if n.refId == "co3")
    assert empty.severity == "critical"
    low = next(n for n in results if n.refId == "co2")
    assert low.severity == "warning"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_notifications.py -v -k low_stock`
Expected: FAIL with `ImportError: cannot import name '_low_stock_notifications'`

- [ ] **Step 3: Write minimal implementation**

Add to `packages/backend/src/myhome/notifications.py`:

```python
def _low_stock_notifications(doc: ConsumableDocument) -> list[Notification]:
    results: list[Notification] = []
    for c in doc.consumables:
        if c.quantity <= 0:
            results.append(Notification(
                type="low_stock", refId=c.id, title=c.name,
                detail="Out of stock", severity="critical",
            ))
        elif c.quantity <= c.minQuantity:
            results.append(Notification(
                type="low_stock", refId=c.id, title=c.name,
                detail=f"Low stock: {c.quantity} {c.unit} left", severity="warning",
            ))
    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_notifications.py -v -k low_stock`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/notifications.py packages/backend/tests/test_notifications.py
git commit -m "feat: compute low-stock notifications"
```

---

## Task 6: `compute_notifications` — warranty (fire-once)

**Files:**
- Modify: `packages/backend/src/myhome/notifications.py`
- Test: `packages/backend/tests/test_notifications.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_notifications.py`:

```python
from myhome.models_inventory import InventoryDocument, InventoryItem
from myhome.models_notifications import NotificationState
from myhome.notifications import _warranty_notifications


def _iso_days_from_now(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_warranty_notifications_fires_once_then_suppresses():
    expiry = _iso_days_from_now(10)
    doc = InventoryDocument(items=[
        InventoryItem(id="i1", name="TV", warrantyExpiryDate=expiry),
    ])
    state = NotificationState()

    fired, new_state = _warranty_notifications(doc, days_threshold=30, state=state)
    assert len(fired) == 1
    assert fired[0].refId == "i1"
    assert new_state.warrantyNotified["i1"] == expiry

    fired_again, unchanged_state = _warranty_notifications(doc, days_threshold=30, state=new_state)
    assert fired_again == []
    assert unchanged_state == new_state


def test_warranty_notifications_refires_when_expiry_date_changes():
    doc = InventoryDocument(items=[
        InventoryItem(id="i1", name="TV", warrantyExpiryDate=_iso_days_from_now(10)),
    ])
    state = NotificationState(warrantyNotified={"i1": "2020-01-01T00:00:00Z"})
    fired, new_state = _warranty_notifications(doc, days_threshold=30, state=state)
    assert len(fired) == 1
    assert new_state.warrantyNotified["i1"] != "2020-01-01T00:00:00Z"


def test_warranty_notifications_ignores_items_outside_threshold():
    doc = InventoryDocument(items=[
        InventoryItem(id="i1", name="TV", warrantyExpiryDate=_iso_days_from_now(90)),
    ])
    fired, new_state = _warranty_notifications(doc, days_threshold=30, state=NotificationState())
    assert fired == []
    assert new_state == NotificationState()


def test_warranty_notifications_ignores_items_with_no_expiry_date():
    doc = InventoryDocument(items=[InventoryItem(id="i1", name="Ladder")])
    fired, new_state = _warranty_notifications(doc, days_threshold=30, state=NotificationState())
    assert fired == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_notifications.py -v -k warranty`
Expected: FAIL with `ImportError: cannot import name '_warranty_notifications'`

- [ ] **Step 3: Write minimal implementation**

Add to `packages/backend/src/myhome/notifications.py`:

```python
def _warranty_notifications(
    doc: InventoryDocument, days_threshold: int, state: NotificationState,
) -> tuple[list[Notification], NotificationState]:
    now = datetime.now(timezone.utc)
    notified = dict(state.warrantyNotified)
    fired: list[Notification] = []
    changed = False

    for item in doc.items:
        if not item.warrantyExpiryDate:
            continue
        if notified.get(item.id) == item.warrantyExpiryDate:
            continue
        expiry = _parse_iso(item.warrantyExpiryDate)
        days_left = (expiry.date() - now.date()).days
        if days_left > days_threshold:
            continue
        detail = "Warranty expired" if days_left < 0 else f"Warranty expires in {days_left}d"
        fired.append(Notification(
            type="warranty", refId=item.id, title=item.name, detail=detail, severity="info",
        ))
        notified[item.id] = item.warrantyExpiryDate
        changed = True

    new_state = state.model_copy(update={"warrantyNotified": notified}) if changed else state
    return fired, new_state
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_notifications.py -v -k warranty`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/notifications.py packages/backend/tests/test_notifications.py
git commit -m "feat: compute fire-once warranty notifications"
```

---

## Task 7: `compute_notifications` orchestration + `GET /notifications` route

**Files:**
- Modify: `packages/backend/src/myhome/notifications.py`
- Create: `packages/backend/src/myhome/routes/notifications.py`
- Modify: `packages/backend/src/myhome/main.py`
- Test: `packages/backend/tests/test_notifications.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_notifications.py`:

```python
def test_get_notifications_route_combines_all_three_categories(client, home_id):
    client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep", "emoji": "🧹", "periodDays": 10,
        "nextDueDate": (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    client.post(f"/api/homes/{home_id}/consumables", json={
        "name": "Salt", "quantity": 0, "minQuantity": 1,
    })
    client.post(f"/api/homes/{home_id}/inventory/items", json={
        "name": "TV", "warrantyExpiryDate": (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })

    resp = client.get(f"/api/homes/{home_id}/notifications")
    assert resp.status_code == 200
    types = {n["type"] for n in resp.json()}
    assert types == {"chore", "low_stock", "warranty"}


def test_get_notifications_route_returns_empty_when_disabled(client, home_id):
    from myhome.persistence_settings import load_settings, save_settings
    doc = load_settings(home_id)
    doc.notifications.enabled = False
    save_settings(home_id, doc)

    client.post(f"/api/homes/{home_id}/consumables", json={"name": "Salt", "quantity": 0, "minQuantity": 1})
    resp = client.get(f"/api/homes/{home_id}/notifications")
    assert resp.json() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_notifications.py -v -k get_notifications_route`
Expected: FAIL with 404 (no such route)

- [ ] **Step 3: Write minimal implementation**

Add to `packages/backend/src/myhome/notifications.py` (imports at top, function at bottom):

```python
from .persistence_chores import load_chores
from .persistence_consumables import load_consumables
from .persistence_inventory import load_inventory
from .persistence_notifications import load_notification_state, save_notification_state
from .persistence_settings import load_settings
```

```python
def compute_notifications(home_id: str) -> list[Notification]:
    settings = load_settings(home_id).notifications
    if not settings.enabled:
        return []

    state = load_notification_state(home_id)
    chores_doc = load_chores(home_id)
    consumables_doc = load_consumables(home_id)
    inventory_doc = load_inventory(home_id)

    results: list[Notification] = []
    results += _chore_notifications(chores_doc, settings.choresDueSoonThreshold)
    results += _low_stock_notifications(consumables_doc)
    fired, updated_state = _warranty_notifications(
        inventory_doc, settings.warrantyDaysThreshold, state,
    )
    results += fired
    if updated_state != state:
        save_notification_state(home_id, updated_state)
    return results
```

Create `packages/backend/src/myhome/routes/notifications.py`:

```python
from fastapi import APIRouter

from ..models_notifications import Notification
from ..notifications import compute_notifications

router = APIRouter()


@router.get("/api/homes/{home_id}/notifications", response_model=list[Notification])
def get_notifications(home_id: str) -> list[Notification]:
    return compute_notifications(home_id)
```

In `packages/backend/src/myhome/main.py`, add `notifications` to the routes import and register the router:

```python
from .routes import auth, backup, chores, consumables, costs, ha, homes, house, inventory, kb, mcp_config, notifications, settings, svg, works
```

```python
app.include_router(notifications.router)
```

Add this line near the other `app.include_router(...)` calls, e.g. right after `app.include_router(consumables.router)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_notifications.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/notifications.py packages/backend/src/myhome/routes/notifications.py packages/backend/src/myhome/main.py packages/backend/tests/test_notifications.py
git commit -m "feat: add GET /api/homes/{home_id}/notifications route"
```

---

## Task 8: `call_ha_service` helper

**Files:**
- Modify: `packages/backend/src/myhome/routes/ha.py`
- Test: `packages/backend/tests/test_ha.py` (new)

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_ha.py`:

```python
import pytest
import respx
from httpx import Response

from myhome.routes.ha import call_ha_service


async def test_call_ha_service_posts_to_correct_url_and_payload(monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    with respx.mock:
        route = respx.post("http://supervisor/core/api/services/notify/mobile_app_pixel").mock(
            return_value=Response(200, json={"ok": True})
        )
        await call_ha_service("notify", "mobile_app_pixel", {"message": "hello"})
        assert route.called
        request = route.calls[0].request
        assert request.headers["Authorization"] == "Bearer test-token"
        import json as _json
        assert _json.loads(request.content) == {"message": "hello"}


async def test_call_ha_service_raises_without_token(monkeypatch):
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        await call_ha_service("notify", "mobile_app_pixel", {"message": "hello"})


async def test_call_ha_service_raises_on_http_error(monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    with respx.mock:
        respx.post("http://supervisor/core/api/services/notify/mobile_app_pixel").mock(
            return_value=Response(500)
        )
        with pytest.raises(Exception):
            await call_ha_service("notify", "mobile_app_pixel", {"message": "hello"})
```

This project's `pyproject.toml` already sets `[tool.pytest.ini_options] asyncio_mode = "auto"` with `pytest-asyncio` installed, so plain `async def test_...` functions (no `@pytest.mark.asyncio` needed) are picked up and run automatically — no config changes required.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_ha.py -v`
Expected: FAIL with `ImportError: cannot import name 'call_ha_service'`

- [ ] **Step 3: Write minimal implementation**

Add to `packages/backend/src/myhome/routes/ha.py`:

```python
async def call_ha_service(domain: str, service: str, data: dict) -> None:
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise RuntimeError("SUPERVISOR_TOKEN not set")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_HA_BASE}/services/{domain}/{service}",
            headers=_auth_headers(token),
            json=data,
            timeout=5.0,
        )
        resp.raise_for_status()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_ha.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/ha.py packages/backend/tests/test_ha.py
git commit -m "feat: add call_ha_service helper for outbound HA service calls"
```

---

## Task 9: Notification digest scheduler

**Files:**
- Create: `packages/backend/src/myhome/notification_scheduler.py`
- Test: `packages/backend/tests/test_notification_scheduler.py`

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_notification_scheduler.py`:

```python
from datetime import datetime, timedelta, timezone

import respx
from httpx import Response

from myhome.notification_scheduler import check_and_send_digests
from myhome.persistence_notifications import load_notification_state
from myhome.persistence_settings import load_settings, save_settings


async def test_check_and_send_digests_skips_home_with_push_disabled(client, home_id):
    await check_and_send_digests(now=datetime.now(timezone.utc))
    # No assertion needed beyond "doesn't raise" -- push is disabled by default.
    state = load_notification_state(home_id)
    assert state.lastPushDigestDate is None


async def test_check_and_send_digests_sends_and_marks_date(client, home_id, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    doc = load_settings(home_id)
    doc.notifications.haPushEnabled = True
    doc.notifications.haNotifyService = "notify.mobile_app_pixel"
    doc.notifications.haPushTime = "08:00"
    save_settings(home_id, doc)
    client.post(f"/api/homes/{home_id}/consumables", json={"name": "Salt", "quantity": 0, "minQuantity": 1})

    now = datetime(2026, 7, 6, 9, 0, tzinfo=timezone.utc)
    with respx.mock:
        route = respx.post("http://supervisor/core/api/services/notify/mobile_app_pixel").mock(
            return_value=Response(200)
        )
        await check_and_send_digests(now=now)
        assert route.called

    state = load_notification_state(home_id)
    assert state.lastPushDigestDate == "2026-07-06"


async def test_check_and_send_digests_skips_before_configured_time(client, home_id, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    doc = load_settings(home_id)
    doc.notifications.haPushEnabled = True
    doc.notifications.haNotifyService = "notify.mobile_app_pixel"
    doc.notifications.haPushTime = "20:00"
    save_settings(home_id, doc)

    now = datetime(2026, 7, 6, 9, 0, tzinfo=timezone.utc)
    with respx.mock:
        route = respx.post("http://supervisor/core/api/services/notify/mobile_app_pixel").mock(
            return_value=Response(200)
        )
        await check_and_send_digests(now=now)
        assert not route.called
    assert load_notification_state(home_id).lastPushDigestDate is None


async def test_check_and_send_digests_does_not_mark_date_on_ha_failure(client, home_id, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    doc = load_settings(home_id)
    doc.notifications.haPushEnabled = True
    doc.notifications.haNotifyService = "notify.mobile_app_pixel"
    doc.notifications.haPushTime = "08:00"
    save_settings(home_id, doc)
    client.post(f"/api/homes/{home_id}/consumables", json={"name": "Salt", "quantity": 0, "minQuantity": 1})

    now = datetime(2026, 7, 6, 9, 0, tzinfo=timezone.utc)
    with respx.mock:
        respx.post("http://supervisor/core/api/services/notify/mobile_app_pixel").mock(
            return_value=Response(500)
        )
        await check_and_send_digests(now=now)
    assert load_notification_state(home_id).lastPushDigestDate is None


async def test_check_and_send_digests_skips_already_sent_today(client, home_id, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    doc = load_settings(home_id)
    doc.notifications.haPushEnabled = True
    doc.notifications.haNotifyService = "notify.mobile_app_pixel"
    doc.notifications.haPushTime = "08:00"
    save_settings(home_id, doc)

    now = datetime(2026, 7, 6, 9, 0, tzinfo=timezone.utc)
    with respx.mock:
        route = respx.post("http://supervisor/core/api/services/notify/mobile_app_pixel").mock(
            return_value=Response(200)
        )
        await check_and_send_digests(now=now)
        assert route.call_count == 1
        # Second run same day: no items changed, no HA call expected because
        # lastPushDigestDate already matches today.
        await check_and_send_digests(now=now + timedelta(hours=1))
        assert route.call_count == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_notification_scheduler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'myhome.notification_scheduler'`

- [ ] **Step 3: Write minimal implementation**

Create `packages/backend/src/myhome/notification_scheduler.py`:

```python
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from .notifications import compute_notifications
from .persistence_homes import load_homes
from .persistence_notifications import load_notification_state, save_notification_state
from .persistence_settings import load_settings
from .routes.ha import call_ha_service

log = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60


def _format_digest(notifications) -> str:
    chores = sum(1 for n in notifications if n.type == "chore")
    low_stock = sum(1 for n in notifications if n.type == "low_stock")
    warranty = sum(1 for n in notifications if n.type == "warranty")
    parts = []
    if chores:
        parts.append(f"{chores} chore{'s' if chores != 1 else ''} due/overdue")
    if low_stock:
        parts.append(f"{low_stock} item{'s' if low_stock != 1 else ''} low on stock")
    if warranty:
        parts.append(f"{warranty} warranty notice{'s' if warranty != 1 else ''}")
    return ", ".join(parts) if parts else "No notifications"


async def check_and_send_digests(now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    today = now.date().isoformat()
    current_time = now.strftime("%H:%M")

    for home in load_homes().homes:
        settings = load_settings(home.id).notifications
        if not settings.haPushEnabled or not settings.haNotifyService:
            continue
        state = load_notification_state(home.id)
        if state.lastPushDigestDate == today:
            continue
        if current_time < settings.haPushTime:
            continue

        notifications = compute_notifications(home.id)
        if notifications:
            try:
                domain, service = settings.haNotifyService.split(".", 1)
            except ValueError:
                log.warning("Malformed haNotifyService %r for home %s", settings.haNotifyService, home.id)
                continue
            try:
                await call_ha_service(domain, service, {"message": _format_digest(notifications)})
            except (httpx.HTTPError, RuntimeError):
                log.warning("HA push digest failed for home %s, will retry", home.id)
                continue

        # Reload: compute_notifications may have persisted a warrantyNotified update.
        state = load_notification_state(home.id)
        state.lastPushDigestDate = today
        save_notification_state(home.id, state)


async def notification_digest_loop() -> None:
    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        try:
            await check_and_send_digests()
        except Exception:
            log.exception("notification digest loop iteration failed")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_notification_scheduler.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/notification_scheduler.py packages/backend/tests/test_notification_scheduler.py
git commit -m "feat: add HA push digest background scheduler"
```

---

## Task 10: Wire scheduler into app lifespan

**Files:**
- Modify: `packages/backend/src/myhome/main.py`

There is no new isolated test for this task: `check_and_send_digests` is already fully covered in Task 9, and "does the app still boot" is already exercised by every other test in the suite via the `client` fixture (which constructs `TestClient(app)`, running the full lifespan on each test). This task's own verification is Step 2 below: run the full suite and confirm nothing broke.

- [ ] **Step 1: Write the implementation**

In `packages/backend/src/myhome/main.py`:

```python
import asyncio
import os
import secrets
```

```python
from .notification_scheduler import notification_digest_loop
```

```python
@asynccontextmanager
async def _lifespan(app: FastAPI):
    # The MCP session manager's background task group is NOT started just by
    # mounting mcp_asgi_app -- Starlette never forwards ASGI lifespan events into
    # mounted sub-apps, so it must be entered here explicitly.
    async with mcp.session_manager.run():
        digest_task = asyncio.create_task(notification_digest_loop())
        try:
            yield
        finally:
            digest_task.cancel()
```

- [ ] **Step 2: Run the full suite to confirm nothing broke**

Run: `cd packages/backend && pytest tests/ -v`
Expected: PASS (full suite — confirms the lifespan change doesn't break app startup for any existing test)

- [ ] **Step 3: Commit**

```bash
git add packages/backend/src/myhome/main.py
git commit -m "feat: start notification digest scheduler on app startup"
```

---

## Task 11: Frontend `notificationStore`

**Files:**
- Create: `packages/editor/src/lib/notificationStore.svelte.ts`
- Test: `packages/editor/test/notificationStore.test.ts`

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/notificationStore.test.ts`:

```ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { createNotificationStore } from "../src/lib/notificationStore.svelte";

afterEach(() => vi.unstubAllGlobals());

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

describe("createNotificationStore", () => {
  it("fetches notifications for the current home on init", async () => {
    const sample = [
      { type: "chore", refId: "c1", title: "Sweep", detail: "Due today", severity: "warning" },
    ];
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => sample }));
    const store = createNotificationStore(() => "home-1");
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.notifications).toEqual(sample);
    expect(fetch).toHaveBeenCalledWith("/api/homes/home-1/notifications");
  });

  it("returns an empty list without fetching when there is no active home", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    const store = createNotificationStore(() => null);
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.notifications).toEqual([]);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("refresh() re-fetches", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);
    const store = createNotificationStore(() => "home-1");
    await tick();
    await store.refresh();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("sets loadError on a failed fetch", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    const store = createNotificationStore(() => "home-1");
    await tick();
    expect(store.loadError).toContain("500");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run notificationStore.test.ts`
Expected: FAIL with a module resolution error

- [ ] **Step 3: Write minimal implementation**

Create `packages/editor/src/lib/notificationStore.svelte.ts`:

```ts
export interface Notification {
  type: "chore" | "low_stock" | "warranty";
  refId: string;
  title: string;
  detail: string;
  severity: "info" | "warning" | "critical";
}

export function createNotificationStore(getHomeId: () => string | null = () => null) {
  const notifications = $state<Notification[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) { loaded = true; return; }
    try {
      const resp = await fetch(`/api/homes/${homeId}/notifications`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const list: Notification[] = await resp.json();
      notifications.length = 0;
      for (const n of list) notifications.push(n);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  init();

  return {
    get notifications() { return notifications as Notification[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    refresh: init,
    reload: init,
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run notificationStore.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/notificationStore.svelte.ts packages/editor/test/notificationStore.test.ts
git commit -m "feat: add notificationStore"
```

---

## Task 12: `NotificationBell` component (bell + dropdown)

**Files:**
- Create: `packages/editor/src/lib/components/NotificationBell.svelte`
- Test: `packages/editor/test/NotificationBell.test.ts`

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/NotificationBell.test.ts`:

```ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import NotificationBell from "../src/lib/components/NotificationBell.svelte";
import { createNotificationStore } from "../src/lib/notificationStore.svelte";

const sample = [
  { type: "chore", refId: "c1", title: "Sweep", detail: "Due today", severity: "warning" },
  { type: "low_stock", refId: "co1", title: "Salt", detail: "Out of stock", severity: "critical" },
  { type: "warranty", refId: "i1", title: "TV", detail: "Warranty expires in 5d", severity: "info" },
];

afterEach(() => vi.unstubAllGlobals());

async function makeTick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

function makeStore() {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => sample }));
  return createNotificationStore(() => "home-1");
}

describe("NotificationBell", () => {
  it("shows a badge with the notification count", async () => {
    const store = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(NotificationBell, { target, props: { store, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".notif-badge")!.textContent).toBe("3");

    unmount(comp);
    target.remove();
  });

  it("opens the dropdown grouped by type on click and calls onnavigate on selection", async () => {
    const store = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onnavigate = vi.fn();
    const comp = mount(NotificationBell, { target, props: { store, onnavigate } });
    await tick();
    flushSync();

    (target.querySelector(".notif-bell") as HTMLButtonElement).click();
    await tick();
    flushSync();

    const labels = Array.from(target.querySelectorAll(".notif-group-label")).map((el) => el.textContent);
    expect(labels).toEqual(["Chores", "Low Stock", "Warranty"]);

    (target.querySelector(".notif-item") as HTMLButtonElement).click();
    expect(onnavigate).toHaveBeenCalledWith(sample[0]);
    flushSync();
    expect(target.querySelector(".notif-dropdown")).toBeNull();

    unmount(comp);
    target.remove();
  });

  it("closes the dropdown on outside click", async () => {
    const store = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(NotificationBell, { target, props: { store, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    (target.querySelector(".notif-bell") as HTMLButtonElement).click();
    await tick();
    flushSync();
    expect(target.querySelector(".notif-dropdown")).not.toBeNull();

    document.body.click();
    await tick();
    flushSync();
    expect(target.querySelector(".notif-dropdown")).toBeNull();

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run NotificationBell.test.ts`
Expected: FAIL with a module resolution error

- [ ] **Step 3: Write minimal implementation**

Create `packages/editor/src/lib/components/NotificationBell.svelte`:

```svelte
<!-- packages/editor/src/lib/components/NotificationBell.svelte -->
<script lang="ts">
  import type { createNotificationStore, Notification } from "../notificationStore.svelte";

  type NotificationStore = ReturnType<typeof createNotificationStore>;

  interface Props {
    store: NotificationStore;
    onnavigate: (n: Notification) => void;
  }
  let { store, onnavigate }: Props = $props();

  let dropdownOpen = $state(false);

  const GROUP_LABELS: Record<Notification["type"], string> = {
    chore: "Chores",
    low_stock: "Low Stock",
    warranty: "Warranty",
  };
  const GROUP_ORDER: Notification["type"][] = ["chore", "low_stock", "warranty"];

  const groups = $derived.by(() => {
    const byType = new Map<string, Notification[]>();
    for (const n of store.notifications) {
      if (!byType.has(n.type)) byType.set(n.type, []);
      byType.get(n.type)!.push(n);
    }
    return GROUP_ORDER
      .filter((t) => byType.has(t))
      .map((t) => ({ type: t, label: GROUP_LABELS[t], items: byType.get(t)! }));
  });

  function handleClick(): void {
    dropdownOpen = !dropdownOpen;
    if (dropdownOpen) store.refresh();
  }

  function handleClickOutside(e: MouseEvent): void {
    if (!(e.target as HTMLElement).closest(".notif-bell-wrap")) dropdownOpen = false;
  }

  function select(n: Notification): void {
    dropdownOpen = false;
    onnavigate(n);
  }
</script>

<svelte:window onclick={handleClickOutside} />

<div class="notif-bell-wrap">
  <button class="icon-btn notif-bell" title="Notifications" onclick={handleClick}>
    🔔
    {#if store.notifications.length > 0}
      <span class="notif-badge">{store.notifications.length}</span>
    {/if}
  </button>

  {#if dropdownOpen}
    <div class="notif-dropdown">
      {#if store.notifications.length === 0}
        <div class="notif-empty">No notifications</div>
      {/if}
      {#each groups as group (group.type)}
        <div class="notif-group-label">{group.label}</div>
        {#each group.items as n (n.type + n.refId)}
          <button class="notif-item" onclick={() => select(n)}>
            <div class="notif-item-title">{n.title}</div>
            <div class="notif-item-detail">{n.detail}</div>
          </button>
        {/each}
      {/each}
    </div>
  {/if}
</div>

<style>
  .notif-bell-wrap { position: relative; }
  .notif-bell { position: relative; }
  .notif-badge {
    position: absolute; top: 2px; right: 2px;
    background: #f44336; color: white;
    font-size: 10px; line-height: 1; font-weight: 600;
    border-radius: 999px; padding: 2px 5px; min-width: 14px; text-align: center;
  }
  .notif-dropdown {
    position: absolute; top: calc(100% + 4px); right: 0;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 200; padding: 4px; min-width: 260px; max-height: 360px; overflow-y: auto;
  }
  .notif-empty { padding: 16px; font-size: 12px; color: var(--text-faint); text-align: center; }
  .notif-group-label {
    font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
    color: var(--text-faint); padding: 8px 10px 4px;
  }
  .notif-item {
    display: block; width: 100%; text-align: left;
    padding: 8px 10px; border: none; background: none; border-radius: var(--radius-md); cursor: pointer;
  }
  .notif-item:hover { background: var(--surface-hover); }
  .notif-item-title { font-size: 13px; color: var(--text); font-weight: 500; }
  .notif-item-detail { font-size: 11px; color: var(--text-faint); margin-top: 1px; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run NotificationBell.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/NotificationBell.svelte packages/editor/test/NotificationBell.test.ts
git commit -m "feat: add NotificationBell topbar component"
```

---

## Task 13: Wire `NotificationBell` into `App.svelte`

**Files:**
- Modify: `packages/editor/src/App.svelte`

There is no isolated automated test for this task — `App.svelte` is not covered by component tests in this codebase (confirmed: `handleSearchSelect` and the `CommandPalette` wiring it mirrors have no dedicated `App.svelte` test either). Verify manually per Step 4.

- [ ] **Step 1: Add the store and import**

In `packages/editor/src/App.svelte`, near the other store imports (after the `createConsumableStore` import):

```ts
import { createNotificationStore } from "./lib/notificationStore.svelte";
import type { Notification } from "./lib/notificationStore.svelte";
import NotificationBell from "./lib/components/NotificationBell.svelte";
```

Near `const consumableStore = createConsumableStore(getHomeId);`:

```ts
const notificationStore = createNotificationStore(getHomeId);
```

Near the block that reloads other stores on home switch (the block containing `choreStore.reload(); inventoryStore.reload(); settingsStore.reload();` and `consumableStore.reload();`), add:

```ts
notificationStore.reload();
```

- [ ] **Step 2: Add the navigation handler**

Near `handleSearchSelect`, add:

```ts
function handleNotificationSelect(n: Notification): void {
  if (n.type === "chore") { selectedChoreId = n.refId; window.location.hash = "#/chores"; }
  else if (n.type === "low_stock") { selectedConsumableId = n.refId; window.location.hash = "#/consumables"; }
  else if (n.type === "warranty") { selectedInventoryItemId = n.refId; window.location.hash = "#/inventory"; }
}
```

- [ ] **Step 3: Render the bell in the topbar**

In the `<header class="topbar">` block, add the bell next to the existing search button:

```svelte
<button class="icon-btn search-btn" title="Search (Ctrl+K)" onclick={() => { commandPaletteOpen = true; }}>🔍</button>
<NotificationBell store={notificationStore} onnavigate={handleNotificationSelect} />
```

- [ ] **Step 4: Manually verify**

Run: `cd packages/editor && npm run dev` (or the project's existing dev-server command), log in, and:
1. Create a chore with a due date in the past — confirm the bell badge shows `1` and the dropdown lists it under "Chores"; clicking it navigates to `#/chores` and opens that chore.
2. Set a consumable's quantity to 0 — confirm it appears under "Low Stock" and clicking navigates to `#/consumables`.
3. Set an inventory item's warranty expiry date to within 30 days — confirm it appears under "Warranty" and clicking navigates to `#/inventory`; reload the page and confirm it does **not** reappear (fire-once).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/App.svelte
git commit -m "feat: wire NotificationBell into topbar"
```

---

## Task 14: `settingsStore` support for `NotificationSettings`

**Files:**
- Modify: `packages/editor/src/lib/settingsStore.svelte.ts`
- Create: `packages/editor/test/settingsStore.test.ts` (no test file for this store exists yet — `SettingsPage.test.ts` only exercises the component with a hand-rolled mock store, never the real `createSettingsStore`)

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/settingsStore.test.ts`:

```ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { createSettingsStore } from "../src/lib/settingsStore.svelte";

afterEach(() => vi.unstubAllGlobals());

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

describe("createSettingsStore — notifications", () => {
  it("loads notification settings from the fetched document", async () => {
    const doc = {
      version: 1, costCategories: [], inventoryCategories: [], workCategories: [],
      suppliers: [], consumableUnits: [], consumableCategories: [],
      notifications: {
        enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
        haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
      },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }));
    const store = createSettingsStore(() => "home-1");
    await tick();
    expect(store.notificationSettings.warrantyDaysThreshold).toBe(30);
  });

  it("updateNotificationSettings PUTs to the notifications settings endpoint", async () => {
    const doc = {
      version: 1, costCategories: [], inventoryCategories: [], workCategories: [],
      suppliers: [], consumableUnits: [], consumableCategories: [],
      notifications: {
        enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
        haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
      },
    };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc });
    vi.stubGlobal("fetch", fetchMock);
    const store = createSettingsStore(() => "home-1");
    await tick();

    fetchMock.mockResolvedValue({ ok: true, status: 204, json: async () => ({}) });
    await store.updateNotificationSettings({ ...store.notificationSettings, warrantyDaysThreshold: 45 });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/homes/home-1/settings/notifications",
      expect.objectContaining({ method: "PUT" }),
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run settingsStore.test.ts`
Expected: FAIL — `store.notificationSettings` is `undefined`

- [ ] **Step 3: Write minimal implementation**

In `packages/editor/src/lib/settingsStore.svelte.ts`, add the interface:

```ts
export interface NotificationSettings {
  enabled: boolean;
  choresDueSoonThreshold: number;
  warrantyDaysThreshold: number;
  haPushEnabled: boolean;
  haNotifyService: string | null;
  haPushTime: string;
}
```

Add `notifications: NotificationSettings;` to the `SettingsDocument` interface.

Add state, defaulted to match the backend's Pydantic defaults:

```ts
const notificationSettings = $state<NotificationSettings>({
  enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
  haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
});
```

In `init()`, after the `consumableCategories` block:

```ts
if (doc.notifications) Object.assign(notificationSettings, doc.notifications);
```

Add the update method (near `updateConsumableCategories`):

```ts
async function updateNotificationSettings(settings: NotificationSettings): Promise<void> {
  const homeId = getHomeId();
  if (!homeId) throw new Error("No active home");
  const resp = await fetch(`/api/homes/${homeId}/settings/notifications`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  await init();
}
```

Expose both in the returned object:

```ts
get notificationSettings() { return notificationSettings as NotificationSettings; },
updateNotificationSettings,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run settingsStore.test.ts`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/settingsStore.svelte.ts packages/editor/test/settingsStore.test.ts
git commit -m "feat: add NotificationSettings to settingsStore"
```

---

## Task 15: "Notifications" section in `SettingsPage.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/SettingsPage.svelte`
- Modify: `packages/editor/test/SettingsPage.test.ts`

`SettingsPage.test.ts`'s shared `makeStore()` helper (lines 5–23) returns a hand-rolled plain object, not a real `createSettingsStore` — its methods are `vi.fn()` mocks and the component reads props directly off it. This section's fields need to be added to that helper so every existing test in the file keeps constructing a store the component can fully render (the component will unconditionally read `store.notificationSettings`).

- [ ] **Step 1: Write the failing test**

First, extend `makeStore()` in `packages/editor/test/SettingsPage.test.ts` to include the new fields:

```ts
function makeStore() {
  return {
    costCategories: [],
    inventoryCategories: [],
    workCategories: [],
    suppliers: [],
    consumableUnits: [],
    consumableCategories: [],
    notificationSettings: {
      enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
      haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
    },
    loaded: true,
    loadError: null,
    updateCostCategories: vi.fn(),
    updateInventoryCategories: vi.fn(),
    updateWorkCategories: vi.fn(),
    updateSuppliers: vi.fn(),
    updateConsumableUnits: vi.fn(),
    updateConsumableCategories: vi.fn(),
    placeCostCategory: vi.fn(),
    updateNotificationSettings: vi.fn(),
  };
}
```

Then add a new `describe` block at the end of the file, mirroring the existing `describe("SettingsPage — Backup & Restore", ...)` block's structure:

```ts
describe("SettingsPage — Notifications", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    target.remove();
  });

  it("renders current settings and reflects the enabled toggle", () => {
    const store = makeStore();
    const comp = mount(SettingsPage, { target, props: { store, authStore: makeAuthStore() } });
    flushSync();

    const heading = Array.from(target.querySelectorAll("h2")).find((h) => h.textContent === "Notifications");
    expect(heading).toBeDefined();
    expect((target.querySelector(".notif-enable-toggle") as HTMLInputElement).checked).toBe(true);

    unmount(comp);
  });

  it("hides push fields until 'Send a daily digest' is checked", () => {
    const store = makeStore();
    const comp = mount(SettingsPage, { target, props: { store, authStore: makeAuthStore() } });
    flushSync();

    const labels = Array.from(target.querySelectorAll(".modal-label")).map((el) => el.textContent);
    expect(labels).not.toContain("HA notify service");

    unmount(comp);
  });

  it("saves edited settings via store.updateNotificationSettings", async () => {
    const store = makeStore();
    const comp = mount(SettingsPage, { target, props: { store, authStore: makeAuthStore() } });
    flushSync();

    const enableToggle = target.querySelector(".notif-enable-toggle") as HTMLInputElement;
    enableToggle.click();
    enableToggle.click(); // leave enabled=true, but confirms the checkbox is wired to the draft
    flushSync();

    const saveBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Save"))!;
    (saveBtn as HTMLButtonElement).click();
    await Promise.resolve();

    expect(store.updateNotificationSettings).toHaveBeenCalledWith(
      expect.objectContaining({ enabled: true, warrantyDaysThreshold: 30 }),
    );

    unmount(comp);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run SettingsPage.test.ts -t "Notifications"`
Expected: FAIL — `store.notificationSettings` is `undefined` when `SettingsPage.svelte` renders, so mounting throws

- [ ] **Step 3: Write minimal implementation**

In `packages/editor/src/lib/components/SettingsPage.svelte`, add script state (near the other section-local state blocks):

```ts
let notifDraft = $state({ ...store.notificationSettings });
let notifChoresThresholdStr = $state(String(store.notificationSettings.choresDueSoonThreshold));
let notifWarrantyDaysStr = $state(String(store.notificationSettings.warrantyDaysThreshold));
let notifSynced = $state(false);
let notifError = $state<string | null>(null);
let notifSaving = $state(false);

$effect(() => {
  if (store.loaded && !notifSynced) {
    notifDraft = { ...store.notificationSettings };
    notifChoresThresholdStr = String(store.notificationSettings.choresDueSoonThreshold);
    notifWarrantyDaysStr = String(store.notificationSettings.warrantyDaysThreshold);
    notifSynced = true;
  }
});

async function saveNotificationSettings(): Promise<void> {
  notifError = null;
  notifSaving = true;
  try {
    await store.updateNotificationSettings({
      ...notifDraft,
      choresDueSoonThreshold: parseFloat(notifChoresThresholdStr) || 0,
      warrantyDaysThreshold: parseInt(notifWarrantyDaysStr, 10) || 0,
    });
  } catch (e) {
    notifError = e instanceof Error ? e.message : String(e);
  } finally {
    notifSaving = false;
  }
}
```

Add a new `<Card>` section, placed after the Consumables section and before "API Tokens" (or wherever fits the existing visual order — check the file's current section order before placing it):

```svelte
<Card>
  <div class="section-header">
    <h2>Notifications</h2>
  </div>
  <p class="section-desc">
    Surface chores due soon, low-stock consumables, and expiring warranties in
    one place, with an optional daily summary pushed to Home Assistant.
  </p>
  <label class="module-row">
    <input class="notif-enable-toggle" type="checkbox" bind:checked={notifDraft.enabled} />
    <span class="mod-label">Enable notification center</span>
  </label>
  {#if notifDraft.enabled}
    <div class="modal-form" style="margin-top: var(--space-3)">
      <div class="modal-field">
        <span class="modal-label">Chores "due soon" threshold (fraction of period remaining)</span>
        <Input type="number" bind:value={notifChoresThresholdStr} />
      </div>
      <div class="modal-field">
        <span class="modal-label">Warranty "expiring soon" window (days)</span>
        <Input type="number" bind:value={notifWarrantyDaysStr} />
      </div>
      <label class="module-row">
        <input type="checkbox" bind:checked={notifDraft.haPushEnabled} />
        <span class="mod-label">Send a daily digest via Home Assistant</span>
      </label>
      {#if notifDraft.haPushEnabled}
        <div class="modal-field">
          <span class="modal-label">HA notify service</span>
          <Input bind:value={notifDraft.haNotifyService} placeholder="e.g. notify.mobile_app_pixel" />
        </div>
        <div class="modal-field">
          <span class="modal-label">Digest time (UTC, HH:MM)</span>
          <Input bind:value={notifDraft.haPushTime} placeholder="08:00" />
        </div>
      {/if}
    </div>
  {/if}
  {#if notifError}<div class="error">{notifError}</div>{/if}
  <div class="modal-actions">
    <Button onclick={saveNotificationSettings} disabled={notifSaving}>{notifSaving ? "Saving…" : "Save"}</Button>
  </div>
</Card>
```

Note: `Input`'s `value` prop is typed `string`, so `bind:value={notifDraft.haNotifyService}` requires `haNotifyService` to be a non-null string in the draft for binding to behave — initialize the draft's copy with `haNotifyService: store.notificationSettings.haNotifyService ?? ""` instead of a raw spread, and convert back to `null` on save if empty:

```ts
notifDraft = { ...store.notificationSettings, haNotifyService: store.notificationSettings.haNotifyService ?? "" };
```

```ts
await store.updateNotificationSettings({
  ...notifDraft,
  haNotifyService: notifDraft.haNotifyService.trim() || null,
  choresDueSoonThreshold: parseFloat(notifChoresThresholdStr) || 0,
  warrantyDaysThreshold: parseInt(notifWarrantyDaysStr, 10) || 0,
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run SettingsPage.test.ts`
Expected: PASS (full file, confirming no regressions in other sections)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/SettingsPage.svelte packages/editor/test/SettingsPage.test.ts
git commit -m "feat: add Notifications settings section"
```

---

## Final Verification

- [ ] Run the full backend suite: `cd packages/backend && pytest tests/ -v` — expect all green, including the ~20 new tests added across Tasks 1–10.
- [ ] Run the full frontend suite: `cd packages/editor && npx vitest run` — expect all green, including the new tests from Tasks 11–15.
- [ ] Manually verify per Task 13 Step 4 (bell badge, dropdown grouping, navigation, warranty fire-once across a reload).
- [ ] Update `ROADMAP.md`: move "Notification center" out of "To Be Confirmed" into "Recently Completed", linking this plan and the design spec, following the same format used for OIDC/global search in the current file.
