# Chores module fixes — design

Date: 2026-08-10

## Summary

Four independent fixes/small features in the Chores module:

1. **History room mislabeling** — "mark all done" flows record completions with no room, always falling back to "toute la maison" (whole house).
2. **Planning column mislabeling** — month-restricted `day_of_the_month` schedules are mislabeled "Monthly".
3. **KPI/graph click-to-filter** — stat tiles and the health bar chart are currently inert; clicking should filter and highlight, click again to clear.
4. **Per-assignment custom label** — lets a user distinguish multiple assignments of the same chore in the same room (e.g. two windows in the same living room).

Backend touched only by #1 and #4 (`packages/backend/src/myhome/models_chores.py`, `routes/chores.py`). #2 and #3 are frontend-only (`packages/editor`).

## 1. History room mislabeling

**Root cause:** `POST /chores/{chore_id}/complete` (`routes/chores.py`, used by both `ChoresPage.svelte`'s "Mark all done" row action and `BadgePopup.svelte`'s "✓ All done" floor-plan action, via `choreStore.completeChore()`) creates a single `CompletionRecord` with `assignmentId = None`. The history view's `getRoomName()` (`ChoreEditModal.svelte`) resolves room via `assignmentId → Assignment.roomId`, so a `null` `assignmentId` always falls back to the whole-house label — even for a chore with exactly one specific-room assignment.

**Fix:** change `POST /chores/{chore_id}/complete` to fetch all assignments for the chore and create one `CompletionRecord` per assignment, each with that assignment's `id` set as `assignmentId`. A chore with one room assignment gets one record tagged with that room; a chore with assignments in both the living room and bedroom gets two records, one per room. A whole-house assignment (`roomId = null`) still correctly produces a record that resolves to "toute la maison" — that fallback path is legitimate and unchanged.

No frontend change needed: `getRoomName()` already does the right lookup once records carry a real `assignmentId`.

Any existing side effects of chore-level completion (next-due-date recalculation, streak tracking, etc.) are preserved — this only changes how many `CompletionRecord`s are written and what each one is tagged with, not the completion/scheduling logic itself.

## 2. Planning column mislabeling

**Root cause:** `scheduleLabel()` (`packages/editor/src/lib/choreStore.svelte.ts`) always renders `day_of_the_month` schedules as "Monthly on day {n}" (i18n `chores.schedule.monthlyOnDay`), ignoring `frequencyMetadata.months` — the month-restriction array that `ScheduleEditor.svelte` already lets users set (e.g. `{ months: [8] }` for "August only"). The backend scheduler (`chore_scheduling.py`) already honors this restriction correctly; only the label is wrong.

**Fix:** in the `day_of_the_month` branch of `scheduleLabel()`, check `frequencyMetadata.months`:
- Absent or empty → unchanged: "Monthly on day {n}".
- Restricted to specific month(s) → drop "Monthly" and show the day plus month name(s), e.g. "On day 20 (August)" for one month, or "On day 20 (Jan, Apr, Jul, Oct)" for several. Month names formatted the same way `ScheduleEditor.svelte` already formats them (short `Intl.DateTimeFormat` month names) for consistency.

New i18n keys under `chores.schedule.*` in both `en.json` and `fr.json` (e.g. `dayOfMonthRestricted`, taking `{n}` and a pre-joined month-list string).

Out of scope: no change to any other `frequencyType` branch (weekly, interval, adaptive, days-of-week) — they already convey their cadence clearly and don't reference a month.

## 3. KPI/graph click-to-filter

**Current state:** `ChoresPage.svelte`'s summary section has 3 `StatTile`s (Active / Overdue % / On track %) and a `HorizontalBarChart` with 3 health-bucket segments (on-track / due-soon / overdue). Neither component exposes a click handler today. Existing list filters (`searchQuery`, `roomFilter`, `scheduleFilter`, `dueFilter`) live as local `$state` in `ChoresPage.svelte` and are AND-combined in `filteredChores`.

**Fix:**
- Add an `onsegmentclick?: (bucket: HealthBucket) => void` prop to `HorizontalBarChart.svelte`, mirroring the existing `onsliceclick` pattern already used by `DonutChart.svelte` in Costs.
- Add an optional `onclick?: () => void` prop to `StatTile.svelte`.
- New state in `ChoresPage.svelte`: `let healthFilter = $state<HealthBucket | null>(null)`.
- Wiring:
  - "Overdue %" tile → sets `healthFilter = "overdue"` (or clears if already active).
  - "On track %" tile → sets `healthFilter = "on-track"` (or clears if already active).
  - Bar chart segments → same toggle behavior for all three buckets (`on-track` / `due-soon` / `overdue`) — this is the only way to filter by `due-soon`, since there's no tile for it.
  - "Active" tile → always clears `healthFilter` (it has no matching bucket; it represents the unfiltered total).
- `filteredChores`'s predicate gains a `healthFilter === null || healthBucket(...) === healthFilter` clause, AND-combined with the existing filters, following the same pattern as `roomFilter`/`scheduleFilter`.
- Visual highlight: the active tile gets a highlighted/selected CSS state (border or background, consistent with existing selected-state styling elsewhere in the app); the active bar segment gets a visually emphasized stroke/opacity treatment. Clicking the already-active tile/segment again clears `healthFilter` and removes the highlight.

## 4. Per-assignment custom label

**Motivation:** a chore can have multiple assignments in the same room (e.g. "clean window" placed twice in the living room for two different windows). Today both pins/rows are indistinguishable beyond the chore's own name.

**Fix:**
- Backend: add `label: str | None = None` to `Assignment` (`models_chores.py`), and the matching TS field on the `Assignment` interface (`choreStore.svelte.ts`). Persisted through the existing `PUT /assignments/{id}` endpoint (already used for `position`/`roomId` updates) — no new endpoint needed.
- Editable from:
  - `BadgePopup.svelte` (floor-plan pin popup) — a small inline text field for the label.
  - `ChoreEditModal.svelte`'s existing assignment list — the label field is added alongside the room/position info already shown per assignment there; no other change to that tab.
- Displayed in:
  - `BadgePopup.svelte`'s detail view, when set.
  - History entries (`ChoreEditModal.svelte`'s history tab, via `getRoomName()`'s call site): when the assignment has a label, append it to the room text, e.g. "Living room — Window 1"; when unset, unchanged room-only text ("Living room").

Out of scope: no visible always-on text tag rendered directly on the floor-plan badge/pin icon itself (`ChoreOverlay.svelte`) — the label is only shown in the popup detail, matching what was asked for.

## Testing

- **#1**: backend test for `POST /chores/{chore_id}/complete` asserting one `CompletionRecord` per assignment with correct `assignmentId`s (single-assignment and multi-assignment cases), plus a frontend/history-rendering check that room names now resolve correctly for chore-level completions.
- **#2**: unit tests for `scheduleLabel()` covering unrestricted `day_of_the_month`, single-month restriction, and multi-month restriction.
- **#3**: `ChoresPage.svelte` tests for: clicking each tile/segment sets `healthFilter` and narrows `filteredChores`; clicking the active one again clears it; "Active" tile always clears; filter combines correctly with existing `roomFilter`/`scheduleFilter`/`dueFilter`/`searchQuery`.
- **#4**: backend test for persisting/reading `Assignment.label`; frontend tests for editing the label in `BadgePopup` and `ChoreEditModal`, and for the label appearing in history entries when set.
