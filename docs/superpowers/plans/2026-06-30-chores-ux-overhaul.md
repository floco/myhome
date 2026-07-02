# Chores UX Overhaul — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge the two chores views into ChoresPage, remove redundant topbar buttons, add a "Needs attention" default filter, touch-friendly action buttons, and per-row delay-by-one-week.

**Architecture:** Backend gains a `nextDueDate` field on `AssignmentUpdate`; the store gains `delayAssignment` / `delayChore` helper methods. ChoresPage absorbs all routing and adds the toggle + delay buttons. App.svelte route block is simplified to a single branch for all `#/chores*` paths.

**Tech Stack:** SvelteKit 5 (runes), TypeScript, FastAPI/Python backend, Vitest (frontend tests), pytest (backend tests).

---

## File map

| File | What changes |
|---|---|
| `packages/backend/src/myhome/models_chores.py` | Add `nextDueDate: str | None = None` to `AssignmentUpdate` |
| `packages/backend/src/myhome/routes/chores.py` | Apply `nextDueDate` in `update_assignment` handler |
| `packages/backend/tests/test_chores.py` | Test `PUT /api/assignments/:id` with `nextDueDate` |
| `packages/editor/src/lib/choreStore.svelte.ts` | Add `delayAssignment`, `delayChore`; expose on return object |
| `packages/editor/src/App.svelte` | Merge `#/chores` + `#/chores/manage` to one branch; remove `{#if isChores}` topbar block; remove `ChoreListPage` import |
| `packages/editor/src/lib/components/ChoresPage.svelte` | Add `dueFilter` toggle (default `"attention"`), `needsAttention` helper, `⏭` delay buttons at chore + assignment level, bump `icon-btn` size |

---

### Task 1: Backend — allow updating `nextDueDate` via PUT /api/assignments/:id

**Files:**
- Modify: `packages/backend/src/myhome/models_chores.py` (AssignmentUpdate class, line ~81)
- Modify: `packages/backend/src/myhome/routes/chores.py` (update_assignment handler, line ~390)
- Test: `packages/backend/tests/test_chores.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_chores.py`:

```python
def test_update_assignment_next_due_date(client):
    chore_id = _chore_id(client)
    a_resp = client.post("/api/assignments", json={
        "choreId": chore_id, "nextDueDate": "2027-01-08T00:00:00Z"
    })
    assert a_resp.status_code == 201
    assignment_id = a_resp.json()["id"]

    resp = client.put(f"/api/assignments/{assignment_id}", json={"nextDueDate": "2027-01-15T00:00:00Z"})
    assert resp.status_code == 204

    doc = client.get("/api/chores").json()
    a = next(a for a in doc["assignments"] if a["id"] == assignment_id)
    assert a["nextDueDate"] == "2027-01-15T00:00:00Z"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd packages/backend && python -m pytest tests/test_chores.py::test_update_assignment_next_due_date -v
```

Expected: FAIL — `AssertionError` because `nextDueDate` is not updated (the field is not in the model yet).

- [ ] **Step 3: Add `nextDueDate` to `AssignmentUpdate`**

In `packages/backend/src/myhome/models_chores.py`, replace:

```python
class AssignmentUpdate(BaseModel):
    position: Position | None = None
```

with:

```python
class AssignmentUpdate(BaseModel):
    position: Position | None = None
    nextDueDate: str | None = None
```

- [ ] **Step 4: Apply `nextDueDate` in the handler**

In `packages/backend/src/myhome/routes/chores.py`, replace the `update_assignment` handler body:

```python
@router.put("/api/assignments/{assignment_id}", status_code=204)
def update_assignment(assignment_id: str, body: AssignmentUpdate) -> None:
    doc = load_chores()
    assignment = next((a for a in doc.assignments if a.id == assignment_id), None)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if body.position is not None:
        assignment.position = body.position
    if body.nextDueDate is not None:
        assignment.nextDueDate = body.nextDueDate
    save_chores(doc)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd packages/backend && python -m pytest tests/test_chores.py::test_update_assignment_next_due_date -v
```

Expected: PASS.

- [ ] **Step 6: Run full backend test suite**

```bash
cd packages/backend && python -m pytest -x -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add packages/backend/src/myhome/models_chores.py \
        packages/backend/src/myhome/routes/chores.py \
        packages/backend/tests/test_chores.py
git commit -m "feat(chores): allow updating assignment nextDueDate via PUT"
```

---

### Task 2: Store — add `delayAssignment` and `delayChore`

**Files:**
- Modify: `packages/editor/src/lib/choreStore.svelte.ts`

No dedicated frontend unit test is needed for these thin wrappers — they delegate to the same `PUT /api/assignments/:id` endpoint tested in Task 1. The integration will be exercised by the E2E behaviour in Task 4.

- [ ] **Step 1: Add `delayAssignment` after `updateAssignmentPosition`**

In `packages/editor/src/lib/choreStore.svelte.ts`, add after the `updateAssignmentPosition` function (before `deleteAssignment`):

```ts
  async function delayAssignment(id: string, days: number): Promise<void> {
    const assignment = assignments.find((a) => a.id === id);
    const base = assignment?.nextDueDate ? new Date(assignment.nextDueDate) : new Date();
    base.setDate(base.getDate() + days);
    const nextDueDate = base.toISOString();
    const resp = await fetch(`/api/assignments/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nextDueDate }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function delayChore(choreId: string, days: number): Promise<void> {
    const choreAssignments = assignments.filter((a) => a.choreId === choreId);
    await Promise.all(choreAssignments.map((a) => delayAssignment(a.id, days)));
  }
```

- [ ] **Step 2: Expose the new methods on the return object**

In the `return { ... }` block of `createChoreStore`, add `delayAssignment` and `delayChore`:

```ts
  return {
    get chores() { return chores as Chore[]; },
    get assignments() { return assignments as Assignment[]; },
    get completions() { return completions as CompletionRecord[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    getProgress,
    getColor,
    assignmentsForRoom,
    houseAssignments,
    getCompletionsForChore,
    uploadAttachment,
    deleteAttachment,
    createChore,
    updateChore,
    deleteChore,
    completeChore,
    importFromDonetick,
    createAssignment,
    completeAssignment,
    updateAssignmentPosition,
    deleteAssignment,
    delayAssignment,
    delayChore,
  };
```

- [ ] **Step 3: Type-check**

```bash
cd packages/editor && npx tsc --noEmit 2>&1 | grep -v "^test/"
```

Expected: no errors from `src/` files.

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/choreStore.svelte.ts
git commit -m "feat(chores): add delayAssignment and delayChore to store"
```

---

### Task 3: App.svelte — merge routes, remove redundant topbar buttons

**Files:**
- Modify: `packages/editor/src/App.svelte`

- [ ] **Step 1: Remove the `ChoreListPage` import**

Near the top of `packages/editor/src/App.svelte`, delete this line:

```ts
  import ChoreListPage from "./lib/components/ChoreListPage.svelte";
```

- [ ] **Step 2: Merge the two chores route branches into one**

Find:

```svelte
      {:else if currentRoute === "#/chores"}
        <ChoreListPage store={choreStore} {floorStore} />

      {:else if currentRoute === "#/chores/manage"}
        <ChoresPage store={choreStore} {floorStore} onnewchore={() => { showNewChoreModal = true; }} />
```

Replace with:

```svelte
      {:else if currentRoute === "#/chores" || currentRoute === "#/chores/manage"}
        <ChoresPage store={choreStore} {floorStore} onnewchore={() => { showNewChoreModal = true; }} />
```

- [ ] **Step 3: Remove the `{#if isChores}` topbar block**

Find and delete this entire block (it is inside the `<header>` element):

```svelte
    {#if isChores}
      {#if !isFloorPlan}<span class="spacer"></span>{/if}
      <a
        href={currentRoute === "#/chores/manage" ? "#/chores" : "#/chores/manage"}
        class="icon-btn"
        class:active={currentRoute === "#/chores/manage"}
        title="Chore settings"
      >⚙</a>
      <button
        class="icon-btn new-chore-btn"
        title="New chore"
        onclick={() => { showNewChoreModal = true; }}
      >＋</button>
    {/if}
```

- [ ] **Step 4: Check `isChores` and `showNewChoreModal` are still used elsewhere**

```bash
grep -n "isChores\|showNewChoreModal\|new-chore-btn" packages/editor/src/App.svelte
```

Expected: `isChores` appears only in its own `$derived` line now (can be removed too if unused, but it's harmless to leave). `showNewChoreModal` should still appear in the `NewChoreModal` bind and in the `onnewchore` callback passed to ChoresPage. `new-chore-btn` should be gone.

- [ ] **Step 5: Type-check**

```bash
cd packages/editor && npx tsc --noEmit 2>&1 | grep -v "^test/"
```

Expected: no errors from `src/` files.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/App.svelte
git commit -m "feat(chores): merge #/chores routes, remove redundant topbar buttons"
```

---

### Task 4: ChoresPage — needs-attention toggle, bigger buttons, delay actions

**Files:**
- Modify: `packages/editor/src/lib/components/ChoresPage.svelte`

- [ ] **Step 1: Add `dueFilter` state and `needsAttention` helper**

In the `<script>` block of `ChoresPage.svelte`, after the existing `let scheduleFilter = $state("");` line, add:

```ts
  let dueFilter = $state<"all" | "attention">("attention");

  function needsAttention(assignments: Assignment[]): boolean {
    if (assignments.length === 0) return false;
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() + 7);
    return assignments.some((a) => a.nextDueDate && new Date(a.nextDueDate) <= cutoff);
  }
```

- [ ] **Step 2: Wire `dueFilter` into `filteredChores`**

Replace the existing `filteredChores` derived with:

```ts
  const filteredChores = $derived(
    store.chores.filter((c) => {
      if (searchQuery && !c.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      if (scheduleFilter && scheduleCategory(c) !== scheduleFilter) return false;
      if (roomFilter) {
        const assignments = store.assignments.filter((a) => a.choreId === c.id);
        if (!assignments.some((a) => a.roomId === roomFilter)) return false;
      }
      if (dueFilter === "attention") {
        const assignments = store.assignments.filter((a) => a.choreId === c.id);
        if (!needsAttention(assignments)) return false;
      }
      return true;
    }),
  );
```

- [ ] **Step 3: Add the two-state toggle to the toolbar**

In the toolbar, between the schedule `<select>` and the `<Button>` for ＋ Add chore, add:

```svelte
    <div class="filter-toggle">
      <button class="toggle-btn" class:active={dueFilter === "all"} onclick={() => { dueFilter = "all"; }}>All</button>
      <button class="toggle-btn" class:active={dueFilter === "attention"} onclick={() => { dueFilter = "attention"; }}>⚠ Needs attention</button>
    </div>
```

So the full toolbar becomes:

```svelte
  <div class="toolbar">
    <Input placeholder="🔍 Search…" bind:value={searchQuery} />
    <select class="native-input" bind:value={roomFilter}>
      <option value="">All rooms</option>
      {#each allRooms as room}
        <option value={room.id}>{room.label}</option>
      {/each}
    </select>
    <select class="native-input" bind:value={scheduleFilter}>
      <option value="">All schedules</option>
      <option value="daily">Daily</option>
      <option value="weekly">Weekly</option>
      <option value="monthly">Monthly</option>
      <option value="yearly">Yearly</option>
    </select>
    <div class="filter-toggle">
      <button class="toggle-btn" class:active={dueFilter === "all"} onclick={() => { dueFilter = "all"; }}>All</button>
      <button class="toggle-btn" class:active={dueFilter === "attention"} onclick={() => { dueFilter = "attention"; }}>⚠ Needs attention</button>
    </div>
    <Button onclick={() => onnewchore?.()}>＋ Add chore</Button>
    {#if !showImportInput}
      <Button variant="secondary" onclick={() => { showImportInput = true; }}>Import from Donetick</Button>
    {:else}
      <Input type="password" placeholder="API token" bind:value={importToken} />
      <Button disabled={importStatus === "loading"} onclick={handleImport}>
        {importStatus === "loading" ? "Importing…" : "Import"}
      </Button>
      <Button variant="ghost" onclick={() => { showImportInput = false; }}>Cancel</Button>
      {#if importStatus === "error"}<span class="msg-error">Failed</span>{/if}
      {#if importStatus === "done"}<span class="msg-success">{importCount} imported</span>{/if}
    {/if}
  </div>
```

- [ ] **Step 4: Add ⏭ delay button to the chore row actions cell**

In the chore row's `<td class="actions-cell">`, add the delay button right before the closing `</td>`, after the history button. The full actions cell becomes:

```svelte
            <td class="actions-cell" onclick={(e) => e.stopPropagation()}>
              {#if completingChore}
                <input
                  class="note-input"
                  bind:value={completingChore.notes}
                  placeholder="Note (optional)"
                  onkeydown={(e) => { if (e.key === "Enter") confirmComplete(); if (e.key === "Escape") completing = null; }}
                />
                <button class="icon-btn confirm-btn" onclick={confirmComplete}>✓</button>
                <button class="icon-btn" onclick={() => { completing = null; }}>✕</button>
              {:else}
                <button class="icon-btn" title="Mark all done" onclick={() => { completing = { kind: "chore", id: chore.id, notes: "" }; }}>✓</button>
              {/if}
              <button
                class="icon-btn"
                class:active-hist={isExpanded}
                title={isExpanded ? "Hide history" : "Show history & assignments"}
                onclick={() => { expandedHistory = isExpanded ? null : chore.id; }}
              >🕐</button>
              <button class="icon-btn" title="Delay all assignments by 1 week" onclick={() => store.delayChore(chore.id, 7)}>⏭</button>
            </td>
```

- [ ] **Step 5: Add ⏭ delay button to each expanded assignment row**

In the `<div class="assign-row">` inside the expanded section, add the delay button after the delete button:

```svelte
                        <div class="assign-row">
                          <span class="assign-where">{a.roomId ? getRoomName(a.roomId) : "🏠 Whole house"}</span>
                          <span class="assign-due">Due: {formatDate(a.nextDueDate)}</span>
                          {#if completingAssign}
                            <input
                              class="note-input"
                              bind:value={completingAssign.notes}
                              placeholder="Note (optional)"
                              onkeydown={(e) => { if (e.key === "Enter") confirmComplete(); if (e.key === "Escape") completing = null; }}
                            />
                            <button class="icon-btn confirm-btn" onclick={confirmComplete}>✓</button>
                            <button class="icon-btn" onclick={() => { completing = null; }}>✕</button>
                          {:else}
                            <button class="icon-btn" onclick={() => { completing = { kind: "assignment", id: a.id, notes: "" }; }}>✓</button>
                          {/if}
                          <button class="icon-btn danger" onclick={() => store.deleteAssignment(a.id)}>✕</button>
                          <button class="icon-btn" title="Delay by 1 week" onclick={() => store.delayAssignment(a.id, 7)}>⏭</button>
                        </div>
```

- [ ] **Step 6: Bump `icon-btn` size and add toggle styles**

In the `<style>` block, replace:

```css
  .icon-btn {
    padding: 4px 8px; border: none; border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text-muted); cursor: pointer; font-size: 12px;
  }
```

with:

```css
  .icon-btn {
    padding: 8px 14px; border: none; border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text-muted); cursor: pointer; font-size: 15px;
    min-height: 38px;
  }
```

Then add the toggle styles (after `.native-input:focus` line):

```css
  .filter-toggle { display: flex; border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; flex-shrink: 0; }
  .toggle-btn { padding: 6px 12px; border: none; background: var(--surface-alt); color: var(--text-muted); cursor: pointer; font-size: 12px; white-space: nowrap; }
  .toggle-btn:not(:last-child) { border-right: 1px solid var(--border); }
  .toggle-btn.active { background: var(--accent); color: var(--accent-contrast); }
  .toggle-btn:not(.active):hover { background: var(--surface-hover); color: var(--text); }
```

- [ ] **Step 7: Update the empty state message for attention filter**

Replace the current empty cell content:

```svelte
              {store.chores.length === 0
                ? "No chores yet — click ＋ Add chore to get started."
                : "No chores match your filters."}
```

with:

```svelte
              {store.chores.length === 0
                ? "No chores yet — click ＋ Add chore to get started."
                : dueFilter === "attention"
                  ? "No chores need attention right now."
                  : "No chores match your filters."}
```

- [ ] **Step 8: Type-check**

```bash
cd packages/editor && npx tsc --noEmit 2>&1 | grep -v "^test/"
```

Expected: no errors from `src/` files.

- [ ] **Step 9: Run frontend tests**

```bash
cd packages/editor && npx vitest run 2>&1 | tail -10
```

Expected: all tests pass (count should match or exceed pre-change baseline).

- [ ] **Step 10: Commit**

```bash
git add packages/editor/src/lib/components/ChoresPage.svelte
git commit -m "feat(chores): needs-attention toggle, bigger buttons, delay-by-week actions"
```
