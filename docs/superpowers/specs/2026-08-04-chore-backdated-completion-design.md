# Chore backdated completion

**Date:** 2026-08-04
**Status:** Approved

## Problem

Chores can only be marked complete "now" — the completion endpoint hardcodes
`datetime.now(timezone.utc)` as the completion timestamp. If a user actually
did the chore yesterday (or earlier) but forgot to check it off, there's no
way to log it retroactively; marking it done today either misrepresents when
it happened, or the user skips logging it at all, which throws off adaptive
scheduling averages and history accuracy.

## Goal

Let a user complete a chore (or an assignment) with a backdated completion
date, so it's recorded accurately in history and — if it represents the most
recent completion for that chore — correctly reschedules the next due date.

## Design

### 1. Backend request shape

`CompleteRequest` (`packages/backend/src/myhome/models_chores.py`) gains an
optional field:

```python
class CompleteRequest(BaseModel):
    notes: str = ""
    completedOn: str | None = None  # ISO date, YYYY-MM-DD
```

Both `POST /api/homes/{home_id}/chores/{chore_id}/complete` and
`POST /api/homes/{home_id}/assignments/{assignment_id}/complete`
(`packages/backend/src/myhome/routes/chores.py`) accept it. If omitted,
behavior is exactly as today (uses "now"). If provided and the date is in
the future (relative to the server's current UTC date), the request is
rejected with 400.

### 2. Timestamp construction

When `completedOn` is given, the new `CompletionRecord.completedAt` is built
by taking the current UTC instant and replacing its calendar date with the
picked date, keeping the same time-of-day:

```python
now = datetime.now(timezone.utc)
completed_at = now.replace(year=picked.year, month=picked.month, day=picked.day)
```

This avoids pinning to a fixed time like midnight or noon (which risks
timezone-boundary surprises when compared against other completions) while
still producing a sensible, orderable timestamp.

### 3. Next-due / recurrence rule

After appending the new `CompletionRecord` to the chore's completion list,
compare its `completedAt` against every other existing completion for that
chore (`completions_for_chore`, as already loaded in the handler):

- **If the new completion is the most recent one** (later than all others),
  proceed exactly as the endpoint does today: call
  `next_due_from_schedule(chore, from_dt, completions_for_chore)` using the
  new completion's `completedAt` as `from_dt`, updating `chore.nextDueDate`
  (and, for `frequencyType == "adaptive"`, `chore.periodDays`).
- **If a more recent completion already exists**, skip the recompute
  entirely. `nextDueDate` and `periodDays` are left untouched. The backdated
  record is added purely as a history entry.

This keeps the mental model simple and predictable: the schedule always
reflects the actual most recent known completion, and logging an
older-than-latest completion never perturbs it. This mirrors the existing
Donetick import path, which also appends historical `CompletionRecord`s
without recomputing scheduling.

As today, if `chore.scheduleFromDue` is `true`, next-due is driven by
`chore.nextDueDate` regardless of completion timestamps, so backdating has no
scheduling effect in that mode either way — only the history entry is added.

### 4. Frontend

`ChoreRow.svelte`'s existing mark-done expansion (notes input + confirm
button) gains a `DatePicker` next to the notes input:

- Defaults to today.
- Max selectable date is today (no future dates).
- Reuses the `DatePicker.svelte` component already used elsewhere in
  `ChoreEditModal.svelte`.

`choreStore.svelte.ts`'s `completeAssignment(id, notes)` and
`completeChore(id, notes)` gain a third optional parameter,
`completedOn?: string`. The `POST` payload includes `completedOn` only when
the picked date differs from today, so the common "complete now" path's
request body is unchanged from today.

### 5. i18n

New keys added to `en.json` and `fr.json` (matching the existing
`chores.row.*` key group), e.g. a label for the date field in the mark-done
expansion. No new NL locale file exists in the repo currently, so none is
added here.

### 6. Out of scope

- Editing the `completedAt` of an *already-logged* completion record (the
  History tab's delete-only action is unchanged).
- Any change to the Donetick import path, which already sets arbitrary
  historical timestamps and already skips recompute.

## Testing

- Backend: completing with no `completedOn` behaves identically to today
  (regression). Completing with a past `completedOn` that is the latest
  completion updates `nextDueDate`/`periodDays`. Completing with a past
  `completedOn` older than an existing completion leaves `nextDueDate`/
  `periodDays` unchanged but still inserts the history record. Future-dated
  `completedOn` is rejected with 400. Same coverage for the assignment
  endpoint.
- Frontend: date picker renders, defaults to today, rejects future dates;
  `completeAssignment`/`completeChore` omit `completedOn` when it equals
  today and include it otherwise.
