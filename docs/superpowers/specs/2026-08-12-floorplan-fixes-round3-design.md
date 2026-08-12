# Floor Plan Fixes — Round 3

Date: 2026-08-12
Status: Draft

## Context

Five independent small fixes to the floor plan editor (`packages/editor`), reported together as a batch (consistent with prior "floorplan batch" fix rounds). Each is scoped and implemented independently within one plan.

## 1. Chore pin → open full chore modal

**Current state:** Clicking a chore pin on the floor plan (`ChoreOverlay.svelte`) sets `selectedBadge` in `App.svelte`, rendering `BadgePopup.svelte` — a small inline popup (name, due date, quick complete/remove actions). The full tabbed chore detail modal, `ChoreEditModal.svelte` (info/assignments/media/history tabs), is only reachable from `ChoresPage.svelte` today and is not imported in `App.svelte`.

**Fix:** Add a "details" button to `BadgePopup.svelte` (e.g. a 🔍 icon alongside the existing quick-action buttons). Clicking it:
- Closes `BadgePopup` (clears `selectedBadge`).
- Sets a new `App.svelte` state, e.g. `mapEditChore: Chore | null`, to the assignment's chore.
- Renders `ChoreEditModal` (newly imported into `App.svelte`) with the same props `ChoresPage.svelte` passes: `chore`, `store={choreStore}`, `rooms`, `onclose={() => mapEditChore = null}`.

No changes to `ChoreEditModal` itself.

## 2. Zone/room label placement (avoid overlapping child rooms)

**Current state:** There is no explicit "zone" concept in the data model — only `Room` polygons (`packages/geometry/src/types.ts`), which may geometrically overlap (e.g. an outer boundary room enclosing smaller interior rooms). `RoomShape.svelte` places every room's label at `polygonCentroid(room.polygon)` with no overlap avoidance, so a room whose polygon contains other rooms gets its label buried under them.

**Fix:**
- New helper in `packages/geometry` (e.g. `geometry.ts` or a new file): `computeLabelPosition(room: Room, allRooms: Room[]): Point`.
  - Detect "child" rooms: any other room whose polygon overlaps this room's polygon by ≥50% of the *child's own area* (containment test, geometric — no new data field).
  - If no children found, return `polygonCentroid(room.polygon)` (unchanged behavior).
  - If children found: sample a grid of candidate points within `room.polygon`'s bounding box, keep only points that are inside `room.polygon` (via existing `pointInPolygon`) and outside every child room's polygon, then pick the surviving candidate that maximizes the minimum distance to any child polygon (the most "open" spot). Falls back to the plain centroid if no candidate survives (e.g. fully covered).
  - No polygon-clipping library needed — grid sampling reuses the existing `pointInPolygon` primitive.
- `RoomShape.svelte`: add an `allRooms: Room[]` prop (passed from `Canvas.svelte`, which already has `floor.rooms` in scope at its `{#each}` loop) and use `computeLabelPosition(room, allRooms)` instead of the raw centroid call for `labelPos`.

## 3. Mobile drag-and-drop — root cause: missing `touch-action`

**Current state:** Investigation found the DnD *logic* is already unified across desktop/mobile and across furniture/chores/inventory/etc. via Pointer Events (`pointerdown`/`pointermove`/`pointerup`) in `Canvas.svelte` and `App.svelte`'s `placeDraggedAt`. `Canvas.svelte` and `SelectionHandles.svelte` both explicitly set `touch-action: none` on their draggable elements — but the picker/furniture list rows do not:
- `ItemPickerPanel.svelte` `.item-row` (used for chores, inventory, consumables, costs, works items)
- `FurnitureLibraryPanel.svelte` `.furniture-item`

Without `touch-action: none`, the browser's default touch handling treats the first finger-move on these rows as a scroll gesture on the nearest scrollable ancestor (`.section-body` / `.panel-body`) and fires `pointercancel` instead of continuing `pointermove` — so the app's custom drag never starts. This matches the reported symptom exactly ("nothing happens at all").

**Fix:** Add `touch-action: none;` to `.item-row` (`ItemPickerPanel.svelte`) and `.furniture-item` (`FurnitureLibraryPanel.svelte`). Do not add it to the scrollable containers (`.section-body`, `.panel-body`) — only to the draggable row elements themselves, so vertical scrolling of the list (e.g. via padding/gaps between rows) still works, matching the existing `Canvas.svelte` pattern of scoping `touch-action: none` to the interactive element, not its scrollable ancestor.

## 4. Stairs — top-down rendering + shape variant

**Current state:** `furnitureLibrary.ts` stairs entry (`id: "stairs"`) has only a static `svgContent` zig-zag path — no `params`, no `render` function, so every stair instance looks identical regardless of actual layout (e.g. an L-shaped landing). The `sofa` entry already has a working precedent: a `params` array with an enum `shape` (`straight` | `l-shaped`) and a conditional `corner` enum (`nw`/`ne`/`se`/`sw`, shown only when `shape === "l-shaped"`), consumed by a `renderSofa(ctx)` function.

**Fix:** Mirror the sofa pattern for stairs:
- Add `params` to the stairs template: `shape` enum (`straight` | `l-shaped`, default `straight`), `corner` enum (`nw`/`ne`/`se`/`sw`, default e.g. `se`, `visibleWhen: { paramId: "shape", equals: "l-shaped" }`).
- Add `renderStairs(ctx)`: for `straight`, draw parallel tread lines top-down along the full run (similar to today's static zig-zag but generated procedurally so width/height scale correctly). For `l-shaped`, draw treads following one leg, turning at the specified `corner`, and continuing along the second leg — geometrically analogous to `renderSofa`'s L-turn branch, but as a series of perpendicular tread lines instead of an L-shaped seat outline.
- Wire `render: renderStairs` into the stairs template entry (same mechanism as `render: renderSofa` etc.) — `resolveFurnitureSvg` already prefers `template.render` over the static `svgContent` when present, so no dispatch changes needed elsewhere.
- `FurnitureParamsPanel.svelte` already renders whatever `params` a template declares, so the new `shape`/`corner` controls appear automatically once the template has `params`.

## 5. Mobile toolbar — stable Edit/View toggle position

**Current state:** In `App.svelte`'s `.floating-toolbar`, DOM order is: FloorSwitcher → LayersDropdown → Picker(📋, edit-mode only) → Furniture(🪑, edit-mode only) → separator → **Edit/View toggle(✏️)** → Save(edit-mode only) → ... Desktop and mobile share this single DOM order; CSS (`.ft-desktop-item`/`.ft-mobile-item`) only toggles visibility of the *later* tool buttons per breakpoint, not these earlier ones. Because Picker/Furniture are conditionally rendered (`{#if !viewMode}`), toggling view mode removes/adds them, shifting the toggle button's on-screen position.

**Fix:** Move the Edit/View toggle button's markup earlier in `App.svelte`, to right after `LayersDropdown` and before the Picker/Furniture buttons. This is a straightforward reorder of existing markup (no new conditionals, no CSS changes) — the toggle becomes the first item after LayersDropdown, so nothing before it in the toolbar ever appears/disappears, and it stays in the same slot in both edit and view mode. This changes button order identically on both desktop and mobile (accepted — simplest fix, no mobile-only CSS `order` needed).

## Testing

- Unit tests for `computeLabelPosition` (no children → centroid; with children → point outside all child polygons; fully-covered fallback).
- Unit tests for `renderStairs` (straight vs l-shaped output differs; corner variants).
- Component test for `BadgePopup` details button wiring.
- Existing touch/pointer test patterns (per `feedback_svelte5_jsdom_event_delegation` memory: attach to `document.body`, `bubbles: true`) extended to cover the `touch-action` CSS is present (style assertion) since jsdom doesn't simulate real touch-scroll hijacking.
- Manual browser/mobile check for items 3 and 5 (touch DnD and toolbar stability can't be fully verified by jsdom).
