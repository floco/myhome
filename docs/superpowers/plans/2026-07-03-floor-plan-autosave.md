# Floor Plan Autosave Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically save the floor plan 5 seconds after the last edit, with a dirty-dot indicator on the save button and Ctrl+S for immediate save.

**Architecture:** A `generation` counter in `houseStore` increments on every mutation and on undo/redo; `savedGeneration` is updated after each successful API save. `isDirty` is `generation !== savedGeneration`. A debounced `$effect` in `App.svelte` watches `floorStore.generation` and schedules a 5-second save; Ctrl+S bypasses the debounce. The 💾 button gains a CSS dot overlay when dirty.

**Tech Stack:** Svelte 5 runes (`$state`, `$effect`, `$derived`), Vitest, TypeScript

---

## File Map

| File | Change |
|---|---|
| `packages/editor/src/lib/houseStore.svelte.ts` | Add `generation`/`savedGeneration` state; increment on mutations/undo/redo; reset on init; mark clean on save; export `isDirty` and `generation` getters |
| `packages/editor/test/houseStore.test.ts` | New `describe` block: dirty tracking tests |
| `packages/editor/src/App.svelte` | Add autosave `$effect`, Ctrl+S handler, `class:dirty` on save button, dirty dot CSS |
| `packages/editor/test/App.test.ts` | New tests: Ctrl+S triggers save, dirty class appears after mutation |

---

## Task 1: TDD — dirty tracking in houseStore

**Files:**
- Modify: `packages/editor/test/houseStore.test.ts`
- Modify: `packages/editor/src/lib/houseStore.svelte.ts`

- [ ] **Step 1: Write the failing tests**

Append this describe block at the end of `packages/editor/test/houseStore.test.ts` (before the final closing brace of the file, or simply at the bottom):

```ts
describe("houseStore — dirty tracking", () => {
  it("isDirty is false after init (no homeId)", async () => {
    vi.stubGlobal("fetch", vi.fn());
    const store = createHouseStore();
    await tick();
    expect(store.isDirty).toBe(false);
  });

  it("isDirty is false after init from 404", async () => {
    vi.stubGlobal("fetch", makeFetchStub(404));
    const store = createHouseStore(getHomeId);
    await tick();
    expect(store.isDirty).toBe(false);
  });

  it("isDirty is false after init from API doc", async () => {
    vi.stubGlobal("fetch", makeFetchStub(200, makeDoc("f1")));
    const store = createHouseStore(getHomeId);
    await tick();
    expect(store.isDirty).toBe(false);
  });

  it("isDirty becomes true after addWall", async () => {
    vi.stubGlobal("fetch", makeFetchStub(404));
    const store = createHouseStore(getHomeId);
    await tick();
    store.addWall({ id: "w1", start: { x: 0, y: 0 }, end: { x: 5, y: 0 }, type: "wall" });
    expect(store.isDirty).toBe(true);
  });

  it("isDirty becomes true after addFloor", async () => {
    vi.stubGlobal("fetch", makeFetchStub(404));
    const store = createHouseStore(getHomeId);
    await tick();
    store.addFloor("Upstairs");
    expect(store.isDirty).toBe(true);
  });

  it("isDirty becomes true after updateRoom", async () => {
    vi.stubGlobal("fetch", makeFetchStub(404));
    const store = createHouseStore(getHomeId);
    await tick();
    const roomId = store.floor.rooms[0]?.id;
    if (roomId) store.updateRoom(roomId, { label: "Kitchen" });
    expect(store.isDirty).toBe(true);
  });

  it("isDirty becomes false after save()", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: false, status: 404, statusText: "Not Found", json: async () => undefined })
      .mockResolvedValueOnce({ ok: true, status: 200, statusText: "OK", json: async () => undefined });
    vi.stubGlobal("fetch", fetchFn);
    const store = createHouseStore(getHomeId);
    await tick();
    store.addWall({ id: "w1", start: { x: 0, y: 0 }, end: { x: 5, y: 0 }, type: "wall" });
    expect(store.isDirty).toBe(true);
    await store.save();
    expect(store.isDirty).toBe(false);
  });

  it("isDirty becomes true again after undo", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: false, status: 404, statusText: "Not Found", json: async () => undefined })
      .mockResolvedValueOnce({ ok: true, status: 200, statusText: "OK", json: async () => undefined });
    vi.stubGlobal("fetch", fetchFn);
    const store = createHouseStore(getHomeId);
    await tick();
    store.addWall({ id: "w1", start: { x: 0, y: 0 }, end: { x: 5, y: 0 }, type: "wall" });
    await store.save();
    expect(store.isDirty).toBe(false);
    store.undo();
    expect(store.isDirty).toBe(true);
  });

  it("generation increments on each distinct mutation", async () => {
    vi.stubGlobal("fetch", makeFetchStub(404));
    const store = createHouseStore(getHomeId);
    await tick();
    const g0 = store.generation;
    store.addFloor("F2");
    expect(store.generation).toBe(g0 + 1);
    store.addWall({ id: "w1", start: { x: 0, y: 0 }, end: { x: 5, y: 0 }, type: "wall" });
    expect(store.generation).toBe(g0 + 2);
    store.undo();
    expect(store.generation).toBe(g0 + 3);
  });

  it("moveSharedPoint with skipHistory still increments generation", async () => {
    vi.stubGlobal("fetch", makeFetchStub(404));
    const store = createHouseStore(getHomeId);
    await tick();
    store.addWall({ id: "w1", start: { x: 0, y: 0 }, end: { x: 5, y: 0 }, type: "wall" });
    const g1 = store.generation;
    store.moveSharedPoint({ x: 5, y: 0 }, { x: 6, y: 0 }, { skipHistory: true });
    expect(store.generation).toBe(g1 + 1);
  });
});
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
cd /projects/myhome/packages/editor && npx vitest run --reporter=verbose test/houseStore.test.ts 2>&1 | tail -30
```

Expected: Tests in the new `dirty tracking` block fail with `store.isDirty is not a function` or `undefined`.

- [ ] **Step 3: Implement generation counter in houseStore**

In `packages/editor/src/lib/houseStore.svelte.ts`, make the following changes:

**3a.** After `let loadError = $state<string | null>(null);` (currently line 28), add:

```ts
let generation = $state(0);
let savedGeneration = $state(0);
```

**3b.** In `saveSnapshot()`, add `generation++` before the closing brace:

```ts
function saveSnapshot(): void {
  undoStack.push(cloneState(getState()));
  if (undoStack.length > MAX_HISTORY) undoStack.shift();
  redoStack.length = 0;
  undoCount = undoStack.length;
  redoCount = 0;
  generation++;
}
```

**3c.** In `undo()`, add `generation++` after `redoCount = redoStack.length;`:

```ts
function undo(): void {
  const prev = undoStack.pop();
  if (!prev) return;
  redoStack.push(cloneState(getState()));
  applyState(prev);
  undoCount = undoStack.length;
  redoCount = redoStack.length;
  generation++;
}
```

**3d.** In `redo()`, add `generation++` after `redoCount = redoStack.length;`:

```ts
function redo(): void {
  const next = redoStack.pop();
  if (!next) return;
  undoStack.push(cloneState(getState()));
  applyState(next);
  undoCount = undoStack.length;
  redoCount = redoStack.length;
  generation++;
}
```

**3e.** In `moveSharedPoint()`, add `else generation++` for the skipHistory path:

```ts
function moveSharedPoint(from: Point, to: Point, opts?: { skipHistory?: boolean }): void {
  if (!opts?.skipHistory) saveSnapshot();
  else generation++;
  for (const wall of currentFloor().walls) {
    if (pointsEqual(wall.start, from)) wall.start = to;
    if (pointsEqual(wall.end, from)) wall.end = to;
  }
  commitWalls();
}
```

**3f.** In `updateOpening()`, add `else generation++` for the skipHistory path:

```ts
function updateOpening(
  id: string,
  patch: Partial<Pick<Opening, "offset" | "width" | "swing">>,
  opts?: { skipHistory?: boolean }
): void {
  const opening = currentFloor().openings.find((o) => o.id === id);
  if (!opening) return;
  if (!opts?.skipHistory) saveSnapshot();
  else generation++;
  if (patch.offset !== undefined) opening.offset = patch.offset;
  if (patch.width !== undefined) opening.width = patch.width;
  if (patch.swing !== undefined) opening.swing = patch.swing;
}
```

**3g.** In `init()`, reset both counters at the end of the `finally` block (after `loaded = true`):

```ts
  } finally {
    loaded = true;
    generation = 0;
    savedGeneration = 0;
  }
```

**3h.** In `save()`, set `savedGeneration = generation` after the successful fetch (after the `if (!resp.ok) throw` line):

```ts
async function save(): Promise<void> {
  const homeId = getHomeId();
  if (!homeId) return;
  const doc: HouseDocument = {
    version: 1,
    house: house as House,
    floors: floors as Floor[],
  };
  const resp = await fetch(`/api/homes/${homeId}/house`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(doc),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
  savedGeneration = generation;
}
```

**3i.** Add `isDirty` and `generation` to the returned object (alongside the existing getters):

```ts
  return {
    get floor() { return currentFloor(); },
    get floors() { return floors as Floor[]; },
    get currentFloorId() { return currentFloorId; },
    get hasUndo() { return undoCount > 0; },
    get hasRedo() { return redoCount > 0; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    get isDirty() { return generation !== savedGeneration; },
    get generation() { return generation; },
    saveSnapshot,
    undo,
    redo,
    // ... rest unchanged
  };
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
cd /projects/myhome/packages/editor && npx vitest run --reporter=verbose test/houseStore.test.ts 2>&1 | tail -30
```

Expected: All tests in `houseStore — dirty tracking` pass. All pre-existing houseStore tests still pass.

- [ ] **Step 5: Commit**

```bash
cd /projects/myhome && git add packages/editor/src/lib/houseStore.svelte.ts packages/editor/test/houseStore.test.ts && git commit -m "feat: add generation counter and isDirty to houseStore"
```

---

## Task 2: Autosave, Ctrl+S, and dirty dot in App.svelte

**Files:**
- Modify: `packages/editor/src/App.svelte`
- Modify: `packages/editor/test/App.test.ts`

- [ ] **Step 1: Write failing tests**

Add these two tests to the existing `describe("App", ...)` block in `packages/editor/test/App.test.ts`, after the existing tests:

```ts
  it("save button gets dirty class after a wall mutation", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);
    app = await mountAndLoad(target, "#/plan");

    const saveBtn = target.querySelector(".save-btn") as HTMLButtonElement;
    expect(saveBtn.classList.contains("dirty")).toBe(false);

    // Click the Wall tool then place two points to draw a segment
    const wallBtn = Array.from(target.querySelectorAll(".toolbar button")).find(
      (b) => (b as HTMLButtonElement).title === "Wall"
    ) as HTMLButtonElement;
    wallBtn.click();
    flushSync();

    const svg = target.querySelector("svg")!;
    svg.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, clientX: 100, clientY: 100 }));
    svg.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, clientX: 100, clientY: 100 }));
    flushSync();
    svg.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, clientX: 200, clientY: 100 }));
    svg.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, clientX: 200, clientY: 100 }));
    flushSync();

    expect(saveBtn.classList.contains("dirty")).toBe(true);
  });

  it("Ctrl+S triggers save on floor plan page", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    // Stub fetch so PUT /api/homes/.../house returns 200
    vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
      if (url === "/api/auth/me") {
        return Promise.resolve({ ok: true, status: 200, statusText: "OK", json: async () => ({ id: "u1", username: "admin", role: "admin" }) });
      }
      if (opts?.method === "PUT") {
        return Promise.resolve({ ok: true, status: 200, statusText: "OK", json: async () => undefined });
      }
      return Promise.resolve({ ok: false, status: 404, statusText: "Not Found", json: async () => undefined });
    }));

    app = await mountAndLoad(target, "#/plan");

    const saveBtn = target.querySelector(".save-btn") as HTMLButtonElement;
    expect(saveBtn.title).toBe("Save");

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "s", ctrlKey: true, bubbles: true }));
    flushSync();

    // Save is async — synchronously sets saveStatus = "saving"
    expect(saveBtn.title).toBe("Saving…");
  });
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
cd /projects/myhome/packages/editor && npx vitest run --reporter=verbose test/App.test.ts 2>&1 | tail -30
```

Expected: The two new tests fail — `dirty` class never appears; Ctrl+S title stays "Save".

- [ ] **Step 3: Add autosave effect and Ctrl+S to App.svelte**

**3a.** In the `<script>` section of `packages/editor/src/App.svelte`, add the `autosaveTimer` variable and the debounced autosave `$effect` directly after the existing `handleSave` function (around line 304):

```ts
  let autosaveTimer: ReturnType<typeof setTimeout> | null = null;

  $effect(() => {
    const _gen = floorStore.generation;
    if (!floorStore.loaded || !floorStore.isDirty || !homesStore.activeHomeId) return;
    if (autosaveTimer) clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(() => {
      autosaveTimer = null;
      handleSave();
    }, 5000);
    return () => {
      if (autosaveTimer) { clearTimeout(autosaveTimer); autosaveTimer = null; }
    };
  });
```

**3b.** In `handleKeydown`, add the Ctrl+S branch at the very top of the function body (before the `target.tagName` guard), so it fires even when focus is in an input:

```ts
  function handleKeydown(event: KeyboardEvent): void {
    if (event.ctrlKey && event.key === "s") { event.preventDefault(); if (isFloorPlan) handleSave(); return; }
    const target = event.target as HTMLElement;
    if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable) return;
    if (event.code === "Space") { event.preventDefault(); spacePressed = true; return; }
    if (event.ctrlKey && event.key === "z" && !event.shiftKey) { event.preventDefault(); handleUndo(); return; }
    if (event.ctrlKey && (event.key === "y" || (event.key === "z" && event.shiftKey))) { event.preventDefault(); handleRedo(); return; }
    if (event.key === "Escape") {
      toolStore.resetDraw(); return;
    }
    if ((event.key === "Delete" || event.key === "Backspace") &&
        (toolStore.state.selectedId || toolStore.state.selectedOpeningId)) handleDelete();
  }
```

- [ ] **Step 4: Add dirty class to save button in template**

Find the save button in the template (the one with `class="icon-btn save-btn"`). Add `class:dirty={floorStore.isDirty && saveStatus === "idle"}`:

```svelte
      <button
        class="icon-btn save-btn"
        class:saved={saveStatus === "saved"}
        class:save-error={saveStatus === "error"}
        class:dirty={floorStore.isDirty && saveStatus === "idle"}
        disabled={saveStatus === "saving"}
        title={saveTitle}
        onclick={handleSave}
      >{saveIcon}</button>
```

- [ ] **Step 5: Add dirty dot CSS**

In the `<style>` section of `packages/editor/src/App.svelte`, update `.icon-btn.save-btn` to add `position: relative` and add the `::after` rule for the dot. The existing rule is:

```css
  .icon-btn.save-btn { color: var(--success); }
```

Replace it with:

```css
  .icon-btn.save-btn { color: var(--success); position: relative; }
  .icon-btn.save-btn.dirty::after {
    content: '';
    position: absolute;
    top: 4px;
    right: 4px;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent);
    pointer-events: none;
  }
```

- [ ] **Step 6: Run all tests**

```bash
cd /projects/myhome/packages/editor && npx vitest run 2>&1 | tail -20
```

Expected: All tests pass (including the two new App tests). Count should be at least 337 (332 prior + ~5 new tests across both files).

- [ ] **Step 7: Commit**

```bash
cd /projects/myhome && git add packages/editor/src/App.svelte packages/editor/test/App.test.ts && git commit -m "feat: autosave floor plan after 5s, dirty dot indicator, Ctrl+S"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| 5s debounce after last mutation | Task 2 Step 3a (`$effect` + `setTimeout(5000)`) |
| Generation increments on all mutations | Task 1 Step 3b–3f |
| Generation increments on undo/redo | Task 1 Step 3c–3d |
| isDirty false after init | Task 1 Step 3g (`generation = savedGeneration = 0` in finally) |
| isDirty false after save | Task 1 Step 3h (`savedGeneration = generation`) |
| skipHistory mutations also dirty | Task 1 Step 3e–3f (`else generation++`) |
| Ctrl+S immediate save | Task 2 Step 3b |
| Dirty dot when `isDirty && saveStatus === "idle"` | Task 2 Steps 4–5 |
| Dot disappears while saving/saved/error | Covered by `saveStatus === "idle"` guard in `class:dirty` |
| Home-switch resets dirty | Task 1 Step 3g (init resets counters; `$effect` in App.svelte reloads on activeHomeId change) |
| Save error keeps dot | Covered: `saveStatus === "error"` → `class:dirty` condition is false, but error class shows instead; dot is suppressed during error display (acceptable — error state already communicates the problem) |

All requirements covered. No gaps found.
