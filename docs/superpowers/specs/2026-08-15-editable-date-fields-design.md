# Editable Date Fields with Year-Jump Picker

Date: 2026-08-15

## Problem

`DatePicker.svelte` (`packages/editor/src/lib/components/DatePicker.svelte`) is the shared
date-entry component used across most domain modals (chores, inventory, works, insurance,
costs). Its trigger is a read-only display span — the only way to set a date is clicking
through the calendar popup, and the popup only supports prev/next **month** navigation. Jumping
from, say, today back to a birth year or an old purchase date takes hundreds of clicks.

Two other spots don't use `DatePicker` at all and fall back to the browser's native
`<input type="date">`, which is visually inconsistent with the rest of the app:
- `NewChoreModal.svelte:129`
- `SettingsActivityLog.svelte:90,94` (via the generic `ui/Input.svelte` with `type="date"`)

## Goals

- Every date field in the app supports both typing a date manually and picking it from a
  calendar.
- The calendar popup supports jumping quickly to a distant year, not just stepping by month.
- All date fields behave consistently (same component, same interaction pattern).

## Non-goals

- Adding a `min` prop or other new range-constraint features beyond the existing `max`.
- Changing the on-disk/API date format (still ISO `YYYY-MM-DD` via the bindable `value` prop).
- Redesigning the visual style of the calendar grid itself (colors/spacing stay on existing
  design tokens).

## Design

### 1. Field layout

The trigger changes from a read-only `div.dp-field` wrapping a display `<span>` to a two-part
layout: a real `<input type="text">` bound to the formatted display string, plus a small
calendar icon button that toggles the popup. The bindable `value` prop is unchanged — still an
ISO `YYYY-MM-DD` string; only the internal display/edit layer changes. `compact` mode keeps the
same two-part layout at reduced size/spacing. The `placeholder` and `max` props behave as today.

### 2. Typing and parsing

The text input shows the current `displayValue()` output (existing locale-aware formatter —
MDY/DMY/ISO/long-form depending on locale). Keystrokes are not parsed live. On blur or Enter,
the typed text is parsed against the same locale format used for display:

- If it parses to a valid calendar date within any existing `max` constraint, commit it: update
  `value`, emit the existing change event, and re-render the field with the freshly formatted
  string.
- If parsing fails (unparseable, invalid day-of-month, out-of-range against `max`, etc.), discard
  the typed text and revert the field to the last valid `displayValue()`. No inline error is
  shown.
- Escape while editing reverts the field to the last valid value without committing, same as a
  failed parse.

### 3. Calendar popup — year-grid navigation

Opening the popup via the calendar icon shows the existing day grid unchanged. The header (month
name + prev/next-month arrows) gains a click handler on the month/year label: clicking it swaps
the popup body into a year grid — a 4×3 grid of 12 years — with «/» arrows that page by decade.
Clicking a year in the grid returns to the day grid for that year, preserving the currently
selected month. This is implemented as a new local view state (`view: 'days' | 'years'`) plus
`selectYear` / `prevDecade` / `nextDecade` handlers, following the existing `selectDay` /
`prevMonth` / `nextMonth` pattern and reusing the same CSS custom properties
(`--surface`, `--surface-alt`, `--surface-hover`, `--border`, `--text`, `--text-muted`,
`--text-faint`, `--accent`, `--accent-contrast`, `--radius-md`, `--shadow-md`, `--font-sans`).

### 4. Structural cleanup

`DatePicker.svelte` moves from `packages/editor/src/lib/components/` into
`packages/editor/src/lib/components/ui/`, alongside the other generic reusable primitives
(`Input.svelte`, `Popover.svelte`, `Modal.svelte`, `Button.svelte`). Import paths are updated at
all current call sites: `ChoreCompleteModal.svelte`, `TaskModal.svelte`, `InventoryModal.svelte`,
`WorkModal.svelte`, `InsuranceModal.svelte`, `ChoreEditModal.svelte`, `CostsEntryModal.svelte`.

### 5. Migrating the stragglers

- `NewChoreModal.svelte:129` — replace the native `<input type="date" class="native-input">`
  with `DatePicker`, matching the pattern already used in `ChoreEditModal.svelte` for the same
  field.
- `SettingsActivityLog.svelte:90,94` — replace the two `<Input type="date">` filter fields
  ("from"/"to") with non-compact `DatePicker` instances, keeping the existing `placeholder` text.

### 6. Testing

Component tests for `DatePicker.svelte`:
- Typing a valid date string and blurring/pressing Enter commits the new value and emits change.
- Typing an invalid/unparseable string reverts to the last valid displayed value.
- Pressing Escape while editing reverts without committing.
- Clicking the year/month label switches to the year grid; clicking a year returns to the day
  grid for that year with the previously selected month preserved.
- Decade paging («/») moves the year grid by 10 years.
- Existing day-grid selection, `max` constraint, and `compact` styling tests continue to pass.

Update/add tests for the two migrated call sites (`NewChoreModal`, `SettingsActivityLog`) to
assert a `DatePicker` renders instead of a native `type="date"` input.

## Open questions

None — all decisions were resolved during brainstorming.
