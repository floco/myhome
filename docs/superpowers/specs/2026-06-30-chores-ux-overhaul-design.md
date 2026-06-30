# Chores UX Overhaul — Design Spec

**Date:** 2026-06-30

## Overview

Consolidate the two chores views into one, add per-row delay actions, default to a "Needs attention" filter, and make action buttons touch-friendly.

---

## 1. Routing consolidation

- `#/chores` renders `ChoresPage` directly (same component as `#/chores/manage`)
- `#/chores/manage` remains valid but is no longer the only path to the manage view
- `ChoreListPage` is removed from the router (file stays, becomes unused)
- The `{#if isChores}` topbar block in `App.svelte` (⚙ toggle + ＋ button) is removed entirely — ChoresPage has its own toolbar with ＋ Add chore

## 2. Needs-attention filter (default on)

A two-state toggle in the ChoresPage toolbar replaces no filter at all:

```
[All]  [⚠ Needs attention]   ← default
```

- **Needs attention**: chore has at least one assignment where `nextDueDate` is today or earlier, OR within the next 7 days. Chores with no assignments are excluded from this view.
- **All**: no filtering by due date (existing behaviour)
- Default state on mount: **Needs attention**
- Toggle sits between the schedule dropdown and the ＋ Add chore button

## 3. Delay-by-one-week action

### Backend

`AssignmentUpdate` model gains an optional field:

```python
class AssignmentUpdate(BaseModel):
    position: Position | None = None
    nextDueDate: str | None = None      # new
```

The `update_assignment` handler applies it when present:

```python
if body.nextDueDate is not None:
    assignment.nextDueDate = body.nextDueDate
```

### Store (`choreStore.svelte.ts`)

Two new methods exposed on the store:

```ts
// Delay a single assignment's nextDueDate by `days` days
async function delayAssignment(id: string, days: number): Promise<void>

// Delay all assignments for a chore
async function delayChore(choreId: string, days: number): Promise<void>
```

`delayAssignment` computes the new date from the assignment's current `nextDueDate` (falling back to today if empty), then PUTs `{ nextDueDate }` to `/api/assignments/:id`.

`delayChore` calls `delayAssignment` for every assignment whose `choreId` matches, in parallel.

### UI (ChoresPage)

- Chore row actions cell: ✓  🕐  ⏭  (delay button at chore level → `store.delayChore`)
- Expanded assignment rows: each gains its own ⏭ button → `store.delayAssignment`
- Delay always moves the date forward by 7 days
- No confirmation required — it's easily reversible

## 4. Bigger action buttons

All action buttons in the actions cell (`icon-btn` class) increase to:

```css
padding: 8px 14px;
font-size: 15px;
min-height: 38px;
```

This applies to ✓ complete, ✓ confirm, ✕ cancel, 🕐 history, and ⏭ delay.

---

## Files changed

| File | Change |
|---|---|
| `packages/backend/src/myhome/models_chores.py` | Add `nextDueDate` to `AssignmentUpdate` |
| `packages/backend/src/myhome/routes/chores.py` | Apply `nextDueDate` in `update_assignment` handler |
| `packages/editor/src/lib/choreStore.svelte.ts` | Add `delayAssignment`, `delayChore` |
| `packages/editor/src/App.svelte` | Merge routes; remove isChores topbar block |
| `packages/editor/src/lib/components/ChoresPage.svelte` | Add toggle, bigger buttons, delay actions |
| `packages/backend/tests/test_chores.py` | Test new `nextDueDate` update + delay scenario |

---

## Out of scope

- Removing `nextDueDate` from the `Chore` model (used as creation default — separate refactor)
- Any changes to ChoreListPage internals (it's just removed from routing)
