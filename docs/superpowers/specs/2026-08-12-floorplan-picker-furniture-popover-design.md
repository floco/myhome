# Floor plan mobile: Picker/Furniture as anchored popovers + disabled Picker state

## Problem

The floor plan mobile toolbar's 3rd icon (📋 Picker) appears to do nothing when
tapped: it toggles `pickerOpen`, but its panel is gated by
`pickerOpen && pickerLayers.length > 0` (`App.svelte:1265`), and
`pickerLayers` is empty unless a module layer (Chores/Inventory/Consumables/
Costs/Works) is active — the default `activeLayers` is just `["ha"]`
(`App.svelte:195`). There's no visual indication the button is inert.

Separately, on mobile, Picker and Furniture render as a full-width, 45vh-tall
bottom sheet (`.picker-float`/`.furniture-float`'s `@media (max-width: 480px)`
override) — heavier than the small anchored popovers View/Draw/Actions now
use, and inconsistent with them.

## Scope

Mobile only (`<480px`) for the popover/positioning change; the Picker
disabled-state fix applies at all widths (it's a correctness fix, not a
layout change). `packages/editor/src/App.svelte`, `ui/Popover.svelte`.
Desktop's `.picker-float`/`.furniture-float` free-floating, draggable,
stays-open-after-placement behavior is unchanged.

## Design

### Picker disabled state

`disabled={pickerLayers.length === 0}` added to the Picker toolbar button,
reusing the existing `.ft-btn:disabled { opacity: 0.35; cursor: default; }`
rule already used by Undo/Redo/Delete. Furniture stays always-enabled (not
layer-gated).

### `isMobileViewport` flag

A small reactive flag in `App.svelte`:

```ts
let isMobileViewport = $state(window.matchMedia("(max-width: 480px)").matches);
$effect(() => {
  const mq = window.matchMedia("(max-width: 480px)");
  const update = () => { isMobileViewport = mq.matches; };
  mq.addEventListener("change", update);
  return () => mq.removeEventListener("change", update);
});
```

This is a deliberate, narrowly-scoped exception to the "CSS-only, no JS
viewport detection" pattern used everywhere else in the floor-plan toolbar
work — justified because this specific difference (anchored-vs-free-floating
positioning, auto-close-vs-stays-open) is behavioral, not visual, and CSS
cannot express "run different imperative logic based on viewport." `480px`
matches the `--bp-mobile` convention already documented in `theme.css`.

### Popover gets an optional `width`

`ui/Popover.svelte` gains `width?: number` (pixels). When provided, it's
applied as an inline `width` style on `.ui-popover` and used in place of the
existing hardcoded `200`px `PANEL_WIDTH` constant for the horizontal
viewport-clamp math, so a wider popover doesn't get clamped as if it were
narrow. The 3 existing tool-popover usages (View/Draw/Actions) omit it and
keep their current content-driven sizing — zero behavior change for them.

### Picker/Furniture rendering fork

The existing `{#if pickerOpen && pickerLayers.length > 0}` /
`{#if furnitureLibraryOpen}` blocks each get wrapped in
`{#if isMobileViewport} ... {:else} ... {/if}`:

- **Mobile branch:** the panel renders inside `<Popover open={...}
  anchorEl={...} onclose={...} width={280}>`, anchored above the Picker/
  Furniture toolbar icon (same portal + viewport-clamp mechanism as
  View/Draw/Actions). `onstartdrag` is omitted (it's an optional prop on
  both `ItemPickerPanel`/`FurnitureLibraryPanel` that only renders a
  drag-handle when provided), so no reposition handle appears.
- **Desktop branch (`{:else}`):** identical to today's markup — the
  `.picker-float`/`.furniture-float` div, `ipDrag`/`fpDrag` positioning,
  `onstartdrag` wired up, completely unchanged.

Because this is a real `{#if}/{:else}` fork (not a CSS `display:none` pair
like the toolbar buttons use), only one branch is ever mounted at a time —
no duplicate live panel instances, no duplicate event wiring.

### Auto-close after placement, mobile only

`placeDraggedAt` (`App.svelte:792`) closes the relevant panel immediately
after each *successful* placement, gated by `isMobileViewport`:

- Furniture branch: after `floorStore.addFurniture(...)` succeeds, add
  `if (isMobileViewport) furnitureLibraryOpen = false;`.
- Each module-layer branch (inventory/consumables/costs/works/chores) that
  reaches its actual placement call: add `if (isMobileViewport) pickerOpen =
  false;` right before that branch's `return`.
- Early-return "nothing to place" branches (e.g. chores requiring a room
  that wasn't found) are untouched — they don't close anything, since
  nothing was placed.

Desktop keeps today's behavior: the panel stays open after every placement
so multiple items can be placed in a row without reopening it.

### Testing

- New test: Picker button is `disabled` when `pickerLayers` is empty, and
  enabled once a module layer is toggled on.
- New tests: mobile-viewport-simulated (`matchMedia` mock/stub, the first
  precedent for this in the test suite) rendering of Picker/Furniture opens
  inside `.ui-popover` rather than `.picker-float`/`.furniture-float`.
- Existing desktop-path tests (non-mobile, default `matchMedia` state)
  continue to assert the current `.picker-float`/`.furniture-float`
  behavior unchanged.

## Out of scope

- Changing desktop's Picker/Furniture behavior (positioning, drag-reposition,
  stays-open-after-placement) in any way.
- Changing which layers are pickable, or the placement logic itself beyond
  the added close-on-success calls.
- Extracting `isMobileViewport` into a shared store — it's local to
  `App.svelte`, the only place needing it so far.
