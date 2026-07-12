# Sortable Tables — Design

## Problem

None of the app's 11 `<table>` instances support click-to-sort. Columns are hardcoded per-page with raw `<table>/<thead>/<tbody>` markup, duplicated across Inventory, Works, Consumables, Chores, Costs, and several Settings sub-pages. Users want to click a column header to sort by that column, consistently across the app.

## Scope

**In scope** — 9 table instances across 8 files, migrated to a new shared component:

- `InventoryPage.svelte`
- `WorksPage.svelte`
- `ConsumablesPage.svelte`
- `ChoresPage.svelte`
- `CostsPage.svelte`
- `settings/SettingsCategories.svelte` (5 tab-switched tables: Cost/Inventory/Work categories, Suppliers, Consumable categories — same pattern, all migrated together)
- `settings/SettingsSecurity.svelte` (API Tokens, Users — 2 tables)
- `settings/SettingsBackup.svelte` (Scheduled Backups)

**Out of scope**:
- `settings/SettingsActivityLog.svelte` — server-side paginated; sorting only the currently-loaded page would be misleading, so it's left as-is.
- KB module — no `<table>` element exists there (cards/list UI).

## Architecture

### `SortableTable.svelte`

New shared component in `packages/editor/src/lib/components/ui/SortableTable.svelte`, following the existing pattern of shared UI components (`Button`, `Modal`, `Input`, `Card`, `StatTile`, `Tabs`, `Badge`, `Panel`) in that directory.

It renders the full `<table>/<thead>/<tbody>` — pages no longer hand-write table markup. It owns sort state internally and renders sorted rows via caller-supplied column definitions.

```ts
type Column<T> = {
  key: string;                    // stable id; used for sort state + aria-sort
  label: string;                  // header text
  sortable?: boolean;             // default true
  sortValue?: (row: T) => string | number | Date | null | undefined; // defaults to (row as any)[key]
  cell?: Snippet<[T]>;            // custom cell render; defaults to text of sortValue()
  align?: 'left' | 'right' | 'center';
};
```

Props:
- `columns: Column<T>[]`
- `rows: T[]` — already filtered by the page (filtering stays page-owned, as today)
- `rowClick?: (row: T) => void` — preserves existing click-to-open row behavior
- `defaultSort?: { key: string; direction: 'asc' | 'desc' }` — optional; if omitted, table starts in natural (incoming array) order until the user clicks a header
- `rowKey?: (row: T) => string | number` — for Svelte `{#each}` keying; defaults to array index

### `createSortState` helper

Headless, rune-based helper in `packages/editor/src/lib/utils/sortState.svelte.ts`, used internally by `SortableTable` and unit-testable independent of markup. Owns:
- Current `{ key, direction } | null` state
- `toggle(key)` — cycles asc → desc → unsorted (null) for the given key; switching to a different key resets to asc
- `sortRows(rows, columns)` — returns the sorted array (or the original array, unmodified order, when state is null)

## Sort Behavior & Comparison

- **Single active sort column** at a time. Header click cycles: unsorted → asc → desc → unsorted. Clicking a different sortable header switches immediately to ascending on that column.
- **Visual indicator**: ▲/▼ arrow next to the label on the active column. Sortable headers render as a `<button>` inside the `<th>` (keyboard/focus accessible) with `aria-sort` (`ascending` | `descending` | `none`) set on the `<th>`.
- **Type-aware comparison**: `sortValue()` result is compared by runtime type — numbers numerically, `Date` by timestamp, strings via `localeCompare` (case-insensitive).
- **Nulls-last**: `null`/`undefined` values always sort to the end, regardless of direction.
- **Non-sortable columns** (`sortable: false`, e.g. an actions/icon column): render as plain `<th>` text — no button, no cursor pointer, no arrow.

## Migration Notes

Each of the 8 files replaces its inline `<table>` markup with `<SortableTable columns={...} rows={...} />`, moving custom cell markup (badges, currency formatting, emoji, edit/delete buttons) into `cell` snippets on the relevant columns. Row click-to-open behavior (where present) moves to the `rowClick` prop. Filtering/search logic already living in each page's `$derived` stays unchanged — `SortableTable` only receives the already-filtered array.

## Testing

- **Unit tests** (`sortState.svelte.ts`): tri-state cycling, type-aware comparison per type, nulls-last, switching active column resets to asc.
- **Component tests** (`SortableTable.svelte`): header click sorts rows; `aria-sort` updates correctly; non-sortable columns have no click behavior; custom `cell` snippets render as supplied; `rowClick` fires on row click. Per this repo's known Svelte 5 + jsdom gotcha, test components must be attached to `document.body` and dispatched events need `bubbles: true`, or handlers silently never fire.
- **Regression**: existing per-page tests (row content, actions, click-to-open) continue passing after each page is re-pointed at `SortableTable`.
- **Browser smoke check** (webapp-testing): manually verify click-to-sort on at least one main-module table (e.g. Inventory) and one Settings table, confirming existing row actions still work post-migration.
