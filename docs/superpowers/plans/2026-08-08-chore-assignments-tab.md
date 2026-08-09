# Chore assignments tab + multi-assignment labels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move chore room-assignment management (view/complete/delay/delete/create) from `ChoresPage`'s expand-triangle row into a new "Assignments" tab in `ChoreEditModal`, and add an optional per-assignment `label` so a chore can be intentionally assigned to the same room more than once with each occurrence distinguishable.

**Architecture:** Backend `Assignment` model gains an optional `label` field, threaded through the existing create/update assignment endpoints (no new endpoints, no migration — JSON document store). Frontend: `ChoresPage.svelte` loses its expand-row UI entirely; `ChoreEditModal.svelte` gains an "Assignments" tab that lists/edits/completes/delays/deletes assignments and can create new ones (auto-placed at the target room's polygon centroid via `@myhome/geometry`'s `polygonCentroid`). The History tab gets three small, related fixes: explicit `completedAt`-descending sort (replacing a fragile array `.reverse()`), the assignment's label shown next to the room, and date-only (no time-of-day) formatting.

**Tech Stack:** FastAPI + Pydantic (backend), Svelte 5 + TypeScript + Vitest (frontend), pytest (backend tests).

## Global Constraints

- No DB migration: `Assignment` documents are JSON, so a new optional field with a `None` default reads back cleanly on old data.
- No uniqueness constraint on `(choreId, roomId)` — duplicates are an intentional, supported case per the spec.
- Follow existing i18n key structure under `chores.*` in `packages/editor/src/lib/locales/{en,fr}.json`; both files must stay in exact key parity (enforced by `packages/editor/test/i18nCompleteness.test.ts`).
- Reuse existing shared components (`Tabs`, `Button`, `Modal`, `ChoreCompleteModal`) — no new shared UI components needed.

---

### Task 1: Backend — `Assignment.label` field

**Files:**
- Modify: `packages/backend/src/myhome/models_chores.py:34-39` (`Assignment`), `:74-79` (`AssignmentCreate`), `:81-83` (`AssignmentUpdate`)
- Modify: `packages/backend/src/myhome/routes/chores.py:328-344` (`create_assignment`), `:390-400` (`update_assignment`)
- Test: `packages/backend/tests/test_chores.py`

**Interfaces:**
- Produces: `Assignment.label: str | None` (default `None`), `AssignmentCreate.label: str | None` (default `None`), `AssignmentUpdate.label: str | None` (default `None`). `POST /api/homes/{home_id}/assignments` accepts and returns `label`. `PUT /api/homes/{home_id}/assignments/{assignment_id}` accepts `label` and applies it when not `None` (same pattern as the existing `position`/`nextDueDate` fields on that route).

- [ ] **Step 1: Write the failing tests**

Add to `packages/backend/tests/test_chores.py`, right after `test_create_assignment_404_unknown_chore` (currently ending at line 233):

```python
def test_create_assignment_with_label(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    resp = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1", "label": "Balcony plants"})
    assert resp.status_code == 201
    assert resp.json()["label"] == "Balcony plants"


def test_create_assignment_without_label_defaults_to_none(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    resp = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"})
    assert resp.status_code == 201
    assert resp.json()["label"] is None


def test_create_assignment_duplicate_room_allowed(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    r1 = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1", "label": "Side A"})
    r2 = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1", "label": "Side B"})
    assert r1.status_code == 201
    assert r2.status_code == 201
    assignments = client.get(f"/api/homes/{home_id}/chores").json()["assignments"]
    room_r1 = [a for a in assignments if a["roomId"] == "r1"]
    assert len(room_r1) == 2
    assert {a["label"] for a in room_r1} == {"Side A", "Side B"}
```

And after `test_update_assignment_position` (currently ending at line 245):

```python
def test_update_assignment_label(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    aid = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    put_resp = client.put(f"/api/homes/{home_id}/assignments/{aid}", json={"label": "Watering side"})
    assert put_resp.status_code == 204
    assignments = client.get(f"/api/homes/{home_id}/chores").json()["assignments"]
    a = next(a for a in assignments if a["id"] == aid)
    assert a["label"] == "Watering side"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_chores.py -k "label" -v`
Expected: FAIL (4 tests) — `label` key not present / not accepted, `AssignmentUpdate` has no `label` field.

- [ ] **Step 3: Add `label` to the models**

In `packages/backend/src/myhome/models_chores.py`, change:

```python
class Assignment(BaseModel):
    id: str
    choreId: str
    roomId: str | None = None
    position: Position | None = None
    nextDueDate: str = ""   # per-instance due date; empty string = not yet set
```

to:

```python
class Assignment(BaseModel):
    id: str
    choreId: str
    roomId: str | None = None
    position: Position | None = None
    nextDueDate: str = ""   # per-instance due date; empty string = not yet set
    label: str | None = None   # disambiguates multiple assignments to the same room
```

and change:

```python
class AssignmentCreate(BaseModel):
    choreId: str
    roomId: str | None = None
    position: Position | None = None
    nextDueDate: str = ""   # if empty, backend fills from chore.nextDueDate
```

to:

```python
class AssignmentCreate(BaseModel):
    choreId: str
    roomId: str | None = None
    position: Position | None = None
    nextDueDate: str = ""   # if empty, backend fills from chore.nextDueDate
    label: str | None = None
```

and change:

```python
class AssignmentUpdate(BaseModel):
    position: Position | None = None
    nextDueDate: str | None = None
```

to:

```python
class AssignmentUpdate(BaseModel):
    position: Position | None = None
    nextDueDate: str | None = None
    label: str | None = None
```

- [ ] **Step 4: Wire `label` through the routes**

In `packages/backend/src/myhome/routes/chores.py`, in `create_assignment`, change:

```python
    assignment = Assignment(
        id=str(uuid.uuid4()),
        choreId=body.choreId,
        roomId=body.roomId,
        position=body.position,
        nextDueDate=next_due,
    )
```

to:

```python
    assignment = Assignment(
        id=str(uuid.uuid4()),
        choreId=body.choreId,
        roomId=body.roomId,
        position=body.position,
        nextDueDate=next_due,
        label=body.label,
    )
```

In `update_assignment`, change:

```python
    if body.position is not None:
        assignment.position = body.position
    if body.nextDueDate is not None:
        assignment.nextDueDate = body.nextDueDate
    save_chores(home_id, doc)
```

to:

```python
    if body.position is not None:
        assignment.position = body.position
    if body.nextDueDate is not None:
        assignment.nextDueDate = body.nextDueDate
    if body.label is not None:
        assignment.label = body.label
    save_chores(home_id, doc)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_chores.py -v`
Expected: PASS (all tests, including the 4 new ones)

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/models_chores.py packages/backend/src/myhome/routes/chores.py packages/backend/tests/test_chores.py
git commit -m "feat(chores): add optional label field to room assignments"
```

---

### Task 2: Frontend store — `Assignment.label` + `updateAssignmentLabel`

**Files:**
- Modify: `packages/editor/src/lib/choreStore.svelte.ts:84-90` (`Assignment` interface), and add a new store method near `updateAssignmentPosition` (currently `:257-267`)
- Test: `packages/editor/test/choreStore.test.ts`

**Interfaces:**
- Consumes: none new.
- Produces: `Assignment.label: string | null` on the frontend `Assignment` type; `store.updateAssignmentLabel(id: string, label: string): Promise<void>` — PUTs `{ label }` to `/api/homes/{homeId}/assignments/{id}` and reloads, mirroring `updateAssignmentPosition`. `store.createAssignment` needs no signature change — it already takes `Omit<Assignment, "id">`, which will include `label` once the interface is updated.

- [ ] **Step 1: Write the failing test**

Add to `packages/editor/test/choreStore.test.ts`, after the `describe("choreStore — completedOn", ...)` block (end of file):

```ts
describe("choreStore — updateAssignmentLabel", () => {
  it("PUTs the label to the assignment endpoint", async () => {
    const fetchMock = makeFetch(200, emptyDoc);
    vi.stubGlobal("fetch", fetchMock);
    const store = createChoreStore(getHomeId);
    await tick();

    await store.updateAssignmentLabel("a1", "Balcony plants");

    const putCall = fetchMock.mock.calls.find(([url]) => String(url).endsWith("/assignments/a1"));
    expect(putCall).toBeDefined();
    expect(putCall![1].method).toBe("PUT");
    const sentBody = JSON.parse(putCall![1].body as string);
    expect(sentBody).toEqual({ label: "Balcony plants" });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/choreStore.test.ts -t updateAssignmentLabel`
Expected: FAIL — `store.updateAssignmentLabel is not a function`

- [ ] **Step 3: Add `label` to the `Assignment` interface**

In `packages/editor/src/lib/choreStore.svelte.ts`, change:

```ts
export interface Assignment {
  id: string;
  choreId: string;
  roomId: string | null;
  position: Position | null;
  nextDueDate: string;
}
```

to:

```ts
export interface Assignment {
  id: string;
  choreId: string;
  roomId: string | null;
  position: Position | null;
  nextDueDate: string;
  label: string | null;
}
```

- [ ] **Step 4: Add the `updateAssignmentLabel` method**

Immediately after `updateAssignmentPosition` (currently lines 257-267), add:

```ts
  async function updateAssignmentLabel(id: string, label: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/assignments/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }
```

Then add `updateAssignmentLabel,` to the returned object, right after `updateAssignmentPosition,` (currently line 332).

- [ ] **Step 5: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/choreStore.test.ts`
Expected: PASS (all tests)

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/choreStore.svelte.ts packages/editor/test/choreStore.test.ts
git commit -m "feat(chores): add label field and updateAssignmentLabel to chore store"
```

---

### Task 3: `ChoresPage.svelte` — remove expand-row UI, widen room type

**Files:**
- Modify: `packages/editor/src/lib/components/ChoresPage.svelte`
- Test: `packages/editor/test/ChoresPage.test.ts`

**Interfaces:**
- Consumes: nothing new from Task 1/2.
- Produces: `ChoresPage`'s `floorStore` prop type now requires each room to carry `polygon: Point[] | null` (previously just `{id, label}`), and it passes that full room shape through to `ChoreEditModal`'s `rooms` prop unchanged — this is what Task 4 needs for centroid placement.

- [ ] **Step 1: Update the failing/changing tests first**

In `packages/editor/test/ChoresPage.test.ts`:

Delete the entire `describe("ChoresPage — expand/collapse assignments", ...)` block (lines 83-108).

Delete the `it("assignment-level mark-done confirms with notes and completedOn after picking a past date", ...)` test (lines 255-288) — this behavior moves to `ChoreEditModal` and is covered there in Task 4.

In the `describe("ChoresPage — responsive columns", ...)` block, change:

```ts
    const headers = target.querySelectorAll("thead th");
    // expand, emoji, name, schedule, rooms, nextDue, actions
    expect(headers[4].classList.contains("col-hide-tablet")).toBe(true); // rooms
    expect(headers[3].classList.contains("col-hide-mobile")).toBe(true); // schedule
    expect(headers[6].classList.contains("col-hide-tablet")).toBe(false); // actions
    expect(headers[6].classList.contains("col-hide-mobile")).toBe(false); // actions
```

to:

```ts
    const headers = target.querySelectorAll("thead th");
    // emoji, name, schedule, rooms, nextDue, actions
    expect(headers[3].classList.contains("col-hide-tablet")).toBe(true); // rooms
    expect(headers[2].classList.contains("col-hide-mobile")).toBe(true); // schedule
    expect(headers[5].classList.contains("col-hide-tablet")).toBe(false); // actions
    expect(headers[5].classList.contains("col-hide-mobile")).toBe(false); // actions
```

- [ ] **Step 2: Run tests to verify the remaining ones fail (component not yet changed)**

Run: `cd packages/editor && npx vitest run test/ChoresPage.test.ts`
Expected: FAIL on the "responsive columns" test (indices don't match yet, since the component still has the expand column); other tests still pass.

- [ ] **Step 3: Remove the expand column and expanded-row snippet from `ChoresPage.svelte`**

Remove the `expandedHistory` state (currently line 48):

```ts
  let expandedHistory = $state<string | null>(null);
```

Simplify `CompletingState` (currently lines 59-62) from:

```ts
  type CompletingState =
    | { kind: "chore"; id: string; title: string }
    | { kind: "assignment"; id: string; title: string };
  let completing = $state<CompletingState | null>(null);
```

to:

```ts
  type CompletingState = { kind: "chore"; id: string; title: string };
  let completing = $state<CompletingState | null>(null);
```

Simplify `confirmComplete` (currently lines 184-195) from:

```ts
  async function confirmComplete(notes: string, completedOn?: string): Promise<void> {
    if (!completing) return;
    const c = completing;
    completing = null;
    if (c.kind === "chore") {
      if (completedOn) await store.completeChore(c.id, notes, completedOn);
      else await store.completeChore(c.id, notes);
    } else {
      if (completedOn) await store.completeAssignment(c.id, notes, completedOn);
      else await store.completeAssignment(c.id, notes);
    }
  }
```

to:

```ts
  async function confirmComplete(notes: string, completedOn?: string): Promise<void> {
    if (!completing) return;
    const c = completing;
    completing = null;
    if (completedOn) await store.completeChore(c.id, notes, completedOn);
    else await store.completeChore(c.id, notes);
  }
```

Remove the `expandCell` snippet (currently lines 252-257):

```svelte
      {#snippet expandCell(chore: Chore)}
        <button
          class="expand-btn"
          onclick={(e) => { e.stopPropagation(); expandedHistory = expandedHistory === chore.id ? null : chore.id; }}
        >{expandedHistory === chore.id ? "▼" : "▶"}</button>
      {/snippet}
```

Remove the `assignmentsExpanded` snippet (currently lines 278-295):

```svelte
      {#snippet assignmentsExpanded(chore: Chore)}
        {@const assignments = assignmentsForChore(chore.id)}
        <div class="expand-body">
          {#if assignments.length > 0}
            {#each assignments as a (a.id)}
              <div class="assign-row">
                <span class="assign-where">{a.roomId ? getRoomName(a.roomId) : `🏠 ${$_('chores.list.wholeHouse')}`}</span>
                <span class="assign-due">{$_('chores.badgePopup.due')}: {formatDate(a.nextDueDate)}</span>
                <button class="icon-btn" title={$_('chores.row.markDone')} onclick={() => { completing = { kind: "assignment", id: a.id, title: `${chore.emoji} ${displayName(chore)}` }; }}>✓</button>
                <button class="icon-btn danger" onclick={() => store.deleteAssignment(a.id)}>✕</button>
                <button class="icon-btn" title={$_('chores.page.delayByWeek')} onclick={() => store.delayAssignment(a.id, 7)}>⏭</button>
              </div>
            {/each}
          {:else}
            <div class="no-assign">{$_('chores.page.notAssigned')}</div>
          {/if}
        </div>
      {/snippet}
```

Remove the `expand` column entry from the `columns` array (currently line 299):

```ts
          { key: "expand", label: "", sortable: false, cellClass: "expand-cell", cell: expandCell },
```

Remove `isRowExpanded`/`expandedRow` props from `<SortableTable>` (currently lines 310-311):

```svelte
        isRowExpanded={(chore) => expandedHistory === chore.id}
        expandedRow={assignmentsExpanded}
```

- [ ] **Step 4: Widen the `floorStore` prop type to carry room polygons**

Add an import at the top of `packages/editor/src/lib/components/ChoresPage.svelte`, alongside the existing imports:

```ts
  import type { Point } from "@myhome/geometry";
```

Change the `Props` interface's `floorStore` field from:

```ts
    floorStore: { floors: Array<{ id: string; name: string; rooms: Array<{ id: string; label: string }> }> };
```

to:

```ts
    floorStore: { floors: Array<{ id: string; name: string; rooms: Array<{ id: string; label: string; polygon: Point[] | null }> }> };
```

(`allRooms` and the `<ChoreEditModal ... rooms={allRooms} ...>` call already pass this through unchanged — no other edits needed here.)

- [ ] **Step 5: Remove the now-dead CSS**

Remove these rules from the `<style>` block (currently lines 394, 400, 402-406):

```css
  :global(.expand-cell) { width: 20px; padding: 0 4px; text-align: center; }
  .expand-btn { background: none; border: none; cursor: pointer; color: var(--text-faint); font-size: 9px; padding: 2px 4px; line-height: 1; }
  .expand-btn:hover { color: var(--text); }
```

```css
  .expand-body { padding: 10px 16px; display: flex; flex-direction: column; gap: 6px; }

  .assign-row { display: flex; align-items: center; gap: 8px; font-size: 12px; flex-wrap: wrap; }
  .assign-row .icon-btn { padding: 4px 8px; font-size: 13px; min-height: 28px; }
  .assign-where { flex: 1; min-width: 80px; color: var(--text-muted); }
  .assign-due { color: var(--text-faint); font-size: 11px; white-space: nowrap; }
  .no-assign { font-size: 11px; color: var(--text-faint); font-style: italic; }
```

Keep the `.icon-btn` / `.icon-btn:hover` / `.icon-btn.danger:hover` rules — `actionsCell` still uses them.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/ChoresPage.test.ts`
Expected: PASS (all remaining tests)

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/components/ChoresPage.svelte packages/editor/test/ChoresPage.test.ts
git commit -m "refactor(chores): remove expand-row assignment UI from the chores list"
```

---

### Task 4: `ChoreEditModal.svelte` — new "Assignments" tab

**Files:**
- Modify: `packages/editor/src/lib/components/ChoreEditModal.svelte`
- Modify: `packages/editor/src/lib/locales/en.json`, `packages/editor/src/lib/locales/fr.json`
- Test: `packages/editor/test/ChoreEditModal.test.ts`

**Interfaces:**
- Consumes: `store.assignments`, `store.createAssignment`, `store.updateAssignmentLabel`, `store.deleteAssignment`, `store.delayAssignment`, `store.completeAssignment` (all from Task 2's `choreStore`); `rooms: Array<{ id: string; label: string; polygon: Point[] | null }>` (widened in Task 3); `polygonCentroid` from `@myhome/geometry`.
- Produces: a new "assignments" tab id in `ChoreEditModal`'s internal `activeTab` union, usable the same way `info`/`media`/`history` already are.

- [ ] **Step 1: Add new i18n keys**

In `packages/editor/src/lib/locales/en.json`, inside the `chores.editModal` object, add (e.g. after `"placeOnMap": "Place on map",`):

```json
    "assignments": "Assignments",
    "assignmentsCount": "Assignments ({n})",
    "labelPlaceholder": "Label (optional)",
    "selectRoom": "Select a room…",
    "addAssignment": "Add",
```

In `packages/editor/src/lib/locales/fr.json`, inside the matching `chores.editModal` object, add:

```json
    "assignments": "Affectations",
    "assignmentsCount": "Affectations ({n})",
    "labelPlaceholder": "Étiquette (optionnel)",
    "selectRoom": "Choisir une pièce…",
    "addAssignment": "Ajouter",
```

- [ ] **Step 2: Write the failing tests**

Add to `packages/editor/test/ChoreEditModal.test.ts`. First, extend `makeStore()` to include the new methods, and add a room fixture with a polygon:

```ts
function makeStore(overrides = {}) {
  return {
    updateChore: vi.fn().mockResolvedValue(undefined),
    deleteChore: vi.fn().mockResolvedValue(undefined),
    uploadAttachment: vi.fn().mockResolvedValue("file.jpg"),
    deleteAttachment: vi.fn().mockResolvedValue(undefined),
    getCompletionsForChore: vi.fn().mockReturnValue([]),
    assignments: [],
    deleteCompletion: vi.fn().mockResolvedValue(undefined),
    createAssignment: vi.fn().mockResolvedValue(undefined),
    updateAssignmentLabel: vi.fn().mockResolvedValue(undefined),
    deleteAssignment: vi.fn().mockResolvedValue(undefined),
    delayAssignment: vi.fn().mockResolvedValue(undefined),
    completeAssignment: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

const SQUARE_ROOM = { id: "r1", label: "Kitchen", polygon: [{ x: 0, y: 0 }, { x: 2, y: 0 }, { x: 2, y: 2 }, { x: 0, y: 2 }] };
```

Then add a new describe block, e.g. at the end of the file:

```ts
describe("ChoreEditModal — Assignments tab", () => {
  it("lists existing assignments with their label and room, and completes/delays/deletes them", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore({
      assignments: [
        { id: "a1", choreId: "c1", roomId: "r1", position: { x: 1, y: 1 }, nextDueDate: "2027-01-01T00:00:00Z", label: "Balcony plants" },
      ],
    });
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: [SQUARE_ROOM], onclose: vi.fn() },
    });
    flushSync();

    const assignmentsTab = Array.from(target.querySelectorAll(".tab")).find(t => t.textContent?.includes("Assignments")) as HTMLButtonElement;
    assignmentsTab.click();
    flushSync();

    expect(target.querySelector(".assign-where")?.textContent).toBe("Kitchen");
    expect((target.querySelector(".assign-label-input") as HTMLInputElement).value).toBe("Balcony plants");

    const [completeBtn, delayBtn, deleteBtn] = Array.from(target.querySelectorAll(".assignment-row .icon-btn")) as HTMLButtonElement[];
    delayBtn.click();
    expect(store.delayAssignment).toHaveBeenCalledWith("a1", 7);
    deleteBtn.click();
    expect(store.deleteAssignment).toHaveBeenCalledWith("a1");

    completeBtn.click();
    flushSync();
    expect(target.querySelector(".complete-form")).not.toBeNull(); // ChoreCompleteModal is open

    unmount(app);
    target.remove();
  });

  it("editing the label input blur calls updateAssignmentLabel only when changed", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore({
      assignments: [{ id: "a1", choreId: "c1", roomId: "r1", position: null, nextDueDate: "2027-01-01T00:00:00Z", label: "Side A" }],
    });
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: [SQUARE_ROOM], onclose: vi.fn() },
    });
    flushSync();
    (Array.from(target.querySelectorAll(".tab")).find(t => t.textContent?.includes("Assignments")) as HTMLButtonElement).click();
    flushSync();

    const input = target.querySelector(".assign-label-input") as HTMLInputElement;
    input.value = "Side A";
    input.dispatchEvent(new Event("blur"));
    await tick();
    expect(store.updateAssignmentLabel).not.toHaveBeenCalled();

    input.value = "Side A (near window)";
    input.dispatchEvent(new Event("blur"));
    await tick();
    expect(store.updateAssignmentLabel).toHaveBeenCalledWith("a1", "Side A (near window)");

    unmount(app);
    target.remove();
  });

  it("adding an assignment computes position as the room's polygon centroid", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: [SQUARE_ROOM], onclose: vi.fn() },
    });
    flushSync();
    (Array.from(target.querySelectorAll(".tab")).find(t => t.textContent?.includes("Assignments")) as HTMLButtonElement).click();
    flushSync();

    const roomSelect = target.querySelector(".add-assignment-row select") as HTMLSelectElement;
    roomSelect.value = "r1";
    roomSelect.dispatchEvent(new Event("change", { bubbles: true }));
    const labelInput = target.querySelector(".add-assignment-row .assign-label-input") as HTMLInputElement;
    labelInput.value = "New spot";
    labelInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();

    const addBtn = Array.from(target.querySelectorAll(".add-assignment-row button")).find(b => b.textContent?.trim() === "Add") as HTMLButtonElement;
    addBtn.click();
    await tick();

    expect(store.createAssignment).toHaveBeenCalledWith({
      choreId: "c1", roomId: "r1", position: { x: 1, y: 1 }, nextDueDate: "", label: "New spot",
    });

    unmount(app);
    target.remove();
  });

  it("shows an assignment count badge on the tab when assignments exist", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore({
      assignments: [{ id: "a1", choreId: "c1", roomId: "r1", position: null, nextDueDate: "2027-01-01T00:00:00Z", label: null }],
    });
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: [SQUARE_ROOM], onclose: vi.fn() },
    });
    flushSync();

    const tabs = Array.from(target.querySelectorAll(".tab")).map(t => t.textContent?.trim());
    expect(tabs).toContain("Assignments (1)");

    unmount(app);
    target.remove();
  });
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/ChoreEditModal.test.ts -t "Assignments tab"`
Expected: FAIL — no "Assignments" tab exists yet, `.assign-where`/`.assignment-row`/`.add-assignment-row` not found.

- [ ] **Step 4: Update imports, types, and state in `ChoreEditModal.svelte`**

Change the imports (currently lines 1-16) — add three new imports and drop the now-unused `formatDateTime` (its removal is finished in Task 5; for now just add the new imports):

```ts
  import { _ } from "svelte-i18n";
  import type { createChoreStore, Chore } from "../choreStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import { apiUrl } from "../apiUrl";
  import { homesStore } from "../homesStore.svelte";
  import Modal from "./ui/Modal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import Tabs from "./ui/Tabs.svelte";
  import DatePicker from "./DatePicker.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";
  import EmojiPicker from "./ui/EmojiPicker.svelte";
  import ScheduleEditor from "./ScheduleEditor.svelte";
  import ChoreCompleteModal from "./ChoreCompleteModal.svelte";
  import { polygonCentroid } from "@myhome/geometry";
  import type { Point } from "@myhome/geometry";
  import { formatDate, formatDateTime } from "../dateFormat";
```

Change the `ChoreStore` type (currently line 18) from:

```ts
  type ChoreStore = Pick<ReturnType<typeof createChoreStore>, "updateChore" | "deleteChore" | "uploadAttachment" | "deleteAttachment" | "getCompletionsForChore" | "assignments" | "deleteCompletion">;
```

to:

```ts
  type ChoreStore = Pick<ReturnType<typeof createChoreStore>, "updateChore" | "deleteChore" | "uploadAttachment" | "deleteAttachment" | "getCompletionsForChore" | "assignments" | "deleteCompletion" | "createAssignment" | "updateAssignmentLabel" | "deleteAssignment" | "delayAssignment" | "completeAssignment">;
```

Change the `Props` interface's `rooms` field (currently line 23) from:

```ts
    rooms: Array<{ id: string; label: string }>;
```

to:

```ts
    rooms: Array<{ id: string; label: string; polygon: Point[] | null }>;
```

Change `activeTab`'s type (currently line 30) from:

```ts
  let activeTab = $state<"info" | "media" | "history">("info");
```

to:

```ts
  let activeTab = $state<"info" | "assignments" | "media" | "history">("info");
```

Add new state, right after the existing `lightboxIndex` declaration (currently line 48):

```ts
  let newAssignmentRoomId = $state("");
  let newAssignmentLabel = $state("");
  let completing = $state<{ id: string; title: string } | null>(null);
```

Add a new derived value right after the `history` derived (currently line 50):

```ts
  const assignmentsForChore = $derived(chore ? store.assignments.filter((a) => a.choreId === chore.id) : []);
```

- [ ] **Step 5: Add the assignment helpers**

Right after `getRoomName` (currently lines 53-58), add:

```ts
  async function handleLabelBlur(assignmentId: string, value: string): Promise<void> {
    const trimmed = value.trim();
    const current = store.assignments.find((a) => a.id === assignmentId)?.label ?? "";
    if (trimmed === current) return;
    await store.updateAssignmentLabel(assignmentId, trimmed);
  }

  async function handleAddAssignment(): Promise<void> {
    if (!chore || !newAssignmentRoomId) return;
    const room = rooms.find((r) => r.id === newAssignmentRoomId);
    const position = room?.polygon ? polygonCentroid(room.polygon) : null;
    await store.createAssignment({
      choreId: chore.id,
      roomId: newAssignmentRoomId,
      position,
      nextDueDate: "",
      label: newAssignmentLabel.trim() || null,
    });
    newAssignmentRoomId = "";
    newAssignmentLabel = "";
  }

  async function confirmCompleteAssignment(notes: string, completedOn?: string): Promise<void> {
    if (!completing) return;
    const id = completing.id;
    completing = null;
    if (completedOn) await store.completeAssignment(id, notes, completedOn);
    else await store.completeAssignment(id, notes);
  }
```

In the `$effect.pre` block (currently lines 67-81), add the two new resets alongside the existing ones — change:

```ts
      draftDescription = chore.description ?? "";
      activeTab = "info";
      error = null;
```

to:

```ts
      draftDescription = chore.description ?? "";
      activeTab = "info";
      newAssignmentRoomId = "";
      newAssignmentLabel = "";
      error = null;
```

- [ ] **Step 6: Add the "Assignments" tab to the tab bar and render its body**

Change the `<Tabs>` element (currently lines 142-150) from:

```svelte
    <Tabs
      tabs={[
        { id: "info", label: $_('chores.editModal.info') },
        { id: "media", label: (chore.attachments?.length ?? 0) > 0 ? $_('chores.editModal.mediaCount', { values: { n: chore.attachments.length } }) : $_('chores.editModal.media') },
        { id: "history", label: history.length > 0 ? $_('chores.editModal.historyCount', { values: { n: history.length } }) : $_('chores.editModal.history') },
      ]}
      active={activeTab}
      onchange={(id) => { activeTab = id as "info" | "media" | "history"; }}
    />
```

to:

```svelte
    <Tabs
      tabs={[
        { id: "info", label: $_('chores.editModal.info') },
        { id: "assignments", label: assignmentsForChore.length > 0 ? $_('chores.editModal.assignmentsCount', { values: { n: assignmentsForChore.length } }) : $_('chores.editModal.assignments') },
        { id: "media", label: (chore.attachments?.length ?? 0) > 0 ? $_('chores.editModal.mediaCount', { values: { n: chore.attachments.length } }) : $_('chores.editModal.media') },
        { id: "history", label: history.length > 0 ? $_('chores.editModal.historyCount', { values: { n: history.length } }) : $_('chores.editModal.history') },
      ]}
      active={activeTab}
      onchange={(id) => { activeTab = id as "info" | "assignments" | "media" | "history"; }}
    />
```

Insert a new `{:else if activeTab === "assignments"}` branch between the `{#if activeTab === "info"}...{/if}` block and the `{:else if activeTab === "media"}` branch (i.e. change the `{:else if activeTab === "media"}` line at the top of the media block to be preceded by the new branch):

```svelte
    {:else if activeTab === "assignments"}
      <div class="assignments-pane">
        {#if assignmentsForChore.length === 0}
          <div class="no-assignments">{$_('chores.page.notAssigned')}</div>
        {:else}
          {#each assignmentsForChore as a (a.id)}
            <div class="assignment-row">
              <span class="assign-where">{a.roomId ? (rooms.find((r) => r.id === a.roomId)?.label ?? $_('chores.list.unknownRoom')) : `🏠 ${$_('chores.list.wholeHouse')}`}</span>
              <input
                class="native-input assign-label-input"
                placeholder={$_('chores.editModal.labelPlaceholder')}
                value={a.label ?? ""}
                onblur={(e) => handleLabelBlur(a.id, (e.target as HTMLInputElement).value)}
              />
              <span class="assign-due">{$_('chores.badgePopup.due')}: {formatDate(a.nextDueDate)}</span>
              <button class="icon-btn" title={$_('chores.row.markDone')} onclick={() => { completing = { id: a.id, title: `${chore.emoji} ${chore.name}` }; }}>✓</button>
              <button class="icon-btn" title={$_('chores.page.delayByWeek')} onclick={() => store.delayAssignment(a.id, 7)}>⏭</button>
              <button class="icon-btn danger" onclick={() => store.deleteAssignment(a.id)}>✕</button>
            </div>
          {/each}
        {/if}
        <div class="add-assignment-row">
          <select class="native-input" bind:value={newAssignmentRoomId}>
            <option value="">{$_('chores.editModal.selectRoom')}</option>
            {#each rooms as room}
              <option value={room.id}>{room.label}</option>
            {/each}
          </select>
          <input class="native-input assign-label-input" placeholder={$_('chores.editModal.labelPlaceholder')} bind:value={newAssignmentLabel} />
          <Button variant="secondary" disabled={!newAssignmentRoomId} onclick={handleAddAssignment}>{$_('chores.editModal.addAssignment')}</Button>
        </div>
      </div>
```

- [ ] **Step 7: Render `ChoreCompleteModal` for per-assignment completion**

After the existing `{#if lightboxOpen && mediaItems.length > 0}...{/if}` block (currently lines 233-235), add:

```svelte
{#if completing}
  <ChoreCompleteModal title={completing.title} onclose={() => { completing = null; }} onconfirm={confirmCompleteAssignment} />
{/if}
```

- [ ] **Step 8: Add CSS for the new tab**

Append to the `<style>` block:

```css
  .assignments-pane { min-height: 160px; display: flex; flex-direction: column; gap: 8px; }
  .no-assignments { font-size: 11px; color: var(--text-faint); font-style: italic; padding: 12px 0; }
  .assignment-row { display: flex; align-items: center; gap: 8px; font-size: 12px; flex-wrap: wrap; padding: 6px 0; border-bottom: 1px solid var(--border); }
  .assign-where { flex: 1; min-width: 80px; color: var(--text-muted); }
  .assign-label-input { flex: 1; min-width: 100px; }
  .assign-due { color: var(--text-faint); font-size: 11px; white-space: nowrap; }
  .add-assignment-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding-top: 4px; }
  .add-assignment-row select { flex: 1; min-width: 120px; }
  .icon-btn {
    padding: 6px 10px; border: none; border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text-muted); cursor: pointer; font-size: 13px;
    min-height: 30px;
  }
  .icon-btn:hover { background: var(--surface-hover); color: var(--text); }
  .icon-btn.danger:hover { color: var(--danger); }
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/ChoreEditModal.test.ts test/i18nCompleteness.test.ts`
Expected: PASS (all tests, including the pre-existing ones and the new i18n parity check)

- [ ] **Step 10: Commit**

```bash
git add packages/editor/src/lib/components/ChoreEditModal.svelte packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/ChoreEditModal.test.ts
git commit -m "feat(chores): add Assignments tab to the chore edit modal"
```

---

### Task 5: `ChoreEditModal.svelte` — History tab fixes

**Files:**
- Modify: `packages/editor/src/lib/components/ChoreEditModal.svelte`
- Test: `packages/editor/test/ChoreEditModal.test.ts`

**Interfaces:**
- Consumes: `assignmentsForChore`/`store.assignments` from Task 4 (for label lookup).
- Produces: no new public interface — internal correctness/formatting fixes to the existing History tab.

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/ChoreEditModal.test.ts`:

```ts
describe("ChoreEditModal — History tab", () => {
  it("sorts completions by completedAt descending even when a backdated one is inserted out of order", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore({
      // Noon UTC (not midnight) so the rendered calendar date is stable regardless of the test machine's local timezone.
      getCompletionsForChore: vi.fn().mockReturnValue([
        { id: "r1", choreId: "c1", assignmentId: null, completedAt: "2026-08-01T12:00:00Z", scheduledDue: "", notes: "" },
        { id: "r2", choreId: "c1", assignmentId: null, completedAt: "2026-07-01T12:00:00Z", scheduledDue: "", notes: "" }, // backdated, inserted after r1 but earlier in time
        { id: "r3", choreId: "c1", assignmentId: null, completedAt: "2026-08-15T12:00:00Z", scheduledDue: "", notes: "" },
      ]),
    });
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: [], onclose: vi.fn() },
    });
    flushSync();
    (Array.from(target.querySelectorAll(".tab")).find(t => t.textContent?.includes("History")) as HTMLButtonElement).click();
    flushSync();

    const dates = Array.from(target.querySelectorAll(".hist-date")).map(el => el.textContent);
    // Default test locale is "en" -> MDY date format (see localization.ts LANGUAGE_DEFAULTS)
    expect(dates).toEqual(["08/15/2026", "08/01/2026", "07/01/2026"]);

    unmount(app);
    target.remove();
  });

  it("shows the assignment's label next to the room name, and no time-of-day", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore({
      assignments: [{ id: "a1", choreId: "c1", roomId: "r1", position: null, nextDueDate: "2027-01-01T00:00:00Z", label: "Balcony plants" }],
      getCompletionsForChore: vi.fn().mockReturnValue([
        { id: "r1", choreId: "c1", assignmentId: "a1", completedAt: "2026-08-01T12:00:00Z", scheduledDue: "", notes: "" },
      ]),
    });
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: [{ id: "r1", label: "Kitchen", polygon: null }], onclose: vi.fn() },
    });
    flushSync();
    (Array.from(target.querySelectorAll(".tab")).find(t => t.textContent?.includes("History")) as HTMLButtonElement).click();
    flushSync();

    expect(target.querySelector(".hist-room")?.textContent).toContain("Kitchen");
    expect(target.querySelector(".hist-label")?.textContent).toBe("(Balcony plants)");
    expect(target.querySelector(".hist-date")?.textContent).toBe("08/01/2026");

    unmount(app);
    target.remove();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/ChoreEditModal.test.ts -t "History tab"`
Expected: FAIL — dates currently include time-of-day and are in fetch order (not sorted), no `.hist-label` element exists.

- [ ] **Step 3: Fix the sort, add the label, switch to date-only formatting**

Change the `history` derived (currently line 50) from:

```ts
  const history = $derived(chore ? store.getCompletionsForChore(chore.id).slice().reverse() : []);
```

to:

```ts
  const history = $derived(
    chore
      ? store.getCompletionsForChore(chore.id).slice().sort((a, b) => b.completedAt.localeCompare(a.completedAt))
      : []
  );
```

Add a helper right after `getRoomName` (from Task 4, currently just above `handleLabelBlur`):

```ts
  function getAssignmentLabel(assignmentId: string | null): string | null {
    if (!assignmentId) return null;
    return store.assignments.find((a) => a.id === assignmentId)?.label ?? null;
  }
```

Change the history row rendering (currently lines 198-206) from:

```svelte
          {#each history as rec (rec.id)}
            <div class="history-row">
              <span class="hist-room">{getRoomName(rec.assignmentId)}</span>
              <span class="hist-date">{formatDateTime(rec.completedAt)}</span>
              {#if rec.scheduledDue}<span class="hist-due">{$_('chores.editModal.dueOn', { values: { date: formatDate(rec.scheduledDue) } })}</span>{/if}
              {#if rec.notes}<span class="hist-notes">{rec.notes}</span>{/if}
              <button class="hist-del" disabled={deletingCompletion === rec.id} title={$_('chores.editModal.deleteRecord')} onclick={() => handleDeleteCompletion(rec.id)}>🗑</button>
            </div>
          {/each}
```

to:

```svelte
          {#each history as rec (rec.id)}
            {@const label = getAssignmentLabel(rec.assignmentId)}
            <div class="history-row">
              <span class="hist-room">{getRoomName(rec.assignmentId)}{#if label} <span class="hist-label">({label})</span>{/if}</span>
              <span class="hist-date">{formatDate(rec.completedAt)}</span>
              {#if rec.scheduledDue}<span class="hist-due">{$_('chores.editModal.dueOn', { values: { date: formatDate(rec.scheduledDue) } })}</span>{/if}
              {#if rec.notes}<span class="hist-notes">{rec.notes}</span>{/if}
              <button class="hist-del" disabled={deletingCompletion === rec.id} title={$_('chores.editModal.deleteRecord')} onclick={() => handleDeleteCompletion(rec.id)}>🗑</button>
            </div>
          {/each}
```

Remove the now-unused `formatDateTime` import — change:

```ts
  import { formatDate, formatDateTime } from "../dateFormat";
```

to:

```ts
  import { formatDate } from "../dateFormat";
```

Add a style for the new label span, in the `<style>` block near `.hist-room`:

```css
  .hist-label { color: var(--text-faint); font-weight: 400; }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/ChoreEditModal.test.ts`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Run the full frontend and backend suites**

Run: `cd packages/editor && npx vitest run`
Run: `cd packages/backend && python -m pytest -v`
Expected: PASS (full suites, no regressions)

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/ChoreEditModal.svelte packages/editor/test/ChoreEditModal.test.ts
git commit -m "fix(chores): sort history by completedAt, show assignment label, drop time-of-day"
```

---

## Final steps (after all tasks)

- [ ] Run the full test suites one more time to confirm nothing regressed: `cd packages/editor && npx vitest run` and `cd packages/backend && python -m pytest -v`.
- [ ] Manually smoke-test in the browser (via the `run` skill or dev server): open a chore's edit modal, confirm the Assignments tab lists/edits/completes/delays/deletes assignments, add a second assignment to an already-assigned room with a distinguishing label, and confirm the History tab shows dates only (no time) with labels next to room names, sorted most-recent-first.
- [ ] Follow `superpowers:finishing-a-development-branch` to push, open a PR, and merge.
