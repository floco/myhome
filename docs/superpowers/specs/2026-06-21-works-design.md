# Works Module (Spec 5) — Design Document

**Status:** Approved for planning
**Date:** 2026-06-21

## Overview

A Works module (`#/works`) for tracking past and planned house works: renovations, repairs, and improvements. Each work record has a status lifecycle, PDF invoice attachments stored locally, a markdown notes field, and an optional floor plan pin placed via the existing picker panel.

Two supporting lists are added to Settings: **work categories** (Plumbing, Electrical, etc.) and **suppliers** (contractor names). The supplier list is shared with the Costs module, upgrading its current freeform text field to a managed dropdown.

---

## Data Model

### `/data/works.json`

```json
{
  "version": 1,
  "works": [
    {
      "id": "uuid",
      "title": "Boiler replacement",
      "description": "Replaced 15-year-old boiler with a 24kW condensing unit",
      "status": "done",
      "categoryId": "cat-plumbing",
      "date": "2025-11-10",
      "totalCost": 3200.00,
      "supplierId": "sup-chauffage-pro",
      "notes": "## Notes\n\nUsed a Viessmann Vitodens 200-W...",
      "attachments": ["invoice-2025-11.pdf", "quote-2025-10.pdf"],
      "placement": {
        "floorId": "floor-uuid",
        "position": { "x": 120.5, "y": 88.2 }
      }
    }
  ]
}
```

**Work fields:**

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID string | Generated on creation |
| `title` | string | Required; shown in list and floor plan pin |
| `description` | string | Short summary; default `""` |
| `status` | `"planned"` \| `"in_progress"` \| `"done"` | Required |
| `categoryId` | string \| null | References a `WorkCategory.id` |
| `date` | ISO date string | Required |
| `totalCost` | float \| null | Total cost in € |
| `supplierId` | string \| null | References a `Supplier.id` |
| `notes` | string | Markdown; default `""` |
| `attachments` | list[string] | Filenames stored under `/data/works-attachments/{id}/` |
| `placement` | `{floorId, position{x,y}}` \| null | Optional floor plan pin |

### `/data/works-attachments/{workId}/{filename}`

PDF files stored on disk, one subfolder per work. The subfolder is created on first upload and deleted with the work. Filenames are sanitised on upload: spaces replaced with underscores, characters outside `[a-zA-Z0-9._-]` stripped, `.pdf` extension enforced (added if missing). The sanitised filename is what gets stored in the `attachments` list and used in the GET/DELETE routes.

### Settings additions (`/data/settings.json`)

```json
"workCategories": [
  { "id": "uuid", "name": "Plumbing",   "emoji": "🔧" },
  { "id": "uuid", "name": "Electrical", "emoji": "⚡" },
  { "id": "uuid", "name": "Roofing",    "emoji": "🏠" },
  { "id": "uuid", "name": "Painting",   "emoji": "🎨" },
  { "id": "uuid", "name": "Flooring",   "emoji": "🪵" }
],
"suppliers": [
  { "id": "uuid", "name": "Jean Dupont Plomberie" },
  { "id": "uuid", "name": "Élec Pro" }
]
```

`suppliers` is shared between Works and Costs. The `CostEntry` model's `supplier: str | null` freeform field is replaced by `supplierId: str | null`. On load, any entry with a `supplier` key but no `supplierId` key has `supplierId` set to `null` (old text value is discarded — it was optional and freeform).

---

## Backend

### New files

```
packages/backend/src/myhome/
  models_works.py
  persistence_works.py
  routes/works.py
```

### Models (`models_works.py`)

```python
class WorkPosition(BaseModel):
    x: float
    y: float

class WorkPlacement(BaseModel):
    floorId: str
    position: WorkPosition

class Work(BaseModel):
    id: str
    title: str
    description: str = ""
    status: Literal["planned", "in_progress", "done"]
    categoryId: str | None = None
    date: str
    totalCost: float | None = None
    supplierId: str | None = None
    notes: str = ""
    attachments: list[str] = []
    placement: WorkPlacement | None = None

class WorksDocument(BaseModel):
    version: int = 1
    works: list[Work] = []

class WorkCreate(BaseModel):
    title: str
    description: str = ""
    status: Literal["planned", "in_progress", "done"] = "planned"
    categoryId: str | None = None
    date: str
    totalCost: float | None = None
    supplierId: str | None = None
    notes: str = ""

class WorkUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: Literal["planned", "in_progress", "done"] | None = None
    categoryId: str | None = None
    date: str | None = None
    totalCost: float | None = None
    supplierId: str | None = None
    notes: str | None = None
```

### Routes (`routes/works.py`)

| Method | Path | Body | Response | Notes |
|--------|------|------|----------|-------|
| GET | `/api/works` | — | `WorksDocument` | Full list |
| POST | `/api/works` | `WorkCreate` | `Work` (201) | Generates UUID |
| PUT | `/api/works/{id}` | `WorkUpdate` | 204 | Partial update |
| DELETE | `/api/works/{id}` | — | 204 | Also removes attachment subfolder |
| POST | `/api/works/{id}/attachments` | multipart file | `{"filename": "..."}` (201) | Saves to `/data/works-attachments/{id}/`; enforces `.pdf` extension; 400 if not PDF |
| GET | `/api/works/{id}/attachments/{filename}` | — | file | `Content-Type: application/pdf`; 404 if missing |
| DELETE | `/api/works/{id}/attachments/{filename}` | — | 204 | 404 if not found |
| PUT | `/api/works/{id}/placement` | `WorkPlacement` | 204 | Sets floor + position |
| DELETE | `/api/works/{id}/placement` | — | 204 | Clears placement |

### Settings updates (`models_settings.py`, `routes/settings.py`)

New models added to `SettingsDocument`:

```python
class WorkCategory(BaseModel):
    id: str
    name: str
    emoji: str

class Supplier(BaseModel):
    id: str
    name: str
```

New routes:
- `PUT /api/settings/work-categories` → 204 (replaces full list)
- `PUT /api/settings/suppliers` → 204 (replaces full list)

Default work categories returned when `settings.json` is missing:
Plumbing 🔧, Electrical ⚡, Roofing 🏠, Painting 🎨, Flooring 🪵

Default suppliers list is empty.

### Costs upgrade (`models_costs.py`, `routes/costs.py`)

`CostEntry.supplier: str | None` → `CostEntry.supplierId: str | None`

`load_costs()` applies a migration shim: if a stored entry has a `"supplier"` key and no `"supplierId"` key, the entry is loaded with `supplierId=None` (the old freeform value is dropped). This is safe because the field was purely informational.

---

## Frontend

### New files

```
packages/editor/src/lib/
  worksStore.svelte.ts
  components/
    WorksPage.svelte
    WorkModal.svelte
    WorksOverlay.svelte
    WorksPinPopup.svelte
```

### `worksStore.svelte.ts`

```typescript
export interface WorkPlacement { floorId: string; position: { x: number; y: number }; }

export interface Work {
  id: string; title: string; description: string;
  status: "planned" | "in_progress" | "done";
  categoryId: string | null; date: string;
  totalCost: number | null; supplierId: string | null;
  notes: string; attachments: string[];
  placement: WorkPlacement | null;
}

export function createWorksStore() {
  // $state works list, loaded from GET /api/works
  // createWork(), updateWork(), deleteWork()
  // uploadAttachment(id, file): Promise<string>   — POST multipart, returns filename
  // deleteAttachment(id, filename): Promise<void> — DELETE
  // setPlacement(id, placement | null): Promise<void> — PUT or DELETE
}
```

### `WorksPage.svelte`

- Props: `store: WorksStore`, `settingsStore: SettingsStore`
- Filter bar: search input · status dropdown (All / Planned / In Progress / Done) · category dropdown
- Card list: coloured left border by status (planned → `#cc8833`, in_progress → `#3388cc`, done → `#33aa66`); each card shows category emoji · title · date · status chip · supplier name · cost · 📍 if pinned
- Card click → opens `WorkModal` in edit mode
- `＋ Add work` button in topbar → opens `WorkModal` in create mode
- Footer: `N works · total: X €` (filtered; only works with `totalCost` set contribute to total)
- Empty state when no works match filters

### `WorkModal.svelte`

- Props: `work?: Work`, `store: WorksStore`, `settingsStore: SettingsStore`, `onclose: () => void`, `onplaceonmap?: (workId: string) => void`
- Three tabs: **Info** · **Notes** · **Attachments**
- **Info tab**: title (required), category dropdown, status dropdown, date (DatePicker), total cost (€), supplier dropdown, description textarea
- **Notes tab**: full-height `<textarea>` for markdown; no live preview (raw markdown only)
- **Attachments tab**: list of filenames with download link (`/api/works/{id}/attachments/{filename}`) and delete button; `＋ Upload PDF` file input (`.pdf` only); upload calls `store.uploadAttachment()`
- Footer: 🗑 Delete (edit mode, inline confirm) · `📍 Place on map` (calls `onplaceonmap`) · Save / Create button
- Attachments tab only available in edit mode (work must exist to upload)

### `WorksOverlay.svelte`

Same SVG pin pattern as `InventoryOverlay`:
- Props: `works: Work[]`, `viewport`, `active`, `width`, `height`, `onclick`, `ondragend`
- Pin: category emoji (falls back to 🔧) at font-size 26 + truncated title label in dark pill below
- Drag to reposition calls `ondragend(workId, worldPos)`
- Click calls `onclick(workId)`

### `WorksPinPopup.svelte`

- Props: `work: Work`, `settingsStore: SettingsStore`, `screenX`, `screenY`, `onopen`, `onremove`, `onclose`
- Shows: category emoji + title, status chip (coloured), supplier name if set
- Buttons: `📂 Open` · `✕ Remove` · Close

### `LayersDropdown.svelte`

Add `{ id: "works", icon: "🔧", label: "Works" }` to the layers array.

### `App.svelte`

- Import `WorksOverlay`, `WorksPinPopup`, `createWorksStore`, `WorksPage`
- `worksStore = createWorksStore()`
- `worksLayerActive = $derived(activeLayers.has("works"))`
- `currentFloorWorks = $derived(worksStore.works.filter(w => w.placement?.floorId === floorStore.currentFloorId))`
- `worksPickerLayer`: maps `worksStore.works` to picker items (`placed = w.placement !== null`)
- Include `worksPickerLayer` in `pickerLayers` when `worksLayerActive`
- `handleDrop` handles `layerId === "works"`: calls `worksStore.setPlacement(itemId, { floorId, position })`
- Render `WorksOverlay` when `worksLayerActive`
- Render `WorksPinPopup` when a work pin is selected
- Placement mode for works (same crosshair overlay pattern as costs)
- Route `#/works` → `<WorksPage {worksStore} {settingsStore} onplaceonmap={...} />`

### `SettingsPage.svelte`

Two new sections:
- **Work categories**: inline-edit rows (emoji + name), same pattern as cost categories
- **Suppliers**: name-only rows, add/delete, same pattern as inventory categories

### `CostsEntryModal.svelte`

Supplier field: `<input type="text">` → `<select>` populated from `settingsStore.suppliers`. Shows "— No supplier —" as default option. If `supplierId` is null or references a deleted supplier, shows the default.

### `settingsStore.svelte.ts`

Add `WorkCategory[]` and `Supplier[]` state, `updateWorkCategories()`, `updateSuppliers()`, expose in return object. Add both to `SettingsDocument` interface.

---

## Testing

### Backend (`packages/backend/tests/`)

**`test_works.py`:**
- `POST /api/works` creates work, returns it with id
- `GET /api/works` returns all works
- `PUT /api/works/{id}` partial update (only provided fields change)
- `DELETE /api/works/{id}` removes work; 404 on missing
- `POST /api/works/{id}/attachments` uploads PDF; 400 for non-PDF
- `GET /api/works/{id}/attachments/{filename}` returns file content
- `DELETE /api/works/{id}/attachments/{filename}` removes file; 404 if missing
- `PUT /api/works/{id}/placement` sets placement; `DELETE` clears it

**`test_works_persistence.py`:**
- Atomic write (`.tmp` + replace)
- Empty document when file missing (file not created on read)

**`test_settings.py` additions:**
- `PUT /api/settings/work-categories` replaces list
- `PUT /api/settings/suppliers` replaces list
- Default work categories returned when file missing

**`test_costs.py` additions:**
- Entries with old `supplier` string field load with `supplierId=None`
- New entries use `supplierId`

### Frontend (`packages/editor/test/`)

**`worksStore.test.ts`:**
- `init()` fetches and populates works list
- `createWork()` posts and refreshes
- `setPlacement()` calls PUT then refreshes; null calls DELETE

---

## What is NOT in scope

- Markdown preview in the Notes tab (raw textarea only)
- Photo attachments (PDFs only)
- Work templates or recurring works
- Budget tracking / spend forecasting
- Linking works to cost entries from the Costs module
- Multi-location works (one pin per work)
- Export to PDF report
