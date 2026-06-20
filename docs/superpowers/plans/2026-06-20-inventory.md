# Inventory Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a household inventory tracker — backend CRUD API, floor-plan pin overlay on a new layer system, drag-from-picker placement, and a full list page with item detail modals.

**Architecture:** Backend follows the exact chores pattern (models → persistence → routes). The frontend replaces `choreMode: boolean` with a generic `activeLayers: Set<string>` that drives a "Layers" dropdown and controls which SVG overlays and picker panels are rendered. The inventory module adds `inventoryStore`, `InventoryOverlay`, `InventoryPickerPanel`, `InventoryPage`, and `InventoryModal`.

**Tech Stack:** Python / FastAPI / Pydantic (backend), Svelte 5 runes / TypeScript / Vitest / jsdom (frontend).

---

## File Map

**New backend:**
- `packages/backend/src/myhome/models_inventory.py`
- `packages/backend/src/myhome/persistence_inventory.py`
- `packages/backend/src/myhome/routes/inventory.py`
- `packages/backend/tests/test_inventory_persistence.py`
- `packages/backend/tests/test_inventory.py`

**Modified backend:**
- `packages/backend/src/myhome/main.py` — register inventory router

**New frontend:**
- `packages/editor/src/lib/inventoryStore.svelte.ts`
- `packages/editor/src/lib/components/LayersDropdown.svelte`
- `packages/editor/src/lib/components/InventoryOverlay.svelte`
- `packages/editor/src/lib/components/InventoryPinPopup.svelte`
- `packages/editor/src/lib/components/InventoryPickerPanel.svelte`
- `packages/editor/src/lib/components/InventoryModal.svelte`
- `packages/editor/test/inventoryStore.test.ts`
- `packages/editor/test/InventoryOverlay.test.ts`

**Modified frontend:**
- `packages/editor/src/App.svelte` — layers refactor + inventory wiring (Tasks 4–7)
- `packages/editor/src/lib/components/InventoryPage.svelte` — replace stub (Task 7)

---

## Task 1: Backend models & persistence

**Files:**
- Create: `packages/backend/src/myhome/models_inventory.py`
- Create: `packages/backend/src/myhome/persistence_inventory.py`
- Create: `packages/backend/tests/test_inventory_persistence.py`

- [ ] **Step 1: Write the failing persistence tests**

```python
# packages/backend/tests/test_inventory_persistence.py
from myhome.models_inventory import InventoryDocument, InventoryItem, InventoryPlacement, InventoryPosition
from myhome.persistence_inventory import load_inventory, save_inventory


def make_doc() -> InventoryDocument:
    return InventoryDocument(
        version=1,
        items=[
            InventoryItem(
                id="i1",
                name="Samsung TV",
                emoji="📺",
                category="Electronics",
                purchasePrice=1200.0,
                warrantyExpiryDate="2026-05-12",
                placement=InventoryPlacement(
                    floorId="f1",
                    roomId="r1",
                    position=InventoryPosition(x=3.4, y=2.1),
                ),
            )
        ],
    )


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    doc = load_inventory()
    assert doc.items == []


def test_save_creates_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    assert (tmp_path / "inventory.json").exists()


def test_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    loaded = load_inventory()
    assert loaded.items[0].id == "i1"
    assert loaded.items[0].emoji == "📺"
    assert loaded.items[0].purchasePrice == 1200.0
    assert loaded.items[0].placement.position.x == 3.4
    assert loaded.items[0].placement.roomId == "r1"


def test_item_without_placement_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    doc = InventoryDocument(
        items=[InventoryItem(id="i2", name="Chair", emoji="🪑")]
    )
    save_inventory(doc)
    loaded = load_inventory()
    assert loaded.items[0].placement is None


def test_save_creates_data_dir_if_missing(tmp_path, monkeypatch):
    nested = tmp_path / "nested" / "data"
    monkeypatch.setenv("DATA_DIR", str(nested))
    save_inventory(make_doc())
    assert (nested / "inventory.json").exists()
```

- [ ] **Step 2: Run to confirm all tests fail**

```bash
cd /projects/myhome && python -m pytest packages/backend/tests/test_inventory_persistence.py -v
```

Expected: `ModuleNotFoundError: No module named 'myhome.models_inventory'`

- [ ] **Step 3: Create `models_inventory.py`**

```python
# packages/backend/src/myhome/models_inventory.py
from __future__ import annotations
from pydantic import BaseModel


class InventoryPosition(BaseModel):
    x: float
    y: float


class InventoryPlacement(BaseModel):
    floorId: str
    roomId: str | None = None
    position: InventoryPosition


class InventoryItem(BaseModel):
    id: str
    name: str
    emoji: str = "📦"
    category: str = ""
    brand: str | None = None
    model: str | None = None
    serialNumber: str | None = None
    purchaseDate: str | None = None
    purchasePrice: float | None = None
    warrantyExpiryDate: str | None = None
    notes: str = ""
    placement: InventoryPlacement | None = None


class InventoryDocument(BaseModel):
    version: int = 1
    items: list[InventoryItem] = []


class InventoryItemCreate(BaseModel):
    name: str
    emoji: str = "📦"
    category: str = ""
    brand: str | None = None
    model: str | None = None
    serialNumber: str | None = None
    purchaseDate: str | None = None
    purchasePrice: float | None = None
    warrantyExpiryDate: str | None = None
    notes: str = ""


class InventoryItemUpdate(BaseModel):
    name: str | None = None
    emoji: str | None = None
    category: str | None = None
    brand: str | None = None
    model: str | None = None
    serialNumber: str | None = None
    purchaseDate: str | None = None
    purchasePrice: float | None = None
    warrantyExpiryDate: str | None = None
    notes: str | None = None


class PlacementUpdate(BaseModel):
    placement: InventoryPlacement | None = None
```

- [ ] **Step 4: Create `persistence_inventory.py`**

```python
# packages/backend/src/myhome/persistence_inventory.py
import json
import os
from pathlib import Path

from .models_inventory import InventoryDocument


def _inventory_file() -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "inventory.json"


def load_inventory() -> InventoryDocument:
    path = _inventory_file()
    if not path.exists():
        return InventoryDocument()
    with path.open() as f:
        return InventoryDocument.model_validate(json.load(f))


def save_inventory(doc: InventoryDocument) -> None:
    path = _inventory_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)
```

- [ ] **Step 5: Run tests — expect all pass**

```bash
cd /projects/myhome && python -m pytest packages/backend/tests/test_inventory_persistence.py -v
```

Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/models_inventory.py \
        packages/backend/src/myhome/persistence_inventory.py \
        packages/backend/tests/test_inventory_persistence.py
git commit -m "feat: inventory backend models and persistence"
```

---

## Task 2: Backend routes

**Files:**
- Create: `packages/backend/src/myhome/routes/inventory.py`
- Modify: `packages/backend/src/myhome/main.py`
- Create: `packages/backend/tests/test_inventory.py`

- [ ] **Step 1: Write the failing route tests**

```python
# packages/backend/tests/test_inventory.py
import pytest
from fastapi.testclient import TestClient
from myhome.main import app
from myhome.models_inventory import InventoryDocument, InventoryItem, InventoryPlacement, InventoryPosition
from myhome.persistence_inventory import save_inventory


def make_doc() -> InventoryDocument:
    return InventoryDocument(
        items=[
            InventoryItem(
                id="i1",
                name="Samsung TV",
                emoji="📺",
                category="Electronics",
                purchasePrice=1200.0,
                warrantyExpiryDate="2026-05-12",
            )
        ]
    )


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return TestClient(app)


# --- GET /api/inventory ---

def test_get_inventory_empty_when_no_file(client):
    resp = client.get("/api/inventory")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_get_inventory_returns_saved_data(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    resp = TestClient(app).get("/api/inventory")
    assert resp.status_code == 200
    assert resp.json()["items"][0]["id"] == "i1"


# --- POST /api/inventory/items ---

def test_create_item(client):
    payload = {
        "name": "Washing machine",
        "emoji": "🧺",
        "category": "Appliance",
        "purchasePrice": 650.0,
    }
    resp = client.post("/api/inventory/items", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Washing machine"
    assert data["emoji"] == "🧺"
    assert data["purchasePrice"] == 650.0
    assert "id" in data
    assert data["placement"] is None
    # Verify persisted
    get = client.get("/api/inventory")
    assert any(i["name"] == "Washing machine" for i in get.json()["items"])


def test_create_item_defaults(client):
    resp = client.post("/api/inventory/items", json={"name": "Generic item"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["emoji"] == "📦"
    assert data["category"] == ""
    assert data["placement"] is None


# --- PUT /api/inventory/items/{id} ---

def test_update_item_partial(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    resp = c.put("/api/inventory/items/i1", json={"name": "LG TV", "purchasePrice": 900.0})
    assert resp.status_code == 204
    item = c.get("/api/inventory").json()["items"][0]
    assert item["name"] == "LG TV"
    assert item["purchasePrice"] == 900.0
    assert item["emoji"] == "📺"          # unchanged
    assert item["category"] == "Electronics"  # unchanged


def test_update_item_404(client):
    resp = client.put("/api/inventory/items/nonexistent", json={"name": "X"})
    assert resp.status_code == 404


# --- DELETE /api/inventory/items/{id} ---

def test_delete_item(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    resp = c.delete("/api/inventory/items/i1")
    assert resp.status_code == 204
    assert c.get("/api/inventory").json()["items"] == []


def test_delete_item_404(client):
    resp = client.delete("/api/inventory/items/nonexistent")
    assert resp.status_code == 404


# --- PUT /api/inventory/items/{id}/placement ---

def test_set_placement(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    payload = {
        "placement": {
            "floorId": "f1",
            "roomId": "r1",
            "position": {"x": 3.4, "y": 2.1},
        }
    }
    resp = c.put("/api/inventory/items/i1/placement", json=payload)
    assert resp.status_code == 204
    item = c.get("/api/inventory").json()["items"][0]
    assert item["placement"]["floorId"] == "f1"
    assert item["placement"]["position"]["x"] == 3.4
    assert item["placement"]["roomId"] == "r1"


def test_clear_placement(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    doc = make_doc()
    doc.items[0].placement = InventoryPlacement(
        floorId="f1", roomId="r1", position=InventoryPosition(x=1.0, y=2.0)
    )
    save_inventory(doc)
    c = TestClient(app)
    resp = c.put("/api/inventory/items/i1/placement", json={"placement": None})
    assert resp.status_code == 204
    assert c.get("/api/inventory").json()["items"][0]["placement"] is None


def test_placement_404(client):
    resp = client.put(
        "/api/inventory/items/nonexistent/placement",
        json={"placement": None},
    )
    assert resp.status_code == 404
```

- [ ] **Step 2: Run to confirm all tests fail**

```bash
cd /projects/myhome && python -m pytest packages/backend/tests/test_inventory.py -v
```

Expected: errors about missing route or 404 responses.

- [ ] **Step 3: Create `routes/inventory.py`**

```python
# packages/backend/src/myhome/routes/inventory.py
import uuid

from fastapi import APIRouter, HTTPException

from ..models_inventory import (
    InventoryDocument,
    InventoryItem,
    InventoryItemCreate,
    InventoryItemUpdate,
    PlacementUpdate,
)
from ..persistence_inventory import load_inventory, save_inventory

router = APIRouter()


@router.get("/api/inventory", response_model=InventoryDocument)
def get_inventory() -> InventoryDocument:
    return load_inventory()


@router.post("/api/inventory/items", response_model=InventoryItem, status_code=201)
def create_item(body: InventoryItemCreate) -> InventoryItem:
    doc = load_inventory()
    item = InventoryItem(id=str(uuid.uuid4()), **body.model_dump())
    doc.items.append(item)
    save_inventory(doc)
    return item


@router.put("/api/inventory/items/{id}", status_code=204)
def update_item(id: str, body: InventoryItemUpdate) -> None:
    doc = load_inventory()
    item = next((i for i in doc.items if i.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    save_inventory(doc)


@router.delete("/api/inventory/items/{id}", status_code=204)
def delete_item(id: str) -> None:
    doc = load_inventory()
    before = len(doc.items)
    doc.items = [i for i in doc.items if i.id != id]
    if len(doc.items) == before:
        raise HTTPException(status_code=404)
    save_inventory(doc)


@router.put("/api/inventory/items/{id}/placement", status_code=204)
def update_placement(id: str, body: PlacementUpdate) -> None:
    doc = load_inventory()
    item = next((i for i in doc.items if i.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    item.placement = body.placement
    save_inventory(doc)
```

- [ ] **Step 4: Register the router in `main.py`**

Add one import and one `include_router` call:

```python
# packages/backend/src/myhome/main.py
import os
from pathlib import Path
from fastapi import FastAPI
from .routes import house, svg, ha, chores
from .routes import inventory          # ← add this line

app = FastAPI(title="MyHome Backend", version="0.1.0")
app.include_router(house.router)
app.include_router(svg.router)
app.include_router(ha.router)
app.include_router(chores.router)
app.include_router(inventory.router)   # ← add this line

_static_dir = Path(os.environ.get("STATIC_DIR", "/app/static"))
if _static_dir.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
```

- [ ] **Step 5: Run tests — expect all pass**

```bash
cd /projects/myhome && python -m pytest packages/backend/tests/test_inventory.py packages/backend/tests/test_inventory_persistence.py -v
```

Expected: `16 passed`

- [ ] **Step 6: Run the full backend test suite to check for regressions**

```bash
cd /projects/myhome && python -m pytest packages/backend/tests/ -v
```

Expected: all existing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add packages/backend/src/myhome/models_inventory.py \
        packages/backend/src/myhome/persistence_inventory.py \
        packages/backend/src/myhome/routes/inventory.py \
        packages/backend/src/myhome/main.py \
        packages/backend/tests/test_inventory.py
git commit -m "feat: inventory CRUD backend routes"
```

---

## Task 3: Frontend inventory store

**Files:**
- Create: `packages/editor/src/lib/inventoryStore.svelte.ts`
- Create: `packages/editor/test/inventoryStore.test.ts`

- [ ] **Step 1: Write the failing store tests**

```typescript
// packages/editor/test/inventoryStore.test.ts
import { describe, it, expect, afterEach, vi } from "vitest";
import { createInventoryStore } from "../src/lib/inventoryStore.svelte";
import type { InventoryItem } from "../src/lib/inventoryStore.svelte";

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

function makeItem(overrides: Partial<InventoryItem> = {}): InventoryItem {
  return {
    id: "i1",
    name: "TV",
    emoji: "📺",
    category: "Electronics",
    brand: null,
    model: null,
    serialNumber: null,
    purchaseDate: null,
    purchasePrice: 1200,
    warrantyExpiryDate: null,
    notes: "",
    placement: null,
    ...overrides,
  };
}

const emptyDoc = { version: 1, items: [] };

describe("inventoryStore — init", () => {
  it("loads items from API", async () => {
    const doc = { version: 1, items: [makeItem()] };
    vi.stubGlobal("fetch", makeFetch(200, doc));
    const store = createInventoryStore();
    await tick();
    expect(store.items.length).toBe(1);
    expect(store.items[0].id).toBe("i1");
    expect(store.loaded).toBe(true);
  });

  it("marks loaded on fetch error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("net fail")));
    const store = createInventoryStore();
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("net fail");
  });
});

describe("inventoryStore — warrantyStatus", () => {
  it("returns ok when no warrantyExpiryDate", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createInventoryStore();
    await tick();
    expect(store.warrantyStatus(makeItem({ warrantyExpiryDate: null }))).toBe("ok");
  });

  it("returns ok when expiry more than 30 days away", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createInventoryStore();
    await tick();
    const future = new Date(Date.now() + 31 * 86400 * 1000).toISOString().slice(0, 10);
    expect(store.warrantyStatus(makeItem({ warrantyExpiryDate: future }))).toBe("ok");
  });

  it("returns soon when expiry 30 days or less away but not past", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createInventoryStore();
    await tick();
    const soon = new Date(Date.now() + 15 * 86400 * 1000).toISOString().slice(0, 10);
    expect(store.warrantyStatus(makeItem({ warrantyExpiryDate: soon }))).toBe("soon");
  });

  it("returns soon at exactly 30 days", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createInventoryStore();
    await tick();
    const exactly30 = new Date(Date.now() + 30 * 86400 * 1000).toISOString().slice(0, 10);
    expect(store.warrantyStatus(makeItem({ warrantyExpiryDate: exactly30 }))).toBe("soon");
  });

  it("returns expired when expiry is in the past", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createInventoryStore();
    await tick();
    const past = new Date(Date.now() - 86400 * 1000).toISOString().slice(0, 10);
    expect(store.warrantyStatus(makeItem({ warrantyExpiryDate: past }))).toBe("expired");
  });
});

describe("inventoryStore — placedItems / unplacedItems", () => {
  it("splits by placement presence", async () => {
    const placed = makeItem({ id: "p1", placement: { floorId: "f1", roomId: null, position: { x: 1, y: 2 } } });
    const unplaced = makeItem({ id: "u1", placement: null });
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, items: [placed, unplaced] }));
    const store = createInventoryStore();
    await tick();
    expect(store.placedItems().length).toBe(1);
    expect(store.placedItems()[0].id).toBe("p1");
    expect(store.unplacedItems().length).toBe(1);
    expect(store.unplacedItems()[0].id).toBe("u1");
  });

  it("returns empty arrays when all items are unplaced", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, items: [makeItem()] }));
    const store = createInventoryStore();
    await tick();
    expect(store.placedItems()).toEqual([]);
    expect(store.unplacedItems().length).toBe(1);
  });
});
```

- [ ] **Step 2: Run to confirm tests fail**

```bash
cd /projects/myhome && npm --workspace packages/editor run test -- inventoryStore
```

Expected: `Cannot find module '../src/lib/inventoryStore.svelte'`

- [ ] **Step 3: Create `inventoryStore.svelte.ts`**

```typescript
// packages/editor/src/lib/inventoryStore.svelte.ts

export interface InventoryPosition {
  x: number;
  y: number;
}

export interface InventoryPlacement {
  floorId: string;
  roomId: string | null;
  position: InventoryPosition;
}

export interface InventoryItem {
  id: string;
  name: string;
  emoji: string;
  category: string;
  brand: string | null;
  model: string | null;
  serialNumber: string | null;
  purchaseDate: string | null;
  purchasePrice: number | null;
  warrantyExpiryDate: string | null;
  notes: string;
  placement: InventoryPlacement | null;
}

export type WarrantyStatus = "ok" | "soon" | "expired";

export function createInventoryStore() {
  const items = $state<InventoryItem[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    try {
      const resp = await fetch("/api/inventory");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: { items: InventoryItem[] } = await resp.json();
      items.length = 0;
      for (const i of doc.items) items.push(i);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  function warrantyStatus(item: InventoryItem): WarrantyStatus {
    if (!item.warrantyExpiryDate) return "ok";
    const expiry = new Date(item.warrantyExpiryDate).getTime();
    const now = Date.now();
    if (expiry < now) return "expired";
    if (expiry - now <= 30 * 86400 * 1000) return "soon";
    return "ok";
  }

  function placedItems(): InventoryItem[] {
    return items.filter((i) => i.placement !== null);
  }

  function unplacedItems(): InventoryItem[] {
    return items.filter((i) => i.placement === null);
  }

  async function createItem(
    data: Omit<InventoryItem, "id" | "placement">
  ): Promise<void> {
    const resp = await fetch("/api/inventory/items", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateItem(
    id: string,
    patch: Partial<Omit<InventoryItem, "id" | "placement">>
  ): Promise<void> {
    const resp = await fetch(`/api/inventory/items/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteItem(id: string): Promise<void> {
    const resp = await fetch(`/api/inventory/items/${id}`, {
      method: "DELETE",
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function setPlacement(
    id: string,
    placement: InventoryPlacement | null
  ): Promise<void> {
    const resp = await fetch(`/api/inventory/items/${id}/placement`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ placement }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  init();

  return {
    get items() { return items as InventoryItem[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    warrantyStatus,
    placedItems,
    unplacedItems,
    createItem,
    updateItem,
    deleteItem,
    setPlacement,
  };
}
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
cd /projects/myhome && npm --workspace packages/editor run test -- inventoryStore
```

Expected: `14 passed`

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/inventoryStore.svelte.ts \
        packages/editor/test/inventoryStore.test.ts
git commit -m "feat: inventory frontend store with warrantyStatus helpers"
```

---

## Task 4: Layers system refactor

Replace `choreMode: boolean` in `App.svelte` with a generic `activeLayers: Set<string>`. Add `LayersDropdown.svelte`.

**Files:**
- Create: `packages/editor/src/lib/components/LayersDropdown.svelte`
- Modify: `packages/editor/src/App.svelte`

- [ ] **Step 1: Create `LayersDropdown.svelte`**

```svelte
<!-- packages/editor/src/lib/components/LayersDropdown.svelte -->
<script lang="ts">
  interface Props {
    activeLayers: Set<string>;
    ontoggle: (layer: string) => void;
  }
  let { activeLayers, ontoggle }: Props = $props();

  let open = $state(false);

  const layers = [
    { id: "chores", icon: "✅", label: "Chores" },
    { id: "inventory", icon: "📦", label: "Inventory" },
  ];

  function handleClickOutside(e: MouseEvent) {
    if (!(e.target as HTMLElement).closest(".layers-dropdown")) open = false;
  }
</script>

<svelte:window onclick={handleClickOutside} />

<div class="layers-dropdown">
  <button
    class="layers-btn"
    class:active={activeLayers.size > 0}
    onclick={() => { open = !open; }}
    title="Toggle map layers"
  >
    Layers <span class="caret">▾</span>
  </button>

  {#if open}
    <div class="dropdown">
      {#each layers as layer}
        <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
        <label class="layer-row" class:checked={activeLayers.has(layer.id)}>
          <input
            type="checkbox"
            checked={activeLayers.has(layer.id)}
            onchange={() => ontoggle(layer.id)}
          />
          <span class="layer-icon">{layer.icon}</span>
          <span>{layer.label}</span>
        </label>
      {/each}
    </div>
  {/if}
</div>

<style>
  .layers-dropdown { position: relative; }

  .layers-btn {
    background: #2a2a4a; border: 1px solid #3a3a5a; color: #aaf;
    padding: 3px 10px; border-radius: 4px; font-size: 11px;
    cursor: pointer; display: flex; align-items: center; gap: 5px;
    white-space: nowrap; height: 26px;
  }
  .layers-btn:hover { background: #333360; }
  .layers-btn.active { border-color: #5566cc; color: #ccf; }
  .caret { font-size: 9px; }

  .dropdown {
    position: absolute; top: calc(100% + 4px); right: 0;
    background: #1a1a30; border: 1px solid #3a3a5a;
    border-radius: 6px; padding: 6px; min-width: 160px;
    z-index: 100; box-shadow: 0 4px 12px #0006;
  }

  .layer-row {
    display: flex; align-items: center; gap: 8px;
    padding: 5px 8px; border-radius: 4px; cursor: pointer;
    color: #aaa; font-size: 12px;
  }
  .layer-row:hover { background: #2a2a4a; }
  .layer-row.checked { color: #eee; }
  .layer-row input { accent-color: #5566cc; cursor: pointer; }
  .layer-icon { font-size: 14px; width: 18px; text-align: center; }
</style>
```

- [ ] **Step 2: Refactor `App.svelte` — state (script section)**

In the `<script>` block of `packages/editor/src/App.svelte`, make the following changes:

**Add import** (alongside existing component imports):
```typescript
import LayersDropdown from "./lib/components/LayersDropdown.svelte";
```

**Replace** the `choreMode` state line:
```typescript
// REMOVE:
let choreMode = $state(false);

// ADD:
let activeLayers = $state(new Set<string>());
const choreLayerActive = $derived(activeLayers.has("chores"));
const inventoryLayerActive = $derived(activeLayers.has("inventory"));

function toggleLayer(layer: string): void {
  const next = new Set(activeLayers);
  if (next.has(layer)) next.delete(layer);
  else next.add(layer);
  activeLayers = next;
  if (next.has("chores")) toolStore.setTool("select");
}
```

**Add effect** to clear selectedBadge when chore layer is turned off (add anywhere after the `toggleLayer` function):
```typescript
$effect(() => {
  if (!choreLayerActive) selectedBadge = null;
});
```

- [ ] **Step 3: Refactor `App.svelte` — template**

In the template section, make these replacements:

**Replace** the 📋 icon button (the `onclick={() => { choreMode = !choreMode; ... }}` button) with:
```svelte
<LayersDropdown {activeLayers} ontoggle={toggleLayer} />
```

**Replace** `{#if !choreMode}` (the drawing toolbar conditional) with:
```svelte
{#if !choreLayerActive}
```

**In** the `<ChoreOverlay ... />` tag, change `{choreMode}` to:
```svelte
choreMode={choreLayerActive}
```

**Replace** `{#if choreMode}` (the ChorePanel conditional) with:
```svelte
{#if choreLayerActive}
```

- [ ] **Step 4: Verify chore tests still pass**

```bash
cd /projects/myhome && npm --workspace packages/editor run test
```

Expected: all existing tests pass (no regressions). If `App.test.ts` references `choreMode` in its DOM queries, update those queries to match the new dropdown.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/LayersDropdown.svelte \
        packages/editor/src/App.svelte
git commit -m "feat: replace choreMode with generic activeLayers + LayersDropdown"
```

---

## Task 5: InventoryOverlay + floor plan pin wiring

**Files:**
- Create: `packages/editor/src/lib/components/InventoryOverlay.svelte`
- Create: `packages/editor/src/lib/components/InventoryPinPopup.svelte`
- Create: `packages/editor/test/InventoryOverlay.test.ts`
- Modify: `packages/editor/src/App.svelte`

- [ ] **Step 1: Write failing InventoryOverlay tests**

```typescript
// packages/editor/test/InventoryOverlay.test.ts
import { describe, it, expect, afterEach, vi } from "vitest";
import { mount, unmount } from "svelte";
import InventoryOverlay from "../src/lib/components/InventoryOverlay.svelte";
import type { InventoryItem } from "../src/lib/inventoryStore.svelte";

afterEach(() => vi.unstubAllGlobals());

function makeItem(overrides: Partial<InventoryItem> = {}): InventoryItem {
  return {
    id: "i1", name: "TV", emoji: "📺", category: "", brand: null,
    model: null, serialNumber: null, purchaseDate: null,
    purchasePrice: null, warrantyExpiryDate: null, notes: "",
    placement: { floorId: "f1", roomId: null, position: { x: 1, y: 2 } },
    ...overrides,
  };
}

const viewport = { panX: 0, panY: 0, zoom: 100 };

describe("InventoryOverlay", () => {
  it("renders one emoji pin per placed item", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(InventoryOverlay, {
      target,
      props: {
        items: [makeItem({ id: "i1", emoji: "📺" }), makeItem({ id: "i2", emoji: "🧺" })],
        viewport,
        active: true,
        width: 800,
        height: 600,
        onclick: vi.fn(),
        ondragend: vi.fn(),
      },
    });

    const emojiTexts = Array.from(target.querySelectorAll("text")).filter(
      (t) => t.textContent === "📺" || t.textContent === "🧺"
    );
    expect(emojiTexts.length).toBe(2);

    unmount(comp);
    target.remove();
  });

  it("renders no pins for unplaced items", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(InventoryOverlay, {
      target,
      props: {
        items: [makeItem({ placement: null })],
        viewport,
        active: true,
        width: 800,
        height: 600,
        onclick: vi.fn(),
        ondragend: vi.fn(),
      },
    });

    const svgGroups = target.querySelectorAll("svg g");
    expect(svgGroups.length).toBe(0);

    unmount(comp);
    target.remove();
  });

  it("applies orange drop-shadow for soon-expiring warranty", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);

    const soonDate = new Date(Date.now() + 15 * 86400 * 1000)
      .toISOString()
      .slice(0, 10);

    const comp = mount(InventoryOverlay, {
      target,
      props: {
        items: [makeItem({ warrantyExpiryDate: soonDate })],
        viewport,
        active: true,
        width: 800,
        height: 600,
        onclick: vi.fn(),
        ondragend: vi.fn(),
      },
    });

    const emojiText = Array.from(target.querySelectorAll("text")).find(
      (t) => t.textContent === "📺"
    );
    expect(emojiText?.getAttribute("style")).toContain(
      "drop-shadow(0 0 6px #ff9800)"
    );

    unmount(comp);
    target.remove();
  });

  it("applies red drop-shadow for expired warranty", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);

    const pastDate = new Date(Date.now() - 86400 * 1000)
      .toISOString()
      .slice(0, 10);

    const comp = mount(InventoryOverlay, {
      target,
      props: {
        items: [makeItem({ warrantyExpiryDate: pastDate })],
        viewport,
        active: true,
        width: 800,
        height: 600,
        onclick: vi.fn(),
        ondragend: vi.fn(),
      },
    });

    const emojiText = Array.from(target.querySelectorAll("text")).find(
      (t) => t.textContent === "📺"
    );
    expect(emojiText?.getAttribute("style")).toContain(
      "drop-shadow(0 0 6px #f44336)"
    );

    unmount(comp);
    target.remove();
  });

  it("sets pointer-events none when not active", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(InventoryOverlay, {
      target,
      props: {
        items: [makeItem()],
        viewport,
        active: false,
        width: 800,
        height: 600,
        onclick: vi.fn(),
        ondragend: vi.fn(),
      },
    });

    const g = target.querySelector("svg g");
    expect(g?.getAttribute("style")).toContain("pointer-events:none");

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run to confirm all tests fail**

```bash
cd /projects/myhome && npm --workspace packages/editor run test -- InventoryOverlay
```

Expected: `Cannot find module '../src/lib/components/InventoryOverlay.svelte'`

- [ ] **Step 3: Create `InventoryOverlay.svelte`**

```svelte
<!-- packages/editor/src/lib/components/InventoryOverlay.svelte -->
<script lang="ts">
  import { worldToScreen, type ViewportState } from "../viewportStore.svelte";
  import type { InventoryItem } from "../inventoryStore.svelte";

  interface Props {
    items: InventoryItem[];
    viewport: ViewportState;
    active: boolean;
    width: number;
    height: number;
    onclick: (itemId: string) => void;
    ondragend: (itemId: string, worldPos: { x: number; y: number }) => void;
  }

  let { items, viewport, active, width, height, onclick, ondragend }: Props =
    $props();

  function glowFilter(item: InventoryItem): string {
    if (!item.warrantyExpiryDate) return "drop-shadow(0 1px 4px #0008)";
    const expiry = new Date(item.warrantyExpiryDate).getTime();
    const now = Date.now();
    if (expiry < now) return "drop-shadow(0 0 6px #f44336)";
    if (expiry - now <= 30 * 86400 * 1000)
      return "drop-shadow(0 0 6px #ff9800)";
    return "drop-shadow(0 1px 4px #0008)";
  }

  let dragId = $state<string | null>(null);
  let dragStartScreen = $state({ x: 0, y: 0 });
  let dragStartWorld = $state({ x: 0, y: 0 });
  let dragOffsetScreen = $state({ x: 0, y: 0 });

  function pinScreen(item: InventoryItem): { x: number; y: number } | null {
    if (!item.placement) return null;
    const base = worldToScreen(item.placement.position, viewport);
    if (dragId === item.id) {
      return {
        x: base.x + dragOffsetScreen.x,
        y: base.y + dragOffsetScreen.y,
      };
    }
    return base;
  }

  function handlePointerDown(e: PointerEvent, item: InventoryItem): void {
    if (!active || !item.placement) return;
    e.stopPropagation();
    (e.currentTarget as SVGElement).setPointerCapture(e.pointerId);
    dragId = item.id;
    dragStartScreen = { x: e.clientX, y: e.clientY };
    dragStartWorld = {
      x: item.placement.position.x,
      y: item.placement.position.y,
    };
    dragOffsetScreen = { x: 0, y: 0 };
  }

  function handlePointerMove(e: PointerEvent): void {
    if (!dragId) return;
    dragOffsetScreen = {
      x: e.clientX - dragStartScreen.x,
      y: e.clientY - dragStartScreen.y,
    };
  }

  function handlePointerUp(e: PointerEvent, item: InventoryItem): void {
    if (!dragId || dragId !== item.id) return;
    const dx = e.clientX - dragStartScreen.x;
    const dy = e.clientY - dragStartScreen.y;
    const moved = Math.hypot(dx, dy) > 4;
    if (moved) {
      ondragend(item.id, {
        x: dragStartWorld.x + dx / viewport.zoom,
        y: dragStartWorld.y + dy / viewport.zoom,
      });
    } else {
      onclick(item.id);
    }
    dragId = null;
    dragOffsetScreen = { x: 0, y: 0 };
  }

  const placedItems = $derived(items.filter((i) => i.placement !== null));
</script>

<svelte:window onpointermove={handlePointerMove} />

<svg
  {width}
  {height}
  style="position:absolute;top:0;left:0;pointer-events:none;overflow:visible"
>
  {#each placedItems as item (item.id)}
    {@const sp = pinScreen(item)}
    {#if sp}
      <g
        transform="translate({sp.x},{sp.y})"
        style="pointer-events:{active ? 'all' : 'none'};cursor:{active
          ? dragId === item.id
            ? 'grabbing'
            : 'grab'
          : 'default'}"
        onpointerdown={(e) => handlePointerDown(e, item)}
        onpointerup={(e) => handlePointerUp(e, item)}
      >
        <text
          text-anchor="middle"
          dominant-baseline="central"
          font-size="26"
          style="filter:{glowFilter(item)};user-select:none;pointer-events:none"
        >{item.emoji}</text>
        <rect
          x="-30" y="15" width="60" height="13" rx="3"
          fill="#1a1a3a" fill-opacity="0.85" stroke="#5566cc44" stroke-width="1"
        />
        <text
          x="0" y="22"
          text-anchor="middle" font-size="9" fill="#99a"
          style="pointer-events:none;user-select:none"
        >{item.name.length > 14
            ? item.name.slice(0, 13) + "…"
            : item.name}</text>
      </g>
    {/if}
  {/each}
</svg>
```

- [ ] **Step 4: Run InventoryOverlay tests — expect all pass**

```bash
cd /projects/myhome && npm --workspace packages/editor run test -- InventoryOverlay
```

Expected: `5 passed`

- [ ] **Step 5: Create `InventoryPinPopup.svelte`**

```svelte
<!-- packages/editor/src/lib/components/InventoryPinPopup.svelte -->
<script lang="ts">
  import type { InventoryItem } from "../inventoryStore.svelte";

  interface Props {
    item: InventoryItem;
    screenX: number;
    screenY: number;
    onedit: () => void;
    onremove: () => void;
    onclose: () => void;
  }
  let { item, screenX, screenY, onedit, onremove, onclose }: Props = $props();

  function warrantyLabel(): string {
    if (!item.warrantyExpiryDate) return "—";
    const expiry = new Date(item.warrantyExpiryDate).getTime();
    const now = Date.now();
    const days = Math.round((expiry - now) / 86400000);
    if (days < 0) return "Expired";
    if (days === 0) return "Expires today";
    return `${days}d remaining`;
  }

  function warrantyColor(): string {
    if (!item.warrantyExpiryDate) return "#556";
    const expiry = new Date(item.warrantyExpiryDate).getTime();
    const now = Date.now();
    if (expiry < now) return "#f44336";
    if (expiry - now <= 30 * 86400 * 1000) return "#ff9800";
    return "#4caf50";
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
  class="popup"
  style="left:{screenX}px;top:{screenY + 30}px"
  onclick|stopPropagation={() => {}}
>
  <div class="popup-name">{item.emoji} {item.name}</div>
  {#if item.category}
    <div class="popup-row">{item.category}</div>
  {/if}
  <div class="popup-row" style="color:{warrantyColor()}">
    Warranty: {warrantyLabel()}
  </div>
  <div class="popup-actions">
    <button onclick={onedit}>✏️ Edit</button>
    <button onclick={onremove}>✕ Remove</button>
    <button onclick={onclose}>Close</button>
  </div>
</div>

<style>
  .popup {
    position: absolute;
    background: #1e1e3a; border: 1px solid #3a3a5a; border-radius: 8px;
    padding: 10px 14px; min-width: 180px; z-index: 60;
    box-shadow: 0 4px 16px #0006; font-family: sans-serif;
    transform: translateX(-50%);
  }
  .popup-name { font-size: 13px; color: #eee; font-weight: 600; margin-bottom: 6px; }
  .popup-row { font-size: 11px; color: #99a; margin-bottom: 3px; }
  .popup-actions { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
  .popup-actions button {
    border: 1px solid #3a3a5a; background: #111128; color: #aaa;
    padding: 3px 8px; border-radius: 4px; font-size: 10px; cursor: pointer;
  }
  .popup-actions button:hover { background: #2a2a5a; color: #eee; }
</style>
```

- [ ] **Step 6: Wire inventory into `App.svelte` (script section)**

In `packages/editor/src/App.svelte` script block, add these imports:

```typescript
import { createInventoryStore } from "./lib/inventoryStore.svelte";
import type { InventoryItem } from "./lib/inventoryStore.svelte";
import InventoryOverlay from "./lib/components/InventoryOverlay.svelte";
import InventoryPinPopup from "./lib/components/InventoryPinPopup.svelte";
```

Add these state declarations (alongside existing state):

```typescript
const inventoryStore = createInventoryStore();
let selectedInventoryPin = $state<{
  item: InventoryItem;
  screenX: number;
  screenY: number;
} | null>(null);
let selectedInventoryItemId = $state<string | null>(null);

const currentFloorInventoryItems = $derived(
  inventoryStore.items.filter(
    (i) => i.placement?.floorId === floorStore.currentFloorId
  )
);
```

- [ ] **Step 7: Extend `handleDrop` and `handleDragOver` in `App.svelte`**

Replace the entire `handleDrop` function:

```typescript
function handleDrop(e: DragEvent): void {
  e.preventDefault();

  const inventoryItemId =
    e.dataTransfer?.getData("inventoryItemId") ?? draggingInventoryItemId;
  draggingInventoryItemId = null;

  const choreId =
    e.dataTransfer?.getData("choreId") ?? draggingChoreId;
  draggingChoreId = null;

  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
  const screenX = e.clientX - rect.left;
  const screenY = e.clientY - rect.top;
  const worldX =
    (screenX - viewportStore.viewport.panX) / viewportStore.viewport.zoom;
  const worldY =
    (screenY - viewportStore.viewport.panY) / viewportStore.viewport.zoom;

  if (inventoryItemId) {
    const room = floorStore.floor.rooms.find(
      (r) => r.polygon && pointInPolygon({ x: worldX, y: worldY }, r.polygon)
    );
    inventoryStore.setPlacement(inventoryItemId, {
      floorId: floorStore.currentFloorId,
      roomId: room?.id ?? null,
      position: { x: worldX, y: worldY },
    });
    return;
  }

  if (choreId) {
    const room = floorStore.floor.rooms.find((r) => {
      if (!r.polygon) return false;
      return pointInPolygon({ x: worldX, y: worldY }, r.polygon);
    });
    if (!room) return;
    const chore = choreStore.chores.find((c) => c.id === choreId);
    choreStore.createAssignment({
      choreId,
      roomId: room.id,
      position: { x: worldX, y: worldY },
      nextDueDate: chore?.nextDueDate ?? "",
    });
  }
}
```

Also declare `draggingInventoryItemId` (add alongside `draggingChoreId`):
```typescript
let draggingInventoryItemId = $state<string | null>(null);
```

Update `handleDragOver`:
```typescript
function handleDragOver(e: DragEvent): void {
  if (!draggingChoreId && !draggingInventoryItemId) return;
  e.preventDefault();
}
```

- [ ] **Step 8: Add `InventoryOverlay` and `InventoryPinPopup` to the template**

Inside the `{#if floorStore.loaded}` block (after the existing `ChoreOverlay` and before its closing tag), add:

```svelte
<InventoryOverlay
  items={currentFloorInventoryItems}
  viewport={viewportStore.viewport}
  active={inventoryLayerActive}
  width={canvasWidth}
  height={canvasHeight}
  onclick={(itemId) => {
    const item = inventoryStore.items.find((i) => i.id === itemId);
    if (!item?.placement) return;
    const sp = viewportStore.worldToScreen(item.placement.position);
    selectedInventoryPin = { item, screenX: sp.x, screenY: sp.y };
  }}
  ondragend={(itemId, worldPos) => {
    const item = inventoryStore.items.find((i) => i.id === itemId);
    if (!item?.placement) return;
    inventoryStore.setPlacement(itemId, {
      ...item.placement,
      position: worldPos,
    });
  }}
/>
{#if selectedInventoryPin}
  {@const pin = selectedInventoryPin}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div
    style="position:absolute;inset:0;z-index:55"
    onclick={() => { selectedInventoryPin = null; }}
  >
    <InventoryPinPopup
      item={pin.item}
      screenX={pin.screenX}
      screenY={pin.screenY}
      onedit={() => {
        selectedInventoryItemId = pin.item.id;
        selectedInventoryPin = null;
        window.location.hash = "#/inventory";
      }}
      onremove={async () => {
        await inventoryStore.setPlacement(pin.item.id, null);
        selectedInventoryPin = null;
      }}
      onclose={() => { selectedInventoryPin = null; }}
    />
  </div>
{/if}
```

- [ ] **Step 9: Run all frontend tests — expect no regressions**

```bash
cd /projects/myhome && npm --workspace packages/editor run test
```

Expected: all tests pass.

- [ ] **Step 10: Commit**

```bash
git add packages/editor/src/lib/components/InventoryOverlay.svelte \
        packages/editor/src/lib/components/InventoryPinPopup.svelte \
        packages/editor/test/InventoryOverlay.test.ts \
        packages/editor/src/App.svelte
git commit -m "feat: InventoryOverlay floor plan pins with drag-reposition and popup"
```

---

## Task 6: InventoryPickerPanel + right sidebar restructure

**Files:**
- Create: `packages/editor/src/lib/components/InventoryPickerPanel.svelte`
- Modify: `packages/editor/src/App.svelte`

- [ ] **Step 1: Create `InventoryPickerPanel.svelte`**

```svelte
<!-- packages/editor/src/lib/components/InventoryPickerPanel.svelte -->
<script lang="ts">
  import type { InventoryItem } from "../inventoryStore.svelte";

  interface Props {
    items: InventoryItem[];
    currentFloorId: string;
    draggingItemId: string | null;
    onDragStart: (itemId: string) => void;
    onDragEnd: () => void;
  }

  let { items, currentFloorId, draggingItemId, onDragStart, onDragEnd }: Props =
    $props();

  let query = $state("");

  const placed = $derived(
    items.filter((i) => i.placement?.floorId === currentFloorId)
  );
  const allUnplaced = $derived(items.filter((i) => i.placement === null));
  const unplaced = $derived(
    query
      ? allUnplaced.filter((i) =>
          i.name.toLowerCase().includes(query.toLowerCase())
        )
      : allUnplaced
  );
</script>

<div class="panel">
  <div class="panel-header">
    📦 Inventory <span class="hint">— drag to floor</span>
  </div>
  <input class="search" bind:value={query} placeholder="Search…" />

  {#if placed.length > 0}
    <div class="section">
      <div class="section-title">On this floor ({placed.length})</div>
      {#each placed as item (item.id)}
        <div class="item-row placed">
          <span class="emoji">{item.emoji}</span>
          <span class="name">{item.name}</span>
          <span class="pin-icon">📍</span>
        </div>
      {/each}
    </div>
  {/if}

  <div class="section unplaced-section">
    <div class="section-title">
      Unplaced ({allUnplaced.length})
    </div>
    {#each unplaced as item (item.id)}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="item-row"
        class:dragging={draggingItemId === item.id}
        draggable={true}
        ondragstart={(e) => {
          e.dataTransfer?.setData("inventoryItemId", item.id);
          onDragStart(item.id);
        }}
        ondragend={() => onDragEnd()}
      >
        <span class="emoji">{item.emoji}</span>
        <span class="name">{item.name}</span>
      </div>
    {/each}
    {#if unplaced.length === 0 && query}
      <div class="empty">No matches</div>
    {:else if allUnplaced.length === 0}
      <div class="empty">All items placed ✓</div>
    {/if}
  </div>
</div>

<style>
  .panel {
    background: #111130; border-left: 1px solid #2a2a4a;
    display: flex; flex-direction: column; width: 220px; flex-shrink: 0;
    font-family: sans-serif; font-size: 12px; overflow: hidden; flex: 1;
  }
  .panel-header {
    padding: 8px 10px; border-bottom: 1px solid #2a2a3a;
    color: #aaf; font-size: 11px; font-weight: 600; flex-shrink: 0;
  }
  .hint { color: #556; font-weight: normal; font-size: 10px; }
  .search {
    margin: 6px 8px; padding: 4px 7px;
    background: #0a0a20; border: 1px solid #2a2a4a; color: #bbb;
    border-radius: 4px; font-size: 11px; flex-shrink: 0;
  }
  .section { overflow-y: auto; padding: 4px; }
  .unplaced-section { flex: 1; }
  .section-title {
    color: #556; font-size: 9px; text-transform: uppercase;
    letter-spacing: .05em; padding: 2px 4px;
  }
  .item-row {
    display: flex; align-items: center; gap: 6px;
    padding: 4px 6px; border-radius: 4px; cursor: grab; color: #ccc;
  }
  .item-row:hover { background: #1c1c38; }
  .item-row.placed { opacity: .45; cursor: default; }
  .item-row.dragging { opacity: .5; background: #1c1c38; }
  .emoji { font-size: 14px; width: 18px; text-align: center; flex-shrink: 0; }
  .name {
    flex: 1; overflow: hidden; text-overflow: ellipsis;
    white-space: nowrap; font-size: 11px;
  }
  .pin-icon { font-size: 10px; color: #445; }
  .empty { color: #445; font-size: 10px; padding: 4px 6px; }
</style>
```

- [ ] **Step 2: Wire `InventoryPickerPanel` into `App.svelte`**

In `App.svelte` script, add:
```typescript
import InventoryPickerPanel from "./lib/components/InventoryPickerPanel.svelte";
```

In the template, find the `{#if choreLayerActive}` ChorePanel conditional and replace it with a shared `.right-panels` container:

```svelte
{#if choreLayerActive || inventoryLayerActive}
  <div class="right-panels">
    {#if choreLayerActive}
      <ChorePanel
        store={choreStore}
        {draggingChoreId}
        onDragStart={(id) => { draggingChoreId = id; }}
        onDragEnd={() => { draggingChoreId = null; }}
      />
    {/if}
    {#if inventoryLayerActive}
      <InventoryPickerPanel
        items={inventoryStore.items}
        currentFloorId={floorStore.currentFloorId}
        draggingItemId={draggingInventoryItemId}
        onDragStart={(id) => { draggingInventoryItemId = id; }}
        onDragEnd={() => { draggingInventoryItemId = null; }}
      />
    {/if}
  </div>
{/if}
```

In the `<style>` block of `App.svelte`, add:
```css
.right-panels {
  position: absolute; top: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column; z-index: 20; overflow: hidden;
}
```

- [ ] **Step 3: Run all frontend tests**

```bash
cd /projects/myhome && npm --workspace packages/editor run test
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/InventoryPickerPanel.svelte \
        packages/editor/src/App.svelte
git commit -m "feat: InventoryPickerPanel drag-to-place in right sidebar"
```

---

## Task 7: InventoryPage + InventoryModal

Replace the stub `InventoryPage.svelte` with the full list+modal implementation.

**Files:**
- Create: `packages/editor/src/lib/components/InventoryModal.svelte`
- Modify: `packages/editor/src/lib/components/InventoryPage.svelte` (replace stub)
- Modify: `packages/editor/src/App.svelte`

- [ ] **Step 1: Create `InventoryModal.svelte`**

```svelte
<!-- packages/editor/src/lib/components/InventoryModal.svelte -->
<script lang="ts">
  import type { createInventoryStore, InventoryItem } from "../inventoryStore.svelte";

  type InvStore = ReturnType<typeof createInventoryStore>;

  interface Props {
    item: InventoryItem | null; // null = create mode
    store: InvStore;
    onclose: () => void;
    onplaceonmap?: (itemId: string) => void;
  }

  let { item, store, onclose, onplaceonmap }: Props = $props();

  const CATEGORY_SUGGESTIONS = [
    "Electronics", "Furniture", "Appliance", "Tool", "Artwork", "Other",
  ];

  const isCreate = item === null;

  let name = $state(item?.name ?? "");
  let emoji = $state(item?.emoji ?? "📦");
  let category = $state(item?.category ?? "");
  let brand = $state(item?.brand ?? "");
  let model = $state(item?.model ?? "");
  let serialNumber = $state(item?.serialNumber ?? "");
  let purchaseDate = $state(item?.purchaseDate ?? "");
  let purchasePrice = $state<string>(
    item?.purchasePrice != null ? String(item.purchasePrice) : ""
  );
  let warrantyExpiryDate = $state(item?.warrantyExpiryDate ?? "");
  let notes = $state(item?.notes ?? "");

  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);

  async function handleSave(): Promise<void> {
    if (!name.trim()) { error = "Name is required"; return; }
    saving = true; error = null;
    const parsedPrice = purchasePrice ? parseFloat(purchasePrice) : null;
    const patch = {
      name: name.trim(),
      emoji: emoji || "📦",
      category: category.trim(),
      brand: brand.trim() || null,
      model: model.trim() || null,
      serialNumber: serialNumber.trim() || null,
      purchaseDate: purchaseDate || null,
      purchasePrice: parsedPrice !== null && !isNaN(parsedPrice) ? parsedPrice : null,
      warrantyExpiryDate: warrantyExpiryDate || null,
      notes: notes.trim(),
    };
    try {
      if (isCreate) {
        await store.createItem(patch);
      } else {
        await store.updateItem(item!.id, patch);
      }
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Save failed";
    } finally {
      saving = false;
    }
  }

  async function handleDelete(): Promise<void> {
    if (!item) return;
    deleting = true;
    try {
      await store.deleteItem(item.id);
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Delete failed";
      deleting = false;
    }
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="overlay" onclick={(e) => { if (e.target === e.currentTarget) onclose(); }}>
  <div class="modal">
    <div class="modal-header">
      <h2>{isCreate ? "＋ New item" : "Edit item"}</h2>
      <button class="close-btn" onclick={onclose}>✕</button>
    </div>

    <div class="modal-body">
      <div class="row">
        <label>Emoji</label>
        <input class="emoji-input" bind:value={emoji} maxlength="2" />
        <label style="margin-left:16px">Name *</label>
        <input class="flex-input" bind:value={name} placeholder='e.g. Samsung TV 65"' />
      </div>
      <div class="row">
        <label>Category</label>
        <input
          class="flex-input"
          bind:value={category}
          list="inv-cat-list"
          placeholder="Electronics, Furniture…"
        />
        <datalist id="inv-cat-list">
          {#each CATEGORY_SUGGESTIONS as s}<option value={s} />{/each}
        </datalist>
      </div>
      <div class="row">
        <label>Brand</label>
        <input class="flex-input" bind:value={brand} placeholder="Samsung" />
        <label style="margin-left:12px">Model</label>
        <input class="flex-input" bind:value={model} placeholder="QE65Q80C" />
      </div>
      <div class="row">
        <label>Serial #</label>
        <input class="flex-input" bind:value={serialNumber} placeholder="XYZ123" />
      </div>
      <div class="row">
        <label>Purchased</label>
        <input type="date" bind:value={purchaseDate} />
        <label style="margin-left:12px">Price (€)</label>
        <input
          class="price-input"
          bind:value={purchasePrice}
          type="number"
          min="0"
          step="0.01"
          placeholder="0.00"
        />
      </div>
      <div class="row">
        <label>Warranty expiry</label>
        <input type="date" bind:value={warrantyExpiryDate} />
      </div>
      <div class="row col">
        <label>Notes</label>
        <textarea bind:value={notes} rows="3" placeholder="Additional notes…"></textarea>
      </div>
      {#if error}<div class="error">{error}</div>{/if}
    </div>

    <div class="modal-footer">
      {#if !isCreate && onplaceonmap}
        <button class="place-btn" onclick={() => onplaceonmap!(item!.id)}>
          📍 Place on map
        </button>
      {/if}
      <span class="spacer"></span>
      {#if !isCreate}
        {#if confirmDelete}
          <span class="confirm-text">Delete this item?</span>
          <button class="danger-btn" disabled={deleting} onclick={handleDelete}>
            {deleting ? "…" : "Confirm delete"}
          </button>
          <button onclick={() => { confirmDelete = false; }}>Cancel</button>
        {:else}
          <button class="delete-btn" onclick={() => { confirmDelete = true; }}>🗑 Delete</button>
        {/if}
      {/if}
      <button class="save-btn" disabled={saving} onclick={handleSave}>
        {saving ? "Saving…" : isCreate ? "Create" : "Save"}
      </button>
    </div>
  </div>
</div>

<style>
  .overlay {
    position: fixed; inset: 0; z-index: 200;
    background: rgba(0, 0, 0, 0.6);
    display: flex; align-items: center; justify-content: center;
  }
  .modal {
    background: #1a1a30; border: 1px solid #3a3a5a; border-radius: 10px;
    width: 560px; max-width: 95vw; max-height: 90vh;
    display: flex; flex-direction: column; overflow: hidden;
    box-shadow: 0 8px 32px #0008;
  }
  .modal-header {
    display: flex; align-items: center; padding: 14px 18px;
    border-bottom: 1px solid #2a2a4a; flex-shrink: 0;
  }
  h2 {
    margin: 0; font-size: 15px; color: #eee;
    font-family: sans-serif; font-weight: 600; flex: 1;
  }
  .close-btn {
    background: none; border: none; color: #667; font-size: 16px; cursor: pointer;
  }
  .close-btn:hover { color: #aaa; }

  .modal-body {
    padding: 16px 18px; overflow-y: auto; flex: 1; font-family: sans-serif;
  }
  .row {
    display: flex; align-items: center; gap: 8px;
    margin-bottom: 12px; flex-wrap: wrap;
  }
  .row.col { flex-direction: column; align-items: stretch; }
  label { font-size: 11px; color: #778; white-space: nowrap; }
  input, textarea {
    background: #0f0f24; border: 1px solid #2a2a4a; color: #ccc;
    padding: 5px 8px; border-radius: 4px;
    font-size: 12px; font-family: sans-serif;
  }
  input:focus, textarea:focus { outline: none; border-color: #5566cc; }
  .flex-input { flex: 1; min-width: 0; }
  .emoji-input { width: 42px; text-align: center; font-size: 18px; }
  .price-input { width: 90px; }
  textarea { resize: vertical; }
  .error { color: #f44336; font-size: 11px; margin-top: 4px; font-family: sans-serif; }

  .modal-footer {
    display: flex; align-items: center; gap: 8px; padding: 12px 18px;
    border-top: 1px solid #2a2a4a; flex-shrink: 0; flex-wrap: wrap;
    font-family: sans-serif;
  }
  .spacer { flex: 1; }
  button { padding: 5px 14px; border-radius: 4px; font-size: 12px; cursor: pointer; }
  .save-btn { background: #1a3a2a; border: none; color: #4c9; }
  .save-btn:hover:not(:disabled) { background: #224a34; }
  .save-btn:disabled { opacity: 0.5; cursor: default; }
  .delete-btn { background: none; border: 1px solid #3a1a1a; color: #c66; }
  .delete-btn:hover { background: #2a1010; }
  .danger-btn { background: #3a1010; border: none; color: #f88; }
  .danger-btn:hover:not(:disabled) { background: #4a1515; }
  .danger-btn:disabled { opacity: 0.5; cursor: default; }
  .place-btn { background: #1a2a3a; border: 1px solid #2a4a5a; color: #78c; }
  .place-btn:hover { background: #1f3548; }
  .confirm-text { font-size: 11px; color: #c66; }
  button:not(.save-btn):not(.danger-btn):not(.delete-btn):not(.place-btn):not(.close-btn) {
    background: none; border: 1px solid #2a2a4a; color: #778;
  }
</style>
```

- [ ] **Step 2: Replace `InventoryPage.svelte` with the full implementation**

Completely overwrite `packages/editor/src/lib/components/InventoryPage.svelte`:

```svelte
<!-- packages/editor/src/lib/components/InventoryPage.svelte -->
<script lang="ts">
  import type { createInventoryStore, InventoryItem } from "../inventoryStore.svelte";
  import type { createHouseStore } from "../houseStore.svelte";
  import InventoryModal from "./InventoryModal.svelte";

  type InvStore = ReturnType<typeof createInventoryStore>;
  type HouseStore = ReturnType<typeof createHouseStore>;

  interface Props {
    store: InvStore;
    floorStore: HouseStore;
    selectedItemId?: string | null;
    onclearselection?: () => void;
    onplaceonmap?: (itemId: string) => void;
  }

  let {
    store,
    floorStore,
    selectedItemId = null,
    onclearselection,
    onplaceonmap,
  }: Props = $props();

  let modalItem = $state<InventoryItem | "create" | null>(null);
  let searchQuery = $state("");
  let roomFilter = $state("");
  let categoryFilter = $state("");

  $effect(() => {
    if (selectedItemId) {
      const found = store.items.find((i) => i.id === selectedItemId);
      if (found) {
        modalItem = found;
        onclearselection?.();
      }
    }
  });

  function roomName(roomId: string | null | undefined): string {
    if (!roomId) return "—";
    for (const floor of floorStore.floors) {
      const room = floor.rooms.find((r) => r.id === roomId);
      if (room) return room.label || roomId;
    }
    return "—";
  }

  function warrantyChip(item: InventoryItem): { label: string; color: string } {
    if (!item.warrantyExpiryDate) return { label: "—", color: "#445" };
    const expiry = new Date(item.warrantyExpiryDate).getTime();
    const now = Date.now();
    const days = Math.round((expiry - now) / 86400000);
    if (days < 0) return { label: "✕ expired", color: "#f44336" };
    if (days <= 30) return { label: `⚠ ${days}d`, color: "#ff9800" };
    return { label: "✓", color: "#4caf50" };
  }

  function formatDate(d: string | null): string {
    if (!d) return "—";
    return d.slice(0, 10);
  }

  function formatPrice(p: number | null): string {
    if (p == null) return "—";
    return p.toLocaleString() + " €";
  }

  const allRooms = $derived(floorStore.floors.flatMap((f) => f.rooms));
  const allCategories = $derived(
    [...new Set(store.items.map((i) => i.category).filter(Boolean))]
  );

  const filtered = $derived(
    store.items.filter((i) => {
      if (
        searchQuery &&
        !i.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
        return false;
      if (roomFilter) {
        if (!i.placement?.roomId) return false;
        if (i.placement.roomId !== roomFilter) return false;
      }
      if (categoryFilter && i.category !== categoryFilter) return false;
      return true;
    })
  );

  const totalValue = $derived(
    store.items.reduce((sum, i) => sum + (i.purchasePrice ?? 0), 0)
  );
</script>

<div class="page">
  <div class="toolbar">
    <input
      class="search"
      bind:value={searchQuery}
      placeholder="🔍 Search items…"
    />
    <select bind:value={roomFilter}>
      <option value="">All rooms</option>
      {#each allRooms as room}
        <option value={room.id}>{room.label}</option>
      {/each}
    </select>
    <select bind:value={categoryFilter}>
      <option value="">All categories</option>
      {#each allCategories as cat}
        <option value={cat}>{cat}</option>
      {/each}
    </select>
    <button class="add-btn" onclick={() => { modalItem = "create"; }}>
      ＋ Add item
    </button>
  </div>

  <div class="table-wrapper">
    <table>
      <thead>
        <tr>
          <th></th>
          <th>Name</th>
          <th>Category</th>
          <th>Room</th>
          <th>Purchased</th>
          <th>Cost</th>
          <th>Warranty</th>
        </tr>
      </thead>
      <tbody>
        {#each filtered as item (item.id)}
          {@const chip = warrantyChip(item)}
          <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
          <tr onclick={() => { modalItem = item; }}>
            <td class="emoji-cell">{item.emoji}</td>
            <td class="name-cell">{item.name}</td>
            <td>{item.category || "—"}</td>
            <td>{roomName(item.placement?.roomId)}</td>
            <td>{formatDate(item.purchaseDate)}</td>
            <td>{formatPrice(item.purchasePrice)}</td>
            <td>
              <span class="chip" style="color:{chip.color}">{chip.label}</span>
            </td>
          </tr>
        {/each}
        {#if filtered.length === 0}
          <tr>
            <td colspan="7" class="empty">
              {store.items.length === 0
                ? "No items yet — click ＋ Add item to get started."
                : "No items match your filters."}
            </td>
          </tr>
        {/if}
      </tbody>
    </table>
  </div>

  <div class="footer">
    {store.items.length} item{store.items.length !== 1 ? "s" : ""}
    {#if totalValue > 0}
      · total value: {totalValue.toLocaleString()} €
    {/if}
  </div>
</div>

{#if modalItem}
  <InventoryModal
    item={modalItem === "create" ? null : modalItem}
    {store}
    onclose={() => { modalItem = null; }}
    onplaceonmap={onplaceonmap
      ? (id) => { modalItem = null; onplaceonmap!(id); }
      : undefined}
  />
{/if}

<style>
  .page {
    display: flex; flex-direction: column; height: 100%;
    background: #141428; font-family: sans-serif;
  }

  .toolbar {
    display: flex; align-items: center; gap: 8px; padding: 8px 12px;
    background: #1e1e3a; border-bottom: 1px solid #2a2a4a; flex-shrink: 0;
  }
  .search {
    flex: 1; background: #111128; border: 1px solid #2a2a4a; color: #ccc;
    padding: 4px 8px; border-radius: 4px; font-size: 12px;
  }
  .toolbar select {
    background: #111128; border: 1px solid #2a2a4a; color: #aaa;
    padding: 4px 6px; border-radius: 4px; font-size: 11px;
  }
  .add-btn {
    background: #1a3a2a; border: none; color: #4c9;
    padding: 4px 12px; border-radius: 4px; font-size: 12px;
    cursor: pointer; white-space: nowrap;
  }
  .add-btn:hover { background: #224a34; }

  .table-wrapper { flex: 1; overflow-y: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; color: #bbb; }
  thead { position: sticky; top: 0; background: #1a1a30; z-index: 1; }
  th {
    padding: 6px 10px; color: #556; font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.05em;
    text-align: left; border-bottom: 1px solid #2a2a3a;
  }
  td { padding: 7px 10px; border-bottom: 1px solid #1e1e2e; }
  tr:hover td { background: #1c1c38; cursor: pointer; }
  .emoji-cell { font-size: 16px; width: 32px; text-align: center; }
  .name-cell { color: #ddd; }
  .chip { font-size: 10px; font-weight: 500; }
  .empty { text-align: center; color: #445; padding: 32px; }

  .footer {
    padding: 6px 12px; font-size: 11px; color: #445;
    border-top: 1px solid #1e1e2e; flex-shrink: 0;
  }
</style>
```

- [ ] **Step 3: Update `App.svelte` — pass props to `InventoryPage`**

Find the route rendering block for `#/inventory`:
```svelte
{:else if currentRoute === "#/inventory"}
  <InventoryPage />
```

Replace with:
```svelte
{:else if currentRoute === "#/inventory"}
  <InventoryPage
    store={inventoryStore}
    {floorStore}
    selectedItemId={selectedInventoryItemId}
    onclearselection={() => { selectedInventoryItemId = null; }}
    onplaceonmap={(id) => {
      const next = new Set(activeLayers);
      next.add("inventory");
      activeLayers = next;
      window.location.hash = "#/";
    }}
  />
```

Also verify that `import InventoryPage from "./lib/components/InventoryPage.svelte"` is already in `App.svelte` (it was in the stub routing — confirm it's still there after previous tasks).

- [ ] **Step 4: Run all frontend tests**

```bash
cd /projects/myhome && npm --workspace packages/editor run test
```

Expected: all tests pass.

- [ ] **Step 5: Run full backend test suite**

```bash
cd /projects/myhome && python -m pytest packages/backend/tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/InventoryModal.svelte \
        packages/editor/src/lib/components/InventoryPage.svelte \
        packages/editor/src/App.svelte
git commit -m "feat: InventoryPage list + InventoryModal CRUD with Place on map"
```
