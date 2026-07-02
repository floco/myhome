# Multi-Module Media Gallery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add image + PDF upload, grid/list MediaGallery, and fullscreen Lightbox to Inventory, Costs, KB, and Chores modules, matching the Works module pattern.

**Architecture:** Each module gets identical backend attachment plumbing (accept images + PDF, server-side PDF thumbnails via pymupdf, correct content-type serving, thumb cleanup on delete). Frontend wires the existing generic `MediaGallery` and `Lightbox` components — no changes to those shared components needed. Chores gets a new `ChoreEditModal` to replace the current inline edit form.

**Tech Stack:** Python/FastAPI + pymupdf (backend); Svelte 5 + Vitest (frontend); existing `MediaGallery.svelte`, `Lightbox.svelte`, `MediaItem` interface from `packages/editor/src/lib/components/ui/`.

---

## File Map

**Backend — modified:**
- `packages/backend/src/myhome/persistence_inventory.py` — add `generate_pdf_thumbnail`, update `delete_attachment` (thumb cleanup)
- `packages/backend/src/myhome/routes/inventory.py` — update `_sanitise_filename` + `upload_attachment` (images) + `get_attachment` (mimetypes)
- `packages/backend/src/myhome/models_costs.py` — add `attachments: list[str] = []`
- `packages/backend/src/myhome/persistence_costs.py` — add attachment helpers
- `packages/backend/src/myhome/routes/costs.py` — add attachment routes + `delete_all_attachments` call on entry delete
- `packages/backend/src/myhome/models_kb.py` — add `attachments: list[str] = []`
- `packages/backend/src/myhome/persistence_kb.py` — add attachment helpers, update frontmatter serialisation, update `delete_entry`
- `packages/backend/src/myhome/routes/kb.py` — add attachment routes
- `packages/backend/src/myhome/models_chores.py` — add `attachments: list[str] = []` to `Chore`
- `packages/backend/src/myhome/persistence_chores.py` — add attachment helpers
- `packages/backend/src/myhome/routes/chores.py` — add attachment routes + `delete_all_attachments` call on chore delete

**Backend — tests modified:**
- `packages/backend/tests/test_inventory.py`
- `packages/backend/tests/test_costs.py`
- `packages/backend/tests/test_kb.py`
- `packages/backend/tests/test_chores.py`

**Frontend — modified:**
- `packages/editor/src/lib/components/InventoryModal.svelte` — rename tab, MediaGallery, Lightbox
- `packages/editor/src/lib/costsStore.svelte.ts` — add `attachments`, `uploadAttachment`, `deleteAttachment`
- `packages/editor/src/lib/components/CostsEntryModal.svelte` — add tabs, MediaGallery, Lightbox
- `packages/editor/src/lib/kbStore.svelte.ts` — add `attachments`, `uploadAttachment`, `deleteAttachment`
- `packages/editor/src/lib/components/KBPage.svelte` — add contentTab, MediaGallery, Lightbox
- `packages/editor/src/lib/choreStore.svelte.ts` — add `attachments`, `uploadAttachment`, `deleteAttachment`
- `packages/editor/src/lib/components/ChoresPage.svelte` — replace inline edit with `ChoreEditModal`

**Frontend — created:**
- `packages/editor/src/lib/components/ChoreEditModal.svelte` — Info/Media tabs, edit-only modal
- `packages/editor/test/InventoryModal.test.ts` — new
- `packages/editor/test/CostsEntryModal.test.ts` — new
- `packages/editor/test/ChoreEditModal.test.ts` — new

---

### Task 1: Inventory backend — accept images + PDF thumbnails

**Files:**
- Modify: `packages/backend/src/myhome/persistence_inventory.py`
- Modify: `packages/backend/src/myhome/routes/inventory.py`
- Modify: `packages/backend/tests/test_inventory.py`

- [ ] **Step 1: Write failing tests**

Add to `packages/backend/tests/test_inventory.py`:

```python
def _make_valid_pdf() -> bytes:
    import fitz
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    return doc.write()


# Keep fixture and make_doc() from existing file; add below:

def _item_id(client) -> str:
    resp = client.post("/api/inventory/items", json={"name": "TV"})
    return resp.json()["id"]


def test_inv_upload_jpeg_accepted(client, tmp_path):
    iid = _item_id(client)
    resp = client.post(
        f"/api/inventory/items/{iid}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "photo.jpg"
    item = next(i for i in client.get("/api/inventory").json()["items"] if i["id"] == iid)
    assert "photo.jpg" in item["attachments"]


def test_inv_upload_png_accepted(client, tmp_path):
    iid = _item_id(client)
    resp = client.post(
        f"/api/inventory/items/{iid}/attachments",
        files={"file": ("shot.png", b"\x89PNG" + b"\x00" * 50, "image/png")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "shot.png"


def test_inv_upload_webp_accepted(client, tmp_path):
    iid = _item_id(client)
    resp = client.post(
        f"/api/inventory/items/{iid}/attachments",
        files={"file": ("photo.webp", b"RIFF" + b"\x00" * 50, "image/webp")},
    )
    assert resp.status_code == 201


def test_inv_upload_unsupported_rejected(client, tmp_path):
    iid = _item_id(client)
    resp = client.post(
        f"/api/inventory/items/{iid}/attachments",
        files={"file": ("malware.exe", b"\x4d\x5a", "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_inv_sanitise_preserves_extension(client, tmp_path):
    iid = _item_id(client)
    resp = client.post(
        f"/api/inventory/items/{iid}/attachments",
        files={"file": ("my photo 2025.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "my_photo_2025.jpg"


def test_inv_upload_pdf_creates_thumbnail(client, tmp_path):
    iid = _item_id(client)
    resp = client.post(
        f"/api/inventory/items/{iid}/attachments",
        files={"file": ("manual.pdf", _make_valid_pdf(), "application/pdf")},
    )
    assert resp.status_code == 201
    thumb = tmp_path / "inventory-attachments" / iid / "manual.pdf.thumb.jpg"
    assert thumb.exists()


def test_inv_delete_pdf_removes_thumbnail(client, tmp_path):
    iid = _item_id(client)
    client.post(
        f"/api/inventory/items/{iid}/attachments",
        files={"file": ("manual.pdf", _make_valid_pdf(), "application/pdf")},
    )
    thumb = tmp_path / "inventory-attachments" / iid / "manual.pdf.thumb.jpg"
    assert thumb.exists()
    client.delete(f"/api/inventory/items/{iid}/attachments/manual.pdf")
    assert not thumb.exists()


def test_inv_get_jpeg_returns_image_content_type(client, tmp_path):
    iid = _item_id(client)
    client.post(
        f"/api/inventory/items/{iid}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")},
    )
    resp = client.get(f"/api/inventory/items/{iid}/attachments/photo.jpg")
    assert resp.status_code == 200
    assert "image/jpeg" in resp.headers["content-type"]
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd packages/backend
python -m pytest tests/test_inventory.py::test_inv_upload_jpeg_accepted tests/test_inventory.py::test_inv_upload_pdf_creates_thumbnail -v
```

Expected: FAIL (400 for images, PDF no thumbnail).

- [ ] **Step 3: Update `persistence_inventory.py`**

```python
import json
import logging
import os
import shutil
from pathlib import Path

from .models_inventory import InventoryDocument

_log = logging.getLogger(__name__)


def _inventory_file() -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "inventory.json"


def _attachments_dir(item_id: str) -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "inventory-attachments" / item_id


def get_attachment_path(item_id: str, filename: str) -> Path:
    return _attachments_dir(item_id) / filename


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


def save_attachment(item_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(item_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / filename).write_bytes(data)


def delete_attachment(item_id: str, filename: str) -> bool:
    path = _attachments_dir(item_id) / filename
    if not path.exists():
        return False
    path.unlink()
    thumb = path.parent / (filename + ".thumb.jpg")
    if thumb.exists():
        thumb.unlink()
    return True


def delete_all_attachments(item_id: str) -> None:
    path = _attachments_dir(item_id)
    if path.exists():
        shutil.rmtree(path)


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

- [ ] **Step 4: Update `routes/inventory.py`**

Replace the `_sanitise_filename`, `upload_attachment`, and `get_attachment` functions. Also add imports at the top:

```python
import mimetypes
import os
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
    _attachments_dir,
    delete_all_attachments,
    delete_attachment,
    generate_pdf_thumbnail,
    load_inventory,
    save_attachment,
    save_inventory,
)

router = APIRouter()

_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}


def _sanitise_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name or "attachment"


_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _validate_id(item_id: str) -> None:
    if not _ID_RE.fullmatch(item_id):
        raise HTTPException(status_code=400, detail="Invalid id")


def _validate_filename(filename: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", filename) or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")


@router.post("/api/inventory/items/{id}/attachments", status_code=201)
async def upload_attachment(id: str, file: UploadFile) -> dict:
    _validate_id(id)
    doc = load_inventory()
    item = next((i for i in doc.items if i.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    original = file.filename or ""
    ext = os.path.splitext(original.lower())[1]
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not supported")
    filename = _sanitise_filename(original)
    data = await file.read()
    save_attachment(id, filename, data)
    if ext == ".pdf":
        generate_pdf_thumbnail(
            _attachments_dir(id) / filename,
            _attachments_dir(id) / (filename + ".thumb.jpg"),
        )
    if filename not in item.attachments:
        item.attachments.append(filename)
    save_inventory(doc)
    return {"filename": filename}


@router.get("/api/inventory/items/{id}/attachments/{filename}")
def get_attachment(id: str, filename: str) -> FileResponse:
    _validate_id(id)
    _validate_filename(filename)
    base = _attachments_dir(id).resolve()
    path = (base / filename).resolve()
    if not str(path).startswith(str(base) + "/") or not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", content_disposition_type="inline")
```

Keep all other routes (GET inventory, POST items, PUT items, DELETE items, PUT placement, DELETE attachment) exactly as they are.

- [ ] **Step 5: Run new tests — expect pass**

```bash
python -m pytest tests/test_inventory.py -v
```

Expected: all existing + new tests pass.

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/persistence_inventory.py packages/backend/src/myhome/routes/inventory.py packages/backend/tests/test_inventory.py
git commit -m "feat(inventory): accept images, generate PDF thumbnails, fix content-type"
```

---

### Task 2: Inventory frontend — MediaGallery in InventoryModal

**Files:**
- Create: `packages/editor/test/InventoryModal.test.ts`
- Modify: `packages/editor/src/lib/components/InventoryModal.svelte`

- [ ] **Step 1: Write failing tests**

Create `packages/editor/test/InventoryModal.test.ts`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import InventoryModal from "../src/lib/components/InventoryModal.svelte";
import type { InventoryItem } from "../src/lib/inventoryStore.svelte";

function makeItem(overrides: Partial<InventoryItem> = {}): InventoryItem {
  return {
    id: "i1", name: "Samsung TV", emoji: "📺", category: "Electronics",
    brand: null, model: null, serialNumber: null, purchaseDate: null,
    purchasePrice: null, warrantyExpiryDate: null, notes: "", attachments: [],
    placement: null, ...overrides,
  };
}

function makeStore(item: InventoryItem | null = null) {
  return {
    items: item ? [item] : [],
    loaded: true,
    loadError: null,
    createItem: vi.fn().mockResolvedValue(undefined),
    updateItem: vi.fn().mockResolvedValue(undefined),
    deleteItem: vi.fn().mockResolvedValue(undefined),
    uploadAttachment: vi.fn().mockResolvedValue("photo.jpg"),
    deleteAttachment: vi.fn().mockResolvedValue(undefined),
    setPlacement: vi.fn().mockResolvedValue(undefined),
    warrantyStatus: vi.fn().mockReturnValue("ok"),
    placedItems: vi.fn().mockReturnValue([]),
    unplacedItems: vi.fn().mockReturnValue([]),
  };
}

describe("InventoryModal — Media tab", () => {
  afterEach(() => { document.body.innerHTML = ""; });

  it("shows Media tab (not Attachments)", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const item = makeItem();
    const store = makeStore(item);
    const app = mount(InventoryModal, {
      target,
      props: { item, store, inventoryCategories: [], onclose: vi.fn() },
    });
    flushSync();
    const tabs = Array.from(target.querySelectorAll(".tab")).map(t => t.textContent?.trim());
    expect(tabs).toContain("Media");
    expect(tabs.every(t => t !== "Attachments")).toBe(true);
    unmount(app);
  });

  it("Media tab is disabled when creating (item=null)", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(InventoryModal, {
      target,
      props: { item: null, store, inventoryCategories: [], onclose: vi.fn() },
    });
    flushSync();
    const mediaTab = Array.from(target.querySelectorAll(".tab"))
      .find(t => t.textContent?.includes("Media")) as HTMLButtonElement;
    expect(mediaTab.disabled).toBe(true);
    unmount(app);
  });

  it("clicking Media tab renders drop-zone", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const item = makeItem({ attachments: ["photo.jpg"] });
    const store = makeStore(item);
    const app = mount(InventoryModal, {
      target,
      props: { item, store, inventoryCategories: [], onclose: vi.fn() },
    });
    flushSync();
    const mediaTab = Array.from(target.querySelectorAll(".tab"))
      .find(t => t.textContent?.includes("Media")) as HTMLButtonElement;
    mediaTab.click();
    flushSync();
    expect(target.querySelector(".drop-zone") || target.querySelector(".media-grid")).not.toBeNull();
    unmount(app);
  });

  it("Media tab badge shows attachment count", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const item = makeItem({ attachments: ["photo.jpg", "doc.pdf"] });
    const store = makeStore(item);
    const app = mount(InventoryModal, {
      target,
      props: { item, store, inventoryCategories: [], onclose: vi.fn() },
    });
    flushSync();
    const mediaTab = Array.from(target.querySelectorAll(".tab"))
      .find(t => t.textContent?.includes("Media")) as HTMLButtonElement;
    expect(mediaTab.textContent).toContain("2");
    unmount(app);
  });
});
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd packages/editor
npx vitest run test/InventoryModal.test.ts
```

Expected: 4 failures (no Media tab, still shows Attachments).

- [ ] **Step 3: Update `InventoryModal.svelte`**

Replace the entire file with:

```svelte
<script lang="ts">
  import type { createInventoryStore, InventoryItem } from "../inventoryStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import DatePicker from "./DatePicker.svelte";
  import Modal from "./ui/Modal.svelte";
  import Input from "./ui/Input.svelte";
  import Button from "./ui/Button.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";

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

  let activeTab = $state<"info" | "media">("info");
  let name = $state(item?.name ?? "");
  let emoji = $state(item?.emoji ?? "📦");
  let category = $state(item?.category ?? "");
  let brand = $state(item?.brand ?? "");
  let model = $state(item?.model ?? "");
  let serialNumber = $state(item?.serialNumber ?? "");
  let purchaseDate = $state(item?.purchaseDate ?? "");
  let purchasePrice = $state<string>(item?.purchasePrice != null ? String(item.purchasePrice) : "");
  let warrantyExpiryDate = $state(item?.warrantyExpiryDate ?? "");
  let notes = $state(item?.notes ?? "");

  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);
  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);

  const currentItem = $derived(item ? (store.items.find((i) => i.id === item.id) ?? item) : null);
  const attachmentCount = $derived(currentItem?.attachments.length ?? 0);

  const mediaItems = $derived<MediaItem[]>(
    (currentItem?.attachments ?? []).map(name => {
      const url = `/api/inventory/items/${item!.id}/attachments/${name}`;
      const isPdf = name.toLowerCase().endsWith(".pdf");
      return { id: name, name, url, thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url, type: isPdf ? "document" : "image" };
    })
  );

  async function handleSave(): Promise<void> {
    if (!name.trim()) { error = "Name is required"; return; }
    saving = true; error = null;
    const parsedPrice = purchasePrice ? parseFloat(purchasePrice) : null;
    const patch = {
      name: name.trim(), emoji: emoji || "📦", category: category.trim(),
      brand: brand.trim() || null, model: model.trim() || null,
      serialNumber: serialNumber.trim() || null,
      purchaseDate: purchaseDate || null,
      purchasePrice: parsedPrice !== null && !isNaN(parsedPrice) ? parsedPrice : null,
      warrantyExpiryDate: warrantyExpiryDate || null,
      notes: notes.trim(),
    };
    try {
      if (isCreate) { await store.createItem(patch); } else { await store.updateItem(item!.id, patch); }
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
    try { await store.deleteItem(item.id); onclose(); }
    catch (e) { error = e instanceof Error ? e.message : "Delete failed"; deleting = false; }
  }

  async function handleUpload(files: File[]): Promise<void> {
    if (!item) return;
    uploading = true; uploadError = null;
    try { for (const file of files) await store.uploadAttachment(item.id, file); }
    catch (err) { uploadError = err instanceof Error ? err.message : "Upload failed"; }
    finally { uploading = false; }
  }

  async function handleDeleteAttachment(id: string): Promise<void> {
    if (!item) return;
    try { await store.deleteAttachment(item.id, id); }
    catch (err) { uploadError = err instanceof Error ? err.message : "Delete failed"; }
  }

  function handleItemClick(index: number): void { lightboxIndex = index; lightboxOpen = true; }
</script>

<Modal open={true} title={isCreate ? "＋ New item" : "Edit item"} {onclose} width="560px">
  <div class="tabs">
    <button class="tab" class:active={activeTab === "info"} onclick={() => { activeTab = "info"; }}>Info</button>
    <button class="tab" class:active={activeTab === "media"} disabled={isCreate}
      onclick={() => { activeTab = "media"; }}>
      Media{attachmentCount > 0 ? ` (${attachmentCount})` : ""}
    </button>
  </div>

  {#if activeTab === "info"}
    <div class="row">
      <label>Emoji</label>
      <input class="native-input emoji-input" bind:value={emoji} maxlength="2" />
      <label style="margin-left:16px">Name *</label>
      <div class="flex-grow"><Input bind:value={name} placeholder='e.g. Samsung TV 65"' /></div>
    </div>
    <div class="row">
      <label>Category</label>
      <input class="native-input flex-grow" bind:value={category} list="inv-cat-list" placeholder="Electronics, Furniture…" />
      <datalist id="inv-cat-list">{#each inventoryCategories as s}<option value={s} />{/each}</datalist>
    </div>
    <div class="row">
      <label>Brand</label>
      <div class="flex-grow"><Input bind:value={brand} placeholder="Samsung" /></div>
      <label style="margin-left:12px">Model</label>
      <div class="flex-grow"><Input bind:value={model} placeholder="QE65Q80C" /></div>
    </div>
    <div class="row">
      <label>Serial #</label>
      <div class="flex-grow"><Input bind:value={serialNumber} placeholder="XYZ123" /></div>
    </div>
    <div class="row">
      <label>Purchased</label>
      <DatePicker bind:value={purchaseDate} />
      <label style="margin-left:12px">Price (€)</label>
      <input class="native-input price-input" bind:value={purchasePrice} type="number" min="0" step="0.01" placeholder="0.00" />
    </div>
    <div class="row">
      <label>Warranty expiry</label>
      <DatePicker bind:value={warrantyExpiryDate} />
    </div>
    <div class="row col">
      <label>Notes</label>
      <textarea class="native-input" bind:value={notes} rows="3" placeholder="Additional notes…"></textarea>
    </div>
    {#if error}<div class="error">{error}</div>{/if}
  {:else}
    <MediaGallery items={mediaItems} {uploading} {uploadError}
      onUpload={handleUpload} onDelete={handleDeleteAttachment} onItemClick={handleItemClick} />
  {/if}

  {#snippet footer()}
    {#if !isCreate && onplaceonmap}
      <Button variant="secondary" onclick={() => onplaceonmap!(item!.id)}>📍 Place on map</Button>
    {/if}
    <span class="spacer"></span>
    {#if !isCreate}
      {#if confirmDelete}
        <span class="confirm-text">Delete this item?</span>
        <Button variant="danger" disabled={deleting} onclick={handleDelete}>{deleting ? "…" : "Confirm delete"}</Button>
        <Button variant="ghost" onclick={() => { confirmDelete = false; }}>Cancel</Button>
      {:else}
        <Button variant="danger" onclick={() => { confirmDelete = true; }}>🗑 Delete</Button>
      {/if}
    {/if}
    {#if activeTab === "info"}
      <Button variant="primary" disabled={saving} onclick={handleSave}>
        {saving ? "Saving…" : isCreate ? "Create" : "Save"}
      </Button>
    {/if}
  {/snippet}
</Modal>

{#if lightboxOpen && mediaItems.length > 0}
  <Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />
{/if}

<style>
  .tabs { display: flex; border-bottom: 1px solid var(--border); margin-bottom: var(--space-3); }
  .tab { padding: 8px 16px; background: none; border: none; border-bottom: 2px solid transparent; color: var(--text-muted); font-size: 12px; cursor: pointer; font-family: var(--font-sans); }
  .tab:hover:not(:disabled) { color: var(--text); }
  .tab.active { border-bottom-color: var(--accent); color: var(--text); }
  .tab:disabled { color: var(--text-faint); cursor: default; }

  .row { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
  .row.col { flex-direction: column; align-items: stretch; }
  .flex-grow { flex: 1; min-width: 0; }
  label { font-size: 11px; color: var(--text-muted); white-space: nowrap; }

  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px; font-family: var(--font-sans); box-sizing: border-box;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  .native-input::placeholder { color: var(--text-faint); }
  .emoji-input { width: 56px; text-align: center; font-size: 18px; }
  .price-input { width: 100px; }
  textarea.native-input { width: 100%; resize: vertical; }
  .error { color: var(--danger); font-size: 11px; margin-top: 4px; font-family: var(--font-sans); }
  .spacer { flex: 1; }
  .confirm-text { font-size: 11px; color: var(--danger); }
</style>
```

- [ ] **Step 4: Run tests — expect pass**

```bash
npx vitest run test/InventoryModal.test.ts
```

Expected: 4 tests pass.

- [ ] **Step 5: Run full frontend suite**

```bash
npx vitest run
```

Expected: all tests pass (no regressions).

- [ ] **Step 6: Commit**

```bash
git add packages/editor/test/InventoryModal.test.ts packages/editor/src/lib/components/InventoryModal.svelte
git commit -m "feat(inventory): MediaGallery + Lightbox in InventoryModal, rename Attachments → Media"
```

---

### Task 3: Costs backend — attachment model + routes

**Files:**
- Modify: `packages/backend/src/myhome/models_costs.py`
- Modify: `packages/backend/src/myhome/persistence_costs.py`
- Modify: `packages/backend/src/myhome/routes/costs.py`
- Modify: `packages/backend/tests/test_costs.py`

- [ ] **Step 1: Write failing tests**

Add to `packages/backend/tests/test_costs.py`:

```python
def _make_valid_pdf() -> bytes:
    import fitz
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    return doc.write()


def _entry_id(client) -> str:
    resp = client.post("/api/costs/entries", json={
        "categoryId": "cat1", "date": "2026-01-01", "totalAmount": 100.0,
    })
    return resp.json()["id"]


def test_costs_upload_jpeg_accepted(client, tmp_path):
    eid = _entry_id(client)
    resp = client.post(
        f"/api/costs/entries/{eid}/attachments",
        files={"file": ("receipt.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "receipt.jpg"
    entry = next(e for e in client.get("/api/costs").json()["entries"] if e["id"] == eid)
    assert "receipt.jpg" in entry["attachments"]


def test_costs_upload_unsupported_rejected(client, tmp_path):
    eid = _entry_id(client)
    resp = client.post(
        f"/api/costs/entries/{eid}/attachments",
        files={"file": ("x.exe", b"\x4d\x5a", "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_costs_upload_pdf_creates_thumbnail(client, tmp_path):
    eid = _entry_id(client)
    resp = client.post(
        f"/api/costs/entries/{eid}/attachments",
        files={"file": ("invoice.pdf", _make_valid_pdf(), "application/pdf")},
    )
    assert resp.status_code == 201
    thumb = tmp_path / "costs-attachments" / eid / "invoice.pdf.thumb.jpg"
    assert thumb.exists()


def test_costs_delete_attachment_removes_thumb(client, tmp_path):
    eid = _entry_id(client)
    client.post(f"/api/costs/entries/{eid}/attachments",
        files={"file": ("invoice.pdf", _make_valid_pdf(), "application/pdf")})
    thumb = tmp_path / "costs-attachments" / eid / "invoice.pdf.thumb.jpg"
    assert thumb.exists()
    client.delete(f"/api/costs/entries/{eid}/attachments/invoice.pdf")
    assert not thumb.exists()


def test_costs_get_jpeg_returns_image_content_type(client, tmp_path):
    eid = _entry_id(client)
    client.post(f"/api/costs/entries/{eid}/attachments",
        files={"file": ("receipt.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")})
    resp = client.get(f"/api/costs/entries/{eid}/attachments/receipt.jpg")
    assert resp.status_code == 200
    assert "image/jpeg" in resp.headers["content-type"]


def test_costs_attachments_empty_by_default(client):
    eid = _entry_id(client)
    entry = next(e for e in client.get("/api/costs").json()["entries"] if e["id"] == eid)
    assert entry["attachments"] == []
```

Note: the `client` fixture in `test_costs.py` uses `tmp_path` and `monkeypatch.setenv("DATA_DIR", str(tmp_path))`. Check the existing fixture matches this pattern; if the existing fixture doesn't set DATA_DIR, add it. The existing fixture in this file is:

```python
@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return TestClient(app)
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd packages/backend
python -m pytest tests/test_costs.py::test_costs_upload_jpeg_accepted -v
```

Expected: FAIL (404 — route doesn't exist yet).

- [ ] **Step 3: Add `attachments` to `models_costs.py`**

In `CostEntry`, add the field after `notes`:

```python
class CostEntry(BaseModel):
    id: str
    categoryId: str
    date: str
    totalAmount: float
    quantity: float | None = None
    unitPrice: float | None = None
    supplierId: str | None = None
    notes: str = ""
    roomId: str | None = None
    attachments: list[str] = []
```

- [ ] **Step 4: Update `persistence_costs.py`**

```python
import json
import logging
import os
import shutil
from pathlib import Path

from .models_costs import CostsDocument

_log = logging.getLogger(__name__)


def _costs_file() -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "costs.json"


def _attachments_dir(entry_id: str) -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "costs-attachments" / entry_id


def load_costs() -> CostsDocument:
    path = _costs_file()
    if not path.exists():
        return CostsDocument()
    with path.open() as f:
        raw = json.load(f)
    return CostsDocument.model_validate(raw)


def save_costs(doc: CostsDocument) -> None:
    path = _costs_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)


def save_attachment(entry_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(entry_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / filename).write_bytes(data)


def delete_attachment(entry_id: str, filename: str) -> bool:
    path = _attachments_dir(entry_id) / filename
    if not path.exists():
        return False
    path.unlink()
    thumb = path.parent / (filename + ".thumb.jpg")
    if thumb.exists():
        thumb.unlink()
    return True


def delete_all_attachments(entry_id: str) -> None:
    path = _attachments_dir(entry_id)
    if path.exists():
        shutil.rmtree(path)


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

- [ ] **Step 5: Update `routes/costs.py`**

Add to imports at top:

```python
import mimetypes
import os
import re
import uuid

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..models_costs import CostEntry, CostEntryCreate, CostEntryUpdate, CostsDocument
from ..persistence_costs import (
    _attachments_dir,
    delete_all_attachments,
    delete_attachment,
    generate_pdf_thumbnail,
    load_costs,
    save_attachment,
    save_costs,
)
```

Add these helpers and routes (append after existing routes, before end of file):

```python
_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _sanitise_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name or "attachment"


def _validate_id(entry_id: str) -> None:
    if not _ID_RE.fullmatch(entry_id):
        raise HTTPException(status_code=400, detail="Invalid id")


def _validate_filename(filename: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", filename) or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")


@router.post("/api/costs/entries/{id}/attachments", status_code=201)
async def upload_cost_attachment(id: str, file: UploadFile) -> dict:
    _validate_id(id)
    doc = load_costs()
    entry = next((e for e in doc.entries if e.id == id), None)
    if not entry:
        raise HTTPException(status_code=404)
    original = file.filename or ""
    ext = os.path.splitext(original.lower())[1]
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not supported")
    filename = _sanitise_filename(original)
    data = await file.read()
    save_attachment(id, filename, data)
    if ext == ".pdf":
        generate_pdf_thumbnail(
            _attachments_dir(id) / filename,
            _attachments_dir(id) / (filename + ".thumb.jpg"),
        )
    if filename not in entry.attachments:
        entry.attachments.append(filename)
    save_costs(doc)
    return {"filename": filename}


@router.get("/api/costs/entries/{id}/attachments/{filename}")
def get_cost_attachment(id: str, filename: str) -> FileResponse:
    _validate_id(id)
    _validate_filename(filename)
    base = _attachments_dir(id).resolve()
    path = (base / filename).resolve()
    if not str(path).startswith(str(base) + "/") or not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", content_disposition_type="inline")


@router.delete("/api/costs/entries/{id}/attachments/{filename}", status_code=204)
def remove_cost_attachment(id: str, filename: str) -> None:
    _validate_id(id)
    _validate_filename(filename)
    doc = load_costs()
    entry = next((e for e in doc.entries if e.id == id), None)
    if not entry:
        raise HTTPException(status_code=404)
    if not delete_attachment(id, filename):
        raise HTTPException(status_code=404)
    entry.attachments = [a for a in entry.attachments if a != filename]
    save_costs(doc)
```

Also update the existing `delete_entry` route to clean up attachments:

```python
@router.delete("/api/costs/entries/{id}", status_code=204)
def delete_entry(id: str) -> None:
    doc = load_costs()
    before = len(doc.entries)
    doc.entries = [e for e in doc.entries if e.id != id]
    if len(doc.entries) == before:
        raise HTTPException(status_code=404)
    save_costs(doc)
    delete_all_attachments(id)
```

- [ ] **Step 6: Run new tests — expect pass**

```bash
python -m pytest tests/test_costs.py -v
```

Expected: all existing + new tests pass.

- [ ] **Step 7: Commit**

```bash
git add packages/backend/src/myhome/models_costs.py packages/backend/src/myhome/persistence_costs.py packages/backend/src/myhome/routes/costs.py packages/backend/tests/test_costs.py
git commit -m "feat(costs): add attachments field, image+PDF upload routes, PDF thumbnail"
```

---

### Task 4: Costs frontend — tabs + MediaGallery in CostsEntryModal

**Files:**
- Modify: `packages/editor/src/lib/costsStore.svelte.ts`
- Create: `packages/editor/test/CostsEntryModal.test.ts`
- Modify: `packages/editor/src/lib/components/CostsEntryModal.svelte`

- [ ] **Step 1: Write failing tests**

Create `packages/editor/test/CostsEntryModal.test.ts`:

```typescript
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import CostsEntryModal from "../src/lib/components/CostsEntryModal.svelte";
import type { CostEntry } from "../src/lib/costsStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makeEntry(overrides: Partial<CostEntry> = {}): CostEntry {
  return {
    id: "c1", categoryId: "cat-electricity", date: "2026-01-15",
    totalAmount: 120.5, quantity: null, unitPrice: null,
    supplierId: null, notes: "", roomId: null, attachments: [], ...overrides,
  };
}

function makeSettingsStore() {
  return {
    costCategories: [{ id: "cat-electricity", name: "Electricity", emoji: "⚡", color: "#ff0", unit: null }],
    suppliers: [],
    workCategories: [],
  };
}

function makeFloorStore() {
  return { floors: [] };
}

function makeCostsStore(entries: CostEntry[] = []) {
  return {
    entries,
    loaded: true,
    loadError: null,
    createEntry: vi.fn().mockResolvedValue(undefined),
    updateEntry: vi.fn().mockResolvedValue(undefined),
    deleteEntry: vi.fn().mockResolvedValue(undefined),
    uploadAttachment: vi.fn().mockResolvedValue("receipt.jpg"),
    deleteAttachment: vi.fn().mockResolvedValue(undefined),
  };
}

describe("CostsEntryModal — Media tab", () => {
  it("shows Info and Media tabs when editing", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const entry = makeEntry();
    const costsStore = makeCostsStore([entry]);
    const app = mount(CostsEntryModal, {
      target,
      props: { entry, costsStore, settingsStore: makeSettingsStore(), floorStore: makeFloorStore(), onclose: vi.fn() },
    });
    flushSync();
    const tabs = Array.from(target.querySelectorAll(".tab")).map(t => t.textContent?.trim());
    expect(tabs).toContain("Info");
    expect(tabs.some(t => t?.includes("Media"))).toBe(true);
    unmount(app);
  });

  it("Media tab is disabled when creating (entry=null)", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const costsStore = makeCostsStore();
    const app = mount(CostsEntryModal, {
      target,
      props: { entry: null, costsStore, settingsStore: makeSettingsStore(), floorStore: makeFloorStore(), onclose: vi.fn() },
    });
    flushSync();
    const mediaTab = Array.from(target.querySelectorAll(".tab"))
      .find(t => t.textContent?.includes("Media")) as HTMLButtonElement | undefined;
    expect(mediaTab?.disabled).toBe(true);
    unmount(app);
  });

  it("clicking Media tab renders MediaGallery drop-zone", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const entry = makeEntry({ attachments: ["receipt.jpg"] });
    const costsStore = makeCostsStore([entry]);
    const app = mount(CostsEntryModal, {
      target,
      props: { entry, costsStore, settingsStore: makeSettingsStore(), floorStore: makeFloorStore(), onclose: vi.fn() },
    });
    flushSync();
    const mediaTab = Array.from(target.querySelectorAll(".tab"))
      .find(t => t.textContent?.includes("Media")) as HTMLButtonElement;
    mediaTab.click();
    flushSync();
    expect(target.querySelector(".drop-zone") || target.querySelector(".media-grid")).not.toBeNull();
    unmount(app);
  });
});
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd packages/editor
npx vitest run test/CostsEntryModal.test.ts
```

Expected: failures (no Media tab).

- [ ] **Step 3: Update `costsStore.svelte.ts`**

Add `attachments: string[]` to `CostEntry` interface:

```typescript
export interface CostEntry {
  id: string;
  categoryId: string;
  date: string;
  totalAmount: number;
  quantity: number | null;
  unitPrice: number | null;
  supplierId: string | null;
  notes: string;
  roomId: string | null;
  attachments: string[];
}
```

Update `createEntry` signature to omit `attachments`:

```typescript
async function createEntry(data: Omit<CostEntry, "id" | "attachments">): Promise<void> {
```

Add `uploadAttachment` and `deleteAttachment` before the `init()` call at the bottom of the store function:

```typescript
async function uploadAttachment(id: string, file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(`/api/costs/entries/${id}/attachments`, { method: "POST", body: form });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const result = await resp.json();
  await init();
  return result.filename as string;
}

async function deleteAttachment(id: string, filename: string): Promise<void> {
  const resp = await fetch(`/api/costs/entries/${id}/attachments/${filename}`, { method: "DELETE" });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  await init();
}
```

Add them to the returned object:

```typescript
return {
  // ... existing exports ...
  uploadAttachment,
  deleteAttachment,
};
```

- [ ] **Step 4: Update `CostsEntryModal.svelte`**

Replace the entire file:

```svelte
<script lang="ts">
  import type { createCostsStore, CostEntry } from "../costsStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { createHouseStore } from "../houseStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import DatePicker from "./DatePicker.svelte";
  import Modal from "./ui/Modal.svelte";
  import Button from "./ui/Button.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";

  type CostsStore = ReturnType<typeof createCostsStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;
  type HouseStore = ReturnType<typeof createHouseStore>;

  interface Props {
    entry: CostEntry | null;
    costsStore: CostsStore;
    settingsStore: SettingsStore;
    floorStore: HouseStore;
    onclose: () => void;
  }

  let { entry, costsStore, settingsStore, floorStore, onclose }: Props = $props();

  const isCreate = entry === null;

  let activeTab = $state<"info" | "media">("info");
  let categoryId = $state(entry?.categoryId ?? settingsStore.costCategories[0]?.id ?? "");
  let date = $state(entry?.date ?? new Date().toISOString().slice(0, 10));
  let totalAmount = $state<string>(entry?.totalAmount != null ? String(entry.totalAmount) : "");
  let quantity = $state<string>(entry?.quantity != null ? String(entry.quantity) : "");
  let unitPrice = $state<string>(entry?.unitPrice != null ? String(entry.unitPrice) : "");
  let supplierId = $state(entry?.supplierId ?? "");
  let notes = $state(entry?.notes ?? "");
  let roomId = $state(entry?.roomId ?? "");

  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);
  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);

  const selectedCategory = $derived(settingsStore.costCategories.find(c => c.id === categoryId) ?? null);
  const hasUnit = $derived(selectedCategory?.unit != null);
  const allRooms = $derived(floorStore.floors.flatMap((f: { rooms: { id: string; label: string }[] }) => f.rooms));

  const currentEntry = $derived(entry ? (costsStore.entries.find(e => e.id === entry!.id) ?? entry) : null);
  const attachmentCount = $derived(currentEntry?.attachments.length ?? 0);

  const mediaItems = $derived<MediaItem[]>(
    (currentEntry?.attachments ?? []).map(name => {
      const url = `/api/costs/entries/${entry!.id}/attachments/${name}`;
      const isPdf = name.toLowerCase().endsWith(".pdf");
      return { id: name, name, url, thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url, type: isPdf ? "document" : "image" };
    })
  );

  function autoCalc(changed: "total" | "qty" | "price"): void {
    const tot = parseFloat(totalAmount);
    const qty = parseFloat(quantity);
    const ppu = parseFloat(unitPrice);
    const totOk = !isNaN(tot) && tot > 0;
    const qtyOk = !isNaN(qty) && qty > 0;
    const ppuOk = !isNaN(ppu) && ppu > 0;
    if ((changed === "qty" || changed === "price") && qtyOk && ppuOk) { totalAmount = (qty * ppu).toFixed(2); }
    else if (changed === "total" && totOk && qtyOk) { unitPrice = (tot / qty).toFixed(4); }
    else if (changed === "total" && totOk && ppuOk && quantity === "") { quantity = (tot / ppu).toFixed(2); }
  }

  async function handleSave(): Promise<void> {
    if (!categoryId) { error = "Category is required"; return; }
    if (!date) { error = "Date is required"; return; }
    const parsedTotal = parseFloat(totalAmount);
    if (isNaN(parsedTotal) || parsedTotal <= 0) { error = "Total amount is required"; return; }
    saving = true; error = null;
    const patch = {
      categoryId, date, totalAmount: parsedTotal,
      quantity: quantity ? parseFloat(quantity) || null : null,
      unitPrice: unitPrice ? parseFloat(unitPrice) || null : null,
      supplierId: supplierId || null, notes: notes.trim(), roomId: roomId || null,
    };
    try {
      if (isCreate) { await costsStore.createEntry(patch); } else { await costsStore.updateEntry(entry!.id, patch); }
      onclose();
    } catch (e) { error = e instanceof Error ? e.message : "Save failed"; }
    finally { saving = false; }
  }

  async function handleDelete(): Promise<void> {
    if (!entry) return;
    deleting = true;
    try { await costsStore.deleteEntry(entry.id); onclose(); }
    catch (e) { error = e instanceof Error ? e.message : "Delete failed"; deleting = false; }
  }

  async function handleUpload(files: File[]): Promise<void> {
    if (!entry) return;
    uploading = true; uploadError = null;
    try { for (const file of files) await costsStore.uploadAttachment(entry.id, file); }
    catch (err) { uploadError = err instanceof Error ? err.message : "Upload failed"; }
    finally { uploading = false; }
  }

  async function handleDeleteAttachment(id: string): Promise<void> {
    if (!entry) return;
    try { await costsStore.deleteAttachment(entry.id, id); }
    catch (err) { uploadError = err instanceof Error ? err.message : "Delete failed"; }
  }

  function handleItemClick(index: number): void { lightboxIndex = index; lightboxOpen = true; }
</script>

<Modal open={true} title={isCreate ? "＋ New entry" : "Edit entry"} {onclose} width="520px">
  <div class="tabs">
    <button class="tab" class:active={activeTab === "info"} onclick={() => { activeTab = "info"; }}>Info</button>
    <button class="tab" class:active={activeTab === "media"} disabled={isCreate}
      onclick={() => { activeTab = "media"; }}>
      Media{attachmentCount > 0 ? ` (${attachmentCount})` : ""}
    </button>
  </div>

  {#if activeTab === "info"}
    <div class="row">
      <label>Category *</label>
      <select class="native-input flex-grow" bind:value={categoryId}>
        {#each settingsStore.costCategories as cat}
          <option value={cat.id}>{cat.emoji} {cat.name}</option>
        {/each}
      </select>
    </div>
    <div class="row">
      <label>Date *</label>
      <DatePicker bind:value={date} />
    </div>
    {#if hasUnit}
      <div class="row">
        <label>Quantity ({selectedCategory!.unit})</label>
        <input class="native-input num-input" bind:value={quantity} type="number" min="0" step="any" placeholder="0" oninput={() => autoCalc("qty")} />
        <label style="margin-left:12px">Unit price (€/{selectedCategory!.unit})</label>
        <input class="native-input num-input" bind:value={unitPrice} type="number" min="0" step="any" placeholder="0.00" oninput={() => autoCalc("price")} />
      </div>
    {/if}
    <div class="row">
      <label>Total amount (€) *</label>
      <input class="native-input num-input" bind:value={totalAmount} type="number" min="0" step="any" placeholder="0.00" oninput={() => autoCalc("total")} />
    </div>
    <div class="row">
      <label>Supplier</label>
      <select class="native-input flex-grow" bind:value={supplierId}>
        <option value="">— No supplier —</option>
        {#each settingsStore.suppliers as s}<option value={s.id}>{s.name}</option>{/each}
      </select>
    </div>
    <div class="row">
      <label>Room</label>
      <select class="native-input flex-grow" bind:value={roomId}>
        <option value="">No room</option>
        {#each allRooms as room}<option value={room.id}>{room.label}</option>{/each}
      </select>
    </div>
    <div class="row col">
      <label>Notes</label>
      <textarea class="native-input" bind:value={notes} rows="2" placeholder="Optional notes…"></textarea>
    </div>
    {#if error}<div class="error">{error}</div>{/if}
  {:else}
    <MediaGallery items={mediaItems} {uploading} {uploadError}
      onUpload={handleUpload} onDelete={handleDeleteAttachment} onItemClick={handleItemClick} />
  {/if}

  {#snippet footer()}
    <span class="spacer"></span>
    {#if !isCreate}
      {#if confirmDelete}
        <span class="confirm-text">Delete this entry?</span>
        <Button variant="danger" disabled={deleting} onclick={handleDelete}>{deleting ? "…" : "Confirm delete"}</Button>
        <Button variant="ghost" onclick={() => { confirmDelete = false; }}>Cancel</Button>
      {:else}
        <Button variant="danger" onclick={() => { confirmDelete = true; }}>🗑 Delete</Button>
      {/if}
    {/if}
    {#if activeTab === "info"}
      <Button variant="primary" disabled={saving} onclick={handleSave}>
        {saving ? "Saving…" : isCreate ? "Create" : "Save"}
      </Button>
    {/if}
  {/snippet}
</Modal>

{#if lightboxOpen && mediaItems.length > 0}
  <Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />
{/if}

<style>
  .tabs { display: flex; border-bottom: 1px solid var(--border); margin-bottom: var(--space-3); }
  .tab { padding: 8px 16px; background: none; border: none; border-bottom: 2px solid transparent; color: var(--text-muted); font-size: 12px; cursor: pointer; font-family: var(--font-sans); }
  .tab:hover:not(:disabled) { color: var(--text); }
  .tab.active { border-bottom-color: var(--accent); color: var(--text); }
  .tab:disabled { color: var(--text-faint); cursor: default; }

  .row { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
  .row.col { flex-direction: column; align-items: stretch; }
  .flex-grow { flex: 1; min-width: 0; }
  label { font-size: 11px; color: var(--text-muted); white-space: nowrap; }

  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px; font-family: var(--font-sans); box-sizing: border-box;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  .native-input::placeholder { color: var(--text-faint); }
  select.native-input { cursor: pointer; }
  .num-input { width: 120px; }
  textarea.native-input { width: 100%; resize: vertical; }
  .error { color: var(--danger); font-size: 11px; margin-top: 4px; font-family: var(--font-sans); }
  .spacer { flex: 1; }
  .confirm-text { font-size: 11px; color: var(--danger); }
</style>
```

- [ ] **Step 5: Run new tests — expect pass**

```bash
npx vitest run test/CostsEntryModal.test.ts
```

Expected: 3 tests pass.

- [ ] **Step 6: Run full frontend suite**

```bash
npx vitest run
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/costsStore.svelte.ts packages/editor/src/lib/components/CostsEntryModal.svelte packages/editor/test/CostsEntryModal.test.ts
git commit -m "feat(costs): add attachments to store, Info/Media tabs in CostsEntryModal"
```

---

### Task 5: KB backend — attachment model + routes

**Files:**
- Modify: `packages/backend/src/myhome/models_kb.py`
- Modify: `packages/backend/src/myhome/persistence_kb.py`
- Modify: `packages/backend/src/myhome/routes/kb.py`
- Modify: `packages/backend/tests/test_kb.py`

- [ ] **Step 1: Write failing tests**

Add to `packages/backend/tests/test_kb.py`:

```python
def _make_valid_pdf() -> bytes:
    import fitz
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    return doc.write()


def _entry_id(client) -> str:
    resp = client.post("/api/kb", json={"title": "Test entry", "content": "Hello"})
    return resp.json()["id"]


def test_kb_attachments_empty_by_default(client):
    eid = _entry_id(client)
    resp = client.get("/api/kb")
    entry = next(e for e in resp.json()["entries"] if e["id"] == eid)
    assert entry["attachments"] == []


def test_kb_upload_jpeg_accepted(client, tmp_path):
    eid = _entry_id(client)
    resp = client.post(
        f"/api/kb/{eid}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "photo.jpg"
    entry = next(e for e in client.get("/api/kb").json()["entries"] if e["id"] == eid)
    assert "photo.jpg" in entry["attachments"]


def test_kb_upload_unsupported_rejected(client, tmp_path):
    eid = _entry_id(client)
    resp = client.post(
        f"/api/kb/{eid}/attachments",
        files={"file": ("x.docx", b"\x00" * 50, "application/vnd.openxmlformats")},
    )
    assert resp.status_code == 400


def test_kb_upload_pdf_creates_thumbnail(client, tmp_path):
    eid = _entry_id(client)
    resp = client.post(
        f"/api/kb/{eid}/attachments",
        files={"file": ("note.pdf", _make_valid_pdf(), "application/pdf")},
    )
    assert resp.status_code == 201
    thumb = tmp_path / "kb-attachments" / eid / "note.pdf.thumb.jpg"
    assert thumb.exists()


def test_kb_delete_attachment_removes_thumb(client, tmp_path):
    eid = _entry_id(client)
    client.post(f"/api/kb/{eid}/attachments",
        files={"file": ("note.pdf", _make_valid_pdf(), "application/pdf")})
    thumb = tmp_path / "kb-attachments" / eid / "note.pdf.thumb.jpg"
    assert thumb.exists()
    client.delete(f"/api/kb/{eid}/attachments/note.pdf")
    assert not thumb.exists()


def test_kb_get_jpeg_returns_image_content_type(client, tmp_path):
    eid = _entry_id(client)
    client.post(f"/api/kb/{eid}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")})
    resp = client.get(f"/api/kb/{eid}/attachments/photo.jpg")
    assert resp.status_code == 200
    assert "image/jpeg" in resp.headers["content-type"]


def test_kb_attachments_persist_after_entry_update(client, tmp_path):
    eid = _entry_id(client)
    client.post(f"/api/kb/{eid}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")})
    client.put(f"/api/kb/{eid}", json={"title": "Updated title"})
    entry = next(e for e in client.get("/api/kb").json()["entries"] if e["id"] == eid)
    assert "photo.jpg" in entry["attachments"]


def test_kb_delete_entry_removes_attachment_dir(client, tmp_path):
    eid = _entry_id(client)
    client.post(f"/api/kb/{eid}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")})
    att_dir = tmp_path / "kb-attachments" / eid
    assert att_dir.exists()
    client.delete(f"/api/kb/{eid}")
    assert not att_dir.exists()
```

Note: the `client` fixture in `test_kb.py` must set DATA_DIR. If it does not already, update it:
```python
@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return TestClient(app)
```

- [ ] **Step 2: Run tests — expect failures**

```bash
python -m pytest tests/test_kb.py::test_kb_upload_jpeg_accepted -v
```

Expected: FAIL (404 — route not defined, `attachments` not in model).

- [ ] **Step 3: Update `models_kb.py`**

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


class KBDocument(BaseModel):
    version: int = 1
    entries: list[KBEntry] = []


class KBCreate(BaseModel):
    title: str
    content: str = ""


class KBUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
```

- [ ] **Step 4: Update `persistence_kb.py`**

```python
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from .models_kb import KBEntry

_log = logging.getLogger(__name__)


def _kb_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "kb"


def _entry_path(id: str) -> Path:
    return _kb_dir() / f"{id}.md"


def _attachments_dir(entry_id: str) -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "kb-attachments" / entry_id


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
    ]
    if entry.attachments:
        lines.append(f"attachments: {','.join(entry.attachments)}")
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
    return KBEntry(
        id=meta["id"],
        title=meta["title"],
        content=body.lstrip("\n"),
        createdAt=meta.get("createdAt", ""),
        updatedAt=meta.get("updatedAt", ""),
        attachments=attachments,
    )


def load_all() -> list[KBEntry]:
    d = _kb_dir()
    if not d.exists():
        return []
    entries = [e for path in d.glob("*.md") if (e := _read_entry_file(path))]
    entries.sort(key=lambda e: e.createdAt)
    return entries


def load_entry(id: str) -> KBEntry | None:
    return _read_entry_file(_entry_path(id))


def save_entry(entry: KBEntry) -> None:
    d = _kb_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = _entry_path(entry.id)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(_build_file(entry), encoding="utf-8")
    tmp.replace(path)


def delete_entry(id: str) -> bool:
    path = _entry_path(id)
    if not path.exists():
        return False
    path.unlink()
    att_dir = _attachments_dir(id)
    if att_dir.exists():
        shutil.rmtree(att_dir)
    return True


def save_attachment(entry_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(entry_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / filename).write_bytes(data)


def delete_attachment(entry_id: str, filename: str) -> bool:
    path = _attachments_dir(entry_id) / filename
    if not path.exists():
        return False
    path.unlink()
    thumb = path.parent / (filename + ".thumb.jpg")
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

- [ ] **Step 5: Update `routes/kb.py`**

```python
import mimetypes
import os
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..models_kb import KBCreate, KBDocument, KBEntry, KBUpdate
from ..persistence_kb import (
    _attachments_dir,
    delete_attachment,
    delete_entry,
    generate_pdf_thumbnail,
    load_all,
    load_entry,
    save_attachment,
    save_entry,
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


@router.get("/api/kb", response_model=KBDocument)
def get_kb() -> KBDocument:
    return KBDocument(entries=load_all())


@router.post("/api/kb", response_model=KBEntry, status_code=201)
def create_entry(body: KBCreate) -> KBEntry:
    now = _now()
    entry = KBEntry(id=str(uuid.uuid4()), title=body.title, content=body.content, createdAt=now, updatedAt=now)
    save_entry(entry)
    return entry


@router.put("/api/kb/{id}", status_code=204)
def update_entry(id: str, body: KBUpdate) -> None:
    entry = load_entry(id)
    if not entry:
        raise HTTPException(status_code=404)
    if body.title is not None:
        entry.title = body.title
    if body.content is not None:
        entry.content = body.content
    entry.updatedAt = _now()
    save_entry(entry)


@router.delete("/api/kb/{id}", status_code=204)
def delete_kb_entry(id: str) -> None:
    if not delete_entry(id):
        raise HTTPException(status_code=404)


@router.post("/api/kb/{id}/attachments", status_code=201)
async def upload_kb_attachment(id: str, file: UploadFile) -> dict:
    _validate_id(id)
    entry = load_entry(id)
    if not entry:
        raise HTTPException(status_code=404)
    original = file.filename or ""
    ext = os.path.splitext(original.lower())[1]
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not supported")
    filename = _sanitise_filename(original)
    data = await file.read()
    save_attachment(id, filename, data)
    if ext == ".pdf":
        generate_pdf_thumbnail(
            _attachments_dir(id) / filename,
            _attachments_dir(id) / (filename + ".thumb.jpg"),
        )
    if filename not in entry.attachments:
        entry.attachments.append(filename)
    entry.updatedAt = _now()
    save_entry(entry)
    return {"filename": filename}


@router.get("/api/kb/{id}/attachments/{filename}")
def get_kb_attachment(id: str, filename: str) -> FileResponse:
    _validate_id(id)
    _validate_filename(filename)
    base = _attachments_dir(id).resolve()
    path = (base / filename).resolve()
    if not str(path).startswith(str(base) + "/") or not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", content_disposition_type="inline")


@router.delete("/api/kb/{id}/attachments/{filename}", status_code=204)
def delete_kb_attachment(id: str, filename: str) -> None:
    _validate_id(id)
    _validate_filename(filename)
    entry = load_entry(id)
    if not entry:
        raise HTTPException(status_code=404)
    if not delete_attachment(id, filename):
        raise HTTPException(status_code=404)
    entry.attachments = [a for a in entry.attachments if a != filename]
    entry.updatedAt = _now()
    save_entry(entry)
```

- [ ] **Step 6: Run new tests — expect pass**

```bash
python -m pytest tests/test_kb.py -v
```

Expected: all existing + new tests pass.

- [ ] **Step 7: Commit**

```bash
git add packages/backend/src/myhome/models_kb.py packages/backend/src/myhome/persistence_kb.py packages/backend/src/myhome/routes/kb.py packages/backend/tests/test_kb.py
git commit -m "feat(kb): add attachments to model+frontmatter, image+PDF upload routes"
```

---

### Task 6: KB frontend — Media tab in KBPage

**Files:**
- Modify: `packages/editor/src/lib/kbStore.svelte.ts`
- Modify: `packages/editor/src/lib/components/KBPage.svelte`
- Modify: `packages/editor/test/KBPage.test.ts`

- [ ] **Step 1: Write failing tests**

Add to `packages/editor/test/KBPage.test.ts` (append at end):

```typescript
// Update makeEntry to include attachments:
// makeEntry already exists in this file — update its return type:
// attachments: [] as string[]
// Add to the existing makeEntry overrides: attachments: [] as string[]

describe("KBPage — Media tab", () => {
  it("shows Content and Media tab buttons when entry is selected", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    const tabs = Array.from(target.querySelectorAll(".content-tab")).map(t => t.textContent?.trim());
    expect(tabs).toContain("Content");
    expect(tabs.some(t => t?.includes("Media"))).toBe(true);
    unmount(app);
    target.remove();
  });

  it("clicking Media tab renders MediaGallery drop-zone", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = {
      ...makeStore([makeEntry({ attachments: ["photo.jpg"] })]),
      uploadAttachment: vi.fn().mockResolvedValue("photo.jpg"),
      deleteAttachment: vi.fn().mockResolvedValue(undefined),
    };
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    const mediaTab = Array.from(target.querySelectorAll(".content-tab"))
      .find(t => t.textContent?.includes("Media")) as HTMLButtonElement;
    mediaTab.click();
    flushSync();
    expect(target.querySelector(".drop-zone") || target.querySelector(".media-grid")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("switching entries resets to Content tab", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = {
      ...makeStore([makeEntry({ id: "e1" }), makeEntry({ id: "e2", title: "Second entry" })]),
      uploadAttachment: vi.fn().mockResolvedValue("x.jpg"),
      deleteAttachment: vi.fn().mockResolvedValue(undefined),
    };
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    // Select first entry, switch to media
    (target.querySelectorAll(".entry-row")[0] as HTMLElement).click();
    flushSync();
    const mediaTab = Array.from(target.querySelectorAll(".content-tab"))
      .find(t => t.textContent?.includes("Media")) as HTMLButtonElement;
    mediaTab.click();
    flushSync();
    // Select second entry — tab should reset to content
    (target.querySelectorAll(".entry-row")[1] as HTMLElement).click();
    flushSync();
    const activeTab = Array.from(target.querySelectorAll(".content-tab"))
      .find(t => t.classList.contains("active"));
    expect(activeTab?.textContent?.trim()).toBe("Content");
    unmount(app);
    target.remove();
  });
});
```

Also update `makeEntry` in this test file to include `attachments`:
```typescript
function makeEntry(overrides: Partial<KBEntry> = {}): KBEntry {
  return {
    id: "e1",
    title: "How to paint",
    content: "# Painting\n\nUse good brushes.",
    createdAt: "2026-06-28T10:00:00Z",
    updatedAt: "2026-06-28T10:00:00Z",
    attachments: [],
    ...overrides,
  };
}
```

Also update `makeStore` to include `uploadAttachment` and `deleteAttachment`:
```typescript
function makeStore(entries: KBEntry[] = [], overrides: Partial<ReturnType<typeof makeStore>> = {}) {
  return {
    entries,
    loaded: true,
    loadError: null as string | null,
    createEntry: vi.fn().mockResolvedValue(makeEntry({ id: "new1", title: "New entry", content: "" })),
    updateEntry: vi.fn().mockResolvedValue(undefined),
    deleteEntry: vi.fn().mockResolvedValue(undefined),
    uploadAttachment: vi.fn().mockResolvedValue("file.jpg"),
    deleteAttachment: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd packages/editor
npx vitest run test/KBPage.test.ts
```

Expected: new tests fail (no `.content-tab` elements).

- [ ] **Step 3: Update `kbStore.svelte.ts`**

Add `attachments: string[]` to `KBEntry` interface:

```typescript
export interface KBEntry {
  id: string;
  title: string;
  content: string;
  createdAt: string;
  updatedAt: string;
  attachments: string[];
}
```

Add `uploadAttachment` and `deleteAttachment` before `init()` call:

```typescript
async function uploadAttachment(id: string, file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(`/api/kb/${id}/attachments`, { method: "POST", body: form });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const result = await resp.json();
  await init();
  return result.filename as string;
}

async function deleteAttachment(id: string, filename: string): Promise<void> {
  const resp = await fetch(`/api/kb/${id}/attachments/${filename}`, { method: "DELETE" });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  await init();
}
```

Add to the return object:
```typescript
return {
  get entries() { return entries as KBEntry[]; },
  get loaded() { return loaded; },
  get loadError() { return loadError; },
  createEntry,
  updateEntry,
  deleteEntry,
  uploadAttachment,
  deleteAttachment,
};
```

- [ ] **Step 4: Update `KBPage.svelte`**

Replace the entire file:

```svelte
<script lang="ts">
  import type { createKBStore, KBEntry } from "../kbStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import MarkdownEditor from "./ui/MarkdownEditor.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";

  type KBStore = ReturnType<typeof createKBStore>;
  interface Props { store: KBStore; }
  let { store }: Props = $props();

  let selectedId = $state<string | null>(null);
  let contentTab = $state<"content" | "media">("content");
  let editing = $state(false);
  let draftTitle = $state("");
  let draftContent = $state("");
  let confirmDelete = $state(false);
  let saving = $state(false);
  let error = $state<string | null>(null);
  let searchQuery = $state("");
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);
  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);

  const filteredEntries = $derived(
    store.entries.filter((e) => e.title.toLowerCase().includes(searchQuery.toLowerCase())),
  );

  const selectedEntry = $derived(
    selectedId ? (store.entries.find((e) => e.id === selectedId) ?? null) : null,
  );

  const mediaItems = $derived<MediaItem[]>(
    (selectedEntry?.attachments ?? []).map(name => {
      const url = `/api/kb/${selectedId}/attachments/${name}`;
      const isPdf = name.toLowerCase().endsWith(".pdf");
      return { id: name, name, url, thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url, type: isPdf ? "document" : "image" };
    })
  );

  function selectEntry(entry: KBEntry): void {
    selectedId = entry.id;
    draftTitle = entry.title;
    draftContent = entry.content;
    editing = false;
    confirmDelete = false;
    contentTab = "content";
    error = null;
  }

  async function handleNew(): Promise<void> {
    try {
      const entry = await store.createEntry({ title: "New entry", content: "" });
      selectEntry(entry);
      editing = true;
    } catch (e) {
      error = e instanceof Error ? e.message : "Create failed";
    }
  }

  async function handleSave(): Promise<void> {
    if (!selectedId) return;
    if (!draftTitle.trim()) { error = "Title cannot be empty"; return; }
    saving = true; error = null;
    try {
      await store.updateEntry(selectedId, { title: draftTitle.trim(), content: draftContent });
      editing = false;
    } catch (e) {
      error = e instanceof Error ? e.message : "Save failed";
    } finally {
      saving = false;
    }
  }

  function handleCancel(): void {
    if (selectedEntry) { draftTitle = selectedEntry.title; draftContent = selectedEntry.content; }
    editing = false; error = null;
  }

  async function handleDelete(): Promise<void> {
    if (!selectedId) return;
    try {
      await store.deleteEntry(selectedId);
      selectedId = null; editing = false; confirmDelete = false;
    } catch (e) {
      error = e instanceof Error ? e.message : "Delete failed";
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

  function fmtDate(iso: string): string {
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }
</script>

<div class="kb-page">
  <div class="kb-sidebar">
    <div class="sidebar-toolbar">
      <Input placeholder="🔍 Search…" bind:value={searchQuery} />
      <Button onclick={handleNew}>＋ New</Button>
    </div>
    <div class="entry-list">
      {#each filteredEntries as entry (entry.id)}
        <div
          role="button" tabindex="0"
          class="entry-row"
          class:active={entry.id === selectedId}
          onclick={() => selectEntry(entry)}
          onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") selectEntry(entry); }}
        >
          <div class="entry-title">{entry.title}</div>
          <div class="entry-date">{fmtDate(entry.updatedAt)}</div>
        </div>
      {:else}
        <div class="list-empty">
          {searchQuery ? "No matching entries." : "No entries yet."}
        </div>
      {/each}
    </div>
  </div>

  <div class="kb-content">
    {#if !selectedEntry}
      <div class="content-empty">Select an entry or create one</div>
    {:else}
      <div class="content-header">
        <div class="content-tabs-title">
          {#if editing}
            <input class="title-input" bind:value={draftTitle} placeholder="Entry title" />
          {:else}
            <h1 class="content-title">{selectedEntry.title}</h1>
          {/if}
          <div class="content-tab-bar">
            <button class="content-tab" class:active={contentTab === "content"}
              onclick={() => { contentTab = "content"; }}>Content</button>
            <button class="content-tab" class:active={contentTab === "media"}
              onclick={() => { contentTab = "media"; editing = false; }}>
              Media{selectedEntry.attachments.length > 0 ? ` (${selectedEntry.attachments.length})` : ""}
            </button>
          </div>
        </div>
        <div class="header-actions">
          {#if contentTab === "content" && !editing}
            <Button variant="secondary" onclick={() => { editing = true; }}>Edit</Button>
          {/if}
          {#if confirmDelete}
            <span class="confirm-text">Delete?</span>
            <Button variant="danger" onclick={handleDelete}>✓</Button>
            <Button variant="ghost" onclick={() => { confirmDelete = false; }}>✕</Button>
          {:else}
            <Button variant="ghost" onclick={() => { confirmDelete = true; }} title="Delete entry">🗑</Button>
          {/if}
        </div>
      </div>

      <div class="content-body">
        {#if contentTab === "content"}
          <MarkdownEditor bind:value={draftContent} bind:editing placeholder="Start writing in Markdown…" />
          {#if error}<div class="content-error">{error}</div>{/if}
          {#if editing}
            <div class="content-footer">
              <Button variant="primary" disabled={saving} onclick={handleSave}>{saving ? "Saving…" : "Save"}</Button>
              <Button variant="secondary" onclick={handleCancel}>Cancel</Button>
            </div>
          {/if}
        {:else}
          <MediaGallery items={mediaItems} {uploading} {uploadError}
            onUpload={handleUpload} onDelete={handleDeleteAttachment} onItemClick={handleItemClick} />
        {/if}
      </div>
    {/if}
  </div>
</div>

{#if lightboxOpen && mediaItems.length > 0}
  <Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />
{/if}

<style>
  .kb-page { display: flex; height: 100%; background: var(--bg); font-family: var(--font-sans); }

  .kb-sidebar { width: 260px; flex-shrink: 0; display: flex; flex-direction: column; border-right: 1px solid var(--border); }
  .sidebar-toolbar { display: flex; gap: var(--space-2); padding: var(--space-3); border-bottom: 1px solid var(--border); flex-shrink: 0; align-items: center; }
  .sidebar-toolbar :global(.ui-input) { flex: 1; }
  .entry-list { flex: 1; overflow-y: auto; padding: var(--space-2); display: flex; flex-direction: column; gap: 2px; }
  .entry-row { padding: 8px 10px; border-radius: var(--radius-md); cursor: pointer; border-left: 3px solid transparent; }
  .entry-row:hover { background: var(--surface-hover); }
  .entry-row.active { background: var(--surface-alt); border-left-color: var(--accent); }
  .entry-title { font-size: 13px; color: var(--text); font-weight: 500; }
  .entry-date { font-size: 11px; color: var(--text-faint); margin-top: 2px; }
  .list-empty { font-size: 12px; color: var(--text-faint); text-align: center; padding: 20px 0; }

  .kb-content { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
  .content-empty { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--text-faint); font-size: 13px; }

  .content-header { display: flex; align-items: flex-start; gap: var(--space-2); padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--border); flex-shrink: 0; }
  .content-tabs-title { flex: 1; min-width: 0; }
  .content-title { font-size: 18px; font-weight: 600; color: var(--text); margin: 0 0 6px; }
  .title-input { background: var(--surface-alt); border: 1px solid var(--accent); border-radius: var(--radius-md); color: var(--text); font-size: 16px; font-weight: 600; padding: 6px 10px; font-family: var(--font-sans); width: 100%; box-sizing: border-box; margin-bottom: 6px; }
  .title-input:focus { outline: none; }
  .content-tab-bar { display: flex; gap: 0; }
  .content-tab { padding: 4px 12px; background: none; border: none; border-bottom: 2px solid transparent; color: var(--text-muted); font-size: 11px; cursor: pointer; font-family: var(--font-sans); }
  .content-tab:hover { color: var(--text); }
  .content-tab.active { border-bottom-color: var(--accent); color: var(--text); }
  .header-actions { display: flex; align-items: center; gap: var(--space-1); flex-shrink: 0; }
  .confirm-text { font-size: 11px; color: var(--danger); }

  .content-body { flex: 1; overflow: hidden; padding: var(--space-4); display: flex; flex-direction: column; }
  .content-body :global(.md-preview), .content-body :global(.md-editor) { flex: 1; }
  .content-error { padding: 4px 0; font-size: 11px; color: var(--danger); }
  .content-footer { display: flex; gap: var(--space-2); padding-top: var(--space-3); border-top: 1px solid var(--border); flex-shrink: 0; }
</style>
```

- [ ] **Step 5: Run new tests — expect pass**

```bash
npx vitest run test/KBPage.test.ts
```

Expected: all tests (existing + new) pass.

- [ ] **Step 6: Run full frontend suite**

```bash
npx vitest run
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/kbStore.svelte.ts packages/editor/src/lib/components/KBPage.svelte packages/editor/test/KBPage.test.ts
git commit -m "feat(kb): add attachments to store, Content/Media tabs in KBPage"
```

---

### Task 7: Chores backend — attachment model + routes

**Files:**
- Modify: `packages/backend/src/myhome/models_chores.py`
- Modify: `packages/backend/src/myhome/persistence_chores.py`
- Modify: `packages/backend/src/myhome/routes/chores.py`
- Modify: `packages/backend/tests/test_chores.py`

- [ ] **Step 1: Write failing tests**

Add to `packages/backend/tests/test_chores.py`:

```python
def _make_valid_pdf() -> bytes:
    import fitz
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    return doc.write()


def _chore_id(client) -> str:
    from datetime import datetime, timezone, timedelta
    due = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    resp = client.post("/api/chores", json={
        "name": "Clean filters", "emoji": "🧹", "periodDays": 30,
        "nextDueDate": due, "frequencyType": "interval", "frequency": 30,
        "frequencyMetadata": {"unit": "days"}, "scheduleFromDue": False,
    })
    return resp.json()["id"]


def test_chore_attachments_empty_by_default(client):
    cid = _chore_id(client)
    chore = next(c for c in client.get("/api/chores").json()["chores"] if c["id"] == cid)
    assert chore["attachments"] == []


def test_chore_upload_jpeg_accepted(client, tmp_path):
    cid = _chore_id(client)
    resp = client.post(
        f"/api/chores/{cid}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "photo.jpg"
    chore = next(c for c in client.get("/api/chores").json()["chores"] if c["id"] == cid)
    assert "photo.jpg" in chore["attachments"]


def test_chore_upload_unsupported_rejected(client, tmp_path):
    cid = _chore_id(client)
    resp = client.post(
        f"/api/chores/{cid}/attachments",
        files={"file": ("x.exe", b"\x4d\x5a", "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_chore_upload_pdf_creates_thumbnail(client, tmp_path):
    cid = _chore_id(client)
    resp = client.post(
        f"/api/chores/{cid}/attachments",
        files={"file": ("guide.pdf", _make_valid_pdf(), "application/pdf")},
    )
    assert resp.status_code == 201
    thumb = tmp_path / "chores-attachments" / cid / "guide.pdf.thumb.jpg"
    assert thumb.exists()


def test_chore_delete_attachment_removes_thumb(client, tmp_path):
    cid = _chore_id(client)
    client.post(f"/api/chores/{cid}/attachments",
        files={"file": ("guide.pdf", _make_valid_pdf(), "application/pdf")})
    thumb = tmp_path / "chores-attachments" / cid / "guide.pdf.thumb.jpg"
    assert thumb.exists()
    client.delete(f"/api/chores/{cid}/attachments/guide.pdf")
    assert not thumb.exists()


def test_chore_get_jpeg_returns_image_content_type(client, tmp_path):
    cid = _chore_id(client)
    client.post(f"/api/chores/{cid}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")})
    resp = client.get(f"/api/chores/{cid}/attachments/photo.jpg")
    assert resp.status_code == 200
    assert "image/jpeg" in resp.headers["content-type"]
```

The `client` fixture must set DATA_DIR. If the existing fixture in test_chores.py doesn't do that, update it:
```python
@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return TestClient(app)
```

- [ ] **Step 2: Run tests — expect failures**

```bash
python -m pytest tests/test_chores.py::test_chore_upload_jpeg_accepted -v
```

Expected: FAIL.

- [ ] **Step 3: Update `models_chores.py`**

Add `attachments: list[str] = []` to `Chore` (after `description`):

```python
class Chore(BaseModel):
    id: str
    donetickId: int | None = None
    name: str
    emoji: str
    periodDays: float
    frequencyType: str = "interval"
    frequency: int = 1
    frequencyMetadata: dict = {}
    scheduleFromDue: bool = False
    nextDueDate: str
    description: str = ""
    attachments: list[str] = []
```

- [ ] **Step 4: Update `persistence_chores.py`**

Add at end of file:

```python
import logging
import shutil
from pathlib import Path

_log = logging.getLogger(__name__)


def _attachments_dir(chore_id: str) -> Path:
    import os
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "chores-attachments" / chore_id


def save_attachment(chore_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(chore_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / filename).write_bytes(data)


def delete_attachment(chore_id: str, filename: str) -> bool:
    path = _attachments_dir(chore_id) / filename
    if not path.exists():
        return False
    path.unlink()
    thumb = path.parent / (filename + ".thumb.jpg")
    if thumb.exists():
        thumb.unlink()
    return True


def delete_all_attachments(chore_id: str) -> None:
    path = _attachments_dir(chore_id)
    if path.exists():
        shutil.rmtree(path)


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

Note: existing `persistence_chores.py` has imports at the top. Add `import logging`, `import shutil`, and the path import appropriately at the module level rather than inside the function.

Corrected: move the `import os` out of `_attachments_dir` — add `import os` to the module-level imports already present, then:

```python
def _attachments_dir(chore_id: str) -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "chores-attachments" / chore_id
```

- [ ] **Step 5: Update `routes/chores.py`**

Add to imports at top of file:
```python
import mimetypes
import re
from fastapi import UploadFile
from fastapi.responses import FileResponse
from ..persistence_chores import (
    _attachments_dir,
    delete_all_attachments,
    delete_attachment as delete_chore_attachment,
    generate_pdf_thumbnail,
    save_attachment,
)
```

Update the existing `delete_chore` route to call `delete_all_attachments`:

```python
@router.delete("/api/chores/{chore_id}", status_code=204)
def delete_chore(chore_id: str) -> None:
    doc = load_chores()
    if not any(c.id == chore_id for c in doc.chores):
        raise HTTPException(status_code=404, detail="Chore not found")
    doc.chores = [c for c in doc.chores if c.id != chore_id]
    doc.assignments = [a for a in doc.assignments if a.choreId != chore_id]
    save_chores(doc)
    delete_all_attachments(chore_id)
```

Add helpers and routes before the end of the file:

```python
_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
_CHORE_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _sanitise_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name or "attachment"


def _validate_chore_id(chore_id: str) -> None:
    if not _CHORE_ID_RE.fullmatch(chore_id):
        raise HTTPException(status_code=400, detail="Invalid id")


def _validate_chore_filename(filename: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", filename) or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")


@router.post("/api/chores/{chore_id}/attachments", status_code=201)
async def upload_chore_attachment(chore_id: str, file: UploadFile) -> dict:
    _validate_chore_id(chore_id)
    doc = load_chores()
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if not chore:
        raise HTTPException(status_code=404)
    original = file.filename or ""
    ext = os.path.splitext(original.lower())[1]
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not supported")
    filename = _sanitise_filename(original)
    data = await file.read()
    save_attachment(chore_id, filename, data)
    if ext == ".pdf":
        generate_pdf_thumbnail(
            _attachments_dir(chore_id) / filename,
            _attachments_dir(chore_id) / (filename + ".thumb.jpg"),
        )
    if filename not in chore.attachments:
        chore.attachments.append(filename)
    save_chores(doc)
    return {"filename": filename}


@router.get("/api/chores/{chore_id}/attachments/{filename}")
def get_chore_attachment(chore_id: str, filename: str) -> FileResponse:
    _validate_chore_id(chore_id)
    _validate_chore_filename(filename)
    base = _attachments_dir(chore_id).resolve()
    path = (base / filename).resolve()
    if not str(path).startswith(str(base) + "/") or not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", content_disposition_type="inline")


@router.delete("/api/chores/{chore_id}/attachments/{filename}", status_code=204)
def remove_chore_attachment(chore_id: str, filename: str) -> None:
    _validate_chore_id(chore_id)
    _validate_chore_filename(filename)
    doc = load_chores()
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if not chore:
        raise HTTPException(status_code=404)
    if not delete_chore_attachment(chore_id, filename):
        raise HTTPException(status_code=404)
    chore.attachments = [a for a in chore.attachments if a != filename]
    save_chores(doc)
```

Note: `os` is already imported at the top of `routes/chores.py`. Confirm the import exists before adding it again.

- [ ] **Step 6: Run new tests — expect pass**

```bash
python -m pytest tests/test_chores.py -v
```

Expected: all existing + new tests pass.

- [ ] **Step 7: Run full backend suite**

```bash
python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add packages/backend/src/myhome/models_chores.py packages/backend/src/myhome/persistence_chores.py packages/backend/src/myhome/routes/chores.py packages/backend/tests/test_chores.py
git commit -m "feat(chores): add attachments field, image+PDF upload routes, PDF thumbnail"
```

---

### Task 8: Chores frontend — ChoreEditModal

**Files:**
- Modify: `packages/editor/src/lib/choreStore.svelte.ts`
- Create: `packages/editor/src/lib/components/ChoreEditModal.svelte`
- Modify: `packages/editor/src/lib/components/ChoresPage.svelte`
- Create: `packages/editor/test/ChoreEditModal.test.ts`

- [ ] **Step 1: Write failing tests**

Create `packages/editor/test/ChoreEditModal.test.ts`:

```typescript
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import ChoreEditModal from "../src/lib/components/ChoreEditModal.svelte";
import type { Chore } from "../src/lib/choreStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makeChore(overrides: Partial<Chore> = {}): Chore {
  return {
    id: "c1", donetickId: null, name: "Clean filters", emoji: "🧹",
    periodDays: 30, frequencyType: "interval", frequency: 30,
    frequencyMetadata: { unit: "days" }, scheduleFromDue: false,
    nextDueDate: "2026-07-29T00:00:00Z", description: "", attachments: [],
    ...overrides,
  };
}

function makeStore(chore: Chore) {
  return {
    chores: [chore],
    assignments: [], completions: [], loaded: true, loadError: null,
    createChore: vi.fn().mockResolvedValue(undefined),
    updateChore: vi.fn().mockResolvedValue(undefined),
    deleteChore: vi.fn().mockResolvedValue(undefined),
    completeChore: vi.fn().mockResolvedValue(undefined),
    importFromDonetick: vi.fn().mockResolvedValue(0),
    createAssignment: vi.fn().mockResolvedValue(undefined),
    completeAssignment: vi.fn().mockResolvedValue(undefined),
    updateAssignmentPosition: vi.fn().mockResolvedValue(undefined),
    deleteAssignment: vi.fn().mockResolvedValue(undefined),
    uploadAttachment: vi.fn().mockResolvedValue("photo.jpg"),
    deleteAttachment: vi.fn().mockResolvedValue(undefined),
    getProgress: vi.fn().mockReturnValue(0.5),
    getColor: vi.fn().mockReturnValue("#4caf50"),
    assignmentsForRoom: vi.fn().mockReturnValue([]),
    houseAssignments: vi.fn().mockReturnValue([]),
    getCompletionsForChore: vi.fn().mockReturnValue([]),
  };
}

describe("ChoreEditModal", () => {
  it("renders with Info and Media tabs", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const chore = makeChore();
    const store = makeStore(chore);
    const app = mount(ChoreEditModal, { target, props: { chore, store, onclose: vi.fn() } });
    flushSync();
    const tabs = Array.from(target.querySelectorAll(".tab")).map(t => t.textContent?.trim());
    expect(tabs).toContain("Info");
    expect(tabs.some(t => t?.includes("Media"))).toBe(true);
    unmount(app);
  });

  it("Info tab shows name and emoji fields", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const chore = makeChore();
    const store = makeStore(chore);
    const app = mount(ChoreEditModal, { target, props: { chore, store, onclose: vi.fn() } });
    flushSync();
    const inputs = target.querySelectorAll("input");
    const values = Array.from(inputs).map(i => i.value);
    expect(values).toContain("Clean filters");
    expect(values).toContain("🧹");
    unmount(app);
  });

  it("Save calls updateChore and closes", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const chore = makeChore();
    const store = makeStore(chore);
    const onclose = vi.fn();
    const app = mount(ChoreEditModal, { target, props: { chore, store, onclose } });
    flushSync();
    const saveBtn = Array.from(target.querySelectorAll("button"))
      .find(b => b.textContent?.trim() === "Save") as HTMLButtonElement;
    saveBtn.click();
    await new Promise(r => setTimeout(r, 0));
    flushSync();
    expect(store.updateChore).toHaveBeenCalledWith("c1", expect.objectContaining({ name: "Clean filters" }));
    expect(onclose).toHaveBeenCalled();
    unmount(app);
  });

  it("clicking Media tab renders drop-zone", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const chore = makeChore();
    const store = makeStore(chore);
    const app = mount(ChoreEditModal, { target, props: { chore, store, onclose: vi.fn() } });
    flushSync();
    const mediaTab = Array.from(target.querySelectorAll(".tab"))
      .find(t => t.textContent?.includes("Media")) as HTMLButtonElement;
    mediaTab.click();
    flushSync();
    expect(target.querySelector(".drop-zone") || target.querySelector(".media-grid")).not.toBeNull();
    unmount(app);
  });
});
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd packages/editor
npx vitest run test/ChoreEditModal.test.ts
```

Expected: failures (file doesn't exist).

- [ ] **Step 3: Update `choreStore.svelte.ts`**

Add `attachments: string[]` to `Chore` interface (after `description`):

```typescript
export interface Chore {
  id: string;
  donetickId: number | null;
  name: string;
  emoji: string;
  periodDays: number;
  frequencyType: string;
  frequency: number;
  frequencyMetadata: Record<string, unknown>;
  scheduleFromDue: boolean;
  nextDueDate: string;
  description: string;
  attachments: string[];
}
```

Update `createChore` signature to exclude `attachments`:

```typescript
async function createChore(data: Omit<Chore, "id" | "attachments">): Promise<void> {
```

Add `uploadAttachment` and `deleteAttachment` before `init()` call:

```typescript
async function uploadAttachment(id: string, file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(`/api/chores/${id}/attachments`, { method: "POST", body: form });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const result = await resp.json();
  await init();
  return result.filename as string;
}

async function deleteAttachment(id: string, filename: string): Promise<void> {
  const resp = await fetch(`/api/chores/${id}/attachments/${filename}`, { method: "DELETE" });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  await init();
}
```

Add to return object:
```typescript
return {
  // ... all existing exports ...
  uploadAttachment,
  deleteAttachment,
};
```

- [ ] **Step 4: Create `ChoreEditModal.svelte`**

Create `packages/editor/src/lib/components/ChoreEditModal.svelte`:

```svelte
<script lang="ts">
  import type { createChoreStore, Chore } from "../choreStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import Modal from "./ui/Modal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import DatePicker from "./DatePicker.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";

  type ChoreStore = ReturnType<typeof createChoreStore>;

  interface Props {
    chore: Chore;
    store: ChoreStore;
    onclose: () => void;
  }

  let { chore, store, onclose }: Props = $props();

  const UNIT_DAYS: Record<string, number> = { days: 1, weeks: 7, months: 30, years: 365 };

  let activeTab = $state<"info" | "media">("info");
  let name = $state(chore.name);
  let emoji = $state(chore.emoji);
  let freqUnit = $state<"days" | "weeks" | "months" | "years">(
    (chore.frequencyMetadata?.unit as "days" | "weeks" | "months" | "years") ?? "days"
  );
  let freqN = $state(chore.frequency > 0 ? chore.frequency : Math.round(chore.periodDays));
  let nextDue = $state(chore.nextDueDate.slice(0, 10));
  let scheduleFromDue = $state(chore.scheduleFromDue);
  let saving = $state(false);
  let error = $state("");
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);
  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);

  const currentChore = $derived(store.chores.find(c => c.id === chore.id) ?? chore);

  const mediaItems = $derived<MediaItem[]>(
    (currentChore.attachments ?? []).map(fname => {
      const url = `/api/chores/${chore.id}/attachments/${fname}`;
      const isPdf = fname.toLowerCase().endsWith(".pdf");
      return { id: fname, name: fname, url, thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url, type: isPdf ? "document" : "image" };
    })
  );

  const attachmentCount = $derived(currentChore.attachments?.length ?? 0);

  async function handleSave(): Promise<void> {
    if (!name.trim()) { error = "Name is required"; return; }
    saving = true; error = "";
    try {
      await store.updateChore(chore.id, {
        name: name.trim(),
        emoji: emoji.trim() || "📋",
        periodDays: freqN * UNIT_DAYS[freqUnit],
        frequencyType: "interval",
        frequency: freqN,
        frequencyMetadata: { unit: freqUnit },
        scheduleFromDue,
        nextDueDate: new Date(nextDue).toISOString(),
      });
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Save failed";
    } finally {
      saving = false;
    }
  }

  async function handleUpload(files: File[]): Promise<void> {
    uploading = true; uploadError = null;
    try { for (const file of files) await store.uploadAttachment(chore.id, file); }
    catch (err) { uploadError = err instanceof Error ? err.message : "Upload failed"; }
    finally { uploading = false; }
  }

  async function handleDeleteAttachment(id: string): Promise<void> {
    try { await store.deleteAttachment(chore.id, id); }
    catch (err) { uploadError = err instanceof Error ? err.message : "Delete failed"; }
  }

  function handleItemClick(index: number): void { lightboxIndex = index; lightboxOpen = true; }
</script>

<Modal open={true} title="Edit chore" {onclose} width="400px">
  <div class="tabs">
    <button class="tab" class:active={activeTab === "info"} onclick={() => { activeTab = "info"; }}>Info</button>
    <button class="tab" class:active={activeTab === "media"} onclick={() => { activeTab = "media"; }}>
      Media{attachmentCount > 0 ? ` (${attachmentCount})` : ""}
    </button>
  </div>

  {#if activeTab === "info"}
    <div class="field">
      <label for="ce-name">Name</label>
      <Input id="ce-name" bind:value={name} placeholder="Chore name" />
    </div>
    <div class="field">
      <label for="ce-emoji">Emoji</label>
      <input id="ce-emoji" class="native-input emoji-input" bind:value={emoji} maxlength="4" />
    </div>
    <div class="field">
      <label>Repeat every</label>
      <div class="freq-row">
        <input type="number" class="native-input freq-n" bind:value={freqN} min="1" />
        <select class="native-input" bind:value={freqUnit}>
          <option value="days">days</option>
          <option value="weeks">weeks</option>
          <option value="months">months</option>
          <option value="years">years</option>
        </select>
      </div>
    </div>
    <div class="field">
      <label for="ce-due">Next due</label>
      <DatePicker bind:value={nextDue} />
    </div>
    <div class="field-row">
      <input type="checkbox" id="ce-sfd" bind:checked={scheduleFromDue} />
      <label for="ce-sfd" class="checkbox-label" title="Next due = planned date + period">Schedule from due date</label>
    </div>
    {#if error}<div class="error">{error}</div>{/if}
  {:else}
    <MediaGallery items={mediaItems} {uploading} {uploadError}
      onUpload={handleUpload} onDelete={handleDeleteAttachment} onItemClick={handleItemClick} />
  {/if}

  {#snippet footer()}
    <Button variant="secondary" onclick={onclose}>Cancel</Button>
    {#if activeTab === "info"}
      <Button variant="primary" disabled={!name.trim() || saving} onclick={handleSave}>
        {saving ? "Saving…" : "Save"}
      </Button>
    {/if}
  {/snippet}
</Modal>

{#if lightboxOpen && mediaItems.length > 0}
  <Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />
{/if}

<style>
  .tabs { display: flex; border-bottom: 1px solid var(--border); margin-bottom: var(--space-3); }
  .tab { padding: 8px 16px; background: none; border: none; border-bottom: 2px solid transparent; color: var(--text-muted); font-size: 12px; cursor: pointer; font-family: var(--font-sans); }
  .tab:hover { color: var(--text); }
  .tab.active { border-bottom-color: var(--accent); color: var(--text); }

  .field { display: flex; flex-direction: column; gap: 4px; margin-bottom: var(--space-3); }
  .field label { font-size: 11px; color: var(--text-muted); }
  .field-row { display: flex; align-items: center; gap: 8px; margin-bottom: var(--space-3); }
  .checkbox-label { font-size: 12px; color: var(--text-muted); cursor: pointer; }

  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px; font-family: var(--font-sans); box-sizing: border-box;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  select.native-input { cursor: pointer; }
  .emoji-input { width: 80px; }
  .freq-row { display: flex; gap: 8px; }
  .freq-n { width: 80px; }
  .freq-row select { flex: 1; }
  .error { font-size: 11px; color: var(--danger); }
</style>
```

- [ ] **Step 5: Update `ChoresPage.svelte`**

Replace the inline-edit state and form with `ChoreEditModal`. Specifically:

**In `<script>`:** Remove `editingId`, `editName`, `editEmoji`, `editPeriodDays`, `editNextDue`, `editScheduleFromDue` state variables and `startEdit()`, `handleUpdate()` functions. Add:

```typescript
import ChoreEditModal from "./ChoreEditModal.svelte";
// ...
let editChore = $state<Chore | null>(null);
```

**In the template:** Replace `{#if editingId === chore.id}<div class="edit-form">...</div>{:else}` with just the non-edit content block. Add an Edit button in the chore header actions area that sets `editChore = chore`. Add `ChoreEditModal` at the bottom of the template (outside the `{#each}`):

```svelte
{#if editChore}
  <ChoreEditModal chore={editChore} {store} onclose={() => { editChore = null; }} />
{/if}
```

The Edit button should be added to the existing chore row actions (where the complete/delete buttons are). In the existing chore row, find the action buttons area and add:

```svelte
<Button variant="ghost" onclick={() => { editChore = chore; }} title="Edit chore">✏️</Button>
```

**Remove CSS** for `.edit-form` and `.edit-form input[type="number"]` since the inline form is gone.

- [ ] **Step 6: Run new tests — expect pass**

```bash
npx vitest run test/ChoreEditModal.test.ts
```

Expected: 4 tests pass.

- [ ] **Step 7: Run full test suite**

```bash
npx vitest run
cd ../backend
python -m pytest tests/ -v
```

Expected: all frontend and backend tests pass.

- [ ] **Step 8: Commit**

```bash
git add packages/editor/src/lib/choreStore.svelte.ts packages/editor/src/lib/components/ChoreEditModal.svelte packages/editor/src/lib/components/ChoresPage.svelte packages/editor/test/ChoreEditModal.test.ts
git commit -m "feat(chores): add attachments to store, ChoreEditModal with Info/Media tabs"
```

---

## Final Verification

After all 8 tasks:

```bash
# Backend
cd packages/backend && python -m pytest tests/ -v

# Frontend
cd packages/editor && npx vitest run
```

All tests should pass. Then invoke `superpowers:finishing-a-development-branch` to push and open a PR.
