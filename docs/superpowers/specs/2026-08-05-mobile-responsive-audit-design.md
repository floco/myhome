# Mobile Responsiveness & Touch Audit — Design Spec

Date: 2026-08-05

## Problem

The editor frontend (`packages/editor`, Vite + Svelte 5 SPA, no router —
single `App.svelte` switching on `location.hash`) has almost no responsive
design system and no touch-input support:

- **Tables**: 9 modules share `ui/SortableTable.svelte`, which renders a
  plain `<table>` with no column-hiding and no `overflow-x`. On a narrow
  viewport a 7-9 column table (e.g. Inventory) overflows its container with
  no scroll affordance — including the action buttons (edit/delete), which
  become unreachable without horizontal scroll.
- **Topbar** (`App.svelte:778-823`, `.topbar` CSS `App.svelte:1349-1356`)
  has zero `@media` rules — hamburger, title, `HomesSwitcher`, search,
  notification bell, theme toggle, and user menu sit in one fixed row that
  simply overflows on narrow screens.
- **Modals** (`ui/Modal.svelte`) always render as a centered floating box
  capped at `90vw`/`90vh`; they never go full-screen, which is cramped
  below ~480px.
- **Floor-plan canvas** (`Canvas.svelte` + `WallShape`, `RoomShape`,
  `OpeningShape`, `FurnitureShape`, `FurnitureHandles`, `SelectionHandles`)
  binds `MouseEvent` handlers exclusively (`onmousedown`/`onmousemove`/
  `onmouseup`, `onwheel`) — no touch equivalents, no pinch-zoom, no
  `touch-action` on the `<svg>`.
- **Floating panels** (Room panel, Item picker, Furniture library, the
  floating vertical toolbar — all positioned via the shared
  `floatingDrag.svelte.ts` helper) are freely-draggable, fixed-pixel-width,
  mouse-only, and have no `@media` rules — they would overlap each other
  and the canvas on a small screen.
- **Native HTML5 drag-and-drop** is used in two places that have no touch
  support by design: `ui/KBTree.svelte` (page reorder/nesting) and
  `ItemPickerPanel.svelte`/`FurnitureLibraryPanel.svelte` dragging an item
  onto the canvas (`App.svelte` `ondragover`/`ondrop` on `.canvas-area`).

By contrast, the floor-plan pin/badge overlays (`ChoreOverlay.svelte`,
`InventoryOverlay.svelte`, `CostsOverlay.svelte`, `ConsumableOverlay.svelte`,
`WorksOverlay.svelte`) already use Pointer Events + `setPointerCapture`,
which is why they already work reasonably on touch — that pattern is the
model reused throughout this spec.

There is also no breakpoint convention: existing ad hoc `@media` blocks
across the app use raw, inconsistent px values (500, 600, 700, 720, 900).

## Goals

- No table ever requires horizontal scrolling to reach its action buttons;
  lower-priority columns hide instead, with their data still reachable by
  tapping the row (opens the existing edit modal).
- Topbar and modals reflow sensibly on narrow screens instead of
  overflowing or staying a small floating box.
- Floor-plan floating panels stop overlapping on mobile by becoming bottom
  sheets, docked above an always-visible bottom toolbar bar.
- Floor-plan drawing, panning, zooming, and all drag interactions
  (resize/rotate handles, floating panels, KB tree reorder, item
  placement) work via touch, using the same Pointer-Events pattern the pin
  overlays already prove out.
- Introduce two shared breakpoint constants (`--bp-tablet: 700px`,
  `--bp-mobile: 480px`) as the convention for all CSS touched by this
  project.

## Non-goals

- No PWA/manifest/service-worker work.
- No breakpoint tiers beyond tablet (700px) and mobile (480px).
- No restructuring of what the search icon, notification bell, or theme
  toggle *do* — only their layout/visibility.
- Existing untouched components keep their current raw-px `@media` values;
  this project does not retrofit every historical breakpoint to the new
  tokens, only CSS it adds or modifies.
- Desktop mouse/keyboard behavior is preserved exactly; all touch work is
  additive (Pointer Events unify mouse+touch, so this is achieved by
  *replacing* mouse-only listeners with pointer listeners, not by adding a
  parallel touch-only code path).

## Breakpoint tokens

`theme.css` gains, alongside the existing spacing/radius scales:

```css
:root {
  --bp-tablet: 700px;
  --bp-mobile: 480px;
}
```

CSS custom properties cannot be substituted into a static `@media`
condition, so this is a *documented convention*, not literal `var()`
usage: every `@media (max-width: ...)` block added or modified by this
project uses `700px`/`480px` and a `/* --bp-tablet */`/`/* --bp-mobile */`
comment, keeping one source of truth for the two numbers.

## Phase 1 — Tables

**`SortableTable.types.ts`**: `Column<T>` gains an optional field:

```ts
hideBelow?: "tablet" | "mobile";
```

**`SortableTable.svelte`**: each `<th>`/`<td>` gets a class
(`col-hide-tablet` / `col-hide-mobile`) when its column sets `hideBelow`.
Two new `@media` blocks in the component's own `<style>`:

```css
@media (max-width: 700px) { /* --bp-tablet */
  .col-hide-tablet { display: none; }
}
@media (max-width: 480px) { /* --bp-mobile */
  .col-hide-mobile { display: none; }
}
```

Columns marked `stopRowClick: true` (the actions column, per module) never
set `hideBelow` — action buttons are always visible at every width, which
directly fixes the reported problem. Every table's existing sticky-header/
vertical-scroll behavior is unaffected; this only hides whole columns.

**Per-module column priority** (assigned by data importance, applied
during each module's implementation task):

| Module | Always visible | Hidden < 700px | Hidden < 480px (in addition) |
|---|---|---|---|
| Chores | icon, name, actions | frequency/next-due detail columns | assignee/location |
| Inventory | icon, name, actions | category, owner, store, room | purchased, cost, warranty |
| Consumables | icon, name, actions | category, threshold | store, notes |
| Works | icon, title, status, actions | dates, cost | assignee |
| Costs | icon, description, amount, actions | category, date | supplier |
| Contacts | icon, name, actions | type, phone | email, notes |
| Properties | icon, name, status, actions | location, price | notes |
| Insurance | icon, name, actions | provider, premium | renewal date |
| Build (`PhaseSection`) | phase/task name, status, actions | dates | assignee/notes |

Exact column-to-`hideBelow` mapping is finalized per module during
implementation (some modules' current column sets weren't fully enumerated
during the survey); the table above is the priority ordering, not a final
literal column list. In all cases, clicking/tapping a row continues to
open that module's existing edit modal — if any of the 9 modules doesn't
already wire row-click to the edit modal, that gets added as part of its
conversion task so no hidden data becomes unreachable.

**Dead code**: `lib/components/ChoreListPage.svelte` (confirmed unused via
repo-wide grep — `ChoresPage.svelte` + `SortableTable` superseded it) is
deleted in this phase, along with its test file if one exists, since this
phase already touches chore-row responsive CSS.

## Phase 2 — Topbar + Modals

**Topbar** (`App.svelte`): new `@media (max-width: 480px)` block hides the
page-title text (`.topbar` title element), freeing horizontal space. The
icon buttons (HomesSwitcher, search, notifications, theme toggle, user
menu) are already small/touch-sized and stay in place; if `HomesSwitcher`
currently renders a text label alongside its icon, that label is also
hidden at this breakpoint (confirmed/adjusted during implementation by
inspecting its current markup).

**Modal** (`ui/Modal.svelte`): new `@media (max-width: 480px)` block
overrides the centered-floating-box layout:

```css
@media (max-width: 480px) { /* --bp-mobile */
  .ui-modal {
    position: fixed;
    inset: 0;
    top: 0; left: 0;
    transform: none;
    width: 100%;
    height: 100%;
    max-width: 100vw;
    max-height: 100vh;
    border-radius: 0;
  }
}
```

The `width` prop passed by call sites (raw px or `min(92vw, 820px)`) is
overridden by this media query at that breakpoint, so no per-call-site
changes are needed — this is a single shared-component change covering all
existing modals uniformly. Body/footer internal scrolling and footer
button wrapping are unchanged.

## Phase 3 — Floating panels (bottom sheet on mobile)

Below 480px, the floor-plan editor's floating-panel layout changes from
"freely draggable, absolutely positioned" to a fixed bottom toolbar +
docked bottom sheet:

- **Floating toolbar** (`.floating-toolbar` markup/CSS in `App.svelte`)
  gets a `@media (max-width: 480px)` override: `position: fixed; bottom: 0;
  left: 0; right: 0; top: auto; transform: none;` with its icon column
  reflowed to a horizontal row (`flex-direction: row`). It is always
  visible in this mode — no drag-to-reposition on mobile.
- **Room panel / Item picker / Furniture library panel** each get a
  `@media (max-width: 480px)` override: `position: fixed; left: 0; right:
  0; bottom: <toolbar-bar-height>; top: auto; width: 100%; max-height:
  45vh; overflow-y: auto;` replacing their desktop fixed-width/
  free-floating position. A drag handle at the top of the sheet (reusing
  each panel's existing `.{panel}-handle` element, already present for
  desktop drag-to-move) becomes a drag-to-dismiss gesture instead of
  drag-to-reposition. Only one contextual panel is open at a time today
  (each already appears/disappears based on selection state — e.g. Room
  panel only when `selectedRoom` is set), so no new open/close
  coordination logic is needed; the existing conditional-rendering already
  guarantees at most one sheet plus the always-present toolbar bar.

**`floatingDrag.svelte.ts`**: `startDrag`/the `window` listener pair
convert from `MouseEvent`/`mousemove`/`mouseup` to `PointerEvent`/
`pointermove`/`pointerup`, adding `setPointerCapture(e.pointerId)` in
`startDrag` — mirroring `ChoreOverlay.svelte`'s existing pattern. This
fixes touch-dragging on desktop-mode panels (viewports ≥ 480px, where
panels are still free-floating) and doubles as the drag-to-dismiss handle
implementation for the mobile bottom sheets in the same phase.

## Phase 4 — Canvas touch gestures

`Canvas.svelte` and its interactive sub-components swap mouse listeners
for pointer listeners one-for-one:

| File | Before | After |
|---|---|---|
| `Canvas.svelte` | `onmousedown`/`onmousemove`/`onmouseup`, `onwheel` | `onpointerdown`/`onpointermove`/`onpointerup` + gesture tracker (below); `onwheel` kept as-is for desktop scroll-zoom |
| `SelectionHandles.svelte` | `onmousedown` (wall endpoint drag) | `onpointerdown` + `setPointerCapture` |
| `OpeningShape.svelte` | `onmousedown` (door/window handle) | `onpointerdown` + `setPointerCapture` |
| `FurnitureHandles.svelte` | `onmousedown` (resize/rotate corners) | `onpointerdown` + `setPointerCapture` |
| `FurnitureShape.svelte` | `onmousedown` (body drag) | `onpointerdown` + `setPointerCapture` |

Global drag-continuation listeners (currently `window.onmousemove`/
`onmouseup` wired in `App.svelte`, e.g. `App.svelte:761`) become
`pointermove`/`pointerup`.

**Gesture mapping**:
- 1 active pointer down on empty canvas + current tool active → draw
  (wall/room/etc.), same as today's left-click.
- 1 active pointer down on a handle/shape → drag/resize/rotate it, same as
  today's left-click-drag.
- 1 active pointer down elsewhere → select, same as today's left-click.
- 2 active pointers → a new gesture tracker in `Canvas.svelte` computes
  the centroid delta between frames for **pan** (replaces
  middle-click-drag / space+drag, neither of which exist on touch) and the
  distance ratio between the two pointers for **pinch-zoom** (replaces
  `onwheel`). Implemented via a `Map<pointerId, {x,y}>` updated in the
  existing `onpointermove` handler; when the map size is 2, pan/zoom logic
  runs instead of draw/select logic.
- `touch-action: none` is added to the canvas `<svg>`'s style
  (`Canvas.svelte:317-320`) so the browser never intercepts a touch
  gesture for native scroll/zoom while the user is interacting with the
  canvas.

## Phase 5 — HTML5 DnD → Pointer Events

**`ui/KBTree.svelte`**: `draggable="true"`/`ondragstart`/`ondragover`/
`ondrop` (`KBTree.svelte:167-172`) is replaced with `onpointerdown`
(starts drag, captures the pointer) / `onpointermove` (updates a floating
ghost row positioned at the pointer, and recomputes the
before/after/inside drop-position indicator from the pointer's Y position
over candidate rows — reusing the existing indicator-calculation logic,
just fed from pointer position instead of `dragover` events) /
`onpointerup` (commits the move, matching today's `handleTreeDrop`). The
trash drop-zone (`KBPage.svelte:425-427`) is updated the same way.

**`ItemPickerPanel.svelte`/`FurnitureLibraryPanel.svelte` → canvas**:
`draggable`/`ondragstart` on each item thumbnail is replaced with
`onpointerdown`, which renders a small floating ghost icon following
`pointermove`; `onpointerup` checks whether the pointer is over
`.canvas-area` and, if so, converts the pointer's screen position to
canvas coordinates (reusing the existing screen→canvas conversion already
used by `handleDrop`) and places the item there — same end result as
today's `ondrop`, different input path. `App.svelte`'s `ondragover`/
`ondrop` handlers on `.canvas-area` are removed once both panels no longer
emit native drag events.

## Verification

Each phase is checked with the `webapp-testing` skill (Playwright) using
device-emulated contexts:

- Viewport 375×667 (mobile) and 768×1024 (tablet), `hasTouch: true`.
- Assertions: no horizontal scroll on any page/table, action buttons
  present in the DOM and within the viewport bounds at both sizes, bottom
  sheets/toolbar don't overlap, modals fill the viewport at 375×667.
- Phase 4 (canvas gestures) additionally gets a manual walkthrough in a
  real touch-capable browser context, since Playwright's synthetic
  multi-touch simulation doesn't reliably reproduce real pinch/pan
  hardware behavior — documented as a manual QA note in that phase's
  implementation task rather than an automated assertion.

## Rollout

Five independently mergeable phases, each its own PR, in this order:

1. Tables (+ breakpoint tokens, + `ChoreListPage.svelte` deletion)
2. Topbar + Modals
3. Floating panels → bottom sheet + `floatingDrag` → Pointer Events
4. Canvas touch gestures
5. HTML5 DnD → Pointer Events (KB tree, item/furniture placement)

Phases 3 and 4 both touch floor-plan interaction code but are separable:
Phase 3 is layout + the shared drag helper, Phase 4 is the canvas's own
event bindings. Phase 5 is independent of 3 and 4 (different files
entirely) and could ship in parallel, but is ordered last since it's the
lowest-traffic interaction (KB reorder, item placement) relative to core
canvas usability.
