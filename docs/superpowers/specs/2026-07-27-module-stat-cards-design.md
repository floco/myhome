# Module Overview Stat Cards — Design Spec

Date: 2026-07-27

## Problem

Every module page's overview/summary section currently packs its stats
("Active: 12", "Overdue: 3", "Total Value: 4,200 €", ...) as small
`.stat-chip` divs inside one shared `Card`, often alongside a chart. This
reads as one dense block rather than a set of distinct, scannable facts.
The Build module already does it differently — one boxed `Card` per stat,
in a row — and that's the layout the rest of the app should adopt.

## Goals

- Every module's overview stats render as individual `Card`-backed tiles
  (via the existing but currently near-unused `StatTile.svelte`), not
  `.stat-chip` divs merged into one card.
- Where a module also shows a chart, the chart stays in its own card,
  separate from the stat tiles.
- Fix a real bug found while surveying the current code: Chores'
  overdue/on-track colors and Consumables' low/empty colors are hardcoded
  hex (`#f44336`, `#4caf50`, `#ff9800`) that don't adapt between light and
  dark theme, unlike the rest of the app's `--danger`/`--success`/
  `--warning` tokens. Moving these onto `StatTile` fixes this as a side
  effect of the conversion, not a separate task.
- Preserve every existing stat, value, and piece of conditional styling —
  this is a layout refactor, not a change in what data is shown.

## Non-goals

- No change to chart components themselves (`DonutChart`,
  `HorizontalBarChart`, `WorksTimeline`, Costs' custom bar chart).
- No change to table/list sections below the overview, or to empty-state
  markup (`.empty-charts`).
- KB module stays out of scope (no overview/summary section exists there,
  consistent with the prior module-summary-cards effort's decision).
- No new i18n keys — every stat's label already has a translation key from
  the current `.stat-chip` markup; the conversion reuses them verbatim.

## Architecture

Two shared-component changes, then nine per-page conversions:

1. **`StatTile.svelte`** gains two new optional props: `variant` (color)
   and `valueContent` (rich content override), both backward compatible —
   existing usage (`CostsCategoryModal.svelte`) needs no changes.
2. **New `StatTileRow.svelte`** — a thin wrapper providing the responsive
   grid CSS, so it isn't copy-pasted into nine files. Takes children only.
3. Each of the 9 pages (Build, Contacts, Properties, Chores, Inventory,
   Consumables, Insurance, Works, Costs) replaces its `.stat-chip`/
   hand-rolled-`Card` markup with `<StatTileRow>` wrapping one `StatTile`
   per stat, in the same order as today. Pages with a chart keep the chart
   in its own `Card`, now holding only the chart (plus its `chart-label`).

## `StatTile.svelte` changes

```svelte
<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    value: string | number;
    label: string;
    variant?: "success" | "danger" | "warning";
    valueContent?: Snippet;
  }
  let { value, label, variant, valueContent }: Props = $props();
</script>

<div class="ui-card ui-stat-tile">
  <div class="ui-stat-value" class:success={variant === "success"} class:danger={variant === "danger"} class:warning={variant === "warning"}>
    {#if valueContent}{@render valueContent()}{:else}{value}{/if}
  </div>
  <div class="ui-stat-label">{label}</div>
</div>

<style>
  /* existing .ui-stat-tile / .ui-stat-label rules unchanged */
  .ui-stat-value.success { color: var(--success); }
  .ui-stat-value.danger { color: var(--danger); }
  .ui-stat-value.warning { color: var(--warning); }
</style>
```

`value` stays required even when `valueContent` is passed, so plain-text
consumers (screen readers reading a stray `{value}` interpolation, tests
asserting on text content) still see something meaningful — call sites
that use `valueContent` pass the same information as `value` in plain-text
form as a fallback/accessible label.

## `StatTileRow.svelte` (new)

```svelte
<script lang="ts">
  import type { Snippet } from "svelte";
  interface Props { children: Snippet }
  let { children }: Props = $props();
</script>

<div class="ui-stat-row">
  {@render children()}
</div>

<style>
  .ui-stat-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: var(--space-3);
  }
</style>
```

`auto-fit`/`minmax` (rather than Build's current hardcoded
`repeat(5, 1fr)`) handles every module's stat count without a breakpoint
per module — from Costs' 2 stats up to Contacts' dynamic per-type count.
This also replaces Build's existing `@media (max-width: 900px)` override,
which becomes unnecessary.

## Per-module conversion

For each page, the `{#if ...}...{:else}...{/if}` empty-state branch is
untouched; only the non-empty branch's markup changes.

**No chart (stats-only row):**
- **Build**: `<StatTileRow>` with 5 `StatTile`s (status, current phase, %
  complete, planned budget, actual cost), replacing the current
  `.stat-row` of hand-rolled `Card`s. The `.stat-row-wrap`/`.stat-row`/
  `.stat-title`/`.stat-value` CSS rules are deleted from `BuildPage.svelte`.
  **Visible change:** Build's current markup puts the title above the
  value; `StatTile` puts the value above the label (matching its existing
  use in `CostsCategoryModal.svelte`). Standardizing on `StatTile`'s order
  is the point of sharing one component, so this flips for Build. This is
  the one place where the conversion isn't purely internal — call it out,
  don't silently override the standing test for it (see Testing below).
- **Contacts**: `<StatTileRow>` with one `StatTile` per
  `settingsStore.contactTypes` entry (`value={typeCounts.get(t.id) ?? 0}`,
  `label={t.name}`), replacing `.stat-chips-row` inside the chart card —
  and since Contacts has no chart, the wrapping `Card`/`chart-card-wrap`
  goes away entirely in favor of the bare `StatTileRow`.
- **Properties**: `<StatTileRow>` with 6 `StatTile`s (watching, visited,
  proposal made, purchased, rejected, total), same treatment — no chart,
  so the `Card` wrapper is dropped in favor of the bare `StatTileRow`.

**Chart + stats (chart card and stat row become siblings):**
- **Chores**: chart `Card` keeps `HorizontalBarChart` only. New
  `<StatTileRow>` (outside/after that card) with 3 `StatTile`s: Active
  (`variant` none), Overdue (`variant="danger"`), On Track %
  (`variant="success"`).
- **Inventory**: chart `Card` keeps `DonutChart` only. New
  `<StatTileRow>` with 2 `StatTile`s: Items, Total Value.
- **Consumables**: chart `Card` keeps `HorizontalBarChart` only. New
  `<StatTileRow>` with 2 `StatTile`s: Low (`variant="warning"`), Empty
  (`variant="danger"`).
- **Insurance**: chart `Card` keeps `DonutChart` only. New
  `<StatTileRow>` with 2 `StatTile`s: Policies, Annual Cost.
- **Works**: chart `Card` keeps `WorksTimeline` (and its `chart-label`)
  only. New `<StatTileRow>` with 4 `StatTile`s: Planned, In Progress,
  Done, Total Cost.
- **Costs**: chart `Card` is unchanged (still holds both the category
  `DonutChart` and the custom 10-year bar chart together, per the
  brainstorm decision to keep multi-chart cards intact). New
  `<StatTileRow>` with 2 `StatTile`s: 10yr Avg (plain `value`), Last
  Complete Year (uses `valueContent` to render the existing
  `{amount} € <span class="yoy">...</span>` markup with its up/down
  arrow and conditional color, since that's richer than a plain string).

In every "chart + stats" case, the new `<StatTileRow>` is placed as a
sibling block after the chart `Card`, not nested inside it — same visual
region of the page, same order (chart first, stats after), just no longer
inside the same box.

## Order and placement

Stat order within each row matches the current chip order exactly (see
per-module lists above) — this is a pure layout change, not a
re-prioritization of which numbers matter most.

## Testing

Existing component tests for these 9 pages already assert on visible text
(e.g. `target.textContent` containing a count or amount) — those
assertions keep passing unchanged since the values themselves don't move.
Two additions:
- `StatTile.svelte` gets new unit tests for `variant` (asserts the right
  CSS class is applied) and `valueContent` (asserts the snippet renders
  instead of the plain value).
- `StatTileRow.svelte` gets a minimal render test (renders its children).
- `ChoresPage.test.ts` (lines 131-132) and `ConsumablesPage.test.ts`
  (lines 183-184) assert directly on the old selectors
  (`.stat-value.overdue`, `.stat-value.ontrack`, `.stat-value.low`,
  `.stat-value.empty`), which the new `StatTile`-based markup won't
  produce (`StatTile` renders `.ui-stat-value.danger` /
  `.ui-stat-value.success` / `.ui-stat-value.warning` instead). These four
  assertions must be updated to the new selectors as part of the Chores
  and Consumables conversion tasks, not left to break silently.
- `BuildPage.test.ts` has two assertions that must be updated in the Build
  conversion task: the `.stat-value` selector (line 61) becomes
  `.ui-stat-value`, and the "puts the card title above the value" test
  (lines 68-83) gets rewritten to assert the opposite order (value then
  label) — renamed to reflect what it now actually checks, not deleted,
  since the ordering is still a real invariant worth locking down.
- `InventoryPage.test.ts` line 38's `.stat-value` selector becomes
  `.ui-stat-value`; its `.chart-card-wrap svg path`/`.chart-card-wrap`
  assertions (lines 37, 54, 71) are unaffected since the chart stays
  inside `.chart-card-wrap`.
- `WorksPage.test.ts` line 65's `.chart-card-wrap circle` selector is
  unaffected for the same reason.

## Rollout

Nine independent per-page conversions plus the two shared-component
changes — eleven total units of work, each independently testable and
committable. No shared runtime state between pages, so ordering within
the implementation plan is not load-bearing (shared components first,
then pages in any order).
