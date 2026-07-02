# Consumables Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone consumables module that tracks household stock levels (batteries, cleaning products, etc.) with quantity history, floor-plan badges, and low-stock alerts.

**Architecture:** New standalone module following the existing inventory/chores pattern: backend gets `models_consumables.py` + `persistence_consumables.py` + `routes/consumables.py`; frontend gets `consumableStore.svelte.ts` + page/modal/overlay/popup/widget components. Settings is extended with `consumableUnits` and `consumableCategories`. The `ConsumablesPage.svelte` stub is replaced in-place.

**Tech Stack:** FastAPI + Pydantic (backend), Svelte 5 runes + TypeScript (frontend), Vitest (frontend tests), pytest + FastAPI TestClient (backend tests).

---

## File Map

**Backend — new files:**
- `packages/backend/src/myhome/models_consumables.py`
- `packages/backend/src/myhome/persistence_consumables.py`
- `packages/backend/src/myhome/routes/consumables.py`
- `packages/backend/tests/test_consumables_persistence.py`
- `packages/backend/tests/test_consumables.py`

**Backend — modified files:**
- `packages/backend/src/myhome/models_settings.py` — add `ConsumableCategory`, `consumableUnits`, `consumableCategories`
- `packages/backend/src/myhome/persistence_settings.py` — defaults load correctly
- `packages/backend/src/myhome/routes/settings.py` — two new PUT routes
- `packages/backend/src/myhome/main.py` — include consumables router
- `packages/backend/tests/test_settings.py` — add tests for new routes

**Frontend — new files:**
- `packages/editor/src/lib/consumableStore.svelte.ts`
- `packages/editor/src/lib/components/ConsumableModal.svelte`
- `packages/editor/src/lib/components/ConsumableOverlay.svelte`
- `packages/editor/src/lib/components/ConsumablePinPopup.svelte`
- `packages/editor/src/lib/components/HomeConsumablesWidget.svelte`
- `packages/editor/test/consumableStore.test.ts`
- `packages/editor/test/ConsumablesPage.test.ts`
- `packages/editor/test/ConsumableModal.test.ts`
- `packages/editor/test/HomeConsumablesWidget.test.ts`

**Frontend — modified files:**
- `packages/editor/src/lib/components/ConsumablesPage.svelte` — replace stub
- `packages/editor/src/lib/settingsStore.svelte.ts` — add consumable units/categories
- `packages/editor/src/lib/components/SettingsPage.svelte` — add consumables section
- `packages/editor/src/lib/components/LayersDropdown.svelte` — add consumables layer
- `packages/editor/src/lib/components/HomePage.svelte` — add widget
- `packages/editor/src/App.svelte` — wire store, overlay, picker, popup, route

---

## Task 1: Backend models

**Files:**
- Create: `packages/backend/src/myhome/models_consumables.py`

- [ ] **Step 1: Create the models file**

```python
# packages/backend/src/myhome/models_consumables.py
from __future__ import annotations
from pydantic import BaseModel


class ConsumablePosition(BaseModel):
    x: float
    y: float


class ConsumablePlacement(BaseModel):
    floorId: str
    roomId: str | None = None
    position: ConsumablePosition


class Consumable(BaseModel):
    id: str
    name: str
    emoji: str = "🛒"
    unit: str = "count"
    quantity: float = 0.0
    minQuantity: float = 1.0
    categoryId: str | None = None
    description: str = ""
    placement: ConsumablePlacement | None = None


class ConsumableTransaction(BaseModel):
    id: str
    consumableId: str
    delta: float         # positive = added, negative = consumed
    quantityAfter: float
    note: str = ""
    timestamp: str       # ISO 8601


class ConsumableDocument(BaseModel):
    version: int = 1
    consumables: list[Consumable] = []
    transactions: list[ConsumableTransaction] = []


class ConsumableCreate(BaseModel):
    name: str
    emoji: str = "🛒"
    unit: str = "count"
    quantity: float = 0.0
    minQuantity: float = 1.0
    categoryId: str | None = None
    description: str = ""


class ConsumableUpdate(BaseModel):
    name: str | None = None
    emoji: str | None = None
    unit: str | None = None
    minQuantity: float | None = None
    categoryId: str | None = None
    description: str | None = None


class StockUpdate(BaseModel):
    quantity: float
    note: str = ""


class ConsumablePlacementUpdate(BaseModel):
    placement: ConsumablePlacement | None = None
```

- [ ] **Step 2: Commit**

```bash
git add packages/backend/src/myhome/models_consumables.py
git commit -m "feat(consumables): add backend Pydantic models"
```

---

## Task 2: Backend persistence

**Files:**
- Create: `packages/backend/src/myhome/persistence_consumables.py`
- Create: `packages/backend/tests/test_consumables_persistence.py`

- [ ] **Step 1: Write the failing persistence tests**

```python
# packages/backend/tests/test_consumables_persistence.py
from myhome.models_consumables import (
    Consumable, ConsumableDocument, ConsumablePlacement, ConsumablePosition,
    ConsumableTransaction,
)
from myhome.persistence_consumables import load_consumables, save_consumables


def make_doc() -> ConsumableDocument:
    return ConsumableDocument(
        consumables=[
            Consumable(
                id="c1",
                name="AA Batteries",
                emoji="🔋",
                unit="count",
                quantity=6.0,
                minQuantity=4.0,
                placement=ConsumablePlacement(
                    floorId="f1",
                    roomId="r1",
                    position=ConsumablePosition(x=2.0, y=3.5),
                ),
            )
        ],
        transactions=[
            ConsumableTransaction(
                id="t1",
                consumableId="c1",
                delta=6.0,
                quantityAfter=6.0,
                note="initial stock",
                timestamp="2026-07-02T10:00:00Z",
            )
        ],
    )


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    doc = load_consumables()
    assert doc.consumables == []
    assert doc.transactions == []


def test_save_creates_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_consumables(make_doc())
    assert (tmp_path / "consumables.json").exists()


def test_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_consumables(make_doc())
    loaded = load_consumables()
    assert loaded.consumables[0].id == "c1"
    assert loaded.consumables[0].quantity == 6.0
    assert loaded.consumables[0].placement.position.x == 2.0
    assert loaded.transactions[0].delta == 6.0


def test_consumable_without_placement_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    doc = ConsumableDocument(consumables=[Consumable(id="c2", name="Soap")])
    save_consumables(doc)
    loaded = load_consumables()
    assert loaded.consumables[0].placement is None


def test_save_creates_data_dir_if_missing(tmp_path, monkeypatch):
    nested = tmp_path / "nested" / "data"
    monkeypatch.setenv("DATA_DIR", str(nested))
    save_consumables(make_doc())
    assert (nested / "consumables.json").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/backend && python -m pytest tests/test_consumables_persistence.py -v
```
Expected: `ModuleNotFoundError: No module named 'myhome.persistence_consumables'`

- [ ] **Step 3: Implement persistence**

```python
# packages/backend/src/myhome/persistence_consumables.py
import json
import os
from pathlib import Path

from .models_consumables import ConsumableDocument


def _consumables_file() -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "consumables.json"


def load_consumables() -> ConsumableDocument:
    path = _consumables_file()
    if not path.exists():
        return ConsumableDocument()
    with path.open() as f:
        return ConsumableDocument.model_validate(json.load(f))


def save_consumables(doc: ConsumableDocument) -> None:
    path = _consumables_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd packages/backend && python -m pytest tests/test_consumables_persistence.py -v
```
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/persistence_consumables.py packages/backend/tests/test_consumables_persistence.py
git commit -m "feat(consumables): add backend persistence + tests"
```

---

## Task 3: Backend routes

**Files:**
- Create: `packages/backend/src/myhome/routes/consumables.py`
- Create: `packages/backend/tests/test_consumables.py`
- Modify: `packages/backend/src/myhome/main.py`

- [ ] **Step 1: Write the failing route tests**

```python
# packages/backend/tests/test_consumables.py
import pytest
from fastapi.testclient import TestClient
from myhome.main import app
from myhome.models_consumables import Consumable, ConsumableDocument, ConsumableTransaction
from myhome.persistence_consumables import save_consumables


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return TestClient(app)


def make_doc() -> ConsumableDocument:
    return ConsumableDocument(
        consumables=[Consumable(id="c1", name="AA Batteries", emoji="🔋", unit="count", quantity=6.0, minQuantity=4.0)],
        transactions=[ConsumableTransaction(id="t1", consumableId="c1", delta=6.0, quantityAfter=6.0, timestamp="2026-07-02T10:00:00Z")],
    )


# --- GET /api/consumables ---

def test_get_consumables_empty(client):
    resp = client.get("/api/consumables")
    assert resp.status_code == 200
    data = resp.json()
    assert data["consumables"] == []
    assert data["transactions"] == []


def test_get_consumables_returns_saved(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_consumables(make_doc())
    resp = TestClient(app).get("/api/consumables")
    assert resp.status_code == 200
    assert resp.json()["consumables"][0]["id"] == "c1"


# --- POST /api/consumables ---

def test_create_consumable(client):
    payload = {"name": "Dish soap", "emoji": "🧴", "unit": "mL", "quantity": 500.0, "minQuantity": 100.0}
    resp = client.post("/api/consumables", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Dish soap"
    assert data["unit"] == "mL"
    assert data["quantity"] == 500.0
    assert "id" in data
    assert data["placement"] is None


def test_create_consumable_defaults(client):
    resp = client.post("/api/consumables", json={"name": "Batteries"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["emoji"] == "🛒"
    assert data["unit"] == "count"
    assert data["quantity"] == 0.0


# --- PUT /api/consumables/{id} ---

def test_update_consumable(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_consumables(make_doc())
    resp = TestClient(app).put("/api/consumables/c1", json={"name": "AAA Batteries", "minQuantity": 6.0})
    assert resp.status_code == 204
    data = TestClient(app).get("/api/consumables").json()
    assert data["consumables"][0]["name"] == "AAA Batteries"
    assert data["consumables"][0]["minQuantity"] == 6.0


def test_update_consumable_not_found(client):
    resp = client.put("/api/consumables/nope", json={"name": "X"})
    assert resp.status_code == 404


# --- DELETE /api/consumables/{id} ---

def test_delete_consumable(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_consumables(make_doc())
    resp = TestClient(app).delete("/api/consumables/c1")
    assert resp.status_code == 204
    data = TestClient(app).get("/api/consumables").json()
    assert data["consumables"] == []
    assert data["transactions"] == []   # cascade delete


def test_delete_consumable_not_found(client):
    resp = client.delete("/api/consumables/nope")
    assert resp.status_code == 404


# --- PUT /api/consumables/{id}/placement ---

def test_set_placement(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_consumables(make_doc())
    payload = {"placement": {"floorId": "f1", "roomId": "r1", "position": {"x": 3.0, "y": 4.0}}}
    resp = TestClient(app).put("/api/consumables/c1/placement", json=payload)
    assert resp.status_code == 204
    data = TestClient(app).get("/api/consumables").json()
    assert data["consumables"][0]["placement"]["floorId"] == "f1"


def test_clear_placement(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_consumables(make_doc())
    TestClient(app).put("/api/consumables/c1/placement", json={"placement": {"floorId": "f1", "position": {"x": 1.0, "y": 2.0}}})
    resp = TestClient(app).put("/api/consumables/c1/placement", json={"placement": None})
    assert resp.status_code == 204
    data = TestClient(app).get("/api/consumables").json()
    assert data["consumables"][0]["placement"] is None


# --- POST /api/consumables/{id}/stock ---

def test_update_stock_adds_transaction(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_consumables(make_doc())
    resp = TestClient(app).post("/api/consumables/c1/stock", json={"quantity": 10.0, "note": "restocked"})
    assert resp.status_code == 204
    data = TestClient(app).get("/api/consumables").json()
    assert data["consumables"][0]["quantity"] == 10.0
    # original t1 + new transaction
    assert len(data["transactions"]) == 2
    new_tx = next(t for t in data["transactions"] if t["id"] != "t1")
    assert new_tx["delta"] == 4.0     # 10 - 6
    assert new_tx["quantityAfter"] == 10.0
    assert new_tx["note"] == "restocked"


def test_update_stock_negative_delta(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_consumables(make_doc())
    TestClient(app).post("/api/consumables/c1/stock", json={"quantity": 2.0})
    data = TestClient(app).get("/api/consumables").json()
    new_tx = next(t for t in data["transactions"] if t["id"] != "t1")
    assert new_tx["delta"] == -4.0    # 2 - 6


def test_update_stock_not_found(client):
    resp = client.post("/api/consumables/nope/stock", json={"quantity": 5.0})
    assert resp.status_code == 404


# --- DELETE /api/consumable-transactions/{id} ---

def test_delete_transaction(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_consumables(make_doc())
    resp = TestClient(app).delete("/api/consumable-transactions/t1")
    assert resp.status_code == 204
    data = TestClient(app).get("/api/consumables").json()
    assert data["transactions"] == []


def test_delete_transaction_not_found(client):
    resp = client.delete("/api/consumable-transactions/nope")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/backend && python -m pytest tests/test_consumables.py -v
```
Expected: import errors because routes don't exist yet

- [ ] **Step 3: Implement routes**

```python
# packages/backend/src/myhome/routes/consumables.py
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from ..models_consumables import (
    Consumable,
    ConsumableCreate,
    ConsumablePlacementUpdate,
    ConsumableUpdate,
    ConsumableTransaction,
    StockUpdate,
)
from ..persistence_consumables import load_consumables, save_consumables

router = APIRouter()


@router.get("/api/consumables")
def get_consumables():
    return load_consumables()


@router.post("/api/consumables", response_model=Consumable, status_code=201)
def create_consumable(body: ConsumableCreate) -> Consumable:
    doc = load_consumables()
    item = Consumable(id=str(uuid.uuid4()), **body.model_dump())
    doc.consumables.append(item)
    save_consumables(doc)
    return item


@router.put("/api/consumables/{id}", status_code=204)
def update_consumable(id: str, body: ConsumableUpdate) -> None:
    doc = load_consumables()
    item = next((c for c in doc.consumables if c.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    save_consumables(doc)


@router.delete("/api/consumables/{id}", status_code=204)
def delete_consumable(id: str) -> None:
    doc = load_consumables()
    before = len(doc.consumables)
    doc.consumables = [c for c in doc.consumables if c.id != id]
    if len(doc.consumables) == before:
        raise HTTPException(status_code=404)
    doc.transactions = [t for t in doc.transactions if t.consumableId != id]
    save_consumables(doc)


@router.put("/api/consumables/{id}/placement", status_code=204)
def update_placement(id: str, body: ConsumablePlacementUpdate) -> None:
    doc = load_consumables()
    item = next((c for c in doc.consumables if c.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    item.placement = body.placement
    save_consumables(doc)


@router.post("/api/consumables/{id}/stock", status_code=204)
def update_stock(id: str, body: StockUpdate) -> None:
    doc = load_consumables()
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
    save_consumables(doc)


@router.delete("/api/consumable-transactions/{id}", status_code=204)
def delete_transaction(id: str) -> None:
    doc = load_consumables()
    before = len(doc.transactions)
    doc.transactions = [t for t in doc.transactions if t.id != id]
    if len(doc.transactions) == before:
        raise HTTPException(status_code=404)
    save_consumables(doc)
```

- [ ] **Step 4: Register router in main.py**

In `packages/backend/src/myhome/main.py`, add the consumables router. The existing import line is:
```python
from .routes import house, svg, ha, chores, inventory, settings, costs, works, kb, backup
```
Change it to:
```python
from .routes import house, svg, ha, chores, inventory, settings, costs, works, kb, backup, consumables
```
And add after `app.include_router(backup.router)`:
```python
app.include_router(consumables.router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd packages/backend && python -m pytest tests/test_consumables.py tests/test_consumables_persistence.py -v
```
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/routes/consumables.py packages/backend/src/myhome/main.py packages/backend/tests/test_consumables.py
git commit -m "feat(consumables): add backend routes + tests"
```

---

## Task 4: Settings backend extension

**Files:**
- Modify: `packages/backend/src/myhome/models_settings.py`
- Modify: `packages/backend/src/myhome/routes/settings.py`
- Modify: `packages/backend/tests/test_settings.py`

- [ ] **Step 1: Write the failing settings tests**

Append to `packages/backend/tests/test_settings.py`:

```python
from myhome.models_settings import ConsumableCategory


def test_get_settings_returns_default_consumable_units(client):
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    units = resp.json()["consumableUnits"]
    assert "count" in units
    assert "L" in units
    assert len(units) >= 8


def test_get_settings_returns_empty_consumable_categories(client):
    resp = client.get("/api/settings")
    assert resp.json()["consumableCategories"] == []


def test_put_consumable_units(client):
    resp = client.put("/api/settings/consumable-units", json=["count", "kg", "L"])
    assert resp.status_code == 204
    data = client.get("/api/settings").json()
    assert data["consumableUnits"] == ["count", "kg", "L"]


def test_put_consumable_categories(client):
    cats = [{"id": "cc1", "name": "Cleaning", "emoji": "🧹"}]
    resp = client.put("/api/settings/consumable-categories", json=cats)
    assert resp.status_code == 204
    data = client.get("/api/settings").json()
    assert data["consumableCategories"][0]["name"] == "Cleaning"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/backend && python -m pytest tests/test_settings.py::test_get_settings_returns_default_consumable_units -v
```
Expected: `KeyError: 'consumableUnits'`

- [ ] **Step 3: Extend models_settings.py**

In `packages/backend/src/myhome/models_settings.py`, add after the `WorkCategory` class:

```python
class ConsumableCategory(BaseModel):
    id: str
    name: str
    emoji: str


def _default_consumable_units() -> list[str]:
    return ["count", "L", "mL", "kg", "g", "packs", "rolls", "pairs"]
```

Then extend `SettingsDocument` to add the two new fields (find the class and add):
```python
class SettingsDocument(BaseModel):
    version: int = 1
    costCategories: list[CostCategory] = []
    inventoryCategories: list[InventoryCategory] = []
    workCategories: list[WorkCategory] = []
    suppliers: list[Supplier] = []
    consumableUnits: list[str] = []
    consumableCategories: list[ConsumableCategory] = []
```

Note: `consumableUnits` defaults to `[]` in the model — the persistence layer fills defaults on load (see next step).

- [ ] **Step 4: Update persistence_settings.py to fill defaults**

In `packages/backend/src/myhome/persistence_settings.py`, find `load_settings()` and add default-filling after loading. The existing function already calls `_default_cost_categories()` etc. Add the consumable defaults in the same pattern. The file currently looks like (find `load_settings`):

```python
def load_settings() -> SettingsDocument:
    path = _settings_file()
    if not path.exists():
        return SettingsDocument(
            costCategories=_default_cost_categories(),
            inventoryCategories=_default_inventory_categories(),
            workCategories=_default_work_categories(),
        )
    with path.open() as f:
        doc = SettingsDocument.model_validate(json.load(f))
    if not doc.costCategories:
        doc.costCategories = _default_cost_categories()
    if not doc.inventoryCategories:
        doc.inventoryCategories = _default_inventory_categories()
    if not doc.workCategories:
        doc.workCategories = _default_work_categories()
    return doc
```

Read the actual file first to see its current content, then add these lines after the existing `if not doc.workCategories:` block:
```python
    if not doc.consumableUnits:
        doc.consumableUnits = _default_consumable_units()
```
And in the `not path.exists()` branch, add `consumableUnits=_default_consumable_units()`.

Also add the import of `ConsumableCategory` and `_default_consumable_units` at the top of the routes/settings.py file.

- [ ] **Step 5: Add routes to routes/settings.py**

In `packages/backend/src/myhome/routes/settings.py`, update the import to include `ConsumableCategory` and `_default_consumable_units`:

```python
from ..models_settings import (
    CostCategory, CostCategoryPlacement, InventoryCategory, WorkCategory,
    Supplier, SettingsDocument, ConsumableCategory,
)
```

Then add two new routes at the end of the file:

```python
@router.put("/api/settings/consumable-units", status_code=204)
def put_consumable_units(body: list[str]) -> None:
    doc = load_settings()
    doc.consumableUnits = body
    save_settings(doc)


@router.put("/api/settings/consumable-categories", status_code=204)
def put_consumable_categories(body: list[ConsumableCategory]) -> None:
    doc = load_settings()
    doc.consumableCategories = body
    save_settings(doc)
```

- [ ] **Step 6: Run all settings tests**

```bash
cd packages/backend && python -m pytest tests/test_settings.py -v
```
Expected: all tests pass (including the new ones)

- [ ] **Step 7: Commit**

```bash
git add packages/backend/src/myhome/models_settings.py packages/backend/src/myhome/persistence_settings.py packages/backend/src/myhome/routes/settings.py packages/backend/tests/test_settings.py
git commit -m "feat(consumables): extend settings with consumable units and categories"
```

---

## Task 5: Frontend store + settings store extension

**Files:**
- Create: `packages/editor/src/lib/consumableStore.svelte.ts`
- Create: `packages/editor/test/consumableStore.test.ts`
- Modify: `packages/editor/src/lib/settingsStore.svelte.ts`

- [ ] **Step 1: Write failing consumableStore tests**

```typescript
// packages/editor/test/consumableStore.test.ts
import { describe, it, expect, afterEach, vi } from "vitest";
import { createConsumableStore, stockStatus, barFill } from "../src/lib/consumableStore.svelte";

function makeFetch(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({ ok: status >= 200 && status < 300, status, json: async () => body });
}

const emptyDoc = { version: 1, consumables: [], transactions: [] };

const sampleDoc = {
  version: 1,
  consumables: [
    { id: "c1", name: "AA Batteries", emoji: "🔋", unit: "count", quantity: 6.0, minQuantity: 4.0, categoryId: null, description: "", placement: null },
    { id: "c2", name: "Dish Soap", emoji: "🧴", unit: "mL", quantity: 0.0, minQuantity: 100.0, categoryId: null, description: "", placement: null },
  ],
  transactions: [
    { id: "t1", consumableId: "c1", delta: 6.0, quantityAfter: 6.0, note: "", timestamp: "2026-07-02T10:00:00Z" },
  ],
};

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => vi.unstubAllGlobals());

describe("consumableStore — init", () => {
  it("loads consumables and transactions from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createConsumableStore();
    await tick();
    expect(store.consumables.length).toBe(2);
    expect(store.transactions.length).toBe(1);
    expect(store.loaded).toBe(true);
  });

  it("marks loaded on fetch error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network")));
    const store = createConsumableStore();
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("Network");
  });
});

describe("stockStatus", () => {
  it("returns empty when quantity is 0", () => {
    const c = { id: "x", name: "", emoji: "", unit: "count", quantity: 0, minQuantity: 5, categoryId: null, description: "", placement: null };
    expect(stockStatus(c)).toBe("empty");
  });

  it("returns low when quantity <= minQuantity", () => {
    const c = { id: "x", name: "", emoji: "", unit: "count", quantity: 3, minQuantity: 5, categoryId: null, description: "", placement: null };
    expect(stockStatus(c)).toBe("low");
  });

  it("returns ok when quantity > minQuantity", () => {
    const c = { id: "x", name: "", emoji: "", unit: "count", quantity: 10, minQuantity: 5, categoryId: null, description: "", placement: null };
    expect(stockStatus(c)).toBe("ok");
  });
});

describe("barFill", () => {
  it("returns 1/3 fill at minQuantity (threshold mark)", () => {
    const c = { id: "x", name: "", emoji: "", unit: "count", quantity: 5, minQuantity: 5, categoryId: null, description: "", placement: null };
    expect(barFill(c)).toBeCloseTo(1 / 3, 5);
  });

  it("returns 1 at 3× minQuantity", () => {
    const c = { id: "x", name: "", emoji: "", unit: "count", quantity: 15, minQuantity: 5, categoryId: null, description: "", placement: null };
    expect(barFill(c)).toBe(1);
  });

  it("returns 0 when empty", () => {
    const c = { id: "x", name: "", emoji: "", unit: "count", quantity: 0, minQuantity: 5, categoryId: null, description: "", placement: null };
    expect(barFill(c)).toBe(0);
  });

  it("handles zero minQuantity without NaN", () => {
    const c = { id: "x", name: "", emoji: "", unit: "count", quantity: 5, minQuantity: 0, categoryId: null, description: "", placement: null };
    const fill = barFill(c);
    expect(isNaN(fill)).toBe(false);
    expect(fill).toBe(1);
  });
});

describe("consumableStore — updateStock", () => {
  it("calls POST /api/consumables/:id/stock and re-fetches", async () => {
    const fetchMock = makeFetch(204);
    vi.stubGlobal("fetch", fetchMock);
    const store = createConsumableStore();
    await tick();
    fetchMock.mockResolvedValueOnce({ ok: true, status: 204, json: async () => ({}) });
    fetchMock.mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc });
    await store.updateStock("c1", 10.0, "restock");
    const stockCall = fetchMock.mock.calls.find((c) => c[0] === "/api/consumables/c1/stock");
    expect(stockCall).toBeTruthy();
    const body = JSON.parse(stockCall![1].body);
    expect(body.quantity).toBe(10.0);
    expect(body.note).toBe("restock");
  });
});
```

- [ ] **Step 2: Run to verify failure**

```bash
cd packages/editor && npm test -- --reporter=verbose test/consumableStore.test.ts
```
Expected: cannot find module `../src/lib/consumableStore.svelte`

- [ ] **Step 3: Implement consumableStore.svelte.ts**

```typescript
// packages/editor/src/lib/consumableStore.svelte.ts

export interface ConsumablePlacement {
  floorId: string;
  roomId: string | null;
  position: { x: number; y: number };
}

export interface Consumable {
  id: string;
  name: string;
  emoji: string;
  unit: string;
  quantity: number;
  minQuantity: number;
  categoryId: string | null;
  description: string;
  placement: ConsumablePlacement | null;
}

export interface ConsumableTransaction {
  id: string;
  consumableId: string;
  delta: number;
  quantityAfter: number;
  note: string;
  timestamp: string;
}

export interface ConsumableDocument {
  version: number;
  consumables: Consumable[];
  transactions: ConsumableTransaction[];
}

export type StockState = "ok" | "low" | "empty";

export function stockStatus(c: Consumable): StockState {
  if (c.quantity === 0) return "empty";
  if (c.quantity <= c.minQuantity) return "low";
  return "ok";
}

export function barFill(c: Consumable): number {
  if (c.minQuantity === 0) return c.quantity > 0 ? 1 : 0;
  return Math.min(1, c.quantity / (c.minQuantity * 3));
}

export function createConsumableStore() {
  const consumables = $state<Consumable[]>([]);
  const transactions = $state<ConsumableTransaction[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    try {
      const resp = await fetch("/api/consumables");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: ConsumableDocument = await resp.json();
      consumables.length = 0;
      for (const c of doc.consumables) consumables.push(c);
      transactions.length = 0;
      for (const t of doc.transactions) transactions.push(t);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function createConsumable(data: Omit<Consumable, "id" | "placement">): Promise<void> {
    const resp = await fetch("/api/consumables", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateConsumable(id: string, patch: Partial<Omit<Consumable, "id" | "placement">>): Promise<void> {
    const resp = await fetch(`/api/consumables/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteConsumable(id: string): Promise<void> {
    const resp = await fetch(`/api/consumables/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function setPlacement(id: string, placement: ConsumablePlacement | null): Promise<void> {
    const resp = await fetch(`/api/consumables/${id}/placement`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ placement }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateStock(id: string, quantity: number, note: string = ""): Promise<void> {
    const resp = await fetch(`/api/consumables/${id}/stock`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quantity, note }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteTransaction(id: string): Promise<void> {
    const resp = await fetch(`/api/consumable-transactions/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  function transactionsFor(consumableId: string): ConsumableTransaction[] {
    return transactions.filter((t) => t.consumableId === consumableId);
  }

  function placedConsumables(): Consumable[] {
    return consumables.filter((c) => c.placement !== null);
  }

  init();

  return {
    get consumables() { return consumables as Consumable[]; },
    get transactions() { return transactions as ConsumableTransaction[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    createConsumable,
    updateConsumable,
    deleteConsumable,
    setPlacement,
    updateStock,
    deleteTransaction,
    transactionsFor,
    placedConsumables,
  };
}
```

- [ ] **Step 4: Extend settingsStore.svelte.ts**

Add the new interfaces after the `Supplier` interface:
```typescript
export interface ConsumableCategory {
  id: string;
  name: string;
  emoji: string;
}
```

In `SettingsDocument`, add:
```typescript
export interface SettingsDocument {
  version: number;
  costCategories: CostCategory[];
  inventoryCategories: InventoryCategory[];
  workCategories: WorkCategory[];
  suppliers: Supplier[];
  consumableUnits: string[];
  consumableCategories: ConsumableCategory[];
}
```

In `createSettingsStore`, add two new `$state` arrays at the top of the function:
```typescript
const consumableUnits = $state<string[]>([]);
const consumableCategories = $state<ConsumableCategory[]>([]);
```

In the `init()` function, after the `suppliers` loading block, add:
```typescript
consumableUnits.length = 0;
for (const u of (doc.consumableUnits ?? [])) consumableUnits.push(u);
consumableCategories.length = 0;
for (const c of (doc.consumableCategories ?? [])) consumableCategories.push(c);
```

Add two new async functions:
```typescript
async function updateConsumableUnits(list: string[]): Promise<void> {
  const resp = await fetch("/api/settings/consumable-units", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(list),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  await init();
}

async function updateConsumableCategories(list: ConsumableCategory[]): Promise<void> {
  const resp = await fetch("/api/settings/consumable-categories", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(list),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  await init();
}
```

Expose them in the return object:
```typescript
get consumableUnits() { return consumableUnits as string[]; },
get consumableCategories() { return consumableCategories as ConsumableCategory[]; },
updateConsumableUnits,
updateConsumableCategories,
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd packages/editor && npm test -- --reporter=verbose test/consumableStore.test.ts
```
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/consumableStore.svelte.ts packages/editor/src/lib/settingsStore.svelte.ts packages/editor/test/consumableStore.test.ts
git commit -m "feat(consumables): add frontend store + settings store extension"
```

---

## Task 6: ConsumablesPage

**Files:**
- Modify: `packages/editor/src/lib/components/ConsumablesPage.svelte` (replace stub)
- Create: `packages/editor/test/ConsumablesPage.test.ts`

- [ ] **Step 1: Write failing tests**

```typescript
// packages/editor/test/ConsumablesPage.test.ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import ConsumablesPage from "../src/lib/components/ConsumablesPage.svelte";
import { createConsumableStore } from "../src/lib/consumableStore.svelte";

const sampleDoc = {
  version: 1,
  consumables: [
    { id: "c1", name: "AA Batteries", emoji: "🔋", unit: "count", quantity: 6.0, minQuantity: 4.0, categoryId: null, description: "", placement: null },
    { id: "c2", name: "Dish Soap", emoji: "🧴", unit: "mL", quantity: 0.0, minQuantity: 100.0, categoryId: "cat1", description: "", placement: null },
    { id: "c3", name: "Toothpaste", emoji: "🪥", unit: "g", quantity: 50.0, minQuantity: 100.0, categoryId: null, description: "", placement: null },
  ],
  transactions: [],
};

async function makeTick(): Promise<void> { await new Promise((r) => setTimeout(r, 0)); }

function makeStore() {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => sampleDoc }));
  return createConsumableStore();
}

afterEach(() => vi.unstubAllGlobals());

describe("ConsumablesPage", () => {
  it("renders all consumables in the table", async () => {
    const store = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumablesPage, {
      target,
      props: { store, settingsStore: { consumableCategories: [], consumableUnits: [] }, onplaceonmap: vi.fn() },
    });
    await tick(); flushSync();
    expect(target.querySelectorAll("tbody tr").length).toBe(3);
    unmount(comp); target.remove();
  });

  it("filters to low/empty items with needs-attention toggle", async () => {
    const store = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumablesPage, {
      target,
      props: { store, settingsStore: { consumableCategories: [], consumableUnits: [] }, onplaceonmap: vi.fn() },
    });
    await tick(); flushSync();
    // Click "attention" toggle (should be on by default or toggled)
    const attentionBtn = Array.from(target.querySelectorAll("button")).find(b => b.textContent?.includes("⚠"));
    if (attentionBtn) { attentionBtn.dispatchEvent(new MouseEvent("click", { bubbles: true })); flushSync(); }
    // c2 (empty) and c3 (low) should show; c1 (ok) should not
    const rows = target.querySelectorAll("tbody tr");
    const text = Array.from(rows).map(r => r.textContent ?? "").join(" ");
    expect(text).toContain("Dish Soap");
    expect(text).toContain("Toothpaste");
    unmount(comp); target.remove();
  });

  it("shows empty state when no consumables", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ version: 1, consumables: [], transactions: [] }) }));
    const store = createConsumableStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumablesPage, {
      target,
      props: { store, settingsStore: { consumableCategories: [], consumableUnits: [] }, onplaceonmap: vi.fn() },
    });
    await tick(); flushSync();
    expect(target.querySelector(".empty")).not.toBeNull();
    unmount(comp); target.remove();
  });
});
```

- [ ] **Step 2: Run to verify failure**

```bash
cd packages/editor && npm test -- --reporter=verbose test/ConsumablesPage.test.ts
```
Expected: tests fail (stub renders no table rows)

- [ ] **Step 3: Implement ConsumablesPage.svelte**

Replace entire file content:

```svelte
<script lang="ts">
  import type { createConsumableStore, Consumable } from "../consumableStore.svelte";
  import { stockStatus, barFill } from "../consumableStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import ConsumableModal from "./ConsumableModal.svelte";

  type ConsumableStore = ReturnType<typeof createConsumableStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    store: ConsumableStore;
    settingsStore: SettingsStore;
    onplaceonmap?: (id: string) => void;
  }

  let { store, settingsStore, onplaceonmap }: Props = $props();

  let searchQuery = $state("");
  let categoryFilter = $state("");
  let attentionFilter = $state(false);
  let editConsumable = $state<Consumable | null>(null);
  let showCreate = $state(false);

  const STATUS_COLOR: Record<string, string> = { ok: "var(--success)", low: "#ff9800", empty: "var(--danger)" };
  const STATUS_LABEL: Record<string, string> = { ok: "OK", low: "LOW", empty: "EMPTY" };

  const filtered = $derived(
    store.consumables.filter((c) => {
      if (searchQuery && !c.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      if (categoryFilter && c.categoryId !== categoryFilter) return false;
      if (attentionFilter) {
        const s = stockStatus(c);
        if (s === "ok") return false;
      }
      return true;
    })
  );

  function categoryName(id: string | null): string {
    if (!id) return "—";
    return settingsStore.consumableCategories.find((c) => c.id === id)?.name ?? "—";
  }

  function formatDelta(delta: number): string {
    return delta >= 0 ? `+${delta}` : String(delta);
  }

  function formatTs(iso: string): string {
    return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  }
</script>

<div class="page">
  <div class="toolbar">
    <Input placeholder="🔍 Search…" bind:value={searchQuery} />
    <select class="native-input" bind:value={categoryFilter}>
      <option value="">All categories</option>
      {#each settingsStore.consumableCategories as cat}
        <option value={cat.id}>{cat.emoji} {cat.name}</option>
      {/each}
    </select>
    <div class="filter-toggle">
      <button class="toggle-btn" class:active={!attentionFilter} onclick={() => { attentionFilter = false; }}>☰ All</button>
      <button class="toggle-btn" class:active={attentionFilter} onclick={() => { attentionFilter = true; }}>⚠ Needs attention</button>
    </div>
    <Button onclick={() => { showCreate = true; }}>＋ Add consumable</Button>
  </div>

  <div class="table-wrapper">
    <table>
      <thead>
        <tr>
          <th></th>
          <th>Name</th>
          <th>Category</th>
          <th>Quantity</th>
          <th>Min</th>
          <th>Stock</th>
          <th>Status</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {#each filtered as c (c.id)}
          {@const st = stockStatus(c)}
          {@const fill = barFill(c)}
          <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
          <tr onclick={() => { editConsumable = c; }} class:row-low={st === "low"} class:row-empty={st === "empty"}>
            <td class="emoji-cell">{c.emoji}</td>
            <td class="name-cell">{c.name}</td>
            <td>{categoryName(c.categoryId)}</td>
            <td>{c.quantity} {c.unit}</td>
            <td class="faint">{c.minQuantity} {c.unit}</td>
            <td class="bar-cell">
              <div class="bar-track">
                <div class="bar-fill" style="width:{fill * 100}%;background:{STATUS_COLOR[st]}"></div>
                <div class="bar-min"></div>
              </div>
            </td>
            <td>
              <span class="status-badge" style="color:{STATUS_COLOR[st]};background:{STATUS_COLOR[st]}22">
                {STATUS_LABEL[st]}
              </span>
            </td>
            <td class="actions-cell" onclick={(e) => e.stopPropagation()}>
              {#if onplaceonmap && !c.placement}
                <button class="icon-btn" title="Place on map" onclick={() => onplaceonmap?.(c.id)}>📌</button>
              {/if}
            </td>
          </tr>
        {/each}

        {#if filtered.length === 0}
          <tr>
            <td colspan="8" class="empty">
              {store.consumables.length === 0
                ? "No consumables yet — click ＋ Add consumable to get started."
                : "No consumables match your filters."}
            </td>
          </tr>
        {/if}
      </tbody>
    </table>
  </div>

  <div class="footer">{filtered.length} item{filtered.length !== 1 ? "s" : ""}</div>
</div>

{#if showCreate}
  <ConsumableModal
    consumable={null}
    {store}
    {settingsStore}
    onclose={() => { showCreate = false; }}
    {onplaceonmap}
  />
{/if}

{#if editConsumable}
  <ConsumableModal
    consumable={editConsumable}
    {store}
    {settingsStore}
    onclose={() => { editConsumable = null; }}
    {onplaceonmap}
  />
{/if}

<style>
  .page { display: flex; flex-direction: column; height: 100%; background: var(--bg); font-family: var(--font-sans); }

  .toolbar {
    display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3);
    background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0; flex-wrap: wrap;
  }
  .toolbar :global(.ui-input) { flex: 1; min-width: 140px; }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px;
    font-family: var(--font-sans); box-sizing: border-box; cursor: pointer;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  .filter-toggle { display: flex; border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; flex-shrink: 0; }
  .toggle-btn { padding: 6px 10px; border: none; background: var(--surface-alt); color: var(--text-muted); cursor: pointer; font-size: 11px; white-space: nowrap; }
  .toggle-btn:not(:last-child) { border-right: 1px solid var(--border); }
  .toggle-btn.active { background: var(--accent); color: var(--accent-contrast); }
  .toggle-btn:not(.active):hover { background: var(--surface-hover); color: var(--text); }

  .table-wrapper { flex: 1; overflow-y: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; color: var(--text-muted); }
  thead { position: sticky; top: 0; background: var(--surface-alt); z-index: 1; }
  th { padding: 6px 10px; color: var(--text-faint); font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; text-align: left; border-bottom: 1px solid var(--border); }
  td { padding: 7px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:not(.empty):hover td { background: var(--surface-hover); cursor: pointer; }
  .emoji-cell { font-size: 16px; width: 32px; text-align: center; }
  .name-cell { color: var(--text); font-weight: 600; }
  .faint { color: var(--text-faint); }
  .actions-cell { white-space: nowrap; text-align: right; }
  .empty { text-align: center; color: var(--text-faint); padding: 32px; }

  .row-low td { background: color-mix(in srgb, #ff9800 6%, transparent); }
  .row-empty td { background: color-mix(in srgb, var(--danger) 8%, transparent); }

  .bar-cell { width: 80px; }
  .bar-track { position: relative; width: 60px; height: 6px; background: var(--surface-alt); border-radius: 3px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 3px; transition: width 0.2s; }
  .bar-min { position: absolute; left: 33.3%; top: 0; bottom: 0; width: 1.5px; background: rgba(255,255,255,0.35); }

  .status-badge { font-size: 10px; padding: 2px 6px; border-radius: 10px; font-weight: 600; letter-spacing: 0.04em; }

  .icon-btn { padding: 4px 8px; border: none; border-radius: var(--radius-sm); background: var(--surface-alt); color: var(--text-muted); cursor: pointer; font-size: 13px; }
  .icon-btn:hover { background: var(--surface-hover); color: var(--text); }

  .footer { padding: 6px 12px; font-size: 11px; color: var(--text-faint); border-top: 1px solid var(--border); flex-shrink: 0; }
</style>
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd packages/editor && npm test -- --reporter=verbose test/ConsumablesPage.test.ts
```
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ConsumablesPage.svelte packages/editor/test/ConsumablesPage.test.ts
git commit -m "feat(consumables): implement ConsumablesPage list view"
```

---

## Task 7: ConsumableModal

**Files:**
- Create: `packages/editor/src/lib/components/ConsumableModal.svelte`
- Create: `packages/editor/test/ConsumableModal.test.ts`

- [ ] **Step 1: Write failing tests**

```typescript
// packages/editor/test/ConsumableModal.test.ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import ConsumableModal from "../src/lib/components/ConsumableModal.svelte";
import { createConsumableStore } from "../src/lib/consumableStore.svelte";

const emptyDoc = { version: 1, consumables: [], transactions: [] };
const sampleConsumable = { id: "c1", name: "AA Batteries", emoji: "🔋", unit: "count", quantity: 6.0, minQuantity: 4.0, categoryId: null, description: "", placement: null };
const sampleDoc = { version: 1, consumables: [sampleConsumable], transactions: [
  { id: "t1", consumableId: "c1", delta: 6.0, quantityAfter: 6.0, note: "restock", timestamp: "2026-07-02T10:00:00Z" }
]};

async function makeTick(): Promise<void> { await new Promise((r) => setTimeout(r, 0)); }
afterEach(() => vi.unstubAllGlobals());

function makeStore(doc = sampleDoc) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }));
  return createConsumableStore();
}

describe("ConsumableModal — create mode", () => {
  it("renders details fields in create mode", async () => {
    const store = makeStore(emptyDoc);
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumableModal, {
      target,
      props: { consumable: null, store, settingsStore: { consumableUnits: ["count", "L"], consumableCategories: [] }, onclose: vi.fn() },
    });
    await tick(); flushSync();
    const inputs = target.querySelectorAll("input, select, textarea");
    expect(inputs.length).toBeGreaterThan(0);
    unmount(comp); target.remove();
  });

  it("does not show Stock tab in create mode", async () => {
    const store = makeStore(emptyDoc);
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumableModal, {
      target,
      props: { consumable: null, store, settingsStore: { consumableUnits: ["count"], consumableCategories: [] }, onclose: vi.fn() },
    });
    await tick(); flushSync();
    const tabs = target.querySelectorAll(".tab-btn");
    const tabText = Array.from(tabs).map(t => t.textContent ?? "").join(" ");
    expect(tabText).not.toContain("Stock");
    unmount(comp); target.remove();
  });
});

describe("ConsumableModal — edit mode", () => {
  it("shows Stock tab in edit mode", async () => {
    const store = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumableModal, {
      target,
      props: { consumable: sampleConsumable, store, settingsStore: { consumableUnits: ["count"], consumableCategories: [] }, onclose: vi.fn() },
    });
    await tick(); flushSync();
    const tabs = target.querySelectorAll(".tab-btn");
    const tabText = Array.from(tabs).map(t => t.textContent ?? "").join(" ");
    expect(tabText).toContain("Stock");
    unmount(comp); target.remove();
  });

  it("shows transaction history in Stock tab", async () => {
    const store = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumableModal, {
      target,
      props: { consumable: sampleConsumable, store, settingsStore: { consumableUnits: ["count"], consumableCategories: [] }, onclose: vi.fn() },
    });
    await tick(); flushSync();
    // Switch to Stock tab
    const stockTab = Array.from(target.querySelectorAll(".tab-btn")).find(b => b.textContent?.includes("Stock"));
    stockTab?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();
    expect(target.textContent).toContain("restock");
    unmount(comp); target.remove();
  });

  it("calls onclose when cancel is clicked", async () => {
    const store = makeStore();
    await makeTick();
    const onclose = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumableModal, {
      target,
      props: { consumable: sampleConsumable, store, settingsStore: { consumableUnits: ["count"], consumableCategories: [] }, onclose },
    });
    await tick(); flushSync();
    const cancelBtn = Array.from(target.querySelectorAll("button")).find(b => b.textContent?.includes("Cancel"));
    cancelBtn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();
    expect(onclose).toHaveBeenCalledOnce();
    unmount(comp); target.remove();
  });
});
```

- [ ] **Step 2: Run to verify failure**

```bash
cd packages/editor && npm test -- --reporter=verbose test/ConsumableModal.test.ts
```
Expected: cannot find module ConsumableModal

- [ ] **Step 3: Implement ConsumableModal.svelte**

```svelte
<script lang="ts">
  import type { createConsumableStore, Consumable, ConsumableTransaction } from "../consumableStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import Modal from "./ui/Modal.svelte";
  import Input from "./ui/Input.svelte";
  import Button from "./ui/Button.svelte";
  import Tabs from "./ui/Tabs.svelte";

  type ConsumableStore = ReturnType<typeof createConsumableStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    consumable: Consumable | null;
    store: ConsumableStore;
    settingsStore: SettingsStore;
    onclose: () => void;
    onplaceonmap?: (id: string) => void;
  }

  let { consumable, store, settingsStore, onclose, onplaceonmap }: Props = $props();

  const isCreate = consumable === null;

  const PRESET_SENTINEL = "__custom__";
  const DEFAULT_UNITS = ["count", "L", "mL", "kg", "g", "packs", "rolls", "pairs"];

  const availableUnits = $derived(settingsStore.consumableUnits?.length ? settingsStore.consumableUnits : DEFAULT_UNITS);

  let activeTab = $state<"details" | "stock">("details");

  let name = $state(consumable?.name ?? "");
  let emoji = $state(consumable?.emoji ?? "🛒");
  let unit = $state(consumable?.unit ?? "count");
  let unitIsCustom = $state(!availableUnits.includes(consumable?.unit ?? "count"));
  let customUnit = $state(unitIsCustom ? (consumable?.unit ?? "") : "");
  let minQuantity = $state(String(consumable?.minQuantity ?? 1));
  let categoryId = $state(consumable?.categoryId ?? "");
  let description = $state(consumable?.description ?? "");

  let newQuantity = $state(String(consumable?.quantity ?? 0));
  let newNote = $state("");

  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);
  let stockError = $state<string | null>(null);
  let stockSaving = $state(false);

  const currentTransactions = $derived(
    consumable ? store.transactionsFor(consumable.id).slice().reverse() : []
  );

  const resolvedUnit = $derived(unitIsCustom ? customUnit : unit);

  const tabs = $derived(isCreate
    ? [{ id: "details", label: "Details" }]
    : [{ id: "details", label: "Details" }, { id: "stock", label: "Stock" }]
  );

  async function handleSave(): Promise<void> {
    if (!name.trim()) { error = "Name is required"; return; }
    saving = true; error = null;
    try {
      const payload = { name: name.trim(), emoji, unit: resolvedUnit, minQuantity: parseFloat(minQuantity) || 0, categoryId: categoryId || null, description };
      if (isCreate) {
        await store.createConsumable({ ...payload, quantity: 0 });
      } else {
        await store.updateConsumable(consumable!.id, payload);
      }
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Save failed";
    } finally {
      saving = false;
    }
  }

  async function handleDelete(): Promise<void> {
    if (!confirmDelete) { confirmDelete = true; return; }
    deleting = true;
    try {
      await store.deleteConsumable(consumable!.id);
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Delete failed";
    } finally {
      deleting = false;
    }
  }

  async function handleUpdateStock(): Promise<void> {
    const qty = parseFloat(newQuantity);
    if (isNaN(qty)) { stockError = "Invalid quantity"; return; }
    stockSaving = true; stockError = null;
    try {
      await store.updateStock(consumable!.id, qty, newNote);
      newNote = "";
    } catch (e) {
      stockError = e instanceof Error ? e.message : "Update failed";
    } finally {
      stockSaving = false;
    }
  }

  function formatDelta(delta: number): string {
    return delta >= 0 ? `+${delta}` : String(delta);
  }

  function formatTs(iso: string): string {
    return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  }
</script>

<Modal title={isCreate ? "Add consumable" : consumable!.name} onclose={onclose}>
  <div slot="body">
    <Tabs {tabs} bind:active={activeTab} />

    {#if activeTab === "details"}
      <div class="form">
        <div class="row">
          <div class="field short">
            <label>Emoji</label>
            <Input bind:value={emoji} maxlength={4} style="text-align:center;font-size:20px" />
          </div>
          <div class="field grow">
            <label>Name *</label>
            <Input bind:value={name} placeholder="e.g. AA Batteries" />
          </div>
        </div>

        <div class="row">
          <div class="field grow">
            <label>Unit</label>
            <select class="native-input" bind:value={unit} onchange={() => { unitIsCustom = unit === PRESET_SENTINEL; }}>
              {#each availableUnits as u}
                <option value={u}>{u}</option>
              {/each}
              <option value={PRESET_SENTINEL}>Custom…</option>
            </select>
            {#if unitIsCustom}
              <Input bind:value={customUnit} placeholder="e.g. tablets" style="margin-top:4px" />
            {/if}
          </div>
          <div class="field short">
            <label>Min qty</label>
            <Input type="number" bind:value={minQuantity} min="0" step="any" />
          </div>
        </div>

        <div class="field">
          <label>Category</label>
          <select class="native-input" bind:value={categoryId}>
            <option value="">— None —</option>
            {#each settingsStore.consumableCategories as cat}
              <option value={cat.id}>{cat.emoji} {cat.name}</option>
            {/each}
          </select>
        </div>

        <div class="field">
          <label>Description</label>
          <textarea bind:value={description} rows="2" class="native-textarea" placeholder="Optional notes…"></textarea>
        </div>

        {#if error}<div class="error">{error}</div>{/if}
      </div>

    {:else if activeTab === "stock"}
      <div class="stock-section">
        <div class="current-qty">
          Current stock: <strong>{consumable?.quantity} {consumable?.unit}</strong>
        </div>
        <div class="update-form">
          <div class="row">
            <div class="field grow">
              <label>Set new quantity ({consumable?.unit})</label>
              <Input type="number" bind:value={newQuantity} min="0" step="any" />
            </div>
            <div class="field grow">
              <label>Note (optional)</label>
              <Input bind:value={newNote} placeholder="e.g. restocked" />
            </div>
          </div>
          <Button onclick={handleUpdateStock} disabled={stockSaving}>
            {stockSaving ? "Updating…" : "Update stock"}
          </Button>
          {#if stockError}<div class="error">{stockError}</div>{/if}
        </div>

        <div class="history">
          <div class="history-title">History</div>
          {#if currentTransactions.length === 0}
            <div class="history-empty">No transactions yet</div>
          {:else}
            {#each currentTransactions as tx (tx.id)}
              <div class="tx-row">
                <span class="tx-delta" class:positive={tx.delta >= 0} class:negative={tx.delta < 0}>{formatDelta(tx.delta)}</span>
                <span class="tx-after">→ {tx.quantityAfter}</span>
                <span class="tx-note">{tx.note || "—"}</span>
                <span class="tx-ts">{formatTs(tx.timestamp)}</span>
                <button class="tx-del" title="Delete" onclick={() => store.deleteTransaction(tx.id)}>✕</button>
              </div>
            {/each}
          {/if}
        </div>
      </div>
    {/if}
  </div>

  <div slot="footer">
    {#if !isCreate}
      {#if confirmDelete}
        <span class="delete-confirm">Sure?</span>
        <Button variant="danger" onclick={handleDelete} disabled={deleting}>{deleting ? "Deleting…" : "Yes, delete"}</Button>
        <Button variant="ghost" onclick={() => { confirmDelete = false; }}>Cancel</Button>
      {:else}
        <Button variant="ghost" onclick={() => { confirmDelete = true; }}>Delete</Button>
      {/if}
      {#if onplaceonmap && !consumable?.placement}
        <Button variant="secondary" onclick={() => { onplaceonmap!(consumable!.id); onclose(); }}>📌 Place on map</Button>
      {/if}
    {/if}
    <span class="spacer"></span>
    <Button variant="ghost" onclick={onclose}>Cancel</Button>
    {#if activeTab === "details"}
      <Button onclick={handleSave} disabled={saving}>{saving ? "Saving…" : isCreate ? "Add" : "Save"}</Button>
    {/if}
  </div>
</Modal>

<style>
  .form { display: flex; flex-direction: column; gap: var(--space-3); padding: var(--space-3) 0; }
  .row { display: flex; gap: var(--space-2); }
  .field { display: flex; flex-direction: column; gap: 4px; }
  .field.grow { flex: 1; }
  .field.short { width: 80px; flex-shrink: 0; }
  label { font-size: 11px; font-weight: 600; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.05em; }
  .native-input, .native-textarea {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 10px; border-radius: var(--radius-md); font-size: 13px; font-family: var(--font-sans); width: 100%; box-sizing: border-box;
  }
  .native-input:focus, .native-textarea:focus { outline: none; border-color: var(--accent); }
  .native-textarea { resize: vertical; }
  .error { color: var(--danger); font-size: 12px; }

  .stock-section { padding: var(--space-3) 0; display: flex; flex-direction: column; gap: var(--space-3); }
  .current-qty { font-size: 13px; color: var(--text-muted); }
  .update-form { display: flex; flex-direction: column; gap: var(--space-2); }

  .history { display: flex; flex-direction: column; gap: 4px; }
  .history-title { font-size: 11px; font-weight: 600; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
  .history-empty { font-size: 12px; color: var(--text-faint); font-style: italic; }
  .tx-row { display: flex; align-items: center; gap: 8px; font-size: 12px; padding: 4px 0; border-bottom: 1px solid var(--border); }
  .tx-delta { font-weight: 600; min-width: 40px; }
  .tx-delta.positive { color: var(--success); }
  .tx-delta.negative { color: var(--danger); }
  .tx-after { color: var(--text-muted); min-width: 40px; }
  .tx-note { flex: 1; color: var(--text-muted); }
  .tx-ts { color: var(--text-faint); font-size: 11px; white-space: nowrap; }
  .tx-del { border: none; background: none; color: var(--text-faint); cursor: pointer; font-size: 10px; padding: 2px 4px; }
  .tx-del:hover { color: var(--danger); }

  .spacer { flex: 1; }
  .delete-confirm { font-size: 12px; color: var(--danger); }
</style>
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd packages/editor && npm test -- --reporter=verbose test/ConsumableModal.test.ts
```
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ConsumableModal.svelte packages/editor/test/ConsumableModal.test.ts
git commit -m "feat(consumables): add ConsumableModal with details + stock tabs"
```

---

## Task 8: ConsumableOverlay (floor plan badge)

**Files:**
- Create: `packages/editor/src/lib/components/ConsumableOverlay.svelte`

No separate unit test — SVG overlays in this codebase are not unit-tested (same pattern as `ChoreOverlay.svelte` and `InventoryOverlay.svelte`). Integration is verified in Task 12.

- [ ] **Step 1: Create ConsumableOverlay.svelte**

```svelte
<script lang="ts">
  import { worldToScreen, type ViewportState } from "../viewportStore.svelte";
  import type { Consumable } from "../consumableStore.svelte";
  import { stockStatus, barFill } from "../consumableStore.svelte";

  interface Props {
    consumables: Consumable[];
    viewport: ViewportState;
    active: boolean;
    width: number;
    height: number;
    onclick: (id: string) => void;
    ondragend: (id: string, worldPos: { x: number; y: number }) => void;
  }

  let { consumables, viewport, active, width, height, onclick, ondragend }: Props = $props();

  const BAR_X = 26;
  const BAR_W = 10;
  const BAR_H = 38;
  const BAR_INNER_H = 34; // fill area (2px padding top+bottom)

  const STATE_COLOR: Record<string, string> = {
    ok: "#4caf50",
    low: "#ff9800",
    empty: "#f44336",
  };

  let dragId = $state<string | null>(null);
  let dragStartScreen = $state({ x: 0, y: 0 });
  let dragStartWorld = $state({ x: 0, y: 0 });
  let dragOffsetScreen = $state({ x: 0, y: 0 });

  function pinScreen(c: Consumable): { x: number; y: number } | null {
    if (!c.placement) return null;
    const base = worldToScreen(c.placement.position, viewport);
    if (dragId === c.id) {
      return { x: base.x + dragOffsetScreen.x, y: base.y + dragOffsetScreen.y };
    }
    return base;
  }

  function handlePointerDown(e: PointerEvent, c: Consumable): void {
    if (!active || !c.placement) return;
    e.stopPropagation();
    (e.currentTarget as SVGElement).setPointerCapture(e.pointerId);
    dragId = c.id;
    dragStartScreen = { x: e.clientX, y: e.clientY };
    dragStartWorld = { x: c.placement.position.x, y: c.placement.position.y };
    dragOffsetScreen = { x: 0, y: 0 };
  }

  function handlePointerMove(e: PointerEvent): void {
    if (!dragId) return;
    dragOffsetScreen = { x: e.clientX - dragStartScreen.x, y: e.clientY - dragStartScreen.y };
  }

  function handlePointerUp(e: PointerEvent, c: Consumable): void {
    if (!dragId || dragId !== c.id) return;
    const dx = e.clientX - dragStartScreen.x;
    const dy = e.clientY - dragStartScreen.y;
    const moved = Math.hypot(dx, dy) > 4;
    if (moved) {
      ondragend(c.id, {
        x: dragStartWorld.x + dx / viewport.zoom,
        y: dragStartWorld.y + dy / viewport.zoom,
      });
    } else {
      onclick(c.id);
    }
    dragId = null;
    dragOffsetScreen = { x: 0, y: 0 };
  }

  const placedConsumables = $derived(consumables.filter((c) => c.placement !== null));
</script>

<svelte:window onpointermove={handlePointerMove} />

<svg {width} {height} style="position:absolute;top:0;left:0;pointer-events:none;overflow:visible">
  {#each placedConsumables as c (c.id)}
    {@const sp = pinScreen(c)}
    {#if sp}
      {@const st = stockStatus(c)}
      {@const fill = barFill(c)}
      {@const color = STATE_COLOR[st]}
      {@const fillH = Math.round(fill * BAR_INNER_H)}
      {@const fillY = BAR_H / 2 - 1 - fillH}
      <g
        transform="translate({sp.x},{sp.y})"
        style="pointer-events:{active ? 'all' : 'none'};cursor:{active ? (dragId === c.id ? 'grabbing' : 'grab') : 'default'}"
        onpointerdown={(e) => handlePointerDown(e, c)}
        onpointerup={(e) => handlePointerUp(e, c)}
      >
        <!-- backdrop -->
        <circle r="22" fill="#1a1a2e" opacity="0.8"/>
        <!-- circle outline coloured by state -->
        <circle r="18" fill="#1e1e3a" stroke={color} stroke-width={st === "ok" ? 1 : 2}/>
        <text text-anchor="middle" dominant-baseline="central" font-size="16" style="user-select:none;pointer-events:none">{c.emoji}</text>

        <!-- vertical bar track, centered vertically on the circle -->
        <rect x={BAR_X} y={-BAR_H / 2} width={BAR_W} height={BAR_H} rx="3"
          fill="#1a1a2e" stroke={color} stroke-width="1"/>

        <!-- fill from bottom (st=empty: no fill, just ✕) -->
        {#if st === "empty"}
          <text x={BAR_X + BAR_W / 2} y="0" text-anchor="middle" dominant-baseline="central"
            font-size="8" fill={color} style="pointer-events:none;user-select:none">✕</text>
        {:else}
          <rect x={BAR_X + 1} y={fillY} width={BAR_W - 2} height={fillH} rx="2" fill={color}/>
        {/if}

        <!-- min threshold dashed line at 1/3 from bottom -->
        {@const minY = BAR_H / 2 - 1 - Math.round(BAR_INNER_H / 3)}
        <line x1={BAR_X - 2} x2={BAR_X + BAR_W + 2} y1={minY} y2={minY}
          stroke={color} stroke-width="1" stroke-dasharray="2,1" opacity="0.8"/>

        <!-- quantity label below bar -->
        {@const labelQty = c.quantity % 1 === 0 ? String(c.quantity) : c.quantity.toFixed(1)}
        <text x={BAR_X + BAR_W / 2} y={BAR_H / 2 + 10} text-anchor="middle"
          font-size="8" fill={color} font-family="sans-serif"
          style="pointer-events:none;user-select:none">{labelQty}</text>
      </g>
    {/if}
  {/each}
</svg>
```

- [ ] **Step 2: Commit**

```bash
git add packages/editor/src/lib/components/ConsumableOverlay.svelte
git commit -m "feat(consumables): add ConsumableOverlay SVG badge"
```

---

## Task 9: ConsumablePinPopup

**Files:**
- Create: `packages/editor/src/lib/components/ConsumablePinPopup.svelte`

- [ ] **Step 1: Create ConsumablePinPopup.svelte**

```svelte
<script lang="ts">
  import type { createConsumableStore, Consumable } from "../consumableStore.svelte";
  import { stockStatus } from "../consumableStore.svelte";

  type ConsumableStore = ReturnType<typeof createConsumableStore>;

  interface Props {
    consumable: Consumable;
    store: ConsumableStore;
    screenX: number;
    screenY: number;
    onedit: () => void;
    onremove: () => void;
    onclose: () => void;
  }

  let { consumable, store, screenX, screenY, onedit, onremove, onclose }: Props = $props();

  const STATE_COLOR: Record<string, string> = { ok: "#4caf50", low: "#ff9800", empty: "#f44336" };
  const STATE_LABEL: Record<string, string> = { ok: "In stock", low: "Low stock", empty: "Empty" };

  let newQty = $state(String(consumable.quantity));
  let note = $state("");
  let updating = $state(false);
  let updateError = $state<string | null>(null);

  const st = $derived(stockStatus(consumable));
  const color = $derived(STATE_COLOR[st]);

  async function handleUpdate(): Promise<void> {
    const qty = parseFloat(newQty);
    if (isNaN(qty)) { updateError = "Invalid quantity"; return; }
    updating = true; updateError = null;
    try {
      await store.updateStock(consumable.id, qty, note);
      onclose();
    } catch {
      updateError = "Update failed";
    } finally {
      updating = false;
    }
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
  class="popup"
  style="left:{screenX}px;top:{screenY + 30}px"
  onclick={(e) => e.stopPropagation()}
>
  <div class="popup-name">{consumable.emoji} {consumable.name}</div>
  <div class="popup-status" style="color:{color}">{STATE_LABEL[st]} — {consumable.quantity} {consumable.unit}</div>

  <div class="quick-update">
    <input class="qty-input" type="number" bind:value={newQty} min="0" step="any" />
    <span class="unit-label">{consumable.unit}</span>
    <input class="note-input" type="text" bind:value={note} placeholder="note…" />
    <button class="update-btn" onclick={handleUpdate} disabled={updating}>
      {updating ? "…" : "✓"}
    </button>
  </div>
  {#if updateError}<div class="popup-error">{updateError}</div>{/if}

  <div class="popup-actions">
    <button onclick={onedit}>✏️ Edit</button>
    <button onclick={onremove}>✕ Remove pin</button>
    <button onclick={onclose}>Close</button>
  </div>
</div>

<style>
  .popup {
    position: absolute;
    background: #1e1e3a; border: 1px solid #3a3a5a; border-radius: 8px;
    padding: 10px 14px; min-width: 220px; z-index: 60;
    box-shadow: 0 4px 16px #0006; font-family: sans-serif;
    transform: translateX(-50%);
  }
  .popup-name { font-size: 13px; color: #eee; font-weight: 600; margin-bottom: 4px; }
  .popup-status { font-size: 11px; margin-bottom: 8px; }
  .quick-update { display: flex; align-items: center; gap: 4px; margin-bottom: 4px; }
  .qty-input { width: 52px; padding: 3px 6px; background: #111128; border: 1px solid #3a3a5a; border-radius: 4px; color: #eee; font-size: 12px; }
  .unit-label { font-size: 11px; color: #667; flex-shrink: 0; }
  .note-input { flex: 1; padding: 3px 6px; background: #111128; border: 1px solid #3a3a5a; border-radius: 4px; color: #eee; font-size: 12px; }
  .update-btn { border: none; background: #27ae60; color: #fff; padding: 3px 8px; border-radius: 4px; font-size: 12px; cursor: pointer; }
  .update-btn:disabled { opacity: 0.5; cursor: default; }
  .popup-error { font-size: 11px; color: #f44336; margin-bottom: 4px; }
  .popup-actions { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
  .popup-actions button {
    border: 1px solid #3a3a5a; background: #111128; color: #aaa;
    padding: 3px 8px; border-radius: 4px; font-size: 10px; cursor: pointer;
  }
  .popup-actions button:hover { background: #2a2a5a; color: #eee; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add packages/editor/src/lib/components/ConsumablePinPopup.svelte
git commit -m "feat(consumables): add ConsumablePinPopup for map badge click"
```

---

## Task 10: HomeConsumablesWidget

**Files:**
- Create: `packages/editor/src/lib/components/HomeConsumablesWidget.svelte`
- Create: `packages/editor/test/HomeConsumablesWidget.test.ts`

- [ ] **Step 1: Write failing tests**

```typescript
// packages/editor/test/HomeConsumablesWidget.test.ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import HomeConsumablesWidget from "../src/lib/components/HomeConsumablesWidget.svelte";
import { createConsumableStore } from "../src/lib/consumableStore.svelte";

const allOkDoc = {
  version: 1,
  consumables: [
    { id: "c1", name: "Batteries", emoji: "🔋", unit: "count", quantity: 10, minQuantity: 4, categoryId: null, description: "", placement: null },
  ],
  transactions: [],
};

const alertDoc = {
  version: 1,
  consumables: [
    { id: "c1", name: "Batteries", emoji: "🔋", unit: "count", quantity: 0, minQuantity: 4, categoryId: null, description: "", placement: null },
    { id: "c2", name: "Dish Soap", emoji: "🧴", unit: "mL", quantity: 50, minQuantity: 100, categoryId: null, description: "", placement: null },
    { id: "c3", name: "Toothpaste", emoji: "🪥", unit: "g", quantity: 200, minQuantity: 50, categoryId: null, description: "", placement: null },
  ],
  transactions: [],
};

async function makeTick(): Promise<void> { await new Promise((r) => setTimeout(r, 0)); }
afterEach(() => vi.unstubAllGlobals());

function makeStore(doc: unknown) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }));
  return createConsumableStore();
}

describe("HomeConsumablesWidget", () => {
  it("renders nothing when all items are OK", async () => {
    const consumableStore = makeStore(allOkDoc);
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeConsumablesWidget, { target, props: { consumableStore, onnavigate: vi.fn() } });
    await tick(); flushSync();
    expect(target.querySelector(".widget")).toBeNull();
    unmount(comp); target.remove();
  });

  it("shows empty and low items only", async () => {
    const consumableStore = makeStore(alertDoc);
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeConsumablesWidget, { target, props: { consumableStore, onnavigate: vi.fn() } });
    await tick(); flushSync();
    const text = target.textContent ?? "";
    expect(text).toContain("Batteries");   // empty
    expect(text).toContain("Dish Soap");   // low
    expect(text).not.toContain("Toothpaste"); // ok — should not appear
    unmount(comp); target.remove();
  });

  it("shows empty and low count pills", async () => {
    const consumableStore = makeStore(alertDoc);
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeConsumablesWidget, { target, props: { consumableStore, onnavigate: vi.fn() } });
    await tick(); flushSync();
    const text = target.textContent ?? "";
    expect(text).toContain("1 empty");
    expect(text).toContain("1 low");
    unmount(comp); target.remove();
  });

  it("clicking widget calls onnavigate", async () => {
    const consumableStore = makeStore(alertDoc);
    await makeTick();
    const onnavigate = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeConsumablesWidget, { target, props: { consumableStore, onnavigate } });
    await tick(); flushSync();
    (target.querySelector(".widget") as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();
    expect(onnavigate).toHaveBeenCalledOnce();
    unmount(comp); target.remove();
  });
});
```

- [ ] **Step 2: Run to verify failure**

```bash
cd packages/editor && npm test -- --reporter=verbose test/HomeConsumablesWidget.test.ts
```
Expected: cannot find module HomeConsumablesWidget

- [ ] **Step 3: Implement HomeConsumablesWidget.svelte**

```svelte
<script lang="ts">
  import type { createConsumableStore } from "../consumableStore.svelte";
  import { stockStatus } from "../consumableStore.svelte";
  import Card from "./ui/Card.svelte";

  type ConsumableStore = ReturnType<typeof createConsumableStore>;

  interface Props {
    consumableStore: ConsumableStore;
    onnavigate: () => void;
  }

  let { consumableStore, onnavigate }: Props = $props();

  const alertItems = $derived(
    consumableStore.consumables.filter((c) => {
      const s = stockStatus(c);
      return s === "low" || s === "empty";
    })
  );

  const emptyCount = $derived(alertItems.filter((c) => stockStatus(c) === "empty").length);
  const lowCount = $derived(alertItems.filter((c) => stockStatus(c) === "low").length);

  const STATE_COLOR: Record<string, string> = { ok: "#4caf50", low: "#ff9800", empty: "#f44336" };
</script>

{#if alertItems.length > 0}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
  <div class="widget" role="button" tabindex="0" onclick={onnavigate} onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onnavigate(); } }}>
    <Card>
      <div class="header">
        <h3>🛒 Consumables</h3>
      </div>
      <div class="pills">
        {#if emptyCount > 0}
          <span class="pill empty">{emptyCount} empty</span>
        {/if}
        {#if lowCount > 0}
          <span class="pill low">{lowCount} low</span>
        {/if}
      </div>
      <ul class="item-list">
        {#each alertItems as c (c.id)}
          {@const st = stockStatus(c)}
          <li>
            <span class="item-emoji">{c.emoji}</span>
            <span class="item-name">{c.name}</span>
            <span class="item-qty" style="color:{STATE_COLOR[st]}">{c.quantity} {c.unit}</span>
          </li>
        {/each}
      </ul>
    </Card>
  </div>
{/if}

<style>
  .widget { cursor: pointer; }
  .header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: var(--space-2); }
  .header h3 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text); }
  .pills { display: flex; gap: 6px; margin-bottom: var(--space-2); }
  .pill { font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 10px; letter-spacing: 0.04em; }
  .pill.empty { background: #33100f; color: #f44336; }
  .pill.low { background: #332610; color: #ff9800; }
  .item-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  .item-list li { display: flex; align-items: center; gap: 6px; font-size: 12px; }
  .item-emoji { font-size: 14px; }
  .item-name { flex: 1; color: var(--text-muted); }
  .item-qty { font-weight: 600; font-size: 11px; }
</style>
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd packages/editor && npm test -- --reporter=verbose test/HomeConsumablesWidget.test.ts
```
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/HomeConsumablesWidget.svelte packages/editor/test/HomeConsumablesWidget.test.ts
git commit -m "feat(consumables): add HomeConsumablesWidget"
```

---

## Task 11: SettingsPage extension

**Files:**
- Modify: `packages/editor/src/lib/components/SettingsPage.svelte`

Read the current SettingsPage.svelte first to understand the existing section pattern (how `workCategories` and `inventoryCategories` are edited), then add a new "Consumables" section at the end with:
1. **Consumable units** — a tag-list editor (add a text input + "Add" button; each unit shown as a chip with a remove ✕ button; save on every add/remove)
2. **Consumable categories** — a CRUD list (name + emoji fields, add row button; inline editing via a simple form; save button per row)

Follow the exact pattern used by the existing `workCategories` section. The key variables and calls to add:

```svelte
<!-- In the script block, add: -->
let newUnit = $state("");
let newCatName = $state("");
let newCatEmoji = $state("📦");

async function addUnit(): Promise<void> {
  const u = newUnit.trim();
  if (!u || store.consumableUnits.includes(u)) return;
  await store.updateConsumableUnits([...store.consumableUnits, u]);
  newUnit = "";
}

async function removeUnit(u: string): Promise<void> {
  await store.updateConsumableUnits(store.consumableUnits.filter((x) => x !== u));
}

async function addConsumableCategory(): Promise<void> {
  const name = newCatName.trim();
  if (!name) return;
  const id = `ccat-${Date.now()}`;
  await store.updateConsumableCategories([...store.consumableCategories, { id, name, emoji: newCatEmoji }]);
  newCatName = ""; newCatEmoji = "📦";
}

async function removeConsumableCategory(id: string): Promise<void> {
  await store.updateConsumableCategories(store.consumableCategories.filter((c) => c.id !== id));
}
```

In the template, add a new `<section>` block following the pattern of existing sections:

```svelte
<section>
  <h2>Consumables</h2>

  <h3>Units</h3>
  <div class="tag-list">
    {#each store.consumableUnits as u}
      <span class="tag">{u} <button onclick={() => removeUnit(u)}>✕</button></span>
    {/each}
  </div>
  <div class="add-row">
    <Input bind:value={newUnit} placeholder="e.g. tablets" onkeydown={(e) => { if (e.key === "Enter") addUnit(); }} />
    <Button onclick={addUnit}>Add unit</Button>
  </div>

  <h3>Categories</h3>
  <div class="cat-list">
    {#each store.consumableCategories as cat (cat.id)}
      <div class="cat-row">
        <span class="cat-emoji">{cat.emoji}</span>
        <span class="cat-name">{cat.name}</span>
        <button class="remove-btn" onclick={() => removeConsumableCategory(cat.id)}>✕</button>
      </div>
    {/each}
  </div>
  <div class="add-row">
    <Input bind:value={newCatEmoji} style="width:48px;text-align:center" maxlength={4} />
    <Input bind:value={newCatName} placeholder="Category name" />
    <Button onclick={addConsumableCategory}>Add category</Button>
  </div>
</section>
```

Add minimal CSS for `.tag-list`, `.tag`, `.add-row`, `.cat-list`, `.cat-row`, `.cat-emoji`, `.cat-name`, `.remove-btn` that matches the surrounding styles.

- [ ] **Step 1: Read the current SettingsPage.svelte**

Read `packages/editor/src/lib/components/SettingsPage.svelte` fully, then implement the changes above following the existing code style.

- [ ] **Step 2: Run existing tests to confirm no regressions**

```bash
cd packages/editor && npm test -- --reporter=verbose test/SettingsPage.test.ts
```
Expected: all existing tests still pass

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/SettingsPage.svelte
git commit -m "feat(consumables): extend SettingsPage with consumable units and categories"
```

---

## Task 12: App.svelte + LayersDropdown wiring

**Files:**
- Modify: `packages/editor/src/lib/components/LayersDropdown.svelte`
- Modify: `packages/editor/src/lib/components/HomePage.svelte`
- Modify: `packages/editor/src/App.svelte`

- [ ] **Step 1: Add consumables layer to LayersDropdown**

In `packages/editor/src/lib/components/LayersDropdown.svelte`, find the `layers` array and add the consumables entry:

```typescript
const layers = [
  { id: "chores",      icon: "✅", label: "Chores"      },
  { id: "inventory",   icon: "📦", label: "Inventory"   },
  { id: "consumables", icon: "🛒", label: "Consumables" },
  { id: "costs",       icon: "💶", label: "Costs"       },
  { id: "works",       icon: "🔧", label: "Works"       },
];
```

- [ ] **Step 2: Add HomeConsumablesWidget to HomePage**

Read `packages/editor/src/lib/components/HomePage.svelte`. Add the import and render the widget alongside the other home widgets. The widget needs `consumableStore` and an `onnavigate` callback.

Add import:
```typescript
import HomeConsumablesWidget from "./HomeConsumablesWidget.svelte";
```

Add `consumableStore` to the Props interface and `let { ..., consumableStore }: Props = $props();`.

In the template, add alongside the existing widgets:
```svelte
<HomeConsumablesWidget
  {consumableStore}
  onnavigate={() => { window.location.hash = "#/consumables"; }}
/>
```

- [ ] **Step 3: Wire everything in App.svelte**

Read `packages/editor/src/App.svelte` fully. Make these additions:

**Imports** (add after the kbStore import):
```typescript
import { createConsumableStore } from "./lib/consumableStore.svelte";
import type { Consumable } from "./lib/consumableStore.svelte";
import ConsumableOverlay from "./lib/components/ConsumableOverlay.svelte";
import ConsumablePinPopup from "./lib/components/ConsumablePinPopup.svelte";
```

**Store** (add after `const kbStore = createKBStore();`):
```typescript
const consumableStore = createConsumableStore();
```

**State** (add alongside the other pin popup state variables):
```typescript
let selectedConsumablePin = $state<{
  consumable: Consumable;
  screenX: number;
  screenY: number;
} | null>(null);
```

**Derived** (add alongside `worksLayerActive` etc.):
```typescript
const consumablesLayerActive = $derived(activeLayers.has("consumables"));
const currentFloorConsumables = $derived(
  consumableStore.consumables.filter((c) => c.placement?.floorId === floorStore.currentFloorId)
);
const consumablesPickerLayer = $derived<PickerLayer>({
  id: "consumables",
  label: "Consumables",
  emoji: "🛒",
  items: consumableStore.consumables.map((c) => ({
    id: c.id,
    name: c.name,
    emoji: c.emoji,
    placed: c.placement !== null,
  })),
});
```

**pickerLayers** — add consumables layer to the existing `pickerLayers` derived:
```typescript
const pickerLayers = $derived<PickerLayer[]>([
  ...(choreLayerActive ? [chorePickerLayer] : []),
  ...(inventoryLayerActive ? [inventoryPickerLayer] : []),
  ...(consumablesLayerActive ? [consumablesPickerLayer] : []),
  ...(costsLayerActive ? [costsPickerLayer] : []),
  ...(worksLayerActive ? [worksPickerLayer] : []),
]);
```

**handleDrop** — add consumables case in `handleDrop()` before the chores case:
```typescript
if (layerId === "consumables") {
  const room = floorStore.floor.rooms.find(r => r.polygon && pointInPolygon({ x: worldX, y: worldY }, r.polygon));
  consumableStore.setPlacement(itemId, {
    floorId: floorStore.currentFloorId,
    roomId: room?.id ?? null,
    position: { x: worldX, y: worldY },
  });
  return;
}
```

**Template** — in the canvas area block (after the worksLayerActive block), add:
```svelte
{#if consumablesLayerActive}
  <ConsumableOverlay
    consumables={currentFloorConsumables}
    viewport={viewportStore.viewport}
    active={true}
    width={canvasWidth}
    height={canvasHeight}
    onclick={(id) => {
      const c = consumableStore.consumables.find((x) => x.id === id);
      if (!c?.placement) return;
      const sp = viewportStore.worldToScreen(c.placement.position);
      selectedConsumablePin = { consumable: c, screenX: sp.x, screenY: sp.y };
    }}
    ondragend={(id, worldPos) => {
      const c = consumableStore.consumables.find((x) => x.id === id);
      if (!c?.placement) return;
      consumableStore.setPlacement(id, { ...c.placement, position: worldPos });
    }}
  />
{/if}
{#if selectedConsumablePin}
  {@const pin = selectedConsumablePin}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div style="position:absolute;inset:0;z-index:55" onclick={() => { selectedConsumablePin = null; }}>
    <ConsumablePinPopup
      consumable={pin.consumable}
      store={consumableStore}
      screenX={pin.screenX}
      screenY={pin.screenY}
      onedit={() => {
        selectedConsumablePin = null;
        window.location.hash = "#/consumables";
      }}
      onremove={async () => {
        await consumableStore.setPlacement(pin.consumable.id, null);
        selectedConsumablePin = null;
      }}
      onclose={() => { selectedConsumablePin = null; }}
    />
  </div>
{/if}
```

**Route** — replace the existing `#/consumables` route (currently just `<ConsumablesPage />`):
```svelte
{:else if currentRoute === "#/consumables"}
  <ConsumablesPage
    store={consumableStore}
    {settingsStore}
    onplaceonmap={(id) => {
      const next = new Set(activeLayers);
      next.add("consumables");
      activeLayers = next;
      pickerHighlightId = id;
      pickerOpen = true;
      window.location.hash = "#/plan";
    }}
  />
```

**HomePage** — pass `consumableStore` to the existing `<HomePage>`:
```svelte
<HomePage
  {floorStore}
  {choreStore}
  {inventoryStore}
  {settingsStore}
  {costsStore}
  {worksStore}
  {consumableStore}
/>
```

- [ ] **Step 4: Run all frontend tests**

```bash
cd packages/editor && npm test
```
Expected: all tests pass (no regressions)

- [ ] **Step 5: Run all backend tests**

```bash
cd packages/backend && python -m pytest tests/ -v
```
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/LayersDropdown.svelte \
        packages/editor/src/lib/components/HomePage.svelte \
        packages/editor/src/App.svelte
git commit -m "feat(consumables): wire overlay, picker, popup, route, home widget in App"
```

---

## Task 13: Final check + PR

- [ ] **Step 1: Run full test suite**

```bash
cd packages/backend && python -m pytest tests/ -v
cd packages/editor && npm test
```
Expected: all pass

- [ ] **Step 2: Create PR**

```bash
git push -u origin HEAD
gh pr create \
  --title "feat: consumables module — stock tracking, floor plan badges, low-stock alerts" \
  --body "$(cat <<'EOF'
## Summary
- New standalone consumables module: track stock levels (batteries, cleaning products, food staples, etc.)
- Vertical bar SVG badge on floor plan with green/orange/red stock state
- Transaction history: set new quantity → backend derives delta and logs it
- Low-stock alerts in the consumables list, floor plan badge, and home dashboard widget
- Settings extended with editable consumable units and consumable categories

## Test plan
- [ ] Run `cd packages/backend && python -m pytest tests/ -v` — all pass
- [ ] Run `cd packages/editor && npm test` — all pass
- [ ] Open app, navigate to Consumables, add an item, set a quantity
- [ ] Place item on floor plan via the map layer, verify vertical badge appears
- [ ] Set quantity below minimum, verify badge turns orange on map and LOW badge appears in list
- [ ] Set quantity to 0, verify red empty badge
- [ ] Check Home page — low/empty items appear in the Consumables widget
- [ ] Go to Settings, add a custom unit and a consumable category
EOF
)"
```
