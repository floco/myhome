# Summary card chart types — design

Date: 2026-07-17

## Problem

The four module summary cards (Costs, Consumables, Chores, Inventory) all reuse
the same `DonutChart.svelte` component. Two problems:

1. Donut isn't the best form for every dataset shown:
   - Costs: category breakdown with widely varying magnitudes — a treemap
     reads relative size better than pie wedges, especially for small
     categories that get lost as thin slivers.
   - Consumables / Chores: a fixed 3-bucket status breakdown (ok/low/empty;
     on-track/due-soon/overdue) — a horizontal bar reads magnitude more
     directly than arc angle for so few, ranked categories.
2. Inventory's category colors are assigned by `hash(name) % 8` into a fixed
   8-color array (`InventoryPage.svelte:82-88`, duplicated in
   `HomeInventoryWidget.svelte:14-19`). With more than 8 distinct inventory
   categories, two categories can collide on the same color — confirmed via
   code inspection, not just theoretical (mod-8 hash bucket, no collision
   check).

## Non-goals

- No new charting library/dependency — stay with the codebase's existing
  hand-rolled inline-SVG pattern (`DonutChart.svelte` is the precedent).
- No change to the Costs "10-year totals" bar chart, or to any `stats-area`
  side panels (Low/Empty chips, Active/Overdue/On-track chips) — those are
  unrelated to this change.
- No change to `WorksTimeline.svelte` (separate component, not a summary
  donut).
- No broader extraction of the duplicated `chart-card-wrap`/`pie-area`/etc.
  CSS across the four pages — out of scope; new rules follow the same
  per-file `<style>` block convention already in use.

## Design

### 1. Costs summary card → `TreemapChart.svelte`

New shared component at `packages/editor/src/lib/components/TreemapChart.svelte`,
replacing `DonutChart` in `CostsPage.svelte`'s "breakdown by category" pie-area.
Same `segments` shape as today (`id, label, emoji, color, valueLabel, pct`) so
the call site mostly just swaps the component and drops `centerLabel`/
`centerValue`. Category `color` values are unchanged — they're user-set per
category in `CostsCategoryModal.svelte` and persisted; the treemap just
renders them.

- **Layout:** squarified treemap algorithm (recursively splits the remaining
  rectangle to keep cells close to square, standard technique — avoids the
  thin-sliver problem a simple slice-and-dice would have with skewed cost
  distributions).
- **Cell content**, chosen by available cell area:
  - Large enough for text: emoji + label + value.
  - Too small for the full label but big enough for an icon: emoji only
    (explicitly requested — better than clipped/missing text when space is
    tight).
  - Too small for even an icon: bare color cell, value still available via
    native `title` tooltip on hover.
- **Text color:** computed per-cell from the fill's relative luminance (dark
  text on light fills, white text on dark fills) — necessary because, unlike
  donut leader-line labels which sit on the page background, treemap labels
  sit directly on the colored fill and must contrast against it specifically.
- **Spacing:** 2px gap between cells (each cell inset by 1px per side).
- **Interaction:** clicking a cell calls the same `onsliceclick` callback
  `CostsPage.svelte` already wires to open that category's filtered view —
  behavior unchanged from the donut.

### 2 & 3. Consumables & Chores summary cards → `HorizontalBarChart.svelte`

New shared component at
`packages/editor/src/lib/components/HorizontalBarChart.svelte`, replacing
`DonutChart` in the `pie-area` of `ConsumablesPage.svelte` (stock status:
ok/low/empty) and `ChoresPage.svelte` (schedule health: on-track/due-soon/
overdue). Same `segments` shape as input.

- **Row order:** fixed status order as defined by each page's existing
  `STOCK_META`/`HEALTH_META` maps — not sorted by count. These are small,
  semantically-ordered categories (not an open categorical set), so order
  should stay meaningful rather than jumping around as counts change.
- **Row content:** emoji + label on the left, a colored bar (4px rounded
  right end, left-anchored) scaled to the largest bucket's value (not to a
  100% total) so relative magnitude is visually direct, value count + pct at
  the bar's end.
- **Colors:** unchanged — reuse each page's existing fixed `STOCK_META`/
  `HEALTH_META` color maps. These are status colors (good/warning/critical
  semantics), correctly kept separate from any categorical palette.
- **Spacing:** 2px gap between bar rows, min row height for a comfortable
  target.
- **Interaction:** native `title` tooltip per row with the exact count/pct
  (parity with the donut's on-chart labels). Neither page currently wires an
  `onsliceclick` for these two donuts, so no click behavior is added.
- Empty buckets (count 0) are filtered out before reaching the component,
  matching today's `.filter((b) => b.count > 0)` behavior on both pages.

### 4. Inventory summary card → collision-free category colors

Fixes `InventoryPage.svelte` (`pie-area`, "By category") and
`HomeInventoryWidget.svelte` (dashboard donut) — both stay `DonutChart`, only
the color assignment changes.

- **New token ramp** in `theme.css`: `--chart-series-1` through
  `--chart-series-8`, light and dark values, using the dataviz skill's
  validated categorical palette (blue/aqua/yellow/green/violet/red/magenta/
  orange). Re-validated against this app's actual surface colors
  (`#ffffff` light / `#1e1e24` dark) — passes CVD-separation and lightness
  checks; the contrast WARN on 3 light-mode slots is already mitigated since
  these donuts always render with `showLabels={true}` (direct labels, not
  color-alone identification).
- **New shared util** `packages/editor/src/lib/colorAssignment.ts`,
  exporting `assignCategoryColors(categories: string[]): Map<string, string>`:
  1. Sort `categories` alphabetically (deterministic order, independent of
     any filter/render-order effects).
  2. For each category, hash its name to a starting slot `0..N-1` where
     `N = categories.length`.
  3. Linear-probe forward (wrapping) to the next unused slot on collision.
     Since there are exactly as many slots as categories, every category is
     guaranteed a free slot — no collisions possible, by construction.
  4. Slots `0..7` map to `var(--chart-series-{n+1})`; if `N > 8`, slots `8+`
     get a generated color via golden-angle hue rotation
     (`hue = (137.508deg * slot) % 360`, fixed saturation/lightness) — not
     validated by the palette script, but this only triggers past 8
     categories, which no seed/demo home data exercises today.
- Both `InventoryPage.svelte` and `HomeInventoryWidget.svelte` call this
  util instead of their local duplicated `PALETTE`/`paletteFor`, which are
  deleted.

## Testing

- Unit tests for `assignCategoryColors`: distinct colors for N categories up
  to and beyond 8 (no collisions), deterministic given the same category
  set, stable-ish behavior when a category is added/removed (existing
  categories' colors only change if their probe chain is actually disturbed).
- Unit tests for the treemap layout function: cells tile the full area with
  no overlap, areas proportional to input values, cell-content-tier
  thresholds (label vs. icon vs. bare).
- Component tests for `HorizontalBarChart.svelte`: renders one row per
  segment in input order, bar width proportional to max value, filters
  already applied upstream (no dead-code path needed in the component for
  zero-count buckets).
- Existing Costs/Consumables/Chores/Inventory page tests updated for the
  swapped component (selector changes only — the underlying user actions
  they test, like "click a category", are unchanged for Costs).
