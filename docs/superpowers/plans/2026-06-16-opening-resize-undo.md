# Opening Resize, Undo/Redo & Overlap Prevention — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent overlapping openings, allow resizing placed openings by dragging their endpoints, and add Undo/Redo (Ctrl+Z / Ctrl+Shift+Z, max 50 steps).

**Architecture:** `floorStore` gains a snapshot-based undo/redo stack (plain arrays, reactive length counters), `saveSnapshot()` for explicit pre-drag saves, and `skipHistory` flags on live-drag mutations. Opening resize reuses the wall-endpoint drag pattern: `OpeningShape` renders handles when selected, App projects cursor onto the wall and calls `updateOpening({skipHistory:true})` during drag. Overlap checks run at placement time and during drag.

**Tech Stack:** Svelte 5 runes, TypeScript, Vitest 4 / jsdom

---

## File Map

**Modify:**
- `packages/editor/src/lib/floorStore.svelte.ts` — undo/redo stack; `updateOpening`; `saveSnapshot`; `skipHistory` opts on `moveSharedPoint` and `updateOpening`; overlap check helper
- `packages/editor/src/lib/toolStore.svelte.ts` — `draggingOpeningHandle` state; `startOpeningDrag`/`endOpeningDrag`
- `packages/editor/src/lib/components/OpeningShape.svelte` — render resize handles when selected; emit `ondraghandlestart`
- `packages/editor/src/lib/components/Canvas.svelte` — plumb `ondragopeninghandlestart` prop
- `packages/editor/src/lib/components/Toolbar.svelte` — Undo/Redo buttons
- `packages/editor/src/App.svelte` — overlap guard at placement; opening handle drag logic; undo/redo wiring; keyboard shortcuts

**Tests (modify):**
- `packages/editor/test/floorStore.test.ts`
- `packages/editor/test/toolStore.test.ts`
- `packages/editor/test/App.test.ts`

---

## Task 1: floorStore — undo/redo + updateOpening + overlap helper + skipHistory

**Files:**
- Modify: `packages/editor/src/lib/floorStore.svelte.ts`
- Modify: `packages/editor/test/floorStore.test.ts`

### Step 1: Write failing tests

Add to `packages/editor/test/floorStore.test.ts`:

```typescript
describe("floorStore — undo/redo", () => {
  beforeEach(() => { localStorage.clear(); });

  it("undo reverts the last addWall", () => {
    const store = createFloorStore();
    const before = store.floor.walls.length;
    store.addWall({ id: "w-new", start: { x: 10, y: 10 }, end: { x: 20, y: 10 }, type: "wall", thickness: 0.15 });
    expect(store.floor.walls.length).toBe(before + 1);
    store.undo();
    expect(store.floor.walls.length).toBe(before);
  });

  it("redo re-applies the reverted action", () => {
    const store = createFloorStore();
    const before = store.floor.walls.length;
    store.addWall({ id: "w-new", start: { x: 10, y: 10 }, end: { x: 20, y: 10 }, type: "wall", thickness: 0.15 });
    store.undo();
    store.redo();
    expect(store.floor.walls.length).toBe(before + 1);
  });

  it("mutation after undo clears the redo stack", () => {
    const store = createFloorStore();
    store.addWall({ id: "w1", start: { x: 10, y: 0 }, end: { x: 20, y: 0 }, type: "wall", thickness: 0.15 });
    store.undo();
    expect(store.hasRedo).toBe(true);
    store.addWall({ id: "w2", start: { x: 30, y: 0 }, end: { x: 40, y: 0 }, type: "wall", thickness: 0.15 });
    expect(store.hasRedo).toBe(false);
  });

  it("hasUndo is false initially and true after a mutation", () => {
    const store = createFloorStore();
    // clear any history from sample floor construction
    expect(store.hasUndo).toBe(false);
    store.addWall({ id: "w-x", start: { x: 50, y: 0 }, end: { x: 60, y: 0 }, type: "wall", thickness: 0.15 });
    expect(store.hasUndo).toBe(true);
  });

  it("undo on empty stack is a no-op", () => {
    const store = createFloorStore();
    expect(() => store.undo()).not.toThrow();
  });
});

describe("floorStore — updateOpening", () => {
  beforeEach(() => { localStorage.clear(); });

  it("updateOpening changes offset and width", () => {
    const store = createFloorStore();
    const wallId = store.floor.walls.find((w) => w.type === "wall")?.id;
    expect(wallId).toBeDefined();
    store.addOpening({ id: "op1", wallId: wallId!, type: "window", offset: 1, width: 1.2 });
    store.updateOpening("op1", { offset: 2, width: 0.9 });
    const op = store.floor.openings.find((o) => o.id === "op1");
    expect(op?.offset).toBeCloseTo(2, 5);
    expect(op?.width).toBeCloseTo(0.9, 5);
  });

  it("updateOpening with skipHistory does not add to undo stack", () => {
    const store = createFloorStore();
    const wallId = store.floor.walls.find((w) => w.type === "wall")?.id;
    expect(wallId).toBeDefined();
    store.addOpening({ id: "op1", wallId: wallId!, type: "window", offset: 1, width: 1.2 });
    const undoCountBefore = store.hasUndo; // true after addOpening
    store.updateOpening("op1", { width: 0.8 }, { skipHistory: true });
    // undo count should not have grown; undo should revert addOpening, not updateOpening
    store.undo(); // should revert addOpening
    expect(store.floor.openings.find((o) => o.id === "op1")).toBeUndefined();
  });
});

describe("floorStore — openingOverlaps", () => {
  beforeEach(() => { localStorage.clear(); });

  it("openingOverlaps returns false when no openings exist", () => {
    const store = createFloorStore();
    expect(store.openingOverlaps("w1", null, 1, 2)).toBe(false);
  });

  it("openingOverlaps returns true when a new opening would overlap an existing one", () => {
    const store = createFloorStore();
    const wallId = store.floor.walls.find((w) => w.type === "wall")?.id;
    expect(wallId).toBeDefined();
    store.addOpening({ id: "op1", wallId: wallId!, type: "window", offset: 1, width: 1.2 });
    // [1, 2.2] already exists; [1.5, 2.7] overlaps
    expect(store.openingOverlaps(wallId!, null, 1.5, 2.7)).toBe(true);
  });

  it("openingOverlaps returns false for non-overlapping range", () => {
    const store = createFloorStore();
    const wallId = store.floor.walls.find((w) => w.type === "wall")?.id;
    expect(wallId).toBeDefined();
    store.addOpening({ id: "op1", wallId: wallId!, type: "window", offset: 1, width: 1.2 });
    // [1, 2.2] exists; [3, 4] is clear
    expect(store.openingOverlaps(wallId!, null, 3, 4)).toBe(false);
  });

  it("openingOverlaps excludes the opening being resized (self)", () => {
    const store = createFloorStore();
    const wallId = store.floor.walls.find((w) => w.type === "wall")?.id;
    expect(wallId).toBeDefined();
    store.addOpening({ id: "op1", wallId: wallId!, type: "window", offset: 1, width: 1.2 });
    // Checking if "op1" itself would overlap [1, 2.2] — should return false (self excluded)
    expect(store.openingOverlaps(wallId!, "op1", 1, 2.2)).toBe(false);
  });
});
```

### Step 2: Run tests — expect failures
```bash
cd /projects/myhome/.worktrees/opening-tools-undo && npm test --workspace=packages/editor 2>&1 | tail -20
```

### Step 3: Implement

Replace `packages/editor/src/lib/floorStore.svelte.ts` with:

```typescript
import { detectRooms, matchRooms, pointsEqual } from "@myhome/geometry";
import type { Floor, Wall, Opening, Room, Point } from "@myhome/geometry";
import { createSampleFloor } from "./sampleFloor";

export const STORAGE_KEY = "myhome.editor.floor";
const PERSIST_DEBOUNCE_MS = 300;
const MAX_HISTORY = 50;

function cloneFloor(f: Floor): Floor {
  return JSON.parse(JSON.stringify(f));
}

function loadFloor(): Floor {
  if (typeof localStorage === "undefined") return createSampleFloor();
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return createSampleFloor();
  try {
    const parsed = JSON.parse(raw);
    if (
      !parsed ||
      typeof parsed !== "object" ||
      !Array.isArray(parsed.walls) ||
      !Array.isArray(parsed.rooms) ||
      !Array.isArray(parsed.openings)
    ) {
      return createSampleFloor();
    }
    return parsed as Floor;
  } catch {
    return createSampleFloor();
  }
}

export function createFloorStore() {
  const floor = $state<Floor>(loadFloor());
  let persistTimer: ReturnType<typeof setTimeout> | undefined;

  // Undo/redo stacks — plain arrays (not reactive)
  const undoStack: Floor[] = [];
  const redoStack: Floor[] = [];
  let undoCount = $state(0);
  let redoCount = $state(0);

  function saveSnapshot(): void {
    undoStack.push(cloneFloor(floor));
    if (undoStack.length > MAX_HISTORY) undoStack.shift();
    redoStack.length = 0;
    undoCount = undoStack.length;
    redoCount = 0;
  }

  function applyFloor(snapshot: Floor): void {
    floor.walls = snapshot.walls;
    floor.openings = snapshot.openings;
    floor.rooms = snapshot.rooms;
  }

  function undo(): void {
    const prev = undoStack.pop();
    if (!prev) return;
    redoStack.push(cloneFloor(floor));
    applyFloor(prev);
    undoCount = undoStack.length;
    redoCount = redoStack.length;
    persist();
  }

  function redo(): void {
    const next = redoStack.pop();
    if (!next) return;
    undoStack.push(cloneFloor(floor));
    applyFloor(next);
    undoCount = undoStack.length;
    redoCount = redoStack.length;
    persist();
  }

  function recomputeRooms(): void {
    const detected = detectRooms(floor.walls);
    const { rooms } = matchRooms(detected, floor.rooms);
    floor.rooms = rooms.filter((r) => r.polygon !== null);
  }

  function persist(): void {
    if (typeof localStorage === "undefined") return;
    if (persistTimer) clearTimeout(persistTimer);
    persistTimer = setTimeout(() => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(floor));
    }, PERSIST_DEBOUNCE_MS);
  }

  function commitWalls(): void {
    recomputeRooms();
    persist();
  }

  function addWall(wall: Wall): void {
    saveSnapshot();
    floor.walls.push(wall);
    commitWalls();
  }

  function removeWall(id: string): void {
    saveSnapshot();
    floor.walls = floor.walls.filter((w) => w.id !== id);
    floor.openings = floor.openings.filter((o) => o.wallId !== id);
    commitWalls();
  }

  function moveSharedPoint(from: Point, to: Point, opts?: { skipHistory?: boolean }): void {
    if (!opts?.skipHistory) saveSnapshot();
    for (const wall of floor.walls) {
      if (pointsEqual(wall.start, from)) wall.start = to;
      if (pointsEqual(wall.end, from)) wall.end = to;
    }
    commitWalls();
  }

  function addOpening(opening: Opening): void {
    saveSnapshot();
    floor.openings.push(opening);
    persist();
  }

  function removeOpening(id: string): void {
    saveSnapshot();
    floor.openings = floor.openings.filter((o) => o.id !== id);
    persist();
  }

  function updateOpening(
    id: string,
    patch: Partial<Pick<Opening, "offset" | "width" | "swing">>,
    opts?: { skipHistory?: boolean }
  ): void {
    if (!opts?.skipHistory) saveSnapshot();
    const opening = floor.openings.find((o) => o.id === id);
    if (!opening) return;
    if (patch.offset !== undefined) opening.offset = patch.offset;
    if (patch.width !== undefined) opening.width = patch.width;
    if (patch.swing !== undefined) opening.swing = patch.swing;
    persist();
  }

  function updateRoom(id: string, patch: Partial<Pick<Room, "label" | "haAreaId">>): void {
    saveSnapshot();
    const room = floor.rooms.find((r) => r.id === id);
    if (!room) return;
    if (patch.label !== undefined) room.label = patch.label;
    if (patch.haAreaId !== undefined) room.haAreaId = patch.haAreaId;
    persist();
  }

  /**
   * Returns true if [from, to] overlaps any existing opening on `wallId`,
   * excluding the opening with id `excludeId` (pass null when placing new).
   */
  function openingOverlaps(
    wallId: string,
    excludeId: string | null,
    from: number,
    to: number
  ): boolean {
    return floor.openings.some(
      (o) =>
        o.wallId === wallId &&
        o.id !== excludeId &&
        from < o.offset + o.width &&
        to > o.offset
    );
  }

  recomputeRooms();

  return {
    get floor() { return floor; },
    get hasUndo() { return undoCount > 0; },
    get hasRedo() { return redoCount > 0; },
    saveSnapshot,
    undo,
    redo,
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

### Step 4: Run tests — all must pass
```bash
cd /projects/myhome/.worktrees/opening-tools-undo && npm test --workspace=packages/editor 2>&1 | tail -10
```

### Step 5: Commit
```bash
cd /projects/myhome/.worktrees/opening-tools-undo && git add packages/editor/src/lib/floorStore.svelte.ts packages/editor/test/floorStore.test.ts && git commit -m "feat(editor): undo/redo stack + updateOpening + openingOverlaps in floorStore"
```

---

## Task 2: toolStore — opening handle drag state

**Files:**
- Modify: `packages/editor/src/lib/toolStore.svelte.ts`
- Modify: `packages/editor/test/toolStore.test.ts`

### Step 1: Write failing tests

Add to `packages/editor/test/toolStore.test.ts`:

```typescript
describe("toolStore — opening handle drag", () => {
  it("startOpeningDrag sets draggingOpeningHandle", () => {
    const store = createToolStore();
    store.startOpeningDrag("op-1", "end");
    expect(store.state.draggingOpeningHandle).toEqual({ openingId: "op-1", side: "end" });
  });

  it("endOpeningDrag clears draggingOpeningHandle", () => {
    const store = createToolStore();
    store.startOpeningDrag("op-1", "start");
    store.endOpeningDrag();
    expect(store.state.draggingOpeningHandle).toBeNull();
  });

  it("endDrag also clears draggingOpeningHandle", () => {
    const store = createToolStore();
    store.startOpeningDrag("op-1", "start");
    store.endDrag();
    expect(store.state.draggingOpeningHandle).toBeNull();
  });

  it("setTool clears draggingOpeningHandle", () => {
    const store = createToolStore();
    store.startOpeningDrag("op-1", "start");
    store.setTool("wall");
    expect(store.state.draggingOpeningHandle).toBeNull();
  });
});
```

### Step 2: Run — expect failures

```bash
cd /projects/myhome/.worktrees/opening-tools-undo && npm test --workspace=packages/editor 2>&1 | tail -20
```

### Step 3: Implement

In `packages/editor/src/lib/toolStore.svelte.ts`, add to `ToolState`:

```typescript
export interface ToolState {
  tool: ToolType;
  selectedId: string | null;
  selectedRoomId: string | null;
  selectedOpeningId: string | null;
  drawPoints: Point[];
  cursorWorld: Point | null;
  draggingPoint: Point | null;
  draggingOpeningHandle: { openingId: string; side: "start" | "end" } | null;
}
```

Initialize: `draggingOpeningHandle: null`

Clear in `setTool`: `state.draggingOpeningHandle = null;`

Add methods:

```typescript
function startOpeningDrag(openingId: string, side: "start" | "end"): void {
  state.draggingOpeningHandle = { openingId, side };
}

function endOpeningDrag(): void {
  state.draggingOpeningHandle = null;
}
```

Update `endDrag` to also clear:
```typescript
function endDrag(): void {
  state.draggingPoint = null;
  state.draggingOpeningHandle = null;
}
```

Add to the returned object: `startOpeningDrag`, `endOpeningDrag`.

### Step 4: Run tests — all pass

```bash
cd /projects/myhome/.worktrees/opening-tools-undo && npm test --workspace=packages/editor 2>&1 | tail -10
```

### Step 5: Commit

```bash
cd /projects/myhome/.worktrees/opening-tools-undo && git add packages/editor/src/lib/toolStore.svelte.ts packages/editor/test/toolStore.test.ts && git commit -m "feat(editor): opening handle drag state in toolStore"
```

---

## Task 3: OpeningShape — resize handles + Canvas plumbing

**Files:**
- Modify: `packages/editor/src/lib/components/OpeningShape.svelte`
- Modify: `packages/editor/src/lib/components/Canvas.svelte`

No separate unit tests — covered by existing Canvas smoke tests plus manual testing.

### Step 1: Add resize handles to OpeningShape.svelte

When `selected` is true, render two circular drag handles at the opening endpoints. The handles work identically to `SelectionHandles.svelte` for walls.

Add a prop: `ondraghandlestart?: (openingId: string, side: "start" | "end", event: MouseEvent) => void`

In the props destructuring:
```typescript
let {
  wall,
  opening,
  viewport,
  tool = "select",
  selected = false,
  onselect,
  ondraghandlestart,
}: {
  // ...existing...
  ondraghandlestart?: (openingId: string, side: "start" | "end", event: MouseEvent) => void;
} = $props();
```

At the end of the SVG template (inside the `{#if dir.length >= 1e-9}` block), add:

```svelte
{#if selected}
  <circle
    class="handle"
    cx={sp1.x}
    cy={sp1.y}
    r="5"
    onmousedown={(e) => { e.stopPropagation(); ondraghandlestart?.(opening.id, "start", e); }}
    role="button"
    tabindex="0"
  />
  <circle
    class="handle"
    cx={sp2.x}
    cy={sp2.y}
    r="5"
    onmousedown={(e) => { e.stopPropagation(); ondraghandlestart?.(opening.id, "end", e); }}
    role="button"
    tabindex="0"
  />
{/if}
```

Add to `<style>`:
```css
.handle {
  fill: #5af;
  stroke: #fff;
  stroke-width: 1.5;
  cursor: ew-resize;
}
```

### Step 2: Plumb through Canvas.svelte

Add a new prop to Canvas:
```typescript
ondragopeninghandlestart?: (openingId: string, side: "start" | "end") => void;
```

In the `OpeningShape` usage in the template, add:
```svelte
ondraghandlestart={(openingId, side, event) => {
  event.stopPropagation();
  ondragopeninghandlestart?.(openingId, side);
}}
```

Also, in `handleMouseUp`, ensure `ondragend?.()` fires (already present) — this covers both wall and opening drag end.

### Step 3: Run tests — all still pass

```bash
cd /projects/myhome/.worktrees/opening-tools-undo && npm test --workspace=packages/editor 2>&1 | tail -10
```

### Step 4: Commit

```bash
cd /projects/myhome/.worktrees/opening-tools-undo && git add packages/editor/src/lib/components/OpeningShape.svelte packages/editor/src/lib/components/Canvas.svelte && git commit -m "feat(editor): opening resize handles in OpeningShape; plumb ondragopeninghandlestart through Canvas"
```

---

## Task 4: Toolbar — Undo/Redo buttons

**File:** `packages/editor/src/lib/components/Toolbar.svelte`

### Step 1: Update Toolbar

Add `hasUndo`, `hasRedo`, `onundo`, `onredo` props and buttons. Place Undo/Redo at the top of the toolbar, above the tool buttons.

```svelte
<script lang="ts">
  import type { ToolType } from "../toolStore.svelte";

  let {
    tool,
    hasSelection,
    hasUndo = false,
    hasRedo = false,
    onselecttool,
    ondelete,
    onundo,
    onredo,
  }: {
    tool: ToolType;
    hasSelection: boolean;
    hasUndo?: boolean;
    hasRedo?: boolean;
    onselecttool: (tool: ToolType) => void;
    ondelete: () => void;
    onundo?: () => void;
    onredo?: () => void;
  } = $props();
</script>

<nav class="toolbar">
  <button disabled={!hasUndo} onclick={() => onundo?.()}>Undo</button>
  <button disabled={!hasRedo} onclick={() => onredo?.()}>Redo</button>
  <hr />
  <button class:active={tool === "select"} onclick={() => onselecttool("select")}>Select</button>
  <button class:active={tool === "wall"} onclick={() => onselecttool("wall")}>Wall</button>
  <button class:active={tool === "divider"} onclick={() => onselecttool("divider")}>Divider</button>
  <button class:active={tool === "door"} onclick={() => onselecttool("door")}>Door</button>
  <button class:active={tool === "window"} onclick={() => onselecttool("window")}>Window</button>
  <button class="delete" disabled={!hasSelection} onclick={ondelete}>Delete</button>
</nav>

<style>
  .toolbar {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 8px 6px;
    background: #333;
    width: 64px;
  }
  hr {
    border: none;
    border-top: 1px solid #555;
    margin: 0;
  }
  button {
    padding: 6px;
    border: none;
    border-radius: 4px;
    background: #444;
    color: #ccc;
    cursor: pointer;
    font-size: 11px;
  }
  button.active {
    background: #555;
    color: #eee;
  }
  button.delete {
    margin-top: auto;
    background: #622;
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
</style>
```

### Step 2: Update App.test.ts button count

The toolbar now has 8 buttons (2 undo/redo + 5 tools + 1 delete). Find any tests in `App.test.ts` that check button count or index by position, and fix them.

### Step 3: Run tests — all pass

```bash
cd /projects/myhome/.worktrees/opening-tools-undo && npm test --workspace=packages/editor 2>&1 | tail -10
```

### Step 4: Commit

```bash
cd /projects/myhome/.worktrees/opening-tools-undo && git add packages/editor/src/lib/components/Toolbar.svelte packages/editor/test/App.test.ts && git commit -m "feat(editor): Undo/Redo buttons in Toolbar"
```

---

## Task 5: App.svelte — wire everything together

**Files:**
- Modify: `packages/editor/src/App.svelte`
- Modify: `packages/editor/test/App.test.ts`

This task wires: overlap guard at placement, opening handle drag, undo/redo keyboard shortcuts, and passing new props to Toolbar and Canvas.

### Step 1: Read current App.svelte

Read the full file before editing.

### Step 2: Apply changes

**Overlap guard in `handleOpeningPlace`:**

After computing `width` and before creating the `opening` object, add:

```typescript
const openingEnd = offset + width;
if (floorStore.openingOverlaps(wall.id, null, offset, openingEnd)) return;
```

**Save snapshot before wall-point drag starts (so undo works for drags):**

In `handleDragStart(point: Point)`, add `floorStore.saveSnapshot()` BEFORE `toolStore.startDrag(point)`:

```typescript
function handleDragStart(point: Point): void {
  floorStore.saveSnapshot();
  toolStore.startDrag(point);
}
```

**Update `handleDragMove` to use `skipHistory`:**

Change `floorStore.moveSharedPoint(dragging, snapped)` to:

```typescript
floorStore.moveSharedPoint(dragging, snapped, { skipHistory: true });
```

**Add opening handle drag handlers:**

```typescript
function handleOpeningHandleDragStart(openingId: string, side: "start" | "end"): void {
  floorStore.saveSnapshot();
  toolStore.startOpeningDrag(openingId, side);
}

const MIN_OPENING_WIDTH = 0.1;

function handleOpeningHandleDrag(worldCursor: Point): void {
  const drag = toolStore.state.draggingOpeningHandle;
  if (!drag) return;
  const opening = floorStore.floor.openings.find((o) => o.id === drag.openingId);
  if (!opening) return;
  const wall = floorStore.floor.walls.find((w) => w.id === opening.wallId);
  if (!wall) return;

  const dx = wall.end.x - wall.start.x;
  const dy = wall.end.y - wall.start.y;
  const len = Math.hypot(dx, dy);
  if (len < 1e-9) return;
  const dirX = dx / len;
  const dirY = dy / len;
  const cx = worldCursor.x - wall.start.x;
  const cy = worldCursor.y - wall.start.y;
  const raw = Math.max(0, Math.min(len, cx * dirX + cy * dirY));
  const snapped = Math.max(0, Math.min(len, Math.round(raw / 0.1) * 0.1));

  if (drag.side === "end") {
    const newWidth = snapped - opening.offset;
    if (newWidth < MIN_OPENING_WIDTH) return;
    if (floorStore.openingOverlaps(wall.id, opening.id, opening.offset, snapped)) return;
    floorStore.updateOpening(opening.id, { width: newWidth }, { skipHistory: true });
  } else {
    const currentEnd = opening.offset + opening.width;
    const newOffset = snapped;
    const newWidth = currentEnd - newOffset;
    if (newWidth < MIN_OPENING_WIDTH) return;
    if (floorStore.openingOverlaps(wall.id, opening.id, newOffset, currentEnd)) return;
    floorStore.updateOpening(opening.id, { offset: newOffset, width: newWidth }, { skipHistory: true });
  }
}
```

**Update `handlePointerMove`** to also call `handleOpeningHandleDrag`:

```typescript
function handlePointerMove(world: Point): void {
  toolStore.setCursor(world);
  if (toolStore.state.draggingPoint) {
    handleDragMove(world);
  }
  if (toolStore.state.draggingOpeningHandle) {
    handleOpeningHandleDrag(world);
  }
}
```

**Update `handleDragEnd`** to clear opening drag state:

```typescript
function handleDragEnd(): void {
  toolStore.endDrag(); // already clears draggingOpeningHandle via Task 2
}
```

**Add undo/redo functions:**

```typescript
function handleUndo(): void {
  floorStore.undo();
  toolStore.select(null);
  toolStore.selectRoom(null);
  toolStore.selectOpening(null);
}

function handleRedo(): void {
  floorStore.redo();
  toolStore.select(null);
  toolStore.selectRoom(null);
  toolStore.selectOpening(null);
}
```

**Update keydown handler** to add Ctrl+Z and Ctrl+Shift+Z/Ctrl+Y:

```typescript
function handleKeydown(event: KeyboardEvent): void {
  if (event.code === "Space") {
    event.preventDefault();
    spacePressed = true;
    return;
  }
  if (event.ctrlKey && event.key === "z" && !event.shiftKey) {
    event.preventDefault();
    handleUndo();
    return;
  }
  if (event.ctrlKey && (event.key === "y" || (event.key === "z" && event.shiftKey))) {
    event.preventDefault();
    handleRedo();
    return;
  }
  if (event.key === "Escape") {
    toolStore.resetDraw();
    return;
  }
  if (
    (event.key === "Delete" || event.key === "Backspace") &&
    (toolStore.state.selectedId || toolStore.state.selectedOpeningId)
  ) {
    handleDelete();
  }
}
```

**Update Toolbar in template** to pass new props:

```svelte
<Toolbar
  tool={toolStore.state.tool}
  hasSelection={toolStore.state.selectedId !== null || toolStore.state.selectedOpeningId !== null}
  hasUndo={floorStore.hasUndo}
  hasRedo={floorStore.hasRedo}
  onselecttool={(tool) => toolStore.setTool(tool)}
  ondelete={handleDelete}
  onundo={handleUndo}
  onredo={handleRedo}
/>
```

**Update Canvas in template** to pass `ondragopeninghandlestart`:

```svelte
<Canvas
  ...
  ondragopeninghandlestart={handleOpeningHandleDragStart}
/>
```

Keep all other Canvas props unchanged.

### Step 3: Add tests

Add to `packages/editor/test/App.test.ts`:

```typescript
describe("App — overlap prevention", () => {
  it("Undo/Redo buttons are disabled initially", async () => {
    const { container } = render(App);
    await tick();
    const buttons = container.querySelectorAll("button");
    // First two buttons are Undo and Redo
    const undoBtn = buttons[0] as HTMLButtonElement;
    const redoBtn = buttons[1] as HTMLButtonElement;
    expect(undoBtn.textContent?.trim()).toBe("Undo");
    expect(redoBtn.textContent?.trim()).toBe("Redo");
    expect(undoBtn.disabled).toBe(true);
    expect(redoBtn.disabled).toBe(true);
  });
});
```

### Step 4: Run tests — all pass

```bash
cd /projects/myhome/.worktrees/opening-tools-undo && npm test --workspace=packages/editor 2>&1 | tail -15
```

Fix any test failures from the Toolbar button count/index changes.

### Step 5: Commit

```bash
cd /projects/myhome/.worktrees/opening-tools-undo && git add packages/editor/src/App.svelte packages/editor/test/App.test.ts && git commit -m "feat(editor): overlap guard + opening resize + undo/redo Ctrl+Z wiring in App"
```

---

## Self-Review

- [x] Spec coverage: overlap prevention ✓, opening resize ✓, undo/redo ✓, keyboard shortcuts ✓
- [x] `saveSnapshot()` called once at drag start (not on every mouse move) → no history bloat
- [x] `skipHistory: true` propagated through `moveSharedPoint` and `updateOpening` for live drag updates
- [x] `openingOverlaps` correctly excludes self (`excludeId`) so resize doesn't reject its own range
- [x] `endDrag` in toolStore clears BOTH `draggingPoint` and `draggingOpeningHandle`
- [x] Undo clears selection (so stale selection doesn't point to a deleted object after undo)
- [x] `hasUndo` / `hasRedo` are reactive via `$state` counters (`undoCount`, `redoCount`)
- [x] `cloneFloor` uses JSON round-trip — no shared references between live floor and stack snapshots
