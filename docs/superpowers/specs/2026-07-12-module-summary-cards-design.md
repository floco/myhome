# Module Summary Cards — Design

## Problem

`CostsPage.svelte` recently gained a two-card layout: a top card with a chart/summary, and the entries table wrapped in its own card below, both floating on the page's gray background. Chores, Inventory, Consumables, and Works still use the older layout (plain toolbar + table, no top summary, table not card-wrapped). The ask is to bring the same visual pattern to these four pages, with each page's top card showing whatever summary is most useful for that module's data — and, for Works specifically, a timeline showing works plotted across the years, so it reads as a history of how the house has evolved.

KB is out of scope: it's a two-pane markdown article list/editor, not a table page, and doesn't fit this pattern.

## Scope

**In scope**: `ChoresPage.svelte`, `InventoryPage.svelte`, `ConsumablesPage.svelte`, `WorksPage.svelte`.

**Out of scope**: KB module (structurally different, no table). Any change to the underlying stores' data model — this is presentation-only, built on data/helpers that already exist.

## Shared layout skeleton

All four pages adopt the same structure already proven in `CostsPage.svelte`:

```
.page (flex column, height 100%)
  .chart-card-wrap (padding: var(--space-4), flex-shrink: 0)
    Card > (module-specific summary content)
  .table-card-wrap (flex: 1, min-height: 0, padding: 0 var(--space-4) var(--space-4), display: flex)
    Card (style="display:flex; flex-direction:column; padding:0; overflow:hidden; flex:1; min-height:0;")
      .toolbar (search/filters/add button — unchanged from today)
      .table-wrapper (flex:1, overflow-y:auto) > SortableTable (unchanged from today)
      .footer (unchanged from today)
```

No new shared layout component is introduced — each page copies this CSS skeleton (as `CostsPage.svelte` currently has it inline), since there are only 4 call sites and the skeleton is a handful of CSS rules, not behavior. If a 5th or 6th page needed it later, extracting a shared wrapper component would be worth revisiting.

Toolbar, table, and footer markup/behavior are **unchanged** — only their wrapping container changes (matching the Costs migration, which didn't touch table content, only added the Card wrapper).

## Per-module summary card content

### Chores — schedule-health donut

- **Data**: for every `Assignment`, compute `pct = store.getProgress(assignment, chore)` (already exists, `choreStore.svelte.ts:101`) and bucket using the same thresholds as the existing `getColor(pct)` (already exists, `choreStore.svelte.ts:108`): on-track (`pct > 0.5`, green `#4caf50`), due-soon (`pct > 0.25`, orange `#ff9800`), overdue (`pct <= 0.25`, red `#f44336`).
- **Chart**: `DonutChart` with 3 segments (on-track/due-soon/overdue counts), `showLabels` on, `centerLabel="Assignments"`, `centerValue` = total count.
- **Stats beside it**: active count, overdue count, on-track % — the same three numbers `HomeChoresWidget.svelte` already computes (`rows.length`, `overdueCount`, `onTrackPct`), recomputed here from the page's own assignment list.
- **Click**: clicking a segment filters the table to that bucket (reuses the page's existing schedule filter, if present, or a new lightweight one) — non-essential polish, not required for the first cut if it adds scope; the plan can decide.

### Inventory — category donut

- **Data**: group `InventoryItem`s by `category` (fallback `"Uncategorized"`), same grouping `HomeInventoryWidget.svelte:27-36` already does. Reuse its `paletteFor(category)` hash-to-color function (or extract it to a shared util if the plan finds a clean spot — small enough that duplicating the ~5-line function is also acceptable).
- **Chart**: `DonutChart`, `showLabels` on, `centerLabel="Items"`, `centerValue` = total item count.
- **Stats beside it**: total item count, total purchase value (page already computes `totalValue`).

### Consumables — stock-status donut

- **Data**: bucket every `Consumable` by the existing exported `stockStatus(c)` helper (`consumableStore.svelte.ts:36`): `ok` (green), `low` (orange), `empty` (red) — reuse `HomeConsumablesWidget.svelte`'s color mapping (`STATE_COLOR`).
- **Chart**: `DonutChart`, `showLabels` on, `centerLabel="Items"`, `centerValue` = total consumable count.
- **Stats beside it**: low count, empty count (mirrors `HomeConsumablesWidget`'s pills).

All three reuse `DonutChart.svelte` exactly as `CostsPage` does — same segment shape (`{id, label, emoji, color, valueLabel, pct}`), no changes needed to that component. Category counts here (2–8 buckets) are within the range the donut's label-declutter logic already handles cleanly (verified against Costs' worst case of 6 categories dominated by one large slice).

### Works — timeline

New component: `WorksTimeline.svelte` (in `packages/editor/src/lib/components/`), replacing the donut pattern for this module since Works data isn't naturally a proportional breakdown.

- **Stat row** above the timeline: Planned / In progress / Done counts + total cost — the same numbers `HomeWorksWidget.svelte` already computes.
- **Axis**: continuous linear date scale from the earliest to the latest work's `date` field (with small padding on each end), *not* a fixed 10-slot window like Costs' bar chart — Works history length is unbounded, unlike Costs' fixed 10-year view. Year gridlines and labels drawn along the bottom. If all works fall within a single year, still show that year's gridline plus month ticks so the axis isn't empty of context.
- **Markers**: one dot per `Work`, positioned at its `date`. Colored using the exact same `statusColor()` function `WorksPage.svelte:65-69` already defines (done=`#33aa66`, in_progress=`#3388cc`, planned=`#cc8833`) — reusing the page's own status colors rather than the dashboard widget's (which use different CSS variables), since the timeline lives on the same page as the status-colored table badges and should match those, not the dashboard.
- **Collision handling**: dots within a small pixel distance on the x-axis get staggered vertically (alternating above/below the center line, growing outward per collision) — the same "declutter while preserving order" approach already built for the donut chart's connector labels (`DonutChart.svelte`'s `declutter()` function), applied here on one axis instead of two per side.
- **"Today" marker**: dashed vertical line at the current date.
- **Interaction**: clicking a dot calls an `onworkclick(id)` callback prop; `WorksPage.svelte` wires this to `modalWork = <that work>`, the same state variable its existing `rowClick` already sets — clicking a dot opens the identical edit modal a table-row click opens today.
- **No permanent per-dot text labels** — avoids reintroducing a label-collision problem. A small status-color legend (Done/In progress/Planned swatches) sits below the chart. Each dot gets a native SVG `<title>` child (title/date/cost) for a free hover tooltip, no new UI chrome.
- **Empty state**: 0 or 1 works — still render the axis with whatever gridlines apply; no special-cased empty message beyond what `WorksPage` already shows when there are zero works at all (existing behavior for the table already covers the true-empty case).

## Testing

- **Component tests** for `WorksTimeline.svelte` (new): renders one dot per work; buckets/stagger logic doesn't crash on 0, 1, or many same-date works; clicking a dot fires `onworkclick` with the right id; today-line renders.
- **Component tests** for each page's new summary-card `$derived` bucketing logic (Chores schedule-health buckets, Inventory category counts, Consumables stock-status buckets) — verifying counts match expectations against a small fixture set, following the existing pattern of `CostsPage.test.ts`'s breakdown assertions.
- **Regression**: existing per-page tests (toolbar filters, row click-to-open, table content) continue passing unchanged, since toolbar/table/footer markup isn't touched — only re-wrapped.
- **Browser smoke check** (webapp-testing): verify each page's new top card renders correctly against demo-home data, and confirm the Works timeline's dot click opens the edit modal.

## Risks / open questions carried into planning

- Whether the Chores donut should be clickable-to-filter (nice-to-have, not required) — left for the plan to size and decide, not a blocking design question.
- Real-world category counts for Inventory could exceed the demo's 8 — the donut's decluttering has no hard upper bound, but very large category counts (15+) would produce a busy chart; not addressing this now since it's outside observed data.
