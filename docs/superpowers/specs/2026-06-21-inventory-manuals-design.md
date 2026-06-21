# Inventory PDF Manuals — Design Document

**Status:** Approved for planning
**Date:** 2026-06-21

## Overview

Add PDF manual support to inventory items. Each item can have at most one PDF manual. Manuals are uploaded via the item modal, stored on the HA add-on filesystem, and opened in a new browser tab. The implementation follows the exact same pattern as works attachments.

---

## Data Model

`InventoryItem` gains one new field:

| Field | Type | Notes |
|-------|------|-------|
| `manual` | `string \| null` | Sanitised filename of the uploaded PDF, e.g. `"dishwasher_manual.pdf"`. `null` = no manual. |

Files are stored at `/data/inventory-manuals/{item_id}/{filename}` — the same per-entity directory pattern as `/data/works-attachments/{work_id}/{filename}`.

`inventory.json` only stores the filename; the file itself lives on disk.

---

## Backend

### `persistence_inventory.py`

Add three helpers mirroring `persistence_works.py`:

```python
def _manuals_dir(item_id: str) -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "inventory-manuals" / item_id

def save_manual(item_id: str, filename: str, data: bytes) -> None:
    path = _manuals_dir(item_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / filename).write_bytes(data)

def delete_item_manual(item_id: str) -> None:
    path = _manuals_dir(item_id)
    if path.exists():
        shutil.rmtree(path)
```

### `models_inventory.py`

Add `manual: str | None = None` to `InventoryItem`. No change to `InventoryItemCreate` or `InventoryItemUpdate` — the manual is managed exclusively via dedicated routes.

### `routes/inventory.py`

Three new routes, using the same id/filename validation and path-traversal guard as `routes/works.py`:

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| `POST` | `/api/inventory/items/{id}/manual` | 201 | Multipart upload; replaces any existing manual; returns `{"filename": "..."}` |
| `GET` | `/api/inventory/items/{id}/manual` | 200 | `FileResponse(path, media_type="application/pdf", content_disposition_type="inline")`; browser opens PDF in new tab without triggering a download |
| `DELETE` | `/api/inventory/items/{id}/manual` | 204 | Removes file from disk; sets `item.manual = None`; saves |

`delete_item` cascades: calls `delete_item_manual(id)` after removing the item from `doc.items`.

Validation helpers (copied verbatim from `routes/works.py`):
- `_sanitise_filename(name)` — strips unsafe chars, ensures `.pdf` extension
- `_validate_id(id)` — regex `[A-Za-z0-9_-]{1,64}`
- `_validate_filename(filename)` — regex `[A-Za-z0-9._-]+`, no leading `.`

---

## Frontend

### `inventoryStore.svelte.ts`

Add `manual: string | null` to the `InventoryItem` interface.

Add two new store methods:

```typescript
async function uploadManual(id: string, file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(`/api/inventory/items/${id}/manual`, { method: "POST", body: form });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const result = await resp.json();
  await init();
  return result.filename as string;
}

async function deleteManual(id: string): Promise<void> {
  const resp = await fetch(`/api/inventory/items/${id}/manual`, { method: "DELETE" });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  await init();
}
```

### `InventoryModal.svelte`

Add a **"Manual"** tab as the third tab, disabled in create mode — identical structure to `WorkModal`'s "Attachments" tab but simplified for a single file.

Tab header: `Manual` (no count badge needed since it's 0 or 1).

Tab body:

- **Manual exists** (`currentItem.manual !== null`):
  - Row: `📄` icon + `<a href="/api/inventory/items/{id}/manual" target="_blank" rel="noopener">{filename}</a>` + ✕ delete button
- **No manual**:
  - `<div class="attach-empty">No manual yet.</div>`
- Below either: `<label class="upload-btn">＋ Upload PDF <input type="file" accept=".pdf" ... /></label>`
- Uploading/error states identical to `WorkModal`

`currentItem` derived the same way as `WorkModal`'s `currentWork`: live lookup from the store by id so the UI updates after upload without closing the modal.

---

## Testing

### Backend (`test_inventory.py`)

- Upload returns 201 and `{"filename": "..."}` with sanitised name
- GET 200 serves the file
- DELETE 204 clears `item.manual` in `inventory.json` and removes the file
- GET/DELETE returns 404 when no manual exists
- Uploading again replaces the previous manual
- Deleting an item cascades to delete the manual directory

### Frontend (`inventoryStore.test.ts`)

- `InventoryItem` fixtures include `manual: null` (or a filename)
- `uploadManual` calls `POST /api/inventory/items/{id}/manual` with form data
- `deleteManual` calls `DELETE /api/inventory/items/{id}/manual`

---

## What is NOT in scope

- Multiple manuals per item
- Photos or other file types
- Inline PDF preview (opens in new browser tab only)
- Manual versioning / history
