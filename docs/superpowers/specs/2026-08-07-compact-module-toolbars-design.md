# Compact module toolbars + KPI rows

## Problem

On mobile, the toolbar above each module's table (search, filter dropdowns,
quick-filter toggle, add button) wraps onto multiple lines because every
control is shown inline at full width. Similarly, the KPI/stat row above the
table (chart + stat tiles) stacks every element onto its own line on narrow
screens, sometimes taking 4-5 lines before the table is even visible.

## Scope

All module list pages with this toolbar/KPI shape: Chores, Consumables,
Inventory, Works, Costs, Contacts, Properties, Insurance, Build.

## Design

### Toolbar

- `Button.svelte` gets an `iconOnly` prop: fixed square sizing, no text
  padding, still respects `variant`. Every module's Add button becomes an
  icon-only `＋` with `title`/`aria-label` carrying the existing i18n label.
- Every filter `<select>` (room, schedule, category, owner, store, status,
  year, type…) moves out of the toolbar and into a `Modal` opened by a new
  filter icon button. The bound state (`roomFilter`, `categoryFilter`, etc.)
  and filtering logic do not change — only where the controls render. The
  filter button shows a small badge dot when any filter is non-default.
- A quick binary toggle that's already icon-based (the ☰/⚠ "attention"
  toggle in Chores/Consumables) stays inline next to search — it's a single
  frequently-used control, not a list of options, so it doesn't move into
  the modal.
- Toolbar order becomes: `[search input] [filter icon (+badge)] [attention
  toggle if present] [add icon]` — fits on one line at any supported width.
- Applied uniformly even to modules with only one filter (Contacts, Insurance)
  so every module has the same toolbar shape.

### KPI row

- Chores/Consumables (chart + loose `StatTile`s as flex siblings): wrap the
  stat tiles in their own flex container so on mobile the chart takes a full
  row and the tiles wrap together into a row beneath it (`flex-wrap: wrap`,
  ~100px min tile width) instead of one tile per line.
- Inventory/Insurance (chart + `StatTileRow direction="column"`) and Works
  (chart + two `StatTileRow direction="column"` groups): fix centrally in
  `StatTileRow.svelte` by adding a `max-width: 700px` breakpoint that makes
  the `column` variant wrap like the `row` variant instead of stacking
  vertically.
- Costs (custom bar chart + `.stats-under-bar`): same idea — the two stat
  tiles wrap onto one row on mobile instead of stacking.
- Properties/Contacts/Build (`StatTileRow direction="row"`, no chart):
  already wraps via CSS grid; tighten `minmax(140px, 1fr)` to
  `minmax(110px, 1fr)` so more tiles fit per row on narrow phones.

### Testing

Existing component tests that query filter selects directly (without opening
the modal first) will need updating to open the filter modal before
interacting with those controls. Filtering behavior itself is unchanged.

## Out of scope

- KB module (no toolbar/KPI row of this shape).
- Changing what each module filters by, or default filter values.
- New icon library — the funnel/filter icon is a small inline SVG using
  `currentColor`, consistent with the app's existing use of visual glyphs
  and to keep it crisp in both themes (Unicode filter glyphs render
  inconsistently across platforms).
