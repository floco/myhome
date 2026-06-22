# Inventory PDF Attachments — Design Document

**Status:** Approved for planning
**Date:** 2026-06-21

## Overview

Add PDF attachment support to inventory items. Each item can have multiple PDF attachments (manual, invoice, warranty certificate, etc.). Attachments are uploaded via the item modal, stored on the HA add-on filesystem, and opened in a new browser tab. The implementation mirrors works attachments exactly.

---

## Data Model

`InventoryItem` gains one new field:

| Field | Type | Notes |
|-------|------|-------|
| `attachments` | `list[str]` | List of sanitised filenames, e.g. `["manual.pdf", "invoice.pdf"]`. Default `[]`. |

Files are stored at `/data/inventory-attachments/{item_id}/{filename}` — the same per-entity directory pattern as `/data/works-attachments/{work_id}/{filename}`.

`inventory.json` stores only filenames; the files themselves live on disk.

---

## Backend

### `persistence_inventory.py`

Add helpers mirroring `persistence_works.py`:

```python
def _attachments_dir(item_id: str) -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "inventory-attachments" / item_id

def save_attachment(item_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(item_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / filename).write_bytes(data)

def delete_attachment(item_id: str, filename: str) -> bool:
    path = _attachments_dir(item_id) / filename
    if not path.exists():
        return False
    path.unlink()
    return True

def delete_all_attachments(item_id: str) -> None:
    path = _attachments_dir(item_id)
    if path.exists():
        shutil.rmtree(path)
```

### `models_inventory.py`

Add `attachments: list[str] = []` to `InventoryItem`. No change to `InventoryItemCreate` or `InventoryItemUpdate` — attachments are managed exclusively via dedicated routes.

### `routes/inventory.py`

Three new routes, using the same id/filename validation and path-traversal guard as `routes/works.py`:

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| `POST` | `/api/inventory/items/{id}/attachments` | 201 | Multipart upload; appends to list if filename not already present; returns `{"filename": "..."}` |
| `GET` | `/api/inventory/items/{id}/attachments/{filename}` | 200 | `FileResponse` with `media_type="application/pdf"`, `content_disposition_type="inline"`; browser opens PDF in new tab |
| `DELETE` | `/api/inventory/items/{id}/attachments/{filename}` | 204 | Removes file from disk; removes filename from `item.attachments`; saves |

`delete_item` cascades: calls `delete_all_attachments(id)` after removing the item from `doc.items`.

Validation helpers (copied verbatim from `routes/works.py`):
- `_sanitise_filename(name)` — strips unsafe chars, ensures `.pdf` extension
- `_validate_id(id)` — regex `[A-Za-z0-9_-]{1,64}`
- `_validate_filename(filename)` — regex `[A-Za-z0-9._-]+`, no leading `.`

---

## Frontend

### `inventoryStore.svelte.ts`

Add `attachments: string[]` to the `InventoryItem` interface.

Add two new store methods mirroring `worksStore.svelte.ts`:

```typescript
async function uploadAttachment(id: string, file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(`/api/inventory/items/${id}/attachments`, { method: "POST", body: form });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const result = await resp.json();
  await init();
  return result.filename as string;
}

async function deleteAttachment(id: string, filename: string): Promise<void> {
  const resp = await fetch(`/api/inventory/items/${id}/attachments/${filename}`, { method: "DELETE" });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  await init();
}
```

### `InventoryModal.svelte`

Add an **"Attachments"** tab as the third tab, disabled in create mode — identical structure to `WorkModal`'s "Attachments" tab.

Tab header: `Attachments (N)` where N is the count, shown only when N > 0.

Tab body (identical to `WorkModal`):
- List of attachment rows: `📄` icon + `<a href="/api/inventory/items/{id}/attachments/{filename}" target="_blank" rel="noopener">{filename}</a>` + ✕ delete button
- "No attachments yet." when list is empty
- `＋ Upload PDF` button (file input, `.pdf` only)
- Uploading/error states

`currentItem` derived from store by id (live lookup so UI updates after upload without closing the modal).

---

## Testing

### Backend (`test_inventory.py`)

- Upload returns 201 + sanitised filename; filename appears in `item.attachments`
- Upload sanitises filename (spaces → underscores)
- Uploading again (same or different filename) appends without duplicate
- Non-PDF rejected (400)
- Upload to missing item → 404
- Invalid id → 400
- GET returns 200 with `content-type: application/pdf`
- GET for non-existent file → 404
- GET with invalid filename → 400
- DELETE 204; filename removed from `item.attachments`; file deleted from disk
- DELETE non-existent → 404
- Deleting an item cascades to delete all attachment files

### Frontend (`inventoryStore.test.ts`)

- `InventoryItem` fixtures include `attachments: []`
- `uploadAttachment` calls `POST /api/inventory/items/{id}/attachments` with FormData
- `deleteAttachment` calls `DELETE /api/inventory/items/{id}/attachments/{filename}`
- Both throw on HTTP error

---

## What is NOT in scope

- Non-PDF file types
- Inline PDF preview (opens in new browser tab only)
- Attachment versioning / history
- Attachment labels or descriptions
