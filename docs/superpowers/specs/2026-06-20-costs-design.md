# Costs Module + Settings Module (Spec 4) — Design Document

**Status:** Approved for planning
**Date:** 2026-06-20

## Overview

Two new modules ship together:

- **Costs** (`#/costs`) — tracks recurring and one-off house expenses: energy orders (fuel, electricity, water, wood), taxes, and any user-defined category. Replaces the existing Finance stub at `#/finance`.
- **Settings** (`#/settings`) — a new page at the bottom of the nav menu that centralises all managed lists: cost categories, inventory categories, and any future global configuration.

The inventory module's hardcoded category suggestions are migrated to Settings so all category management lives in one place.

---

## Data Model

### `/data/settings.json`

```json
{
  "version": 1,
  "costCategories": [
    {
      "id": "uuid",
      "name": "Fuel / Mazout",
      "emoji": "🛢",
      "unit": "L",
      "color": "#4466cc"
    },
    {
      "id": "uuid",
      "name": "Electricity",
      "emoji": "💡",
      "unit": "kWh",
      "color": "#44aacc"
    },
    {
      "id": "uuid",
      "name": "Water",
      "emoji": "💧",
      "unit": "m³",
      "color": "#44ccaa"
    },
    {
      "id": "uuid",
      "name": "Wood",
      "emoji": "🪵",
      "unit": "stère",
      "color": "#cc8844"
    },
    {
      "id": "uuid",
      "name": "Property Tax",
      "emoji": "🏠",
      "unit": null,
      "color": "#9966cc"
    }
  ],
  "inventoryCategories": [
    { "id": "uuid", "name": "Electronics" },
    { "id": "uuid", "name": "Furniture" },
    { "id": "uuid", "name": "Appliance" },
    { "id": "uuid", "name": "Tool" },
    { "id": "uuid", "name": "Artwork" },
    { "id": "uuid", "name": "Other" }
  ]
}
```

**CostCategory fields:**

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID string | Generated on creation |
| `name` | string | Required; displayed everywhere |
| `emoji` | string | Required; used as row icon in the list |
| `unit` | string \| null | e.g. `"L"`, `"kWh"`, `"m³"`, `"stère"`, `"kg"`; `null` for lump-sum categories (taxes, insurance) |
| `color` | string | Hex color; used for the pie slice and per-year bar |

**InventoryCategory fields:**

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID string | Generated on creation |
| `name` | string | Required; used as a suggestion in the inventory modal |

The file ships with the five default cost categories and the six default inventory categories shown above. If the file is missing, the backend returns these defaults (it does **not** create the file on read).

---

### `/data/costs.json`

```json
{
  "version": 1,
  "entries": [
    {
      "id": "uuid",
      "categoryId": "uuid",
      "date": "2025-10-14",
      "totalAmount": 1650.00,
      "quantity": 1500,
      "unitPrice": 1.10,
      "supplier": "Butagaz",
      "notes": "",
      "roomId": "room-uuid"
    }
  ]
}
```

**CostEntry fields:**

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID string | Generated on creation |
| `categoryId` | UUID string | References a `CostCategory.id`; if the category is later deleted the entry is kept and displays "Unknown category" |
| `date` | ISO date string | Required |
| `totalAmount` | float | Required; total cost in € |
| `quantity` | float \| null | Volume delivered/consumed; `null` for lump-sum entries |
| `unitPrice` | float \| null | Price per unit in €; can be entered directly or auto-calculated as `totalAmount / quantity` when quantity is provided |
| `supplier` | string \| null | Optional |
| `notes` | string | Optional; default `""` |
| `roomId` | string \| null | Optional room association; bare ID only (no floor or position — costs are room-level, not pin-level) |

No placement/pin system for cost entries. Room assignment is a dropdown only.

---

## Backend

### New files

```
packages/backend/src/myhome/
  models_settings.py
  persistence_settings.py
  routes/settings.py
  models_costs.py
  persistence_costs.py
  routes/costs.py
```

Both routers are registered in `main.py` alongside the existing ones.

### Persistence

Both follow the identical atomic-write pattern used by inventory and chores:
- Read: load file → validate with Pydantic → return model (return defaults if file missing)
- Write: serialize → write to `.tmp` → `os.replace` to final path

`persistence_settings.py` returns a `SettingsDocument` populated with the five default cost categories and six default inventory categories when `/data/settings.json` is missing.

### Pydantic models (`models_settings.py`)

```python
class CostCategory(BaseModel):
    id: str
    name: str
    emoji: str
    unit: str | None = None
    color: str = "#4466cc"

class InventoryCategory(BaseModel):
    id: str
    name: str

class SettingsDocument(BaseModel):
    version: int = 1
    costCategories: list[CostCategory] = []
    inventoryCategories: list[InventoryCategory] = []
```

### Pydantic models (`models_costs.py`)

```python
class CostEntry(BaseModel):
    id: str
    categoryId: str
    date: str                    # ISO date
    totalAmount: float
    quantity: float | None = None
    unitPrice: float | None = None
    supplier: str | None = None
    notes: str = ""
    roomId: str | None = None

class CostsDocument(BaseModel):
    version: int = 1
    entries: list[CostEntry] = []

class CostEntryCreate(BaseModel):
    categoryId: str
    date: str
    totalAmount: float
    quantity: float | None = None
    unitPrice: float | None = None
    supplier: str | None = None
    notes: str = ""
    roomId: str | None = None

class CostEntryUpdate(BaseModel):
    categoryId: str | None = None
    date: str | None = None
    totalAmount: float | None = None
    quantity: float | None = None
    unitPrice: float | None = None
    supplier: str | None = None
    notes: str | None = None
    roomId: str | None = None
```

### Routes (`routes/settings.py`)

| Method | Path | Body | Response | Notes |
|--------|------|------|----------|-------|
| GET | `/api/settings` | — | `SettingsDocument` | Returns defaults if file missing |
| PUT | `/api/settings/cost-categories` | `list[CostCategory]` | 204 | Replaces the full cost categories list |
| PUT | `/api/settings/inventory-categories` | `list[InventoryCategory]` | 204 | Replaces the full inventory categories list |

PUT routes replace the entire list (not partial patch). The frontend always sends the full updated list.

### Routes (`routes/costs.py`)

| Method | Path | Body | Response | Notes |
|--------|------|------|----------|-------|
| GET | `/api/costs` | — | `CostsDocument` | Full `{ version, entries }` |
| POST | `/api/costs/entries` | `CostEntryCreate` | `CostEntry` (201) | Generates UUID |
| PUT | `/api/costs/entries/{id}` | `CostEntryUpdate` | 204 | Partial update; only provided fields change |
| DELETE | `/api/costs/entries/{id}` | — | 204 | Returns 404 if not found |

---

## Frontend

### New stores

**`settingsStore.svelte.ts`**

- `$state` holding `SettingsDocument` (`{ costCategories, inventoryCategories }`)
- `init()` auto-called: `GET /api/settings`
- `updateCostCategories(list)` → `PUT /api/settings/cost-categories` → `init()`
- `updateInventoryCategories(list)` → `PUT /api/settings/inventory-categories` → `init()`
- Instantiated once in `App.svelte`, passed as a prop to pages that need it

**`costsStore.svelte.ts`**

- `$state` holding `CostsDocument` (`{ entries }`)
- `init()` auto-called: `GET /api/costs`
- `createEntry(data)`, `updateEntry(id, patch)`, `deleteEntry(id)` — same pattern as inventory
- Derived helpers (computed client-side, no extra API calls):
  - `totalByYear()` → `Map<year, totalAmount>` — all entries, all categories, summed per calendar year; used for the 10-year bar chart
  - `breakdownLastCompleteYear(categories)` → array of `{ category, totalAmount, pct }` sorted descending — used for the pie chart; "last complete year" = the most recent year where at least one entry exists and the year is not the current calendar year (falls back to current year if it is the only year with data)
  - `entriesByYear(categoryId)` → `Map<year, { totalAmount, totalQuantity }>` — used for the per-category modal bar chart

### Inventory modal update

`InventoryModal.svelte`: remove the hardcoded `CATEGORY_SUGGESTIONS` constant. Accept `inventoryCategories: string[]` as a new prop. Wire into the existing `<datalist>`.

`InventoryPage.svelte`: accept a new `inventoryCategories: string[]` prop and forward it to `InventoryModal`. `App.svelte` passes `settingsStore.inventoryCategories.map(c => c.name)` to `InventoryPage`.

### Route rename

- `#/finance` → `#/costs` in `NavMenu.svelte` and `App.svelte`
- `FinancePage.svelte` is replaced by `CostsPage.svelte` (the stub file is deleted)

### `CostsPage.svelte`

**Chart section (top):**

Two panels side by side, separated by a 1 px divider:

_Left — Pie chart (SVG):_
- Donut-style pie; center label shows "Total" + sum in €
- Slices use each category's `color`
- Labels placed around the outside with SVG connector lines from slice midpoint to a short horizontal rule to the label text; labels on the left use right-aligned text, labels on the right use left-aligned text
- Each label shows: `{emoji} {name}` on line 1, `{amount} € · {pct}%` on line 2
- Clicking a slice or its label opens `CostsCategoryModal.svelte` for that category

_Right — 10-year bar chart (SVG):_
- One bar per calendar year for the last 10 years (or all years with data if fewer than 10)
- Bar color: `#2a3a6a` for complete years; `#4466cc` highlight for the last complete year; dashed outline + reduced opacity for the current partial year
- Y-axis: 3 tick labels auto-scaled to data range
- Below the chart: two stat chips — "10-year avg: X €/yr" and "Last complete yr: X € ▲/▼Y%"
- The percentage indicator compares the last complete year to the previous year

**Toolbar (below chart section):**

Search input · category dropdown (All categories + each managed category name) · year dropdown (All years + each year present in data, descending) · "＋ Add entry" button

**Table:**

Columns: emoji · Category · Date · Supplier · Qty · Unit price · Total · Room

- Emoji is pulled from the matching `CostCategory`; shows "?" if category is deleted
- Qty column: `{quantity} {unit}` if set, else "—"
- Unit price: `{unitPrice} €/{unit}` if set, else "—"
- Total: always shown in €
- Room: room label looked up from `floorStore`; "—" if null
- Row click → `CostsEntryModal.svelte` (edit mode)

**Empty state:** when there are no entries yet, the chart section is replaced by a centred placeholder ("No entries yet — click ＋ Add entry to get started.") and the table body shows the same message. The toolbar and "＋ Add entry" button are always visible.

**Footer:** `N entries · total: X €` (filtered total if filters are active)

### `CostsCategoryModal.svelte`

Full-screen modal overlay (same dark theme as `InventoryModal`).

Header: `{emoji} {name} — per year`

Body:
- Grouped bar chart per year: for each year, two adjacent bars — cost (€) in category color, volume in a lighter tint of the same color; current partial year rendered with dashed outline and reduced opacity
- Legend: color swatch + "Cost (€)" / "Volume ({unit})"; `* current year, partial` note
- Three stat chips below the chart: "Avg cost / year", "Avg {unit} / year", "Avg price / {unit}" — computed from complete years only
- For lump-sum categories (no unit): only one bar per year (cost only) and only one stat chip (avg cost / year)

Footer: Close button only (no edit/delete — entries are managed from the list)

### `CostsEntryModal.svelte`

Create/edit modal.

Fields:
- Category: dropdown populated from `settingsStore.costCategories`; selecting a category auto-fills the emoji hint
- Date: date input (required)
- Quantity: number input with unit label pulled from selected category; hidden if category has no unit
- Unit price: number input; auto-calculated as `totalAmount / quantity` when both are provided, but user can override; hidden if category has no unit
- Total amount (€): number input (required); auto-calculated as `quantity × unitPrice` when both are provided, but user can override
- Supplier: text input (optional)
- Room: dropdown from `floorStore` rooms (all floors); "No room" option
- Notes: textarea

Auto-calculation rule: when exactly two of {quantity, unitPrice, totalAmount} are filled and the third is empty, compute the third. If all three are filled, no auto-calc (user has explicit control).

Footer: "Place on map" is NOT present (costs have no pin). Delete (with confirm) on edit mode. Save / Create button.

### `SettingsPage.svelte` (`#/settings`)

Two sections, each following the same inline-editing pattern:

**Cost categories section:**
- Header: "Cost categories"
- List: each row shows color swatch · emoji · name · unit (or "—") · edit icon · delete icon
- "＋ Add category" button appends a new blank row in edit mode
- Edit mode per row: color picker (small, inline) · emoji input · name input · unit input · save (✓) · cancel (✕)
- Delete: confirm inline ("Delete?" + Confirm / Cancel)
- On save: calls `settingsStore.updateCostCategories(updatedList)`

**Inventory categories section:**
- Header: "Inventory categories"
- List: each row shows name · delete icon
- Inline add: text input + "＋" button
- Delete: immediate (no confirm — these are just suggestion labels, not referenced by ID)
- On any change: calls `settingsStore.updateInventoryCategories(updatedList)`

### `NavMenu.svelte`

- Add a visual separator (thin horizontal rule) between the existing module links and the bottom area
- Add `#/settings` link with ⚙ icon and label "Settings" below the separator

---

## Testing

**Backend (`packages/backend/tests/`):**

- `test_settings.py`:
  - `GET /api/settings` returns defaults when file missing
  - `PUT /api/settings/cost-categories` replaces list; subsequent GET reflects new list
  - `PUT /api/settings/inventory-categories` replaces list
  - Extra fields in stored JSON are tolerated (forward-compat)
- `test_settings_persistence.py`:
  - Atomic write (`.tmp` + replace)
  - Returns default document when file missing (file is NOT created on read)
- `test_costs.py`:
  - `POST /api/costs/entries` creates entry and returns it
  - `GET /api/costs` returns all entries
  - `PUT /api/costs/entries/{id}` partial update; only provided fields change
  - `DELETE /api/costs/entries/{id}` removes entry; 404 on missing
- `test_costs_persistence.py`:
  - Atomic write
  - Empty document when file missing

**Frontend (`packages/editor/test/`):**

- `costsStore.test.ts`:
  - `totalByYear()` sums correctly across categories and years
  - `breakdownLastCompleteYear()` picks the correct reference year; percentages sum to 100
  - `entriesByYear(categoryId)` filters to the correct category and aggregates per year
- `settingsStore.test.ts`:
  - `init()` fetches and populates both lists
  - `updateCostCategories()` calls PUT then re-fetches

---

## What is NOT in scope

- Currency selection (amounts stored as plain numbers; display in €)
- CSV/PDF export of entries
- Budget targets or alerts (e.g. "notify when fuel cost exceeds X")
- Photo attachments on entries
- Pin placement on floor plan for cost entries
- Per-room cost aggregation in charts (room is informational only)
- Global app preferences (theme, language) in Settings — the Settings page ships with only the two category sections
