# Inventory Module (Spec 3) — Design Document

**Status:** Approved for planning
**Date:** 2026-06-20

## Overview

Add an inventory tracker to the myhome HA add-on. Users can record important household items (appliances, furniture, electronics, tools, artwork, etc.) with purchase info, warranty dates, and free-text notes. Items can optionally be pinned on the floor plan as a dedicated overlay layer.

The floor plan gains a generic **Layers** system (replacing the existing `choreMode` boolean) — a dropdown in the topbar lets users activate any combination of overlay layers (Chores, Inventory, and future modules). Each active layer renders its own SVG overlay and picker panel.

The `#/inventory` page focuses on the list of items only; placement is done from the floor plan picker panel or initiated from the item detail modal.

---

## Data Model

Single new file: **`/data/inventory.json`**

```json
{
  "version": 1,
  "items": [
    {
      "id": "uuid",
      "name": "Samsung TV 65\"",
      "emoji": "📺",
      "category": "Electronics",
      "brand": "Samsung",
      "model": "QE65Q80C",
      "serialNumber": "XYZ123",
      "purchaseDate": "2023-05-12",
      "purchasePrice": 1200,
      "warrantyExpiryDate": "2026-05-12",
      "notes": "",
      "placement": {
        "floorId": "floor-uuid",
        "roomId": "room-uuid",
        "position": { "x": 3.4, "y": 2.1 }
      }
    }
  ]
}
```

**InventoryItem fields:**

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID string | Generated locally |
| `name` | string | Required |
| `emoji` | string | Required; default `📦`; used as the floor plan pin icon |
| `category` | string | Free text; UI suggests: Electronics, Furniture, Appliance, Tool, Artwork, Other |
| `brand` | string \| null | Optional |
| `model` | string \| null | Optional |
| `serialNumber` | string \| null | Optional |
| `purchaseDate` | ISO date string \| null | e.g. `"2023-05-12"` |
| `purchasePrice` | number \| null | In the user's local currency; no currency field stored |
| `warrantyExpiryDate` | ISO date string \| null | Expiry date; UI computes days remaining at render time |
| `notes` | string | Free text; optional, default `""` |
| `placement` | Placement \| null | `null` = unplaced |

**Placement (embedded in item):**

| Field | Type | Notes |
|-------|------|-------|
| `floorId` | string | Floor the item is pinned on |
| `roomId` | string \| null | Optional room association (informational only; no boundary constraint) |
| `position` | `{x, y}` | World coordinates (metres) |

One item has at most one placement (physical objects occupy one location). No separate placements collection.

**Warranty status** (computed client-side, not stored):
- `'ok'` — expiry > 30 days away, or no warranty date
- `'soon'` — expiry ≤ 30 days away
- `'expired'` — expiry date is in the past

---

## Backend

Follows the identical pattern as `routes/chores.py` and `persistence_chores.py`.

**New files:**
- `packages/backend/src/myhome/models_inventory.py`
- `packages/backend/src/myhome/persistence_inventory.py`
- `packages/backend/src/myhome/routes/inventory.py`

Registered in `main.py` alongside existing routers.

**Persistence:** `load_inventory()` / `save_inventory()` using atomic write (`.tmp` + `os.replace`) to `/data/inventory.json`. Returns an empty `InventoryDocument` when the file is missing.

### Pydantic models (`models_inventory.py`)

```python
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
    purchaseDate: str | None = None      # ISO date
    purchasePrice: float | None = None
    warrantyExpiryDate: str | None = None  # ISO date
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

### Routes

| Method | Path | Body | Response | Notes |
|--------|------|------|----------|-------|
| GET | `/api/inventory` | — | `InventoryDocument` | Full `{version, items}` |
| POST | `/api/inventory/items` | `InventoryItemCreate` | `InventoryItem` (201) | Create item; generates UUID |
| PUT | `/api/inventory/items/{id}` | `InventoryItemUpdate` | 204 | Partial update; only provided fields change |
| DELETE | `/api/inventory/items/{id}` | — | 204 | Delete item |
| PUT | `/api/inventory/items/{id}/placement` | `PlacementUpdate` | 204 | Set, update, or remove (`null`) placement |

---

## Frontend

### Layers system refactor (`App.svelte`)

Replace `let choreMode = $state(false)` with:

```typescript
let activeLayers = $state(new Set<string>());
const choreLayerActive = $derived(activeLayers.has('chores'));
const inventoryLayerActive = $derived(activeLayers.has('inventory'));
```

All references to `choreMode` in `App.svelte` (tool reset, overlay pointer-events, panel visibility) are updated to use `choreLayerActive`. Externally, `ChoreOverlay` and `ChorePanel` receive `active={choreLayerActive}` — their internal behaviour is unchanged.

**Floor filtering in App.svelte:** floor-scoped item lists are derived in `App.svelte` (not inside the store, which has no knowledge of the current floor), mirroring the chore pattern:

```typescript
const currentFloorInventoryItems = $derived(
  inventoryStore.items.filter(
    (i) => i.placement?.floorId === floorStore.currentFloorId
  )
);
```

These are passed as props to `InventoryOverlay` and `InventoryPickerPanel`.

**Selected item for deep-link from pin popup:**

```typescript
let selectedInventoryItemId = $state<string | null>(null);
```

When the pin popup's "✏️ Edit" is clicked, `selectedInventoryItemId` is set and the route changes to `#/inventory`. `InventoryPage` receives `selectedInventoryItemId` as a prop and auto-opens the modal for that item on mount (then clears the prop via a callback).

**New component `LayersDropdown.svelte`:** renders in the topbar when on the floor plan view (replacing the existing 📋 chore toggle button). Opens a small dropdown with checkboxes:

```
☑ ✅ Chores
☑ 📦 Inventory
```

Each checkbox toggles the corresponding layer in `activeLayers`. Future modules add entries here with no other wiring needed.

**Right panel stacking:** when multiple layers are active, their picker panels stack vertically in the right sidebar, each with a collapsible section header. If only one layer is active it fills the panel as today.

**Overlay z-order:** `ChoreOverlay` (z-index 10) → `InventoryOverlay` (z-index 11). Inventory pins are clickable first when overlapping a chore badge.

### `inventoryStore.svelte.ts`

Mirrors `choreStore.svelte.ts`:

- `$state` holding `InventoryDocument` (`{ items }`)
- `init()` auto-called: `GET /api/inventory`
- Each mutation calls its endpoint then calls `init()` to refresh
- Computed helpers:
  - `placedItems` — items where `placement !== null` (all floors; floor filtering happens in App.svelte)
  - `unplacedItems` — items where `placement === null`
  - `warrantyStatus(item): 'ok' | 'soon' | 'expired'` — compares `warrantyExpiryDate` to today; ≤30 days = `'soon'`; past = `'expired'`; null or >30 days = `'ok'`

### `InventoryPage.svelte` (replaces stub at `#/inventory`)

Layout:

- **Toolbar (top):** search input, room filter dropdown, category filter dropdown, "＋ Add item" button
- **Table:** columns: emoji · name · category · room · purchase date · cost · warranty chip
  - Warranty chip: green `✓` when ok, orange `⚠ Xd` when soon, red `✕ expired` when expired
  - Room column shows the room name from `floorStore` by looking up `placement.roomId`; "—" if unplaced
- **Footer:** `N items · total value: X €` (sum of `purchasePrice` for items where it is set)
- **Row click** → opens `InventoryModal.svelte`

**`InventoryModal.svelte`:**

- Full-screen modal overlay (same dark theme)
- All item fields editable inline (name, emoji picker, category with suggestions, brand, model, serial, purchase date, purchase price, warranty expiry date, notes)
- "Place on map" button: fires an `onplaceonmap` callback prop (provided by `App.svelte`) which sets `activeLayers.add('inventory')` and navigates to `#/`
- "Save" → `PUT /api/inventory/items/{id}`, close
- "Delete" → confirm dialog → `DELETE /api/inventory/items/{id}`, close
- Create mode (from "＋ Add"): same form, "Create" → `POST /api/inventory/items`

### `InventoryPickerPanel.svelte`

Appears in the right sidebar when `inventoryLayerActive` is true.

- Header: `📦 Inventory` (collapsible when multiple layers active)
- Search field
- **Unplaced section:** list of `unplacedItems`; each row is `draggable="true"` with `ondragstart` setting `dataTransfer.setData('inventoryItemId', item.id)` — identical pattern to `ChorePanel`'s drag
- **Placed section:** dimmed list of `placedItems` (current floor only); each row shows 📍 + name; clicking highlights the pin on `InventoryOverlay`

**Drop handler on canvas** (`App.svelte`): the existing `ondrop` handler is extended to also read `inventoryItemId` from `dataTransfer`. On drop, it computes world coordinates and calls `inventoryStore.setPlacement(id, { floorId, roomId (room under drop point if any), position })`. Room detection uses the same `pointInPolygon` helper already in `App.svelte`.

### `InventoryOverlay.svelte`

SVG layer absolutely positioned over the canvas (same dimensions as `ChoreOverlay`). Pointer-events `none` when `inventoryLayerActive` is false.

For each `placedItems` item on the current floor:

```svg
<!-- Emoji pin -->
<text x={sx} y={sy} text-anchor="middle" dominant-baseline="middle"
      font-size="26" style="filter: drop-shadow(...)">
  {item.emoji}
</text>
<!-- Name label -->
<rect ... />
<text x={sx} y={sy+18} text-anchor="middle" font-size="9" fill="#99a">
  {item.name}
</text>
```

**Warranty glow:**
- `'soon'` → `drop-shadow(0 0 6px #ff9800)`
- `'expired'` → `drop-shadow(0 0 6px #f44336)`
- `'ok'` → `drop-shadow(0 1px 4px #0008)` (default)

**Drag to reposition:** `pointerdown` on pin → capture pointer → track movement → `pointerup` → `PUT /api/inventory/items/{id}/placement` with new world position. Same pattern as badge drag in `ChoreOverlay`.

**Click (no drag):** shows a small popup anchored to the pin:
- Item name + category
- Warranty status
- "✏️ Edit" → sets `selectedInventoryItemId` in `App.svelte` and navigates to `#/inventory`; `InventoryPage` auto-opens the modal for that item
- "✕ Remove from map" → `PUT /api/inventory/items/{id}/placement` with `{ placement: null }`

---

## Testing

**Backend (`packages/backend/tests/`):**
- `test_inventory.py`: CRUD routes, placement set/clear, 404 on missing item, partial update only changes provided fields
- `test_inventory_persistence.py`: atomic write, empty document when file missing

**Frontend (`packages/editor/test/`):**
- `inventoryStore.test.ts`: init fetches, warrantyStatus helper (ok / soon / expired boundary), placedItems/unplacedItems filtering
- `InventoryOverlay.test.ts`: correct number of pins rendered, correct glow class per warranty status

---

## What is NOT in scope

- Photos / file attachments on items
- Import from external sources (receipts, home insurance exports)
- Multiple placements per item (one location only)
- Room-boundary drag constraint on pins
- Currency selection (price stored as a plain number; display format is the user's concern)
- Barcode / QR scanning
- Consumables module (separate future spec)
