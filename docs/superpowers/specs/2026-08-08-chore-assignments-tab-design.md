# Chore assignments tab + multi-assignment labels

**Date:** 2026-08-08
**Status:** Approved

## Problem

Room assignments for a chore currently live in an expandable row (▶/▼) in
`ChoresPage.svelte`'s table, with per-assignment complete/delay/delete
actions inline. This was already a source of friction (it's what the
mobile-horizontal-scroll fix in commit `3833d18` had to work around) and
it's a second, separate place — beside the chore edit modal — where a user
manages a chore. The user wants assignment management consolidated into a
tab of the existing `ChoreEditModal`.

Separately, a chore can already be assigned to the same room more than once
(no uniqueness constraint on `(choreId, roomId)`), which is a real and
intentional case — e.g. "water plants" needing to happen at two spots in the
same room, possibly at different times but the same frequency. There is
currently no way to tell two such assignments apart: no label, no name,
nothing but `id`.

## Goal

- Move per-chore room-assignment management (view, complete, delay, delete,
  and now create) into a new "Assignments" tab inside `ChoreEditModal`.
- Remove the expand-triangle / expanded-row UI from `ChoresPage.svelte`.
- Add an optional label to `Assignment` so duplicate assignments to the same
  room can be told apart.
- Fix a related History tab correctness gap and surface the label there too.

## Design

### 1. Data model — `Assignment.label`

Backend (`packages/backend/src/myhome/models_chores.py`):

```python
class Assignment(BaseModel):
    id: str
    choreId: str
    roomId: str | None = None
    position: Position | None = None
    nextDueDate: str = ""
    label: str | None = None
```

Frontend mirror in `choreStore.svelte.ts` gets the same optional `label?:
string | null`. `AssignmentCreate` and `AssignmentUpdate` request models both
gain optional `label`, so it can be set on creation and edited later via the
existing `PUT /api/homes/{home_id}/assignments/{assignment_id}`. No DB
migration is needed — these are JSON documents; existing assignments simply
read back with `label: None`.

No uniqueness constraint is added on `(choreId, roomId)` — duplicates remain
allowed and are now a supported, intentional case rather than an unlabeled
side effect.

### 2. `ChoresPage.svelte` — remove expand UI

Delete the `expandCell` snippet, the ▶/▼ toggle, `expandedHistory` state, and
the `assignmentsExpanded` snippet (currently lines ~252-295). Row click
continues to open `ChoreEditModal` as it does today. The row-level ✓ "mark
all done" action (completes the chore + all its assignments at once) is
unaffected and stays in the table row.

### 3. `ChoreEditModal.svelte` — new "Assignments" tab

Added to the existing `Tabs.svelte`-driven tab bar (`info` / **`assignments`**
/ `media` / `history`), positioned right after `info`.

**Assignment list**, one row per `Assignment` for this chore:
- Room name (via existing `getRoomName`/room lookup) plus the `label`, if
  set, shown alongside it (e.g. muted text in parentheses).
- Due date (`nextDueDate`).
- Inline-editable label `Input`: blank by default, saves on blur/change via
  `updateAssignment` (extending the existing `updateAssignmentPosition`-style
  PUT call to also send `label`).
- Same per-row actions as today's expanded row: ✓ complete (opens the
  existing `ChoreCompleteModal`, unchanged), ⏭ delay-by-week, ✕ delete.

**Add-assignment control** below the list:
- A room `<select>` listing all rooms in the home (duplicates of
  already-assigned rooms allowed, no warning — this is the supported
  multi-assignment case).
- An optional label `Input`.
- "Add" `Button`, calling a new/extended `createAssignment(choreId, roomId,
  label?)` store method.

### 4. Pin placement for tab-created assignments

Assignments created via drag-and-drop onto the floor plan keep their exact
drop position, unchanged. Assignments created from the new tab control have
no drag position, so `position` is computed as the target room's polygon
centroid using `polygonCentroid(room.polygon)` (from `@myhome/geometry`,
currently only used in `RoomShape.svelte` for label placement). This makes
the new assignment immediately visible as a pin at the room's center; the
user can still drag it to reposition. If the room has no polygon,
`position` falls back to `null` (same as an "unassigned" assignment today).

### 5. History tab fixes

While relocating the label to be visible everywhere an assignment appears,
two related issues in the existing History tab
(`ChoreEditModal.svelte:198-206`) are fixed:

- **Ordering**: `history` is currently computed as
  `store.getCompletionsForChore(chore.id).slice().reverse()` — a naive
  reversal of fetch/insertion order, not an explicit sort. Since backdated
  completion (`completedOn`) was added, a backdated record can be inserted
  out of chronological order and this reversal no longer guarantees
  most-recent-first. Change this to an explicit sort:
  `.slice().sort((a, b) => b.completedAt.localeCompare(a.completedAt))`
  (ISO 8601 timestamps sort lexicographically), so history is always
  correctly ordered most-recent-first regardless of insertion order.
- **Label display**: each history row's room span (`getRoomName(rec
  .assignmentId)`) also shows the assignment's `label`, if set, the same way
  the Assignments tab does.
- **Date formatting**: switch from `formatDateTime(rec.completedAt)` to
  `formatDate(rec.completedAt)` — history rows show only the completion
  date, not the time of day.

### 6. i18n

New keys added to `en.json` and `fr.json` for: the "Assignments" tab label,
the label input's placeholder, and the add-assignment control's texts
(room select placeholder, "Add" button). Matches the existing
`chores.editModal.*` key group.

### 7. Out of scope

- Any change to how `ChoreCompleteModal` works — it stays assignment-agnostic.
- A warning/confirmation when adding a duplicate-room assignment (explicitly
  decided against — duplicates are a normal case now).
- Editing an assignment's room after creation (delete + re-add covers this;
  no "move to a different room" control).

## Testing

- Backend: `Assignment.label` round-trips through create (`POST
  /assignments`) and update (`PUT /assignments/{id}`); omitting it leaves it
  `None`; existing assignments without the field still deserialize.
- Frontend:
  - `ChoresPage.svelte` no longer renders any expand/assignment UI; row click
    still opens `ChoreEditModal`.
  - `ChoreEditModal`'s Assignments tab renders existing assignments with
    labels, supports add/edit-label/delay/delete/complete.
  - Adding an assignment from the tab computes position via
    `polygonCentroid` when the room has a polygon, and `null` otherwise.
  - History tab: completions render sorted by `completedAt` descending even
    when a backdated completion is inserted out of order; each row shows the
    assignment's label when set; dates render without time-of-day.
