# Consumables Module — Design Spec

**Date:** 2026-07-02
**Status:** Approved

## Overview

A standalone module for tracking household stock levels — batteries, cleaning products, food staples, and any other consumable supplies. Users can define items with a unit and minimum threshold, record stock changes (with an automatic transaction log), pin items to rooms on the floor plan, and receive visual alerts when stock runs low or hits zero.

---

## Architecture

Standalone module following the same pattern as Chores, Inventory, and Works. New files only; no existing module is extended.

---

## Data Model

### Consumable

```
id:           str
name:         str
emoji:        str
unit:         str           # from preset list or custom text
quantity:     float         # current stock level
minQuantity:  float         # alert threshold — triggers low/empty state
categoryId:   str | null    # references ConsumableCategory in settings
description:  str = ""
placement:    Placement | null
```

### Placement

```
floorId:   str
position:  { x: float, y: float }
roomId:    str | null
```

### Transaction (stock history entry)

```
id:             str
consumableId:   str
delta:          float   # positive = added, negative = consumed (derived automatically)
quantityAfter:  float   # snapshot after this change
note:           str = ""
timestamp:      str     # ISO 8601
```

When the user sets a new quantity, the backend computes `delta = newQuantity − currentQuantity`, appends a transaction, then updates `consumable.quantity`. No separate add/remove endpoints — one `POST /api/consumables/{id}/stock` with `{ quantity, note }` handles all stock updates.

### ConsumableDocument

```
version:       int = 1
consumables:   list[Consumable]
transactions:  list[Transaction]
```

Stored in `consumables.json`.

### Settings additions

Two new fields added to the existing settings document:

- `consumableUnits: string[]` — user-editable list of unit presets. Default: `["count", "L", "mL", "kg", "g", "packs", "rolls", "pairs"]`. Unit field in ConsumableModal shows a dropdown of these plus a "Custom…" option that reveals a free-text input.
- `consumableCategories: { id, name, emoji }[]` — user-defined types (e.g., `{emoji: "🧹", name: "Cleaning"}`). Empty by default.

---

## Backend

### New files

| File | Purpose |
|------|---------|
| `models_consumables.py` | Pydantic models: `Consumable`, `Transaction`, `ConsumableDocument`, `ConsumableCreate`, `ConsumableUpdate`, `StockUpdate`, `Placement` |
| `persistence_consumables.py` | Read/write `consumables.json` |
| `routes/consumables.py` | REST routes (see below) |

### REST API

```
GET    /api/consumables                        → ConsumableDocument
POST   /api/consumables                        → create consumable
PUT    /api/consumables/{id}                   → update name/emoji/unit/categoryId/minQty/description
DELETE /api/consumables/{id}                   → delete consumable + its transactions
PUT    /api/consumables/{id}/placement         → set or clear floor plan pin (body: Placement | null)
POST   /api/consumables/{id}/stock             → set new quantity; body: { quantity: float, note: str }
                                                 backend derives delta, appends transaction
DELETE /api/transactions/{id}                  → delete a single transaction record
```

### Settings modifications

`models_settings.py`, `persistence_settings.py`, `routes/settings.py` extended with `consumableUnits` and `consumableCategories` fields. Follows the same pattern as `workCategories` and `inventoryCategories`.

---

## Frontend

### New files

| File | Purpose |
|------|---------|
| `consumableStore.svelte.ts` | Reactive store: fetch, create, update, delete, setPlacement, updateStock, deleteTransaction |
| `ConsumablesPage.svelte` | Replaces the existing stub. Table with search, category filter, low-stock filter |
| `ConsumableModal.svelte` | Create/edit modal. Fields: name, emoji, unit (preset dropdown + custom), category, minQty, description. Stock history tab with Update Stock button |
| `ConsumableOverlay.svelte` | SVG floor plan overlay — vertical bar badges, drag-to-reposition |
| `ConsumablePinPopup.svelte` | Popup on badge click: name, current stock, quick Update Stock input, link to full page |
| `HomeConsumablesWidget.svelte` | Home dashboard widget — shows only low/empty items |

### Modified files

| File | Change |
|------|--------|
| `SettingsPage.svelte` | Add "Consumables" section with consumableUnits list editor and consumableCategories CRUD |
| `LayersDropdown.svelte` | Add `{ id: "consumables", icon: "🛒", label: "Consumables" }` |
| `App.svelte` | Wire consumableStore, ConsumableOverlay, picker layer, pin popup, route handler for `#/consumables` |
| `HomePage.svelte` | Add `HomeConsumablesWidget` alongside existing widgets |

---

## Floor Plan Badge

SVG badge rendered by `ConsumableOverlay`. Draggable; click opens `ConsumablePinPopup`.

**Structure:**
- Dark backdrop circle (shadow/contrast)
- Inner circle with emoji (radius 18px, same scale as chore/inventory badges)
- Vertical bar to the right: 10px wide × 38px tall, vertically centered on the circle
- Bar fills from the bottom proportional to `quantity / (minQuantity * 3)` (clamped 0–1, so the bar reaches full at 3× minimum — a reasonable "full" proxy when no max is defined). If `minQuantity === 0`, fall back to `quantity / 10` clamped at 1, or show a full green bar if `quantity > 0`.
- Dashed horizontal line across the bar at the minimum threshold position
- Small quantity + unit text below the bar

**Stock states:**

| State | Condition | Circle outline | Bar fill | Bar outline | Quantity text |
|-------|-----------|---------------|----------|-------------|---------------|
| OK | `quantity > minQuantity` | `#444` (neutral) | `#4caf50` (green) | neutral | `#aaa` |
| Low | `0 < quantity ≤ minQuantity` | `#ff9800` (orange) | `#ff9800` | orange | `#ff9800` |
| Empty | `quantity === 0` | `#f44336` (red) | none (empty bar with ✕) | red | `#f44336` |

---

## ConsumablesPage

- Toolbar: search input, category filter dropdown, low-stock toggle (All / Needs attention)
- Table columns: emoji | name | category | quantity + unit | min qty | stock bar | status badge | actions
- Row click → `ConsumableModal` (edit mode)
- Actions column: Place on map button (navigates to floor plan with consumables layer enabled)
- Footer: item count
- Empty state with "Add consumable" prompt

---

## ConsumableModal

Two tabs (Stock tab only visible in edit mode — not shown during initial creation):

**Details tab:** name, emoji, unit (preset dropdown with "Custom…" fallback), category picker, description textarea, minQuantity input.

**Stock tab (edit mode only):**
- "Update stock" form: new quantity field + optional note → `POST /api/consumables/{id}/stock`
- Transaction history list (newest first): timestamp, delta (+ or −), quantityAfter, note, delete button

---

## Home Dashboard Widget

`HomeConsumablesWidget` shows only items where `quantity <= minQuantity` (including zero).

- Header: "🛒 Consumables"
- Stat row: `N empty` pill (red) + `M low` pill (orange) — hidden if counts are zero
- Item rows: emoji | name | `quantity unit` (colored by state)
- Hidden entirely if no low/empty items exist

---

## Alert Summary

| Surface | Low stock | Empty |
|---------|-----------|-------|
| Floor plan badge | Orange bar + orange circle outline | Empty bar with ✕ + red outline |
| Consumables page list | Orange row tint + LOW badge | Red row tint + EMPTY badge |
| Home dashboard widget | Listed with orange quantity | Listed with red quantity |

---

## Units

Unit field in `ConsumableModal` shows a `<select>` populated from `settingsStore.consumableUnits`. Last option is "Custom…" — selecting it reveals a text input. The stored value is always the plain string (whether from the list or typed).

Default preset list: `count`, `L`, `mL`, `kg`, `g`, `packs`, `rolls`, `pairs`.

---

## Testing

- Backend: `test_consumables.py` (routes), `test_consumables_persistence.py` (file I/O)
- Frontend: `consumableStore.test.ts`, `ConsumablesPage.test.ts`, `ConsumableModal.test.ts`, `HomeConsumablesWidget.test.ts`
