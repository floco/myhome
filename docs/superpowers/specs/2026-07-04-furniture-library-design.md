# Furniture Library — Design Spec

**Date:** 2026-07-04
**Scope:** Add a drag-and-drop furniture/object library to the floor plan canvas. Objects are purely spatial (no data linkage), resizable with free aspect ratio, and rotatable.

---

## 1. Data Model

### New type in `packages/geometry/src/types.ts`

```ts
export interface FurnitureObject {
  id: string;
  templateId: string;   // references a FurnitureTemplate in the built-in library
  x: number;            // world coords (meters), center of object
  y: number;
  width: number;        // meters
  height: number;       // meters
  rotation: number;     // degrees, clockwise
}
```

`Floor` gains one new optional field (defaulted to `[]` on load for backward compat):

```ts
furnitureObjects?: FurnitureObject[];
```

### HouseDocument version

`version` is bumped from `1` to `2`. On load, any floor missing `furnitureObjects` is patched to `[]` so existing saves continue to work without migration.

---

## 2. Furniture Template Library

**File:** `packages/editor/src/lib/furnitureLibrary.ts`

```ts
export type FurnitureCategory =
  | "living-room"
  | "bedroom"
  | "kitchen-dining"
  | "bathroom"
  | "office"
  | "outdoor"
  | "garden";

export interface FurnitureTemplate {
  id: string;
  label: string;
  category: FurnitureCategory;
  defaultWidth: number;   // meters
  defaultHeight: number;  // meters
  svgContent: string;     // SVG elements drawn in a 100×100 viewBox, centered at 50,50
}
```

All shapes are bundled — no external fetches. Each template's `svgContent` is a minimal SVG string (paths, rects, circles, ellipses) representing an architectural top-down view.

### Catalog

| Category | Items |
|---|---|
| Living room | sofa, armchair, coffee-table, tv-unit, bookshelf |
| Bedroom | bed-single, bed-double, wardrobe, nightstand, desk-bedroom |
| Kitchen / Dining | dining-table-rect, dining-table-round, dining-chair, kitchen-island, fridge, oven, sink-kitchen |
| Bathroom | toilet, bathtub, shower, sink-basin |
| Office | desk-office, office-chair, filing-cabinet |
| Outdoor | garden-table, garden-chair, sunlounger, bbq, pool-rect, pool-oval, hot-tub, garden-bench, shed |
| Garden | tree, hedge, deck-terrace, car, plant, grass-patch |

Default sizes are realistic architectural dimensions (e.g. sofa: 2.2 × 0.9 m, bed-double: 1.6 × 2.0 m, tree: 1.5 × 1.5 m).

---

## 3. Components

### `FurnitureShape.svelte`

Renders one placed furniture object inside the Canvas SVG.

**Props:** `object: FurnitureObject`, `template: FurnitureTemplate`, `viewport: ViewportState`, `selected: boolean`, `tool: ToolType`
**Events:** `onselect(id: string)`

Renders a `<g>` with a single SVG transform that:
1. Translates to world center `(x, y)` → screen coords via viewport
2. Rotates by `rotation` degrees around center
3. Scales the 100×100 template viewBox to `(width × height)` in world units × zoom

Fill: `var(--canvas-furniture-fill)`, stroke: `var(--canvas-furniture-stroke)`.
In `select` tool mode: pointer cursor + click fires `onselect`.

### `FurnitureHandles.svelte`

Selection and transform handles for the selected furniture object, rendered as SVG elements inside the Canvas.

**Props:** `object: FurnitureObject`, `viewport: ViewportState`
**Events:** `onmovestart`, `onmove(dx, dy)`, `onmoveend`, `onresizestart(corner)`, `onresize(corner, dx, dy)`, `onresizeend`, `onrotatestart`, `onrotate(angle)`, `onrotateend`

- **4 corner handles** (small squares): drag freely → updates `width` and `height` relative to the opposite corner
- **1 rotation handle** (circle, rendered 20px above the top-center): drag in arc around object center → updates `rotation`
- **Body drag area** (transparent rect over object): `mousedown` → move interaction

### `FurnitureLibraryPanel.svelte`

A fixed-width sidebar panel (same visual style as `ItemPickerPanel`) that serves as the drag source.

- Categories rendered as collapsible sections (open by default)
- Each item: 50×50px SVG thumbnail (the template's `svgContent` in a scaled viewBox) + label below
- Items are `draggable="true"`; `dragstart` stores `furnitureTemplateId` in `dataTransfer`
- Scrollable; grouped by category
- Width: same as `ItemPickerPanel` (~200px)

---

## 4. Canvas Integration

### `Canvas.svelte` new props

`Corner` is a local type: `"tl" | "tr" | "bl" | "br"`.

```ts
furnitureObjects?: FurnitureObject[];
selectedFurnitureId?: string | null;
onselectfurniture?: (id: string | null) => void;
onmovefurniturestart?: (id: string, worldPoint: Point) => void;
onmovefurniture?: (worldPoint: Point) => void;
onresizefurniturestart?: (id: string, corner: "tl"|"tr"|"bl"|"br", worldPoint: Point) => void;
onresizefurniture?: (worldPoint: Point) => void;
onrotatefurniturestart?: (id: string, worldPoint: Point) => void;
onrotatefurniture?: (worldPoint: Point) => void;
onfurnituredragend?: () => void;
```

Furniture is rendered **below walls** (so walls draw on top), **above rooms**:

```
rooms → furniture → walls → openings → draw-preview → handles
```

```svelte
{#each furnitureObjects as obj (obj.id)}
  <FurnitureShape {obj} template={getTemplate(obj.templateId)} ... />
{/each}
{#if selectedFurnitureObj}
  <FurnitureHandles object={selectedFurnitureObj} ... />
{/if}
```

A helper `getTemplate(id): FurnitureTemplate | undefined` is imported from `furnitureLibrary.ts`.

### Click-through: furniture vs. canvas background

In `select` tool, clicks on furniture fire `onselectfurniture`. Clicks on the canvas background clear the furniture selection (same as clearing wall selection today).

---

## 5. Floating Toolbar

A new button is added to the floating toolbar in `App.svelte`:

```
🪑 Furniture
```

Toggles `furnitureLibraryOpen: boolean`. When open, `FurnitureLibraryPanel` appears in `.right-panels` alongside (or instead of) the existing `ItemPickerPanel`.

---

## 6. Store — `houseStore` additions

Five new methods added to `createHouseStore`, following the existing snapshot pattern:

```ts
addFurniture(obj: Omit<FurnitureObject, "id">): void
  // saveSnapshot → push to currentFloor().furnitureObjects → generation++

removeFurniture(id: string): void
  // saveSnapshot → filter out → generation++

moveFurniture(id: string, x: number, y: number, opts?: { skipHistory?: boolean }): void
  // skipHistory during drag; saveSnapshot on mouseup

resizeFurniture(id: string, width: number, height: number, opts?: { skipHistory?: boolean }): void

rotateFurniture(id: string, rotation: number, opts?: { skipHistory?: boolean }): void
```

The existing `save()` / autosave already serializes the full `floors` array, so furniture persists automatically.

---

## 7. Interaction Model (`App.svelte`)

### Drop from library

`handleDrop` gains a `furnitureTemplateId` branch:
1. Read `furnitureTemplateId` from `dataTransfer`
2. Look up template for default `width` / `height`
3. Convert drop screen position to world coords
4. Call `floorStore.addFurniture({ templateId, x, y, width, height, rotation: 0 })`

### Select

`onselectfurniture(id)` sets `selectedFurnitureId`, clears `selectedId`, `selectedOpeningId`, `selectedRoomId`. Clicking canvas background clears all selections.

### Move (drag body)

- `onmovefurniturestart` → `floorStore.saveSnapshot()`, record drag anchor
- `onmovefurniture` (mousemove) → `floorStore.moveFurniture(id, newX, newY, { skipHistory: true })`
- `onfurnituredragend` (mouseup) → nothing extra (snapshot already saved)

### Resize (corner handles)

- `onresizefurniturestart` → `floorStore.saveSnapshot()`, record which corner + anchor
- `onresizefurniture` → compute new width/height from cursor delta relative to opposite corner → `floorStore.resizeFurniture(id, w, h, { skipHistory: true })`. Min size: 0.1 m each dimension.
- `onfurnituredragend` → done

### Rotate (rotation handle)

- `onrotatefurniturestart` → `floorStore.saveSnapshot()`, record object center
- `onrotatefurniture` → compute `atan2(cursor - center)` → `floorStore.rotateFurniture(id, angle, { skipHistory: true })`
- `onfurnituredragend` → done

### Delete

`handleDelete` in `App.svelte` gains a `selectedFurnitureId` branch → `floorStore.removeFurniture(id)`.

`Delete`/`Backspace` keyboard shortcut already routes through `handleKeydown`, extended naturally.

### Undo/Redo

Free — all furniture mutations go through `saveSnapshot`. Existing undo/redo works unchanged.

---

## 8. Theme Tokens

Two new CSS custom properties added to both light and dark themes in `theme.css`:

```css
/* light */
--canvas-furniture-fill: #ede9e0;
--canvas-furniture-stroke: #8a7f6e;

/* dark */
--canvas-furniture-fill: #2a2822;
--canvas-furniture-stroke: #6a5f4e;
```

---

## 9. Backend

**No backend changes.** Furniture is stored as part of the existing `HouseDocument` JSON blob via the existing `PUT /api/homes/{id}/house` route. The version bump is handled on the frontend load path only.

---

## 10. Testing

- Unit tests for `furnitureLibrary.ts`: all templates have required fields, valid SVG content, positive dimensions
- Unit tests for the 5 new `houseStore` methods: add/remove/move/resize/rotate, undo/redo round-trips
- Component tests for `FurnitureShape`: renders at correct transform, fires `onselect`
- Component tests for `FurnitureLibraryPanel`: renders all categories, fires dragstart with correct templateId
- Component tests for `FurnitureHandles`: fires correct events on corner/rotation/body drag
- Integration: drop from panel → object appears on floor, saved in document
