# Floor Plan Editor — Canvas Core Design Spec

**Status:** Approved for planning
**Relationship:** Sub-spec of `2026-06-15-floor-plan-editor-design.md` ("Spec 1: Floor Plan Editor"). Implements the interactive canvas core of Spec 1's Editor UX — the smallest slice that's usable in a browser. Builds on `@myhome/geometry` (Plan 1, complete: `packages/geometry`).

## Context

Spec 1 describes a full floor-plan editor: 5 tools (Select/Wall/Divider/Door/Window), a floor switcher, a room-assignment panel wired to Home Assistant's area registry, and persistence via a FastAPI backend to `/data/house.json`. That's substantial enough to need its own incremental sequencing.

This spec covers the first increment: a standalone, in-browser SVG canvas where you can draw walls and dividers, watch rooms get detected and their areas computed live (via `@myhome/geometry`), and select/move/delete shapes — with no backend, no openings, and no Home Assistant integration yet. The goal is a working, demoable canvas as quickly as possible; everything else from Spec 1 follows in later plans.

## Goals

- An interactive SVG canvas, grid-snapped to `house.gridSnap` (default 0.1 m).
- **Wall tool** and **Divider tool**: click-to-place point chains, producing `Wall` entries with `type: "wall"` (default `thickness: 0.1`) or `type: "divider"` (no thickness) respectively, matching `@myhome/geometry`'s `types.ts`.
- **Live room detection**: on every wall/divider edit, run `buildPlanarGraph` → `detectRooms` → `matchRooms` (all from `@myhome/geometry`) and render the resulting room polygons as highlighted shapes with their `areaM2` displayed.
- **Select tool**: click to select a wall/divider (highlight + endpoint drag handles), drag endpoints to move (re-snapping), Delete key to remove.
- **Pan & zoom**: mouse-wheel zoom centered on cursor, drag-pan, and a reset-view control.
- **Auto-persistence**: the `Floor` is serialized to `localStorage` on every change and restored on load; first-ever load seeds a small built-in sample floor.

## Non-goals (deferred to later plans)

- Door/Window tools, opening rendering (door-swing arcs, window symbols), and anything from `@myhome/geometry`'s `svgRender.ts`'s opening/door code paths.
- Multiple floors / floor switcher (single floor only; the `Floor` type's `order` field is unused).
- Room label editing, HA area assignment panel, "Unresolved rooms" list.
- Explicit Save, JSON export/import, and any backend/API of any kind.
- Undo/Redo.
- Reuse of `renderFloorSvg()` in the editor — it stays reserved for a future static-export feature (see "Canvas Rendering" below).

## Architecture

- New npm workspace package `packages/editor`: Vite + Svelte 5 (runes) + TypeScript + Vitest, matching the conventions already established in `packages/geometry`.
- Depends on `@myhome/geometry` (`"@myhome/geometry": "workspace:*"`) for `Point`, `Wall`, `Floor`, `Room` types and for `buildPlanarGraph`, `detectRooms`, `matchRooms`, `pointInPolygon`, `pointOnSegmentInterior`, `pointsEqual`, `polygonCentroid`.
- Single-page app, no backend, no network calls.

## Data Model & State

Svelte stores/runes:

- **`floor`**: a `Floor` object — `{ id, name, order, walls: Wall[], openings: [], rooms: Room[] }`. `openings` is always `[]` in this plan.
- **`tool`**: `'select' | 'wall' | 'divider'`, plus transient state for the in-progress point chain (array of `Point`s not yet committed, and the current cursor position for the rubber-band preview).
- **`selection`**: id of the selected wall/divider, or `null`.
- **`viewport`**: `{ panX, panY, zoom }` — affine transform from world coordinates (meters) to screen pixels.

**Room detection pipeline:** a reactive effect watches `floor.walls`. On change:
1. `detectRooms(floor.walls)` → `DetectedRoom[]`
2. `matchRooms(detected, floor.rooms)` → `{ rooms, unresolved }`
3. `floor.rooms = rooms` — **`unresolved` entries are dropped**, not retained. There's no "Unresolved rooms" UI in this plan (deferred to Spec 1's full editor), so a room whose polygon disappears simply stops existing rather than lingering with `polygon: null`. This is a deliberate scope simplification; the full `unresolved` handling from Spec 1 applies once that UI exists.

**Persistence:** `floor` is JSON-serialized to `localStorage` (key e.g. `myhome.editor.floor`) on every change, debounced ~300ms. On startup, load from `localStorage` if present; otherwise seed with a built-in sample floor (see "Sample Data").

## Editor Layout

(Layout "A" from visual review — matches Spec 1's eventual full layout.)

- **Top bar:** thin header showing the app title ("Floor Plan Editor"). No floor switcher or Save button in this plan.
- **Left toolbar:** vertical rail with **Select**, **Wall**, **Divider** tool buttons and a **Delete** action (acts on the current selection; also bound to the Delete/Backspace key).
- **Canvas:** fills the remaining space — grid background plus the SVG content area.

## Canvas Rendering

The canvas is built from **native Svelte SVG elements** (not `renderFloorSvg()`):

- **Grid:** lines every `house.gridSnap` (0.1 m) in world space, transformed by `viewport` to screen pixels.
- **Walls** (`type: "wall"`): rendered as a stroked rectangle/path of the wall's `thickness`, matching `renderFloorSvg`'s visual conventions (solid, `class="wall"`-equivalent styling) — but as live Svelte elements with click handlers for selection.
- **Dividers** (`type: "divider"`): dashed centerline, matching `renderFloorSvg`'s `class="divider"` dash style.
- **Room polygons:** semi-transparent fill, with the room's `areaM2` rendered as a centered text label at `polygonCentroid(room.polygon)`.
- **Selection highlight:** selected wall/divider rendered in an accent color with circular endpoint drag handles.
- **Tool-in-progress preview:** dashed rubber-band line from the last placed point to the cursor, with a live length label; a "snap" ring highlight when the cursor is within snap distance of an existing point or the chain's start point (closing the loop).

`@myhome/geometry`'s `renderFloorSvg()` is **not called** by the editor in this plan — all geometry *logic* (planar graph, detection, matching, point/segment math) comes from `@myhome/geometry`, but the small amount of *visual templating* (≈3 element types: walls, dividers, room polygons — openings/doors are out of scope) is reimplemented natively in Svelte for proper interactivity (click targets, drag handles, hover states). `renderFloorSvg()` remains reserved for a future non-interactive export feature.

## Tools & Interactions

- **Select tool:** click a wall/divider to select it (highlight + endpoint handles). Dragging an endpoint moves it, re-snapping to the grid or to other existing endpoints within snap distance; room detection re-runs live as the shape changes. Delete/Backspace removes the selected element. Clicking empty canvas clears the selection.
- **Wall tool:** click to place points, each snapped to the 0.1 m grid or to an existing point within snap distance. A dashed rubber-band preview with live length (meters) shows the pending segment. Clicking at/near the chain's start point closes the loop and ends the chain; Esc or double-click ends the chain without closing. Produces `Wall` entries with `type: "wall"`, `thickness: 0.1`. Zero-length segments (clicking the same point twice) are ignored.
- **Divider tool:** identical interaction, producing `type: "divider"` entries (no `thickness`).
- **Pan & zoom:** mouse wheel zooms, centered on the cursor position. Panning is via click-drag with a held spacebar, or middle-mouse-drag (left-click-drag is reserved for tool point-placement/selection). A "reset view" button restores a default zoom/center.
- **Self-intersections / overlaps:** handled entirely by `@myhome/geometry`'s `buildPlanarGraph` (segments are split at intersections automatically) — no special editor-side handling needed.

## Sample Data

On first load (nothing in `localStorage`), seed `floor` with a built-in sample: a single rectangular room (e.g., 4 m × 3 m, walls with `thickness: 0.1`) bisected by one divider, so room detection visibly produces two rooms immediately.

## Testing Strategy

- **Vitest unit tests** for the room-detection reactive pipeline: given a sequence of wall-list states, assert `floor.rooms` updates correctly — reusing fixture shapes from `@myhome/geometry`'s `roomDetection`/`roomMatching` tests (rectangle, L-shape, divider-split, courtyard) but driven through the editor's store, including the "drop `unresolved`" behavior above.
- **Vitest component tests** (Svelte testing utilities) for pure-ish logic: grid-snap math, point-snap-to-existing-endpoint, loop-closing detection, and the world↔screen viewport transform (pan/zoom).
- **Playwright** end-to-end: draw a rectangle with the Wall tool → room polygon + area appear; add a Divider across it → splits into two rooms; select and delete a wall → room updates/disappears; reload the page → `localStorage` restores the drawing.

## Open Questions for Later Plans

- How explicit Save/export (to a future backend's `/data/house.json`, or local file download) will integrate with this `localStorage`-backed model.
- Floor switcher / multi-floor UI, once more than one `Floor` needs to be held in state.
- Door/Window tool UI and how/when `renderFloorSvg()` gets adopted (e.g., a static "export SVG" view).
- Whether the "drop `unresolved` rooms" simplification needs revisiting once the full "Unresolved rooms" list exists — at that point, `matchRooms`'s `unresolved` output should likely be surfaced instead of discarded.
