# Demo Home Seed Data — Design

Status: approved (brainstormed 2026-07-11)

## 1. Overview & Goals

Let a user create a fully-populated "demo home" in one click from the home-creation modal, useful for exploring the app or as a sandbox, without touching a real home's data. The demo home gets a realistic floor plan and ≥30 records in each of the six content modules (Chores, Inventory, Costs, Works, Knowledge Base, Consumables).

## 2. Trigger Mechanism

`Home.type` gains a third literal value, `"demo"`, alongside the existing `"existing"` / `"project"` (`models_homes.py:22,29,34`). `NewHomeModal.svelte` gets a third radio option ("Demo home — pre-filled with sample data across every module") next to the current two. Selecting it and submitting calls the existing `POST /api/homes` with `type: "demo"` — no new endpoint.

`"demo"` is a real, permanent `Home.type` value, not a one-shot flag:
- `DEFAULT_DEMO_MODULES = ALL_MODULE_IDS` (all modules enabled, since the point is to showcase everything, including the not-yet-implemented placeholder modules which just render "coming soon").
- The home is fully normal afterward: editable, renamable, deletable, and its type can be changed via `PATCH` like any other home.
- The homes switcher (`HomesSwitcher.svelte`) shows a small "Demo" badge next to homes of this type so they're visually distinguishable from real homes.

## 3. Server-Side Seeding Flow

In `persistence_homes.py::create_home()`, after the existing steps (generate id, create `/data/homes/{id}/` dir, register in `homes.json`), if `type == "demo"`, call a new `seed_demo_home(home_id)`.

New module `packages/backend/src/myhome/demo_data.py` exposes `seed_demo_home(home_id: str) -> None`. It builds valid Pydantic documents for each module and writes them via the **existing** save functions (no duplicated file-writing logic):

| Module | Save function |
|---|---|
| Settings | `persistence_settings.save_settings` (already exists) |
| House | `persistence.save_house` |
| Chores | `persistence_chores.save_chores` |
| Inventory | `persistence_inventory.save_inventory` |
| Costs | `persistence_costs.save_costs` |
| Works | `persistence_works.save_works` |
| KB | `persistence_kb.save_entry` (called once per generated entry — the module has no batch `save_all`) |
| Consumables | `persistence_consumables.save_consumables` |

Writes happen in FK-dependency order: **settings → house → {chores, inventory, costs, works, kb, consumables}** (the six content modules only depend on settings/house, not on each other, so their relative order doesn't matter).

If seeding raises partway through, `create_home()` cleans up: remove the partially-written home directory and the just-added `homes.json` registry entry, then re-raise — mirroring the rollback-free-but-consistent behavior already used by `delete_home`'s `shutil.rmtree`. A demo home should never be left half-seeded.

## 4. Floor Plan Generation

A simple grid-based procedural layout, generated fresh per demo home (see Section 6 — randomness) so it's plausible but not identical every time.

**Algorithm**, per floor:
1. Lay out an `R × C` grid of square cells (cell size 3.5m × 3.5m, matching the default `units: "m"`).
2. Curated per-floor room lists are assigned to grid cells in reading order. Some corner cells are left unoccupied to produce a non-rectangular (L-shaped) footprint rather than a plain rectangle.
3. **Walls**: for every occupied cell, emit a wall segment along each edge that is either on the exterior boundary (grid edge or adjacent to an unoccupied cell) or shared with another occupied cell. Shared edges are deduplicated so exactly one `Wall` models the boundary between two adjacent rooms (`type: "wall"`).
4. **Openings (doors)**: build an adjacency graph of occupied cells (cells sharing an edge), compute a spanning tree over it, and place one `Opening` (`type: "door"`) at the midpoint of each spanning-tree edge's shared wall — this guarantees every room is reachable through doors, avoiding a room that's visually sealed off. Additionally place exactly one exterior door per floor on a boundary-facing wall of one occupied cell.
5. **Rooms**: each occupied cell becomes a `Room` with `polygon` = its four corner points in floor coordinates and `areaM2` = cell area. No `haAreaId` (not relevant to a demo home).
6. Module records that place a pin (see Section 5) reference a room's `id` and use that room polygon's centroid as the pin's `x, y` position, so pins render inside the correct room on the canvas.

**Concrete layout**: two floors, ground floor larger (common/utility rooms), first floor smaller (bedrooms):
- **Ground Floor** (`order: 0`): 3×3 grid with 3 cells omitted → 6 rooms: Kitchen, Living Room, Dining Room, Garage, Bathroom, Laundry Room.
- **First Floor** (`order: 1`): 2×2 grid, no omission → 4 rooms: Primary Bedroom, Bedroom 2, Home Office, Bathroom 2.

10 rooms total.

## 5. Content Modules

Each of the six modules gets a curated static list (~35 realistic entries) that the generator randomly samples/orders to produce **≥32 primary records** (comfortably over the 30 floor) with varied, randomized field values. Curated lists live as Python data in `demo_data.py` (or a `demo_data_content.py` submodule if the file gets long). Categories/suppliers referenced below are the demo-specific settings additions from Section 5.1, not the app's built-in defaults.

### 5.1 Settings additions

`settings.json` for a demo home is **not** the same as the built-in `_default_*()` lists (those stay as-is for regular homes) — the demo generator defines its own richer set so the six modules have enough category variety:
- `costCategories` (~9): existing 5 defaults conceptually extended with Groceries, Mortgage/Rent, Insurance, Entertainment/Subscriptions — each with emoji + color.
- `workCategories` (~7): existing 5 defaults plus HVAC, Landscaping.
- `inventoryCategories` (~8): Kitchen Appliances, Electronics, Furniture, Tools, Outdoor, Bedroom, Office, Décor.
- `consumableCategories` (~6): Cleaning Supplies, Kitchen Consumables, Bathroom Supplies, Filters & Batteries, Pet Supplies, Office Supplies (this list has no built-in default today — the demo generator is the first thing to populate it).
- `consumableUnits`: reuse `_default_consumable_units()`.
- `suppliers` (~9): realistic local-business-style names (e.g. "Metro Plumbing Co.", "BrightSpark Electric", "GreenScape Landscaping") — also has no built-in default today.

### 5.2 Chores (~32 chores)

Curated list of common household chores with emoji + typical `periodDays` (e.g. "Clean gutters" 🍂 180d, "Vacuum living room" 🧹 7d, "Change HVAC filter" 🌬️ 90d, "Mow lawn" 🌱 14d, "Test smoke detectors" 🔥 180d). `periodDays` gets ±20% random jitter per instance for variety.

- `nextDueDate` distribution relative to "today": ~20% overdue (past dates), ~30% due within the next 7 days, remainder spread across the chore's period going forward — gives the dashboard a realistic "some things are overdue" feel instead of everything being freshly due.
- ~20 of the 32 chores get one `Assignment` pinning them to a random room (room centroid position).
- Each chore gets 0–4 historical `CompletionRecord`s with `completedAt` spread over the last 90 days, so completion history/stats aren't empty.

### 5.3 Inventory (~32 items)

Curated list of realistic household items mapped to the demo `inventoryCategories` (e.g. "Samsung 55\" QLED TV" 📺 Electronics, "KitchenAid Stand Mixer" 🍰 Kitchen Appliances, "Dyson V11 Vacuum" 🧹 Tools, "Weber Genesis Grill" 🔥 Outdoor).

- `purchaseDate`: random within the last 1–5 years.
- `purchasePrice`: range appropriate to the item (curated list carries a rough price band per entry).
- `warrantyExpiryDate`: `purchaseDate` + 1–3 years; some end up already expired (realistic — not everything is under warranty).
- `placement`: assigned to a plausible room where the curated entry hints at one (e.g. kitchen appliances → Kitchen), otherwise a random room.

### 5.4 Costs (~32 entries)

Spread across the last 12 months, `categoryId` drawn from demo `costCategories`, `totalAmount` ranged appropriately per category (e.g. utilities $50–250, groceries $40–200, mortgage $1200–2000). To feel like a real cost history: one recurring entry per month for 2–3 "regular bill" categories (mortgage, electricity) accounts for a chunk of the 32, plus sporadic one-off entries (repairs, purchases) filling the rest. `supplierId` set on the categories where that makes sense (maintenance-adjacent); occasional `roomId`.

### 5.5 Works (~32 entries)

Curated list of realistic maintenance/improvement titles (e.g. "Replace water heater", "Repaint living room", "Fix leaking faucet", "Service HVAC system", "Replace roof shingles"), `categoryId` from demo `workCategories`.

- `status` distribution: ~50% `done` (past dates, `totalCost` set), ~15% `in_progress` (recent date), ~35% `planned` (future dates, no cost yet).
- `supplierId` set on a subset; `placement.floorId` randomly chosen.

### 5.6 Knowledge Base (~32 entries)

Curated list of realistic home-reference article titles (e.g. "Furnace Filter Replacement Guide", "Wi-Fi Router Reset Instructions", "Water Shutoff Valve Location", "Trash & Recycling Pickup Schedule", "Warranty Contacts"), each with a short (2–4 sentence) markdown body from a matching curated content snippet — not generic lorem ipsum. `createdAt`/`updatedAt` set in the past (updatedAt ≥ createdAt).

### 5.7 Consumables (~32 items)

Curated list of household consumables (e.g. "Paper Towels", "Dish Soap", "HVAC Filter 16x20", "AA Batteries", "Trash Bags", "Dog Food"), `categoryId` from demo `consumableCategories`, `unit` chosen appropriately (count/kg/L) per item from `consumableUnits`.

- `quantity`/`minQuantity` randomized so ~20% end up below `minQuantity`, populating the "low stock" view realistically.
- Each consumable gets 1–3 historical `ConsumableTransaction`s (a restock and consumption events) with `delta`/`quantityAfter` consistent with the final `quantity`.

## 6. Randomness

Every demo home is generated fresh (no fixed seed) — every creation looks different, and dates are computed relative to "today" so overdue/upcoming distributions stay realistic no matter when the home is created. Backend tests assert structural invariants (record counts ≥30, valid FK references, valid enum values, date ordering) rather than exact values, since output isn't reproducible byte-for-byte.

## 7. Attachments

Ship ~5 small static placeholder files in the backend package (e.g. `packages/backend/src/myhome/demo_assets/`: two generic placeholder photos, a placeholder "manual" PDF, a placeholder "receipt" PDF, a placeholder "warranty" PDF). For each module, a random ~25–35% subset of seeded records get exactly one attachment: the generator copies the appropriate placeholder file into that record's `{module}-attachments/{record_id}/{filename}` directory (same layout every module already uses, e.g. `persistence_inventory.py:26-45`) and sets `attachments: [filename]`. Photo-type placeholders go to inventory/works/chores; document-type placeholders go to inventory (manuals), costs (receipts), and works (warranties/invoices).

## 8. API & MCP Wiring

- `models_homes.py`: `Home.type` / `HomeCreate.type` / `HomePatch.type` literals extended to include `"demo"`; add `DEFAULT_DEMO_MODULES = ALL_MODULE_IDS`.
- `persistence_homes.py::create_home()`: branch on `type == "demo"` to call `seed_demo_home()` per Section 3.
- `mcp_tools_homes.py`: add a `create_demo_home` MCP tool (takes an optional `name`, defaults to "Demo Home"), calling `create_home(name, "demo")` — mirrors the existing `create_home`/`update_home`/`delete_home` tools.

## 9. Frontend

- `NewHomeModal.svelte`: add the third radio option with label + inline description, consistent with the existing two. Name field behavior unchanged (still required/editable); no new form fields.
- Wherever `Home.type` / `HomeCreate` is typed on the frontend (e.g. a `HomeType` alias in `homesStore.svelte.ts` or a shared types file), extend the union to include `"demo"`.
- `HomesSwitcher.svelte`: small "Demo" badge/tag next to demo-type entries (reuse the shared Badge component if one exists in the design system, otherwise a simple styled span) so demo homes are visually distinguishable in the list.
- Seeding happens synchronously server-side before the `201` response; the modal's existing submit/loading state already covers the (somewhat longer, one-time) wait. No new progress UI needed.

## 10. Testing

- **Backend**: unit tests for `demo_data.seed_demo_home()` asserting each content module has ≥30 primary records, all FK references (`categoryId`, `supplierId`, `roomId`, `floorId`) resolve to real seeded ids, the house has 2 floors with the expected room counts and at least one door per floor, and the registry entry has `type: "demo"`. Integration test: `POST /api/homes {"type": "demo"}` → `201`, then `GET` each module endpoint returns ≥30 items.
- **Frontend**: `NewHomeModal` test for the third radio option calling `createHome(name, "demo")`; `HomesSwitcher` badge-rendering test for demo-type homes.

## 11. Non-Goals

- No additional role/permission restriction beyond the existing "normal" role requirement already applied to home creation.
- No special lifecycle handling for demo homes — deleted/renamed/retyped exactly like any other home.
- No user-facing configurability of demo data volume or content (fixed curated generator, not a tunable seed wizard).
- The not-yet-implemented placeholder modules (`locations, properties, budget, visits, contacts, checklist`) are not seeded — they have no backend model to seed.
