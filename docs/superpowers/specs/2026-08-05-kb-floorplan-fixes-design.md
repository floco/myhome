# KB panel + floor plan panel fixes — design

Date: 2026-08-05

## Summary

A batch of small UX fixes across two existing modules:

- **Knowledge Base (KB)** page tree: default-collapsed nodes, icon-only toolbar buttons, a collapse/expand-all toggle.
- **Floor plan**: a length label while resizing a wall, HA-Area-driven room-name auto-fill, and a movable/dismissible/frontmost room naming panel — the last of which motivates extracting a shared `FloatingPanel` component used by all floor-plan floating panels.

No new modules, no schema/API changes. Frontend-only (`packages/editor`).

## A. Knowledge Base panel

### A1. Default-collapsed tree

`KBPage.svelte` currently initializes `collapsedIds` as an empty `Set`, so every node with children renders expanded by default (`collapsedIds` membership = collapsed).

Change: on mount, initialize `collapsedIds` with the ids of every KB entry that has at least one child (i.e., every entry acting as a parent in `kbStore`'s flat `parentId` list). This is a **session-only default** — not persisted (no localStorage) — matching the existing non-persistent nature of the per-node toggle. Each remount (e.g. navigating away and back) recomputes the default from the current entries.

Per-node toggle behavior (`toggleTree()`, the disclosure triangle) is unchanged.

### A2. Icon-only toolbar buttons

Four buttons go icon-only (drop their text label, keep a `title` attribute for tooltip/accessibility since `Button.svelte` already supports `title`):

| Button | Location | Icon |
|---|---|---|
| New Page | `.sidebar-toolbar` | ➕ |
| Save | `.header-actions` | 💾 |
| Cancel | `.header-actions` | ✕ |
| Edit | `.header-actions` | ✏️ |

Delete (`🗑`) is already icon-only and unchanged. `Button.svelte`'s padding (`8px 18px`) is unchanged by this spec — the icon-only buttons will look slightly wide/pill-shaped rather than square, consistent with how the existing Delete button already looks. No new icon-only button variant is introduced.

### A3. Collapse/expand-all toggle

One new icon button in `.sidebar-toolbar`, placed immediately to the left of the New Page (➕) button.

State is derived, not stored separately:
- If any entry that has children is currently in `collapsedIds` → button shows an "expand all" icon (⊞), and clicking clears `collapsedIds` (empties the set).
- Else (every parent entry is expanded) → button shows a "collapse all" icon (⊟), and clicking sets `collapsedIds` to contain every entry that has children (same computation as the A1 default).

Search-mode (`searchQuery` non-empty) already force-expands everything in `KBTree.isOpen()`; the toggle button is still shown/clickable during search but its effect is only visible once the search is cleared.

## B. Floor plan panels

### B1. Wall-resize length label

Today, `DrawPreview.svelte` shows a live length label (`{length.toFixed(2)} m`) only while drawing a new wall/divider (`tool === "wall" || "divider"`). Dragging an existing wall's endpoint via `SelectionHandles.svelte` shows no length.

Change: while a wall endpoint is being dragged (`toolStore.state.draggingPoint` is set and a wall is selected), render a length label at the midpoint of the wall being resized, styled identically to `DrawPreview`'s `.length-label` (same font/anchor/offset). Implementation: a small conditional block in `Canvas.svelte` (or an addition to `SelectionHandles.svelte`) that computes the live length from the wall's current `start`/`end` during the drag — reusing the same distance calculation `DrawPreview` uses. The label disappears when the drag ends, same lifecycle as the resize handles themselves.

### B2. HA Area → room name auto-fill

In `RoomPanel.svelte`'s `handleAreaChange`, when a new HA Area is selected: if the room's current `label` is empty (after trim), also call `onupdate({ label: <selected area's name> })` in the same update (or a follow-up call). If the room already has a non-empty label, selecting/changing the HA Area does **not** touch the label — never overwrites a name the user already set. Un-selecting the HA Area (setting it back to none) does not clear or change the label either.

### B3. Movable, frontmost, dismissible room naming panel — shared `FloatingPanel` component

**Problem**: `RoomPanel.svelte` is a plain fixed-position `<aside>` (no drag handle, no dismiss control) that shares its exact default CSS position (`right: 120px; top: 50%; translateY(-50%)`) and z-index (20) with the furniture-library and item-picker floats, so it can render fully obscured behind them with no way to move it out of the way.

Meanwhile the app already has three separate ad-hoc copies of a drag-position pattern (`makeDragHandler` + per-panel `$state` position + manual `.drag-handle` markup) for the floating toolbar, furniture library panel, and item picker panel, in `App.svelte`.

**Design**: extract a new shared component, `packages/editor/src/lib/components/ui/FloatingPanel.svelte`, and adopt it for all four floor-plan floating panels.

- Props: a default position (CSS position, passed as a class or style the panel falls back to before any drag — matching each panel's current default look), a bounding-box selector for drag clamping (same role `makeDragHandler`'s `selector` arg plays today), an optional `onDismiss` callback, a `zIndex`, and a `children` snippet for panel content.
- Internally owns its own drag state (`$state` position, mousedown/mousemove/mouseup handling ported from today's `makeDragHandler`), renders a `.panel-header` row with a `⠿` drag handle and — only when `onDismiss` is provided — an `✕` dismiss button.
- Before any drag, the panel renders at its caller-supplied default CSS position (unchanged visual default for all 4 panels). After a drag, it switches to inline `left`/`top` positioning, same as today.

**Per-panel wiring**:
| Panel | Dismiss button? | z-index |
|---|---|---|
| Floating toolbar | No — always-on primary control bar | 25 (unchanged) |
| Furniture library | Yes → closes `furnitureLibraryOpen` | 20 (unchanged) |
| Item picker | Yes → closes `pickerOpen` | 20 (unchanged) |
| Room naming panel | Yes → clears `selectedRoom` (same effect as clicking empty canvas) | 21 — raised above furniture library / item picker so it renders in front when they overlap |

Raising only the room panel's z-index (rather than moving its default position) directly addresses "should appear in the first plan / not be hidden by other panels" while leaving the other three panels' existing layout untouched. The room panel remains below the floating toolbar (25), which stays reachable at all times.

`App.svelte`'s three existing `makeDragHandler` call sites and their per-panel `$state` position variables (`ftPos`, `fpPos`, `ipPos`) are removed in favor of each panel rendering through `FloatingPanel`.

## Out of scope

- Persisting KB collapse state across reloads.
- A dedicated icon-only `Button` variant/sizing (icon-only buttons keep today's pill padding).
- Any change to wall-creation's existing length label.
- Escape-to-dismiss keyboard handling for floating panels (only the new ✕ button is added).
- Changing the furniture-library/item-picker panels' default position or size.

## Testing

Existing Vitest component-test suites for `KBPage`/`KBTree` and the floor-plan `App`/`Canvas`/`RoomPanel` components get updated/added coverage for: default-collapsed initial render, collapse/expand-all toggle behavior, icon-only button rendering, resize length label, HA-Area auto-fill (empty vs non-empty label cases), and `FloatingPanel` drag/dismiss/z-index behavior per panel.
