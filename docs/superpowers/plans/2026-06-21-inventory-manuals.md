# Inventory PDF Manuals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PDF manual upload/view/delete to inventory items, following the same pattern as works attachments.

**Architecture:** `manual: str | None` field on `InventoryItem` stores the sanitised filename; files live at `/data/inventory-manuals/{item_id}/{filename}`; three new FastAPI routes handle upload (multipart POST), serve (`FileResponse` inline), and delete. The `InventoryModal` gains a "Manual" tab identical in structure to `WorkModal`'s "Attachments" tab.

**Tech Stack:** Python 3.12 / FastAPI / Pydantic v2 · Svelte 5 runes / TypeScript · Vitest · pytest

---

## File Structure

**Backend — modified:**
- `packages/backend/src/myhome/models_inventory.py` — add `manual: str | None = None` to `InventoryItem`
- `packages/backend/src/myhome/persistence_inventory.py` — add `_manuals_dir`, `save_manual`, `delete_item_manual`
- `packages/backend/src/myhome/routes/inventory.py` — add upload/get/delete manual routes + cascade on item delete
- `packages/backend/tests/test_inventory.py` — add manual route tests

**Frontend — modified:**
- `packages/editor/src/lib/inventoryStore.svelte.ts` — add `manual` to `InventoryItem` interface; add `uploadManual`, `deleteManual`
- `packages/editor/test/inventoryStore.test.ts` — add `manual: null` to `makeItem`; add store method tests
- `packages/editor/src/lib/components/InventoryModal.svelte` — add Manual tab

---

### Task 1: Backend model and persistence helpers

**Files:**
- Modify: `packages/backend/src/myhome/models_inventory.py`
- Modify: `packages/backend/src/myhome/persistence_inventory.py`

- [ ] **Step 1: Add `manual` field to `InventoryItem`**

In `packages/backend/src/myhome/models_inventory.py`, add `manual: str | None = None` between `notes` and `placement`. The complete file becomes:

```python
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
    manual: str | None = None
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

- [ ] **Step 2: Add manual file helpers to persistence**

Replace `packages/backend/src/myhome/persistence_inventory.py` with:

```python
import json
import os
import shutil
from pathlib import Path

from .models_inventory import InventoryDocument


def _inventory_file() -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "inventory.json"


def _manuals_dir(item_id: str) -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "inventory-manuals" / item_id


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


def save_manual(item_id: str, filename: str, data: bytes) -> None:
    path = _manuals_dir(item_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / filename).write_bytes(data)


def delete_item_manual(item_id: str) -> None:
    path = _manuals_dir(item_id)
    if path.exists():
        shutil.rmtree(path)
```

- [ ] **Step 3: Verify existing tests still pass**

```bash
cd packages/backend && python3 -m pytest tests/test_inventory.py -v
```

Expected: 11 passed (all existing tests). The `manual` field defaults to `None` and is transparent to existing tests.

- [ ] **Step 4: Commit**

```bash
git add packages/backend/src/myhome/models_inventory.py \
        packages/backend/src/myhome/persistence_inventory.py
git commit -m "feat(inventory): add manual field and persistence helpers"
```

---

### Task 2: Backend routes for manual upload, get, and delete

**Files:**
- Modify: `packages/backend/src/myhome/routes/inventory.py`
- Modify: `packages/backend/tests/test_inventory.py`

- [ ] **Step 1: Write failing tests**

Append to the end of `packages/backend/tests/test_inventory.py`:

```python
# --- Manual routes ---

def test_upload_manual(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    resp = c.post(
        "/api/inventory/items/i1/manual",
        files={"file": ("dishwasher_manual.pdf", b"%PDF-1.4 content", "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "dishwasher_manual.pdf"
    item = c.get("/api/inventory").json()["items"][0]
    assert item["manual"] == "dishwasher_manual.pdf"


def test_upload_manual_sanitises_filename(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    resp = c.post(
        "/api/inventory/items/i1/manual",
        files={"file": ("my manual 2025.pdf", b"%PDF test", "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "my_manual_2025.pdf"


def test_upload_manual_replaces_existing(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    c.post("/api/inventory/items/i1/manual", files={"file": ("v1.pdf", b"%PDF v1", "application/pdf")})
    c.post("/api/inventory/items/i1/manual", files={"file": ("v2.pdf", b"%PDF v2", "application/pdf")})
    item = c.get("/api/inventory").json()["items"][0]
    assert item["manual"] == "v2.pdf"


def test_upload_manual_rejects_non_pdf(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    resp = c.post(
        "/api/inventory/items/i1/manual",
        files={"file": ("image.png", b"fake-png", "image/png")},
    )
    assert resp.status_code == 400


def test_upload_manual_item_not_found(client):
    resp = client.post(
        "/api/inventory/items/nope/manual",
        files={"file": ("manual.pdf", b"%PDF test", "application/pdf")},
    )
    assert resp.status_code == 404


def test_upload_manual_invalid_id(client):
    resp = client.post(
        "/api/inventory/items/i!1/manual",
        files={"file": ("manual.pdf", b"%PDF test", "application/pdf")},
    )
    assert resp.status_code == 400


def test_get_manual(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    c.post("/api/inventory/items/i1/manual", files={"file": ("manual.pdf", b"%PDF-1.4 content", "application/pdf")})
    resp = c.get("/api/inventory/items/i1/manual")
    assert resp.status_code == 200
    assert "pdf" in resp.headers["content-type"]


def test_get_manual_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    resp = TestClient(app).get("/api/inventory/items/i1/manual")
    assert resp.status_code == 404


def test_get_manual_invalid_id(client):
    resp = client.get("/api/inventory/items/i!1/manual")
    assert resp.status_code == 400


def test_delete_manual(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    c.post("/api/inventory/items/i1/manual", files={"file": ("manual.pdf", b"%PDF test", "application/pdf")})
    resp = c.delete("/api/inventory/items/i1/manual")
    assert resp.status_code == 204
    item = c.get("/api/inventory").json()["items"][0]
    assert item["manual"] is None


def test_delete_manual_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    resp = TestClient(app).delete("/api/inventory/items/i1/manual")
    assert resp.status_code == 404


def test_delete_item_cascades_manual(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    c.post("/api/inventory/items/i1/manual", files={"file": ("manual.pdf", b"%PDF test", "application/pdf")})
    c.delete("/api/inventory/items/i1")
    manual_dir = tmp_path / "inventory-manuals" / "i1"
    assert not manual_dir.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/backend && python3 -m pytest tests/test_inventory.py -v -k "manual"
```

Expected: all 12 new tests FAIL with 404 or AttributeError (routes don't exist yet).

- [ ] **Step 3: Implement manual routes**

Replace `packages/backend/src/myhome/routes/inventory.py` with:

```python
import re
import uuid

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..models_inventory import (
    InventoryDocument,
    InventoryItem,
    InventoryItemCreate,
    InventoryItemUpdate,
    PlacementUpdate,
)
from ..persistence_inventory import (
    _manuals_dir,
    delete_item_manual,
    load_inventory,
    save_inventory,
    save_manual,
)

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
    delete_item_manual(id)


@router.put("/api/inventory/items/{id}/placement", status_code=204)
def update_placement(id: str, body: PlacementUpdate) -> None:
    doc = load_inventory()
    item = next((i for i in doc.items if i.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    item.placement = body.placement
    save_inventory(doc)


def _sanitise_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    if not name.lower().endswith(".pdf"):
        name = name + ".pdf"
    return name or "manual.pdf"


_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _validate_id(item_id: str) -> None:
    if not _ID_RE.fullmatch(item_id):
        raise HTTPException(status_code=400, detail="Invalid id")


def _validate_filename(filename: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", filename) or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")


@router.post("/api/inventory/items/{id}/manual", status_code=201)
async def upload_manual(id: str, file: UploadFile) -> dict:
    _validate_id(id)
    doc = load_inventory()
    item = next((i for i in doc.items if i.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    original = file.filename or ""
    content_type = file.content_type or ""
    if content_type not in ("application/pdf", "application/octet-stream") and not original.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    filename = _sanitise_filename(original)
    data = await file.read()
    save_manual(id, filename, data)
    item.manual = filename
    save_inventory(doc)
    return {"filename": filename}


@router.get("/api/inventory/items/{id}/manual")
def get_manual(id: str) -> FileResponse:
    _validate_id(id)
    doc = load_inventory()
    item = next((i for i in doc.items if i.id == id), None)
    if not item or not item.manual:
        raise HTTPException(status_code=404)
    _validate_filename(item.manual)
    base = _manuals_dir(id).resolve()
    path = (base / item.manual).resolve()
    if not str(path).startswith(str(base) + "/") or not path.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(str(path), media_type="application/pdf", content_disposition_type="inline")


@router.delete("/api/inventory/items/{id}/manual", status_code=204)
def delete_manual(id: str) -> None:
    _validate_id(id)
    doc = load_inventory()
    item = next((i for i in doc.items if i.id == id), None)
    if not item or not item.manual:
        raise HTTPException(status_code=404)
    delete_item_manual(id)
    item.manual = None
    save_inventory(doc)
```

- [ ] **Step 4: Run all inventory tests**

```bash
cd packages/backend && python3 -m pytest tests/test_inventory.py -v
```

Expected: 23 passed (11 existing + 12 new).

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/inventory.py \
        packages/backend/tests/test_inventory.py
git commit -m "feat(inventory): add PDF manual upload/get/delete routes"
```

---

### Task 3: Frontend store — `manual` field and methods

**Files:**
- Modify: `packages/editor/src/lib/inventoryStore.svelte.ts`
- Modify: `packages/editor/test/inventoryStore.test.ts`

- [ ] **Step 1: Add `manual: null` to `makeItem` in the test file**

In `packages/editor/test/inventoryStore.test.ts`, update `makeItem` to include `manual: null`:

```typescript
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
    manual: null,
    placement: null,
    ...overrides,
  };
}
```

- [ ] **Step 2: Add failing tests for `uploadManual` and `deleteManual`**

Append to the end of `packages/editor/test/inventoryStore.test.ts`:

```typescript
describe("inventoryStore — uploadManual", () => {
  it("posts to /manual and returns filename", async () => {
    const updatedDoc = { version: 1, items: [makeItem({ manual: "dishwasher.pdf" })] };
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
        .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({ filename: "dishwasher.pdf" }) })
        .mockResolvedValueOnce({ ok: true, status: 200, json: async () => updatedDoc }),
    );
    const store = createInventoryStore();
    await tick();
    const file = new File(["%PDF-1.4"], "dishwasher.pdf", { type: "application/pdf" });
    const filename = await store.uploadManual("i1", file);
    await tick();
    expect(filename).toBe("dishwasher.pdf");
    expect(store.items[0].manual).toBe("dishwasher.pdf");
  });

  it("throws on HTTP error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
        .mockResolvedValueOnce({ ok: false, status: 400, json: async () => ({}) }),
    );
    const store = createInventoryStore();
    await tick();
    await expect(
      store.uploadManual("i1", new File(["img"], "img.png")),
    ).rejects.toThrow("HTTP 400");
  });
});

describe("inventoryStore — deleteManual", () => {
  it("calls DELETE and clears manual in store", async () => {
    const initDoc = { version: 1, items: [makeItem({ manual: "dishwasher.pdf" })] };
    const clearedDoc = { version: 1, items: [makeItem({ manual: null })] };
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce({ ok: true, status: 200, json: async () => initDoc })
        .mockResolvedValueOnce({ ok: true, status: 204, json: async () => ({}) })
        .mockResolvedValueOnce({ ok: true, status: 200, json: async () => clearedDoc }),
    );
    const store = createInventoryStore();
    await tick();
    expect(store.items[0].manual).toBe("dishwasher.pdf");
    await store.deleteManual("i1");
    await tick();
    expect(store.items[0].manual).toBeNull();
  });

  it("throws on HTTP error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
        .mockResolvedValueOnce({ ok: false, status: 404, json: async () => ({}) }),
    );
    const store = createInventoryStore();
    await tick();
    await expect(store.deleteManual("i1")).rejects.toThrow("HTTP 404");
  });
});
```

- [ ] **Step 3: Run tests to verify new tests fail**

```bash
cd packages/editor && npx vitest run test/inventoryStore.test.ts
```

Expected: 9 existing tests pass, 4 new tests FAIL with "store.uploadManual is not a function" or similar.

- [ ] **Step 4: Update `inventoryStore.svelte.ts`**

Replace `packages/editor/src/lib/inventoryStore.svelte.ts` with:

```typescript
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
  manual: string | null;
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
    data: Omit<InventoryItem, "id" | "placement" | "manual">
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
    patch: Partial<Omit<InventoryItem, "id" | "placement" | "manual">>
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

  async function uploadManual(id: string, file: File): Promise<string> {
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch(`/api/inventory/items/${id}/manual`, {
      method: "POST",
      body: form,
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const result = await resp.json();
    await init();
    return result.filename as string;
  }

  async function deleteManual(id: string): Promise<void> {
    const resp = await fetch(`/api/inventory/items/${id}/manual`, {
      method: "DELETE",
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
    uploadManual,
    deleteManual,
  };
}
```

- [ ] **Step 5: Run all frontend store tests**

```bash
cd packages/editor && npx vitest run test/inventoryStore.test.ts
```

Expected: 13 passed (9 existing + 4 new).

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/inventoryStore.svelte.ts \
        packages/editor/test/inventoryStore.test.ts
git commit -m "feat(inventory): add manual field and uploadManual/deleteManual to store"
```

---

### Task 4: Frontend UI — Manual tab in `InventoryModal`

**Files:**
- Modify: `packages/editor/src/lib/components/InventoryModal.svelte`

- [ ] **Step 1: Replace `InventoryModal.svelte` with tabbed version**

Replace `packages/editor/src/lib/components/InventoryModal.svelte` with:

```svelte
<script lang="ts">
  import type { createInventoryStore, InventoryItem } from "../inventoryStore.svelte";
  import DatePicker from "./DatePicker.svelte";

  type InvStore = ReturnType<typeof createInventoryStore>;

  interface Props {
    item: InventoryItem | null;
    store: InvStore;
    inventoryCategories: string[];
    onclose: () => void;
    onplaceonmap?: (itemId: string) => void;
  }

  let { item, store, inventoryCategories, onclose, onplaceonmap }: Props = $props();

  const isCreate = item === null;

  let activeTab = $state<"info" | "manual">("info");
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
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);

  const currentItem = $derived(
    item ? (store.items.find((i) => i.id === item.id) ?? item) : null
  );

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

  async function handleUpload(e: Event): Promise<void> {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file || !item) return;
    uploading = true; uploadError = null;
    try {
      await store.uploadManual(item.id, file);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : "Upload failed";
    } finally {
      uploading = false;
      input.value = "";
    }
  }

  async function handleDeleteManual(): Promise<void> {
    if (!item) return;
    try {
      await store.deleteManual(item.id);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : "Delete failed";
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

    <div class="tabs">
      <button class="tab" class:active={activeTab === "info"} onclick={() => { activeTab = "info"; }}>Info</button>
      <button
        class="tab"
        class:active={activeTab === "manual"}
        disabled={isCreate}
        onclick={() => { activeTab = "manual"; }}
      >Manual{currentItem?.manual ? " (1)" : ""}</button>
    </div>

    <div class="modal-body">
      {#if activeTab === "info"}
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
            {#each inventoryCategories as s}<option value={s} />{/each}
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
          <DatePicker bind:value={purchaseDate} />
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
          <DatePicker bind:value={warrantyExpiryDate} />
        </div>
        <div class="row col">
          <label>Notes</label>
          <textarea bind:value={notes} rows="3" placeholder="Additional notes…"></textarea>
        </div>
        {#if error}<div class="error">{error}</div>{/if}
      {:else}
        <div class="attachments">
          {#if currentItem?.manual}
            <div class="attach-row">
              <span class="attach-icon">📄</span>
              <a
                class="attach-name"
                href="/api/inventory/items/{item!.id}/manual"
                target="_blank"
                rel="noopener"
              >{currentItem.manual}</a>
              <button class="attach-del" onclick={handleDeleteManual} title="Delete">✕</button>
            </div>
          {:else}
            <div class="attach-empty">No manual yet.</div>
          {/if}
          <label class="upload-btn" class:uploading>
            {uploading ? "Uploading…" : "＋ Upload PDF"}
            <input type="file" accept=".pdf" style="display:none" onchange={handleUpload} />
          </label>
          {#if uploadError}<div class="upload-error">{uploadError}</div>{/if}
        </div>
      {/if}
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
      {#if activeTab === "info"}
        <button class="save-btn" disabled={saving} onclick={handleSave}>
          {saving ? "Saving…" : isCreate ? "Create" : "Save"}
        </button>
      {/if}
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

  .tabs { display: flex; border-bottom: 1px solid #2a2a4a; flex-shrink: 0; }
  .tab {
    padding: 8px 16px; background: none; border: none; border-bottom: 2px solid transparent;
    color: #556; font-size: 12px; cursor: pointer; font-family: sans-serif;
  }
  .tab:hover:not(:disabled) { color: #99a; }
  .tab.active { border-bottom-color: #5566cc; color: #aaf; }
  .tab:disabled { color: #334; cursor: default; }

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

  .attachments { display: flex; flex-direction: column; gap: 6px; }
  .attach-row {
    display: flex; align-items: center; gap: 8px;
    background: #111128; border: 1px solid #2a2a4a; border-radius: 4px; padding: 6px 10px;
  }
  .attach-icon { font-size: 14px; }
  .attach-name { flex: 1; font-size: 11px; color: #88aaff; text-decoration: none; }
  .attach-name:hover { text-decoration: underline; }
  .attach-del { background: none; border: none; color: #446; cursor: pointer; font-size: 12px; }
  .attach-del:hover { color: #f44; }
  .attach-empty { font-size: 11px; color: #334; text-align: center; padding: 12px 0; }
  .upload-btn {
    background: #1a1a2e; border: 1px dashed #2a2a4a; color: #556;
    padding: 7px 12px; border-radius: 4px; font-size: 11px; cursor: pointer;
    text-align: center; font-family: sans-serif; display: block;
  }
  .upload-btn:hover:not(.uploading) { background: #2a2a4a; color: #99a; }
  .upload-btn.uploading { color: #334; cursor: default; }
  .upload-error { font-size: 10px; color: #f88; }

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

- [ ] **Step 2: Run typecheck**

```bash
cd packages/editor && npm run typecheck 2>&1 | tail -20
```

Expected: no errors.

- [ ] **Step 3: Run all tests**

```bash
cd packages/backend && python3 -m pytest tests/test_inventory.py -v && cd ../editor && npx vitest run test/inventoryStore.test.ts
```

Expected: 23 backend tests pass, 13 frontend store tests pass.

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/InventoryModal.svelte
git commit -m "feat(inventory): add Manual tab to InventoryModal"
```
