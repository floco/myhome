# Multi-Floor Support — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-floor `floorStore` with a `houseStore` that manages multiple independent floors, add a floor switcher to the top bar (buttons per floor + rename + delete + "+ Add Floor"), and migrate localStorage to a house-level document.

**Architecture:** `floorStore.svelte.ts` is replaced by `houseStore.svelte.ts` which stores `{ floors: Floor[], currentFloorId: string }` in a new localStorage key (`myhome.editor.house`). A migration path reads the old `myhome.editor.floor` key on first load so existing user data is preserved. All existing floor-mutation methods (addWall, removeWall, etc.) are kept with the same signatures — they now operate on the current floor. Undo/redo snapshots all floors simultaneously. A new `FloorSwitcher.svelte` component lives in the top bar. App.svelte changes are minimal: swap import, add FloorSwitcher to the topbar template.

**Tech Stack:** Svelte 5 runes, TypeScript, Vitest 4 / jsdom

---

## File Map

**Create:**
- `packages/editor/src/lib/houseStore.svelte.ts` — replaces floorStore
- `packages/editor/src/lib/components/FloorSwitcher.svelte` — new top-bar component

**Modify:**
- `packages/editor/src/App.svelte` — swap floorStore → houseStore, add FloorSwitcher
- `packages/editor/src/lib/sampleFloor.ts` — export `createSampleHouse()` helper

**Tests (modify):**
- `packages/editor/test/houseStore.test.ts` — new test file (replaces floorStore tests for new API)
- `packages/editor/test/App.test.ts` — fix any assertions that break

**Delete:** `packages/editor/src/lib/floorStore.svelte.ts` and `packages/editor/test/floorStore.test.ts` — only after houseStore tests cover all the same ground.

---

## Task 1: sampleFloor — add createSampleHouse helper

**Files:**
- Modify: `packages/editor/src/lib/sampleFloor.ts`

### Step 1: Read current sampleFloor.ts

Current content:
```typescript
import type { Floor } from "@myhome/geometry";

export const SAMPLE_FLOOR: Floor = {
  id: "floor-1",
  name: "Ground Floor",
  order: 0,
  walls: [
    { id: "wall-1", type: "wall", start: { x: 0, y: 0 }, end: { x: 4, y: 0 }, thickness: 0.1 },
    { id: "wall-2", type: "wall", start: { x: 4, y: 0 }, end: { x: 4, y: 3 }, thickness: 0.1 },
    { id: "wall-3", type: "wall", start: { x: 4, y: 3 }, end: { x: 0, y: 3 }, thickness: 0.1 },
    { id: "wall-4", type: "wall", start: { x: 0, y: 3 }, end: { x: 0, y: 0 }, thickness: 0.1 },
    { id: "divider-1", type: "divider", start: { x: 2, y: 0 }, end: { x: 2, y: 3 } },
  ],
  openings: [],
  rooms: [],
};

export function createSampleFloor(): Floor {
  return structuredClone(SAMPLE_FLOOR);
}
```

### Step 2: Add `createSampleHouse`

Append to `packages/editor/src/lib/sampleFloor.ts`:

```typescript
export interface HouseData {
  floors: import("@myhome/geometry").Floor[];
  currentFloorId: string;
}

export function createSampleHouse(): HouseData {
  const floor = createSampleFloor();
  return { floors: [floor], currentFloorId: floor.id };
}
```

### Step 3: Run tests — all still pass (no breakage)
```bash
cd /projects/myhome/.worktrees/multi-floor && npm test --workspace=packages/editor 2>&1 | tail -8
```

### Step 4: Commit
```bash
cd /projects/myhome/.worktrees/multi-floor && git add packages/editor/src/lib/sampleFloor.ts && git commit -m "feat(editor): add createSampleHouse helper to sampleFloor"
```

---

## Task 2: houseStore — full multi-floor store

**Files:**
- Create: `packages/editor/src/lib/houseStore.svelte.ts`
- Create: `packages/editor/test/houseStore.test.ts`

### Step 1: Write failing tests

Create `packages/editor/test/houseStore.test.ts`:

```typescript
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { createHouseStore, HOUSE_STORAGE_KEY } from "../src/lib/houseStore.svelte";

describe("houseStore — initial state", () => {
  beforeEach(() => { localStorage.clear(); });

  it("starts with one floor and detects two rooms from the sample floor", () => {
    const store = createHouseStore();
    expect(store.floors.length).toBe(1);
    expect(store.floor.rooms.length).toBe(2);
  });

  it("currentFloorId matches the single floor's id", () => {
    const store = createHouseStore();
    expect(store.currentFloorId).toBe(store.floors[0].id);
  });
});

describe("houseStore — floor management", () => {
  beforeEach(() => { localStorage.clear(); });

  it("addFloor adds a new empty floor and switches to it", () => {
    const store = createHouseStore();
    const before = store.floors.length;
    store.addFloor("First Floor");
    expect(store.floors.length).toBe(before + 1);
    const newFloor = store.floors[store.floors.length - 1];
    expect(newFloor.name).toBe("First Floor");
    expect(store.currentFloorId).toBe(newFloor.id);
    expect(store.floor.walls.length).toBe(0);
  });

  it("switchFloor changes the active floor", () => {
    const store = createHouseStore();
    store.addFloor("Upstairs");
    const upstairs = store.floors[store.floors.length - 1].id;
    const groundId = store.floors[0].id;
    store.switchFloor(groundId);
    expect(store.currentFloorId).toBe(groundId);
    store.switchFloor(upstairs);
    expect(store.currentFloorId).toBe(upstairs);
  });

  it("renameFloor changes the floor name", () => {
    const store = createHouseStore();
    const id = store.floors[0].id;
    store.renameFloor(id, "Basement");
    expect(store.floors.find((f) => f.id === id)?.name).toBe("Basement");
  });

  it("removeFloor removes the floor and switches to the first remaining floor", () => {
    const store = createHouseStore();
    store.addFloor("Upstairs");
    const upstairs = store.floors[store.floors.length - 1].id;
    const groundId = store.floors[0].id;
    store.switchFloor(upstairs);
    store.removeFloor(upstairs);
    expect(store.floors.some((f) => f.id === upstairs)).toBe(false);
    expect(store.currentFloorId).toBe(groundId);
  });

  it("removeFloor is a no-op when only one floor remains", () => {
    const store = createHouseStore();
    const id = store.floors[0].id;
    store.removeFloor(id);
    expect(store.floors.length).toBe(1);
    expect(store.currentFloorId).toBe(id);
  });

  it("addFloor assigns incrementing order values", () => {
    const store = createHouseStore();
    store.addFloor("F2");
    store.addFloor("F3");
    const orders = store.floors.map((f) => f.order);
    expect(orders[0]).toBe(0);
    expect(orders[1]).toBe(1);
    expect(orders[2]).toBe(2);
  });
});

describe("houseStore — floor mutations (forwarded to current floor)", () => {
  beforeEach(() => { localStorage.clear(); });

  it("addWall on the current floor does not affect other floors", () => {
    const store = createHouseStore();
    const groundWallsBefore = store.floors[0].walls.length;
    store.addFloor("F2");
    store.addWall({ id: "w-x", start: { x: 10, y: 0 }, end: { x: 20, y: 0 }, type: "wall", thickness: 0.1 });
    // Ground floor is unaffected
    store.switchFloor(store.floors[0].id);
    expect(store.floor.walls.length).toBe(groundWallsBefore);
    // F2 has the new wall
    const f2 = store.floors.find((f) => f.name === "F2")!;
    expect(f2.walls.some((w) => w.id === "w-x")).toBe(true);
  });
});

describe("houseStore — undo/redo across floors", () => {
  beforeEach(() => { localStorage.clear(); });

  it("undo reverts addFloor", () => {
    const store = createHouseStore();
    const before = store.floors.length;
    store.addFloor("F2");
    expect(store.floors.length).toBe(before + 1);
    store.undo();
    expect(store.floors.length).toBe(before);
  });

  it("redo re-applies addFloor", () => {
    const store = createHouseStore();
    const before = store.floors.length;
    store.addFloor("F2");
    store.undo();
    store.redo();
    expect(store.floors.length).toBe(before + 1);
  });

  it("hasUndo is false initially and true after addFloor", () => {
    const store = createHouseStore();
    expect(store.hasUndo).toBe(false);
    store.addFloor("F2");
    expect(store.hasUndo).toBe(true);
  });
});

describe("houseStore — persistence", () => {
  beforeEach(() => { localStorage.clear(); });
  afterEach(() => { vi.useRealTimers(); });

  it("persists to the house storage key after 300ms", () => {
    vi.useFakeTimers();
    const store = createHouseStore();
    store.addFloor("Attic");
    vi.advanceTimersByTime(300);
    const saved = JSON.parse(localStorage.getItem(HOUSE_STORAGE_KEY)!);
    expect(Array.isArray(saved.floors)).toBe(true);
    expect(saved.floors.some((f: { name: string }) => f.name === "Attic")).toBe(true);
  });

  it("migrates old myhome.editor.floor data on first load", () => {
    const { STORAGE_KEY } = await import("../src/lib/floorStore.svelte");
    const oldFloor = {
      id: "old-floor",
      name: "Old Floor",
      order: 0,
      walls: [{ id: "w1", type: "wall", start: { x: 0, y: 0 }, end: { x: 5, y: 0 }, thickness: 0.1 }],
      openings: [],
      rooms: [],
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(oldFloor));
    const store = createHouseStore();
    expect(store.floors.length).toBe(1);
    expect(store.floor.walls.some((w) => w.id === "w1")).toBe(true);
  });
});
```

### Step 2: Run — expect failures
```bash
cd /projects/myhome/.worktrees/multi-floor && npm test --workspace=packages/editor 2>&1 | tail -20
```

### Step 3: Implement `packages/editor/src/lib/houseStore.svelte.ts`

```typescript
import { detectRooms, matchRooms, pointsEqual } from "@myhome/geometry";
import type { Floor, Wall, Opening, Room, Point } from "@myhome/geometry";
import { createSampleHouse } from "./sampleFloor";

export const HOUSE_STORAGE_KEY = "myhome.editor.house";
const OLD_FLOOR_STORAGE_KEY = "myhome.editor.floor";
const PERSIST_DEBOUNCE_MS = 300;
const MAX_HISTORY = 50;

interface HouseState {
  floors: Floor[];
  currentFloorId: string;
}

function cloneState(s: HouseState): HouseState {
  return JSON.parse(JSON.stringify(s));
}

function loadState(): HouseState {
  if (typeof localStorage === "undefined") return createSampleHouse();

  // New key
  const raw = localStorage.getItem(HOUSE_STORAGE_KEY);
  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      if (parsed && Array.isArray(parsed.floors) && parsed.floors.length > 0 && typeof parsed.currentFloorId === "string") {
        return parsed as HouseState;
      }
    } catch { /* fall through */ }
  }

  // Migrate from old single-floor key
  const oldRaw = localStorage.getItem(OLD_FLOOR_STORAGE_KEY);
  if (oldRaw) {
    try {
      const oldFloor = JSON.parse(oldRaw);
      if (oldFloor && Array.isArray(oldFloor.walls) && Array.isArray(oldFloor.openings)) {
        if (!oldFloor.id) oldFloor.id = "floor-1";
        if (!oldFloor.name) oldFloor.name = "Ground Floor";
        if (oldFloor.order === undefined) oldFloor.order = 0;
        if (!Array.isArray(oldFloor.rooms)) oldFloor.rooms = [];
        return { floors: [oldFloor as Floor], currentFloorId: oldFloor.id };
      }
    } catch { /* fall through */ }
  }

  return createSampleHouse();
}

function genId(): string {
  return crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export function createHouseStore() {
  const loaded = loadState();
  const floors = $state<Floor[]>(loaded.floors);
  let currentFloorId = $state<string>(loaded.currentFloorId);
  let persistTimer: ReturnType<typeof setTimeout> | undefined;

  const undoStack: HouseState[] = [];
  const redoStack: HouseState[] = [];
  let undoCount = $state(0);
  let redoCount = $state(0);

  function getState(): HouseState {
    return { floors: floors as Floor[], currentFloorId };
  }

  function applyState(s: HouseState): void {
    floors.length = 0;
    for (const f of s.floors) floors.push(f);
    currentFloorId = s.currentFloorId;
  }

  function saveSnapshot(): void {
    undoStack.push(cloneState(getState()));
    if (undoStack.length > MAX_HISTORY) undoStack.shift();
    redoStack.length = 0;
    undoCount = undoStack.length;
    redoCount = 0;
  }

  function undo(): void {
    const prev = undoStack.pop();
    if (!prev) return;
    redoStack.push(cloneState(getState()));
    applyState(prev);
    undoCount = undoStack.length;
    redoCount = redoStack.length;
    persist();
  }

  function redo(): void {
    const next = redoStack.pop();
    if (!next) return;
    undoStack.push(cloneState(getState()));
    applyState(next);
    undoCount = undoStack.length;
    redoCount = redoStack.length;
    persist();
  }

  function persist(): void {
    if (typeof localStorage === "undefined") return;
    if (persistTimer) clearTimeout(persistTimer);
    persistTimer = setTimeout(() => {
      localStorage.setItem(HOUSE_STORAGE_KEY, JSON.stringify(getState()));
    }, PERSIST_DEBOUNCE_MS);
  }

  function currentFloor(): Floor {
    return floors.find((f) => f.id === currentFloorId) ?? floors[0];
  }

  function recomputeRooms(): void {
    const floor = currentFloor();
    const detected = detectRooms(floor.walls);
    const { rooms } = matchRooms(detected, floor.rooms);
    floor.rooms = rooms.filter((r) => r.polygon !== null);
  }

  function commitWalls(): void {
    recomputeRooms();
    persist();
  }

  // ── Floor management ──────────────────────────────────────────────────────

  function addFloor(name: string): void {
    saveSnapshot();
    const maxOrder = floors.reduce((m, f) => Math.max(m, f.order), -1);
    const newFloor: Floor = {
      id: genId(),
      name,
      order: maxOrder + 1,
      walls: [],
      openings: [],
      rooms: [],
    };
    floors.push(newFloor);
    currentFloorId = newFloor.id;
    persist();
  }

  function removeFloor(id: string): void {
    if (floors.length <= 1) return;
    saveSnapshot();
    const idx = floors.findIndex((f) => f.id === id);
    if (idx === -1) return;
    floors.splice(idx, 1);
    if (currentFloorId === id) {
      currentFloorId = floors[Math.max(0, idx - 1)].id;
    }
    persist();
  }

  function renameFloor(id: string, name: string): void {
    const floor = floors.find((f) => f.id === id);
    if (!floor) return;
    saveSnapshot();
    floor.name = name;
    persist();
  }

  function switchFloor(id: string): void {
    if (floors.some((f) => f.id === id)) {
      currentFloorId = id;
    }
  }

  // ── Floor mutations (operate on current floor) ────────────────────────────

  function addWall(wall: Wall): void {
    saveSnapshot();
    currentFloor().walls.push(wall);
    commitWalls();
  }

  function removeWall(id: string): void {
    saveSnapshot();
    const floor = currentFloor();
    floor.walls = floor.walls.filter((w) => w.id !== id);
    floor.openings = floor.openings.filter((o) => o.wallId !== id);
    commitWalls();
  }

  function moveSharedPoint(from: Point, to: Point, opts?: { skipHistory?: boolean }): void {
    if (!opts?.skipHistory) saveSnapshot();
    for (const wall of currentFloor().walls) {
      if (pointsEqual(wall.start, from)) wall.start = to;
      if (pointsEqual(wall.end, from)) wall.end = to;
    }
    commitWalls();
  }

  function addOpening(opening: Opening): void {
    saveSnapshot();
    currentFloor().openings.push(opening);
    persist();
  }

  function removeOpening(id: string): void {
    saveSnapshot();
    const floor = currentFloor();
    floor.openings = floor.openings.filter((o) => o.id !== id);
    persist();
  }

  function updateOpening(
    id: string,
    patch: Partial<Pick<Opening, "offset" | "width" | "swing">>,
    opts?: { skipHistory?: boolean }
  ): void {
    const opening = currentFloor().openings.find((o) => o.id === id);
    if (!opening) return;
    if (!opts?.skipHistory) saveSnapshot();
    if (patch.offset !== undefined) opening.offset = patch.offset;
    if (patch.width !== undefined) opening.width = patch.width;
    if (patch.swing !== undefined) opening.swing = patch.swing;
    persist();
  }

  function updateRoom(id: string, patch: Partial<Pick<Room, "label" | "haAreaId">>): void {
    const room = currentFloor().rooms.find((r) => r.id === id);
    if (!room) return;
    saveSnapshot();
    if (patch.label !== undefined) room.label = patch.label;
    if (patch.haAreaId !== undefined) room.haAreaId = patch.haAreaId;
    persist();
  }

  function openingOverlaps(wallId: string, excludeId: string | null, from: number, to: number): boolean {
    return currentFloor().openings.some(
      (o) => o.wallId === wallId && o.id !== excludeId && from < o.offset + o.width && to > o.offset
    );
  }

  // Seed room detection on startup
  for (const f of floors) {
    const detected = detectRooms(f.walls);
    const { rooms } = matchRooms(detected, f.rooms);
    f.rooms = rooms.filter((r) => r.polygon !== null);
  }

  return {
    get floor() { return currentFloor(); },
    get floors() { return floors as Floor[]; },
    get currentFloorId() { return currentFloorId; },
    get hasUndo() { return undoCount > 0; },
    get hasRedo() { return redoCount > 0; },
    saveSnapshot,
    undo,
    redo,
    addFloor,
    removeFloor,
    renameFloor,
    switchFloor,
    addWall,
    removeWall,
    moveSharedPoint,
    addOpening,
    removeOpening,
    updateOpening,
    updateRoom,
    openingOverlaps,
  };
}
```

**Note on the migration test:** The migration test uses `await import(...)` to get `STORAGE_KEY` from the old floorStore. That will break once floorStore is deleted, but for now we keep both files. If this causes issues, hardcode the string `"myhome.editor.floor"` in the test instead of importing.

### Step 4: Run tests — all must pass
```bash
cd /projects/myhome/.worktrees/multi-floor && npm test --workspace=packages/editor 2>&1 | tail -15
```

If the migration test cannot import `STORAGE_KEY` (because we deleted floorStore), replace the import with:
```typescript
const STORAGE_KEY = "myhome.editor.floor";
```

### Step 5: Commit
```bash
cd /projects/myhome/.worktrees/multi-floor && git add packages/editor/src/lib/houseStore.svelte.ts packages/editor/test/houseStore.test.ts && git commit -m "feat(editor): houseStore — multi-floor state, floor CRUD, undo/redo"
```

---

## Task 3: FloorSwitcher component

**Files:**
- Create: `packages/editor/src/lib/components/FloorSwitcher.svelte`

### Step 1: Implement FloorSwitcher.svelte

```svelte
<script lang="ts">
  import type { Floor } from "@myhome/geometry";

  let {
    floors,
    currentFloorId,
    onswitchfloor,
    onaddfloor,
    onrenamefloor,
    onremovefloor,
  }: {
    floors: Floor[];
    currentFloorId: string;
    onswitchfloor: (id: string) => void;
    onaddfloor: (name: string) => void;
    onrenamefloor: (id: string, name: string) => void;
    onremovefloor: (id: string) => void;
  } = $props();

  let editingId = $state<string | null>(null);
  let editingName = $state("");

  function startRename(floor: Floor, event: MouseEvent): void {
    if (floor.id !== currentFloorId) {
      onswitchfloor(floor.id);
      return;
    }
    // Double-click on active floor → rename
    if ((event as MouseEvent & { detail: number }).detail === 2) {
      editingId = floor.id;
      editingName = floor.name;
    }
  }

  function commitRename(): void {
    if (!editingId) return;
    const trimmed = editingName.trim();
    if (trimmed) onrenamefloor(editingId, trimmed);
    editingId = null;
  }

  function handleRenameKey(event: KeyboardEvent): void {
    if (event.key === "Enter") commitRename();
    if (event.key === "Escape") editingId = null;
  }

  function handleAddFloor(): void {
    const n = floors.length + 1;
    const names = ["Ground Floor", "First Floor", "Second Floor", "Third Floor", "Basement"];
    const name = names[n - 1] ?? `Floor ${n}`;
    onaddfloor(name);
  }
</script>

<div class="floor-switcher">
  {#each floors as floor (floor.id)}
    <div class="floor-btn" class:active={floor.id === currentFloorId}>
      {#if editingId === floor.id}
        <input
          class="rename-input"
          bind:value={editingName}
          onblur={commitRename}
          onkeydown={handleRenameKey}
          autofocus
        />
      {:else}
        <button
          class="floor-label"
          onclick={(e) => startRename(floor, e)}
          title={floor.id === currentFloorId ? "Double-click to rename" : "Switch to this floor"}
        >
          {floor.name}
        </button>
      {/if}
      {#if floors.length > 1}
        <button
          class="remove-btn"
          onclick={() => onremovefloor(floor.id)}
          title="Delete floor"
          aria-label="Delete {floor.name}"
        >×</button>
      {/if}
    </div>
  {/each}
  <button class="add-btn" onclick={handleAddFloor}>+ Floor</button>
</div>

<style>
  .floor-switcher {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .floor-btn {
    display: flex;
    align-items: center;
    border-radius: 4px;
    background: #444;
    overflow: hidden;
  }

  .floor-btn.active {
    background: #555;
    outline: 1px solid #5af;
  }

  .floor-label {
    padding: 3px 8px;
    border: none;
    background: transparent;
    color: #ccc;
    cursor: pointer;
    font-size: 12px;
    white-space: nowrap;
  }

  .floor-btn.active .floor-label {
    color: #eee;
  }

  .remove-btn {
    padding: 3px 5px;
    border: none;
    border-left: 1px solid #333;
    background: transparent;
    color: #888;
    cursor: pointer;
    font-size: 11px;
    line-height: 1;
  }

  .remove-btn:hover {
    color: #f66;
    background: rgba(255, 0, 0, 0.1);
  }

  .rename-input {
    width: 90px;
    padding: 2px 6px;
    background: #2a2a2a;
    border: 1px solid #5af;
    border-radius: 2px;
    color: #eee;
    font-size: 12px;
  }

  .add-btn {
    padding: 3px 8px;
    border: none;
    border-radius: 4px;
    background: #383838;
    color: #aaa;
    cursor: pointer;
    font-size: 12px;
  }

  .add-btn:hover {
    background: #444;
    color: #ccc;
  }
</style>
```

### Step 2: Run tests — still pass
```bash
cd /projects/myhome/.worktrees/multi-floor && npm test --workspace=packages/editor 2>&1 | tail -8
```

### Step 3: Commit
```bash
cd /projects/myhome/.worktrees/multi-floor && git add packages/editor/src/lib/components/FloorSwitcher.svelte && git commit -m "feat(editor): FloorSwitcher component (switch, rename, delete, add)"
```

---

## Task 4: App.svelte — swap floorStore → houseStore, add FloorSwitcher

**Files:**
- Modify: `packages/editor/src/App.svelte`
- Modify: `packages/editor/test/App.test.ts`

### Step 1: Read current App.svelte

Read the full file before editing.

### Step 2: Apply changes

**Change 1 — swap import:**
```typescript
// Remove:
import { createFloorStore } from "./lib/floorStore.svelte";
// Add:
import { createHouseStore } from "./lib/houseStore.svelte";
```

**Change 2 — add FloorSwitcher import:**
```typescript
import FloorSwitcher from "./lib/components/FloorSwitcher.svelte";
```

**Change 3 — rename store:**
```typescript
// Remove:
const floorStore = createFloorStore();
// Add:
const floorStore = createHouseStore();
```
(Keep the variable name `floorStore` so no other code changes are needed — all existing uses of `floorStore.floor`, `floorStore.addWall`, etc. continue to work.)

**Change 4 — add FloorSwitcher to the topbar template:**

Find the `<header class="topbar">` block and add the FloorSwitcher between the h1 and the reset button:
```svelte
<header class="topbar">
  <h1>Floor Plan Editor</h1>
  <FloorSwitcher
    floors={floorStore.floors}
    currentFloorId={floorStore.currentFloorId}
    onswitchfloor={(id) => floorStore.switchFloor(id)}
    onaddfloor={(name) => floorStore.addFloor(name)}
    onrenamefloor={(id, name) => floorStore.renameFloor(id, name)}
    onremovefloor={(id) => floorStore.removeFloor(id)}
  />
  <button class="reset-view" onclick={() => viewportStore.reset()}>Reset View</button>
</header>
```

**Change 5 — fix reset-view style** to prevent it from being squeezed (add `flex-shrink: 0` if needed).

### Step 3: Delete old floorStore files

```bash
cd /projects/myhome/.worktrees/multi-floor && rm packages/editor/src/lib/floorStore.svelte.ts packages/editor/test/floorStore.test.ts
```

### Step 4: Run tests and fix any breakage
```bash
cd /projects/myhome/.worktrees/multi-floor && npm test --workspace=packages/editor 2>&1 | tail -20
```

Expected breakage: `App.test.ts` imports `STORAGE_KEY` from `floorStore.svelte`. Fix that import:

```typescript
// Remove:
import { STORAGE_KEY } from "../src/lib/floorStore.svelte";
// Add:
import { HOUSE_STORAGE_KEY as STORAGE_KEY } from "../src/lib/houseStore.svelte";
```

Then update the test that checks `localStorage.getItem(STORAGE_KEY)` — the key is now `myhome.editor.house` and the saved format is `{ floors: [...], currentFloorId: "..." }`. Update the assertion in the "dragging a selected wall's endpoint" test:

```typescript
// Old:
const saved = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
const wall1Data = saved.walls.find((w: { id: string }) => w.id === "wall-1");
const wall4Data = saved.walls.find((w: { id: string }) => w.id === "wall-4");
// New:
const saved = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
const wall1Data = saved.floors[0].walls.find((w: { id: string }) => w.id === "wall-1");
const wall4Data = saved.floors[0].walls.find((w: { id: string }) => w.id === "wall-4");
```

Also update the "persists after 300ms" test in `floorStore` (now deleted) — those tests are in `houseStore.test.ts` already.

The "dragging an endpoint onto its own wall" test checks `localStorage.getItem(STORAGE_KEY)` is null — this still holds since houseStore also only persists after 300ms and we don't advance timers.

### Step 5: Run tests — all must pass
```bash
cd /projects/myhome/.worktrees/multi-floor && npm test --workspace=packages/editor 2>&1 | tail -10
```

### Step 6: Commit
```bash
cd /projects/myhome/.worktrees/multi-floor && git add -A && git commit -m "feat(editor): replace floorStore with houseStore; add FloorSwitcher to topbar"
```

---

## Self-Review

- [x] `houseStore.get floor()` returns the current floor — all of App.svelte works unchanged
- [x] `floorStore` variable name kept in App.svelte — zero other changes needed
- [x] All floor-mutation methods (addWall etc.) forward to `currentFloor()` getter — correct
- [x] Migration reads old `myhome.editor.floor` key so existing localStorage data is preserved
- [x] `removeFloor` is no-op when only one floor remains — no orphaned state
- [x] Undo/redo snapshots all floors — addFloor/removeFloor are undoable
- [x] `switchFloor` is NOT on the undo stack — navigation action, not an edit
- [x] `FloorSwitcher` double-click rename only activates on the ALREADY-ACTIVE floor; single-click on inactive floors switches
- [x] `houseStore` tests cover: initial state, floor CRUD, floor isolation (mutations on one floor don't affect others), undo/redo, persistence, migration
