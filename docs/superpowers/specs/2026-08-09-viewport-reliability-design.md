# Viewport Reliability — Design

## Context

This is group A of a batch of floorplan editor requests (see also: garden
border wall [merged, PR #109], opening enhancements, furniture parameters —
separate specs). It bundles three related "the canvas doesn't behave" reports:

1. The floor plan sometimes renders blank after a page refresh, requiring
   the user to manually click "Reset view" to see anything.
2. There's no dedicated pan tool/button — panning only works via
   space+drag, middle-click-drag, or a two-finger touch gesture.
3. Pinch-to-zoom on tablet/phone is untested.

### Root cause of the blank-viewport bug

`createViewportStore()` (`viewportStore.svelte.ts`) initializes to a
hardcoded `DEFAULT_VIEWPORT` (`panX: 400, panY: 300, zoom: 100`). Nothing
calls `viewport.reset(floor, width, height)` — which fits the viewport to
the floor's actual wall bounds via `fitViewportToFloor()` — except a manual
click on the floating toolbar's "Reset view" button. If a floor's wall
geometry isn't centered near world-origin at a scale that happens to fit
the default pan/zoom, it renders off-screen: blank canvas. The same gap
means switching floors (`floorStore.switchFloor()`) never refits either, so
a floor with differently-positioned geometry can also appear blank after a
floor switch, not just after a refresh.

### Existing pan/zoom mechanisms

`Canvas.svelte` already tracks up to two active pointers
(`activePointers`/`gestureBase`) and, when two are down, computes a
centroid delta (→ `onpan`) and a distance ratio (→ `onzoom`) each move —
this is the two-finger touch pan/zoom gesture, already wired end-to-end.
Desktop panning today is only reachable via space+drag or middle-click
(`handlePointerDown`'s `event.button === 1 || (event.button === 0 &&
spacePressed)` check).

## Design

### 1. Auto-fit viewport on load and floor switch

Add an effect in `App.svelte` that calls
`viewportStore.reset(floorStore.floor, canvasWidth, canvasHeight)` whenever
`floorStore.currentFloorId` changes — this fires both on the initial floor
load and on every subsequent `switchFloor()` call, so both the refresh case
and the floor-switch case get fixed by the same mechanism.

Guard on `canvasWidth > 0 && canvasHeight > 0` before fitting: `canvasWidth`/
`canvasHeight` start as `$state(1200)`/`$state(800)` placeholders and are
only corrected once `bind:clientWidth`/`clientHeight` measures the real
`.canvas-area` container. Fitting against the placeholder size before the
real measurement lands could produce a skewed initial fit that never
self-corrects (the effect only re-runs on `currentFloorId` changes, not on
resize).

The existing manual "Reset view" button is unchanged — it remains available
for users who've panned/zoomed away and want to snap back without
switching floors.

### 2. Pan tool

- Extend `ToolType` in `toolStore.svelte.ts`:
  `"select" | "wall" | "divider" | "garden" | "door" | "window" | "pan"`.
- Add a toolbar button (hand icon, e.g. `✋`) in `App.svelte`'s floating
  toolbar, in the same group as Select/Wall/Divider/Garden. Unlike the rest
  of that group — currently gated on `!choreLayerActive && !allFloorsMode &&
  !viewMode` — the Pan button is also shown when `viewMode` is true, since
  panning is non-destructive and useful for read-only viewing. It stays
  hidden for `choreLayerActive`/`allFloorsMode` same as today (those are
  narrower overlay contexts where the whole tool group is suppressed).
- In `Canvas.svelte`'s `handlePointerDown`, add `tool === "pan"` as another
  condition (alongside `event.button === 1 || (event.button === 0 &&
  spacePressed)`) that starts `panState` — reusing the existing pan-drag
  code path in `handlePointerMove`/`handlePointerUp` rather than
  duplicating it.
- Cursor feedback: `.canvas` gets `cursor: grab` when `tool === "pan"`, and
  `cursor: grabbing` while `panState` is active, via a class binding.
- The tool is a persistent toggle (selected in the toolbar like Select/Wall/
  Divider), not a click-and-hold — consistent with how the other tools
  behave, and simpler to reason about.

### 3. Pinch-to-zoom verification

No code changes are planned upfront. This is a verification task for the
implementation plan:

- Automated: drive two synthetic `PointerEvent`s at different screen
  coordinates through `Canvas.svelte`'s pointer handlers (moving them
  apart/together and together-in-unison) and assert `onpan`/`onzoom` fire
  with the expected sign and rough magnitude — locking in the existing
  gesture math as a regression test, since it currently has no direct
  coverage.
- Manual: exercise pinch-zoom and two-finger pan on a real touch device (or
  Chrome DevTools' touch emulation) as a sanity check the automated test
  can't fully substitute for (real multi-touch event sequencing).

If either surfaces a bug, the fix is scoped to the existing
`activePointers`/`gestureBase` logic in `Canvas.svelte` — not a rewrite.

## Testing

- Unit test: the new auto-fit effect calls `viewport.reset()` with the
  right args when `currentFloorId` changes and dimensions are non-zero, and
  does *not* fire while dimensions are still at their placeholder/zero
  state.
- Component test: clicking the Pan toolbar button sets `tool = "pan"`, and
  a left-button drag on the canvas while `tool === "pan"` pans the viewport
  (via the shared `panState` path) instead of drawing or selecting.
- Component test: the Pan button is visible in both edit and view mode, and
  hidden in `allFloorsMode`/chore-layer mode, matching section 2's rule.
- Gesture regression test per section 3, added if not already present.

## Out of scope

- Persisting/remembering per-floor viewport state across floor switches
  (rejected during brainstorming in favor of always auto-fitting).
- Any change to zoom min/max bounds or the fit-padding constant.
- Double-tap-to-reset or other new touch gestures (only verification of the
  existing pinch/pan gesture is in scope).
