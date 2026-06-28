# Home Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new `#/` home dashboard page with five widgets (read-only map, chores, costs, inventory, works) that summarize every module at a glance, and move the floor-plan editor to `#/plan`.

**Architecture:** Extract three small reusable pieces from existing pages (`ChoreRow.svelte` from `ChoreListPage.svelte`, `DonutChart.svelte` from `CostsPage.svelte`, and a new `fitViewportToFloor()` helper), then build five new `Home*Widget.svelte` components on top of the existing stores (`choreStore`, `costsStore`, `inventoryStore`, `worksStore`, `settingsStore`, `houseStore`) and the existing `*Overlay.svelte` components (used in their already-supported read-only mode via `active={false}` / `choreMode={false}` — no new pin-logic extraction is needed, see note in Task 8). A new `HomePage.svelte` assembles the widgets in a 2-col/1-col responsive grid. `App.svelte` and `NavMenu.svelte` get small routing changes so `#/` renders `HomePage` and the editor moves to `#/plan`.

**Tech Stack:** Svelte 5 (runes), TypeScript, Vitest 4 with native `mount`/`unmount`, no router library (hash-based routing), no charting library (hand-rolled SVG donut).

**Deviation from the approved design doc:** `docs/superpowers/specs/2026-06-25-home-dashboard-design.md` says per-layer pin logic needs to be "extracted into small, pure, reusable functions" because it was believed to live inline in `App.svelte`. Direct inspection of `ChoreOverlay.svelte`, `InventoryOverlay.svelte`, `CostsOverlay.svelte`, and `WorksOverlay.svelte` shows this already exists: each component accepts an `active` (or `choreMode`) boolean that, when `false`, disables pointer events and drag/click handling while still rendering the pins. `HomeMapWidget` reuses these components directly with `active={false}` / `choreMode={false}` and no-op `onclick`/`ondragend` callbacks — fulfilling the design's underlying goal (no duplicated/diverging pin logic) with less new code than originally scoped. This should be mentioned to the user when the plan is presented.

---

## File Structure

**New files:**
- `packages/editor/src/lib/choreFormat.ts` — `displayName()` / `formatDue()` pure functions, extracted from `ChoreListPage.svelte` so `HomeChoresWidget` can reuse them.
- `packages/editor/src/lib/viewportFit.ts` — `fitViewportToFloor()`, computes a `ViewportState` that fits a floor's walls into a given pixel size.
- `packages/editor/src/lib/components/ChoreRow.svelte` — one assignment row (emoji, name, optional location, due label, quick-complete checkmark with inline notes). Extracted from `ChoreListPage.svelte`.
- `packages/editor/src/lib/components/DonutChart.svelte` — generic SVG donut/pie renderer (segments → slices + hole + center label, optional connector-line labels). Extracted from `CostsPage.svelte`.
- `packages/editor/src/lib/components/HomeMapWidget.svelte` — read-only floor map widget with its own floor switcher + layer dropdown.
- `packages/editor/src/lib/components/HomeChoresWidget.svelte` — stat row + top-5 urgent chores.
- `packages/editor/src/lib/components/HomeCostsWidget.svelte` — donut chart for last complete year.
- `packages/editor/src/lib/components/HomeInventoryWidget.svelte` — donut chart + per-category counts.
- `packages/editor/src/lib/components/HomeWorksWidget.svelte` — status stat tiles + recent works list.
- `packages/editor/src/lib/components/HomePage.svelte` — assembles the five widgets into the 2-col/1-col responsive grid.
- Test files: `test/viewportFit.test.ts`, `test/ChoreRow.test.ts`, `test/DonutChart.test.ts`, `test/HomeMapWidget.test.ts`, `test/HomeChoresWidget.test.ts`, `test/HomeCostsWidget.test.ts`, `test/HomeInventoryWidget.test.ts`, `test/HomeWorksWidget.test.ts`, `test/HomePage.test.ts`.

**Modified files:**
- `packages/editor/src/lib/components/Canvas.svelte` — new `showGrid` prop (default `true`), wraps `<Grid>` in `{#if showGrid}`.
- `packages/editor/src/lib/components/ChoreListPage.svelte` — use `ChoreRow` + `choreFormat.ts` instead of inline row markup/logic.
- `packages/editor/src/lib/components/CostsPage.svelte` — use `DonutChart` instead of inline SVG donut code.
- `packages/editor/src/lib/components/NavMenu.svelte` — `modules` array: `#/` becomes "Home", new "Floor Plan" entry added for `#/plan`.
- `packages/editor/src/App.svelte` — `isFloorPlan` now means `#/plan`; new `isHome` derived renders `HomePage`.
- `test/Canvas.test.ts` — new test for `showGrid={false}`.
- `test/App.test.ts` — `mountAndLoad` gets an optional `route` param (default `"#/plan"`, preserving every existing call site); one direct-mount test gets an explicit `#/plan` hash; new routing tests for `#/` and `#/plan`.

---

## Task 1: `Canvas.svelte` gains a `showGrid` prop

**Files:**
- Modify: `packages/editor/src/lib/components/Canvas.svelte:16-62` (props), `:202` (Grid usage)
- Test: `packages/editor/test/Canvas.test.ts`

- [ ] **Step 1: Write the failing test**

Add to the end of the `describe("Canvas", ...)` block in `packages/editor/test/Canvas.test.ts` (after the existing `it("renders walls, dividers, and room polygons with area labels", ...)` test, before the closing `});` of the `describe`):

```ts
  it("hides the grid when showGrid is false", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    const floor = createSampleFloor();

    app = mount(Canvas, {
      target,
      props: { floor, viewport: { ...DEFAULT_VIEWPORT }, width: 800, height: 600, showGrid: false },
    });
    flushSync();

    const svg = target.querySelector("svg.canvas");
    expect(svg!.querySelectorAll("line.grid-line")).toHaveLength(0);
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/Canvas.test.ts -t "hides the grid"`
Expected: FAIL — `showGrid` is not a recognized prop yet, so the grid still renders; `toHaveLength(0)` fails because grid lines are present.

- [ ] **Step 3: Add the `showGrid` prop and gate `<Grid>`**

In `packages/editor/src/lib/components/Canvas.svelte`, change the props destructuring (currently lines 16-62) by adding `showGrid = true,` after the `tool = "select",` line and `showGrid?: boolean;` to the type after `tool?: ToolType;`:

```svelte
  let {
    floor,
    viewport,
    width,
    height,
    selectedId = null,
    selectedRoomId = null,
    selectedOpeningId = null,
    onselect,
    onselectroom,
    onselectopening,
    ondragopeninghandlestart,
    tool = "select",
    showGrid = true,
    drawPoints = [],
    cursorWorld = null,
    spacePressed = false,
    onpointermove,
    onplacepoint,
    ondblclick,
    ondragstart,
    ondragend,
    onpan,
    onzoom,
  }: {
    floor: Floor;
    viewport: ViewportState;
    width: number;
    height: number;
    selectedId?: string | null;
    selectedRoomId?: string | null;
    selectedOpeningId?: string | null;
    onselect?: (id: string | null) => void;
    onselectroom?: (id: string | null) => void;
    onselectopening?: (id: string | null) => void;
    ondragopeninghandlestart?: (openingId: string, side: "start" | "end") => void;
    tool?: ToolType;
    showGrid?: boolean;
    drawPoints?: Point[];
    cursorWorld?: Point | null;
    spacePressed?: boolean;
    onpointermove?: (point: Point) => void;
    onplacepoint?: (point: Point) => void;
    ondblclick?: () => void;
    ondragstart?: (point: Point) => void;
    ondragend?: () => void;
    onpan?: (dx: number, dy: number) => void;
    onzoom?: (screen: Point, factor: number) => void;
  } = $props();
```

Then change line 202 (`<Grid {viewport} {width} {height} />`) to:

```svelte
  {#if showGrid}
    <Grid {viewport} {width} {height} />
  {/if}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/Canvas.test.ts`
Expected: PASS (both the existing test and the new one)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/Canvas.svelte packages/editor/test/Canvas.test.ts
git commit -m "feat(canvas): add showGrid prop to suppress the grid background"
```

---

## Task 2: `viewportFit.ts` — auto-fit viewport helper

**Files:**
- Create: `packages/editor/src/lib/viewportFit.ts`
- Test: `packages/editor/test/viewportFit.test.ts`

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/viewportFit.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { fitViewportToFloor } from "../src/lib/viewportFit";
import { worldToScreen } from "../src/lib/viewportStore.svelte";
import type { Floor } from "@myhome/geometry";

function makeFloor(walls: Floor["walls"]): Floor {
  return { id: "f1", name: "Floor", order: 0, walls, openings: [], rooms: [] };
}

describe("fitViewportToFloor", () => {
  it("centers a single wall's midpoint in the viewport", () => {
    const floor = makeFloor([
      { id: "w1", start: { x: 0, y: 0 }, end: { x: 4, y: 0 }, type: "wall" },
    ]);
    const viewport = fitViewportToFloor(floor, 400, 300);

    const mid = worldToScreen({ x: 2, y: 0 }, viewport);
    expect(mid.x).toBeCloseTo(200, 0);
    expect(mid.y).toBeCloseTo(150, 0);
  });

  it("fits the bounding box within the available width/height", () => {
    const floor = makeFloor([
      { id: "w1", start: { x: 0, y: 0 }, end: { x: 10, y: 0 }, type: "wall" },
      { id: "w2", start: { x: 10, y: 0 }, end: { x: 10, y: 4 }, type: "wall" },
    ]);
    const viewport = fitViewportToFloor(floor, 400, 300, 20);

    const corners = [
      worldToScreen({ x: 0, y: 0 }, viewport),
      worldToScreen({ x: 10, y: 4 }, viewport),
    ];
    for (const p of corners) {
      expect(p.x).toBeGreaterThanOrEqual(20 - 1);
      expect(p.x).toBeLessThanOrEqual(400 - 20 + 1);
      expect(p.y).toBeGreaterThanOrEqual(20 - 1);
      expect(p.y).toBeLessThanOrEqual(300 - 20 + 1);
    }
  });

  it("returns a centered default viewport for a floor with no walls", () => {
    const floor = makeFloor([]);
    const viewport = fitViewportToFloor(floor, 400, 300);
    expect(viewport.panX).toBe(200);
    expect(viewport.panY).toBe(150);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/viewportFit.test.ts`
Expected: FAIL — `../src/lib/viewportFit` does not exist.

- [ ] **Step 3: Implement `fitViewportToFloor`**

Create `packages/editor/src/lib/viewportFit.ts`:

```ts
import type { Floor } from "@myhome/geometry";
import { allEndpoints } from "./drawingTool";
import type { ViewportState } from "./viewportStore.svelte";

export function fitViewportToFloor(
  floor: Floor,
  width: number,
  height: number,
  padding = 40
): ViewportState {
  const points = allEndpoints(floor.walls);
  if (points.length === 0) {
    return { panX: width / 2, panY: height / 2, zoom: 100 };
  }

  const minX = Math.min(...points.map((p) => p.x));
  const maxX = Math.max(...points.map((p) => p.x));
  const minY = Math.min(...points.map((p) => p.y));
  const maxY = Math.max(...points.map((p) => p.y));

  const spanX = Math.max(maxX - minX, 0.1);
  const spanY = Math.max(maxY - minY, 0.1);
  const availW = Math.max(width - padding * 2, 1);
  const availH = Math.max(height - padding * 2, 1);
  const zoom = Math.min(availW / spanX, availH / spanY);

  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;

  return {
    panX: width / 2 - cx * zoom,
    panY: height / 2 - cy * zoom,
    zoom,
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/viewportFit.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/viewportFit.ts packages/editor/test/viewportFit.test.ts
git commit -m "feat: add fitViewportToFloor helper for read-only auto-fit map views"
```

---

## Task 3: `choreFormat.ts` — extract `displayName`/`formatDue`

**Files:**
- Create: `packages/editor/src/lib/choreFormat.ts`
- Modify: `packages/editor/src/lib/components/ChoreListPage.svelte:22-39` (remove, replaced by import — wired up fully in Task 5)
- Test: `packages/editor/test/choreFormat.test.ts`

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/choreFormat.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { displayName, formatDue } from "../src/lib/choreFormat";
import type { Chore } from "../src/lib/choreStore.svelte";

function makeChore(name: string, emoji: string): Chore {
  return {
    id: "c1",
    donetickId: null,
    name,
    emoji,
    periodDays: 7,
    frequencyType: "interval",
    frequency: 7,
    frequencyMetadata: {},
    scheduleFromDue: false,
    nextDueDate: new Date().toISOString(),
    description: "",
  };
}

describe("choreFormat — displayName", () => {
  it("strips a leading emoji that duplicates chore.emoji", () => {
    expect(displayName(makeChore("🧹 Sweep", "🧹"))).toBe("Sweep");
  });

  it("leaves the name untouched when it doesn't start with the emoji", () => {
    expect(displayName(makeChore("Sweep", "🧹"))).toBe("Sweep");
  });
});

describe("choreFormat — formatDue", () => {
  it("returns an em dash for an empty string", () => {
    expect(formatDue("")).toBe("—");
  });

  it("labels today, tomorrow, and overdue days", () => {
    const today = new Date();
    expect(formatDue(today.toISOString())).toBe("Today");

    const tomorrow = new Date(today.getTime() + 86400000);
    expect(formatDue(tomorrow.toISOString())).toBe("Tomorrow");

    const twoDaysAgo = new Date(today.getTime() - 2 * 86400000);
    expect(formatDue(twoDaysAgo.toISOString())).toBe("2d overdue");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/choreFormat.test.ts`
Expected: FAIL — `../src/lib/choreFormat` does not exist.

- [ ] **Step 3: Implement `choreFormat.ts`**

Create `packages/editor/src/lib/choreFormat.ts`:

```ts
import type { Chore } from "./choreStore.svelte";

export function displayName(chore: Chore): string {
  let name = chore.name.trim();
  if (chore.emoji && name.startsWith(chore.emoji)) name = name.slice(chore.emoji.length).trim();
  return name;
}

export function formatDue(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const now = new Date();
  const diffDays = Math.round((d.getTime() - now.getTime()) / 86400000);
  if (diffDays < -1) return `${Math.abs(diffDays)}d overdue`;
  if (diffDays === -1) return "Yesterday";
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Tomorrow";
  if (diffDays <= 7) return `In ${diffDays}d`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/choreFormat.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/choreFormat.ts packages/editor/test/choreFormat.test.ts
git commit -m "feat: extract chore displayName/formatDue into choreFormat.ts"
```

(`ChoreListPage.svelte` is switched over to import from here in Task 5, alongside the `ChoreRow` extraction, to avoid an intermediate half-migrated state.)

---

## Task 4: `ChoreRow.svelte` — shared assignment row component

**Files:**
- Create: `packages/editor/src/lib/components/ChoreRow.svelte`
- Test: `packages/editor/test/ChoreRow.test.ts`

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/ChoreRow.test.ts`:

```ts
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import ChoreRow from "../src/lib/components/ChoreRow.svelte";

describe("ChoreRow", () => {
  it("renders emoji, name, location, and due label", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoreRow, {
      target,
      props: {
        emoji: "🧹",
        name: "Sweep",
        location: "Kitchen",
        dueLabel: "Today",
        dueColor: "#4caf50",
        oncomplete: vi.fn(),
      },
    });

    expect(target.querySelector(".emoji")!.textContent).toBe("🧹");
    expect(target.querySelector(".name")!.textContent).toBe("Sweep");
    expect(target.querySelector(".location")!.textContent).toBe("Kitchen");
    expect(target.querySelector(".due")!.textContent).toBe("Today");

    unmount(comp);
    target.remove();
  });

  it("omits the location span when location is not provided", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete: vi.fn() },
    });

    expect(target.querySelector(".location")).toBeNull();

    unmount(comp);
    target.remove();
  });

  it("clicking the checkmark opens a note input, then confirm calls oncomplete with the notes", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const oncomplete = vi.fn();
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();

    const input = target.querySelector(".note-input") as HTMLInputElement;
    expect(input).not.toBeNull();
    input.value = "all done";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();

    (target.querySelector(".done-btn.confirm") as HTMLButtonElement).click();
    flushSync();

    expect(oncomplete).toHaveBeenCalledWith("all done");
    expect(target.querySelector(".note-input")).toBeNull();

    unmount(comp);
    target.remove();
  });

  it("cancel hides the note input without calling oncomplete", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const oncomplete = vi.fn();
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();
    (target.querySelector(".cancel-btn") as HTMLButtonElement).click();
    flushSync();

    expect(target.querySelector(".note-input")).toBeNull();
    expect(oncomplete).not.toHaveBeenCalled();

    unmount(comp);
    target.remove();
  });

  it("clicking the checkmark stops propagation so a parent onclick isn't triggered", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const parentClick = vi.fn();
    target.addEventListener("click", parentClick);
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete: vi.fn() },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();

    expect(parentClick).not.toHaveBeenCalled();

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/ChoreRow.test.ts`
Expected: FAIL — `../src/lib/components/ChoreRow.svelte` does not exist.

- [ ] **Step 3: Implement `ChoreRow.svelte`**

Create `packages/editor/src/lib/components/ChoreRow.svelte`:

```svelte
<script lang="ts">
  interface Props {
    emoji: string;
    name: string;
    location?: string;
    dueLabel: string;
    dueColor: string;
    oncomplete: (notes: string) => void;
  }
  let { emoji, name, location, dueLabel, dueColor, oncomplete }: Props = $props();

  let completing = $state(false);
  let notes = $state("");

  function start(e: Event): void {
    e.stopPropagation();
    completing = true;
    notes = "";
  }

  function confirm(e: Event): void {
    e.stopPropagation();
    completing = false;
    oncomplete(notes);
  }

  function cancel(e: Event): void {
    e.stopPropagation();
    completing = false;
  }

  function handleKeydown(e: KeyboardEvent): void {
    if (e.key === "Enter") confirm(e);
    if (e.key === "Escape") cancel(e);
  }
</script>

<div class="chore-row">
  <span class="emoji">{emoji}</span>
  <span class="name">{name}</span>
  {#if location}<span class="location">{location}</span>{/if}
  <span class="due" style="color:{dueColor}">{dueLabel}</span>
  {#if completing}
    <input
      class="note-input"
      bind:value={notes}
      placeholder="Note (optional)"
      onclick={(e) => e.stopPropagation()}
      onkeydown={handleKeydown}
    />
    <button class="done-btn confirm" onclick={confirm}>✓</button>
    <button class="cancel-btn" onclick={cancel}>✕</button>
  {:else}
    <button class="done-btn" onclick={start} title="Mark done">✓</button>
  {/if}
</div>

<style>
  .chore-row {
    display: flex; align-items: center; gap: 10px;
    padding: 9px 16px; border-bottom: 1px solid var(--border);
    font-size: 13px;
  }
  .chore-row:hover { background: var(--surface-hover); }

  .emoji { font-size: 16px; flex-shrink: 0; width: 22px; text-align: center; }
  .name { flex: 2; min-width: 80px; font-weight: 500; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .location { flex: 2; min-width: 80px; color: var(--text-muted); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .due { flex: 1; min-width: 70px; font-size: 12px; text-align: right; white-space: nowrap; }

  .note-input {
    flex: 1; min-width: 80px; max-width: 160px;
    padding: 3px 8px; background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); color: var(--text); font-size: 11px;
  }
  .note-input:focus { outline: none; border-color: var(--accent); }
  .done-btn {
    padding: 4px 10px; border: none; border-radius: var(--radius-sm);
    background: var(--success); color: var(--accent-contrast); cursor: pointer; font-size: 12px;
    min-height: 30px; flex-shrink: 0; touch-action: manipulation;
  }
  .done-btn:hover { opacity: 0.85; }
  .done-btn:disabled { opacity: 0.5; cursor: default; }
  .cancel-btn {
    padding: 4px 8px; border: none; border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text-muted); cursor: pointer; font-size: 12px;
    min-height: 30px; flex-shrink: 0;
  }
  .cancel-btn:hover { background: var(--surface-hover); }

  @media (max-width: 500px) {
    .chore-row { flex-wrap: wrap; gap: 6px; }
    .location { flex-basis: 100%; order: 3; }
    .due { text-align: left; }
  }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/ChoreRow.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ChoreRow.svelte packages/editor/test/ChoreRow.test.ts
git commit -m "feat: add shared ChoreRow component for assignment rows"
```

---

## Task 5: Refactor `ChoreListPage.svelte` to use `ChoreRow` + `choreFormat`

**Files:**
- Modify: `packages/editor/src/lib/components/ChoreListPage.svelte` (full file rewrite of script + template + style)

This task has no new test file — `ChoreListPage.svelte` has no existing dedicated test file, and its behavior (row content, urgency grouping, complete flow) is now covered by `ChoreRow.test.ts` (Task 4) plus the existing `App.test.ts` chore-related coverage (unaffected, since it does not exercise `#/chores`). Manual verification happens in the final task.

- [ ] **Step 1: Replace the script block**

In `packages/editor/src/lib/components/ChoreListPage.svelte`, replace lines 1-66 (the entire `<script>` block) with:

```svelte
<script lang="ts">
  import type { createChoreStore, Chore, Assignment } from "../choreStore.svelte";
  import { displayName, formatDue } from "../choreFormat";
  import ChoreRow from "./ChoreRow.svelte";

  type ChoreStore = ReturnType<typeof createChoreStore>;

  interface Props {
    store: ChoreStore;
    floorStore: { floors: Array<{ id: string; name: string; rooms: Array<{ id: string; label: string }> }> };
  }

  let { store, floorStore }: Props = $props();

  function getRoomName(roomId: string | null): string {
    if (!roomId) return "🏠 Whole house";
    for (const floor of floorStore.floors) {
      const room = floor.rooms.find((r) => r.id === roomId);
      if (room) return room.label || `Room (${floor.name})`;
    }
    return "Unknown room";
  }

  type Row = { assignment: Assignment; chore: Chore; pct: number };

  const rows = $derived(
    store.assignments
      .map((a) => {
        const chore = store.chores.find((c) => c.id === a.choreId);
        if (!chore) return null;
        return { assignment: a, chore, pct: store.getProgress(a, chore) };
      })
      .filter((r): r is Row => r !== null)
      .sort((a, b) => a.pct - b.pct)
  );

  const overdue = $derived(rows.filter((r) => r.pct <= 0.25));
  const ok = $derived(rows.filter((r) => r.pct > 0.25));
</script>
```

- [ ] **Step 2: Replace the template and style**

Replace everything from `<div class="page">` through the end of the file (originally lines 68-198) with:

```svelte
<div class="page">
  <header class="page-header">
    <h2>Chore List</h2>
    <span class="count">{rows.length} assignments</span>
  </header>

  <div class="list">
    {#if overdue.length > 0}
      <div class="group-header urgent">Needs attention ({overdue.length})</div>
      {#each overdue as { assignment, chore, pct } (assignment.id)}
        <ChoreRow
          emoji={chore.emoji}
          name={displayName(chore)}
          location={getRoomName(assignment.roomId)}
          dueLabel={formatDue(assignment.nextDueDate)}
          dueColor={store.getColor(pct)}
          oncomplete={(notes) => store.completeAssignment(assignment.id, notes)}
        />
      {/each}
    {/if}

    {#if ok.length > 0}
      {#if overdue.length > 0}<div class="group-divider"></div>{/if}
      <div class="group-header">On track ({ok.length})</div>
      {#each ok as { assignment, chore, pct } (assignment.id)}
        <ChoreRow
          emoji={chore.emoji}
          name={displayName(chore)}
          location={getRoomName(assignment.roomId)}
          dueLabel={formatDue(assignment.nextDueDate)}
          dueColor={store.getColor(pct)}
          oncomplete={(notes) => store.completeAssignment(assignment.id, notes)}
        />
      {/each}
    {/if}

    {#if rows.length === 0}
      <div class="empty">No chore assignments yet. Go to Management to create chores and assign them to rooms.</div>
    {/if}
  </div>
</div>

<style>
  .page { display: flex; flex-direction: column; height: 100%; background: var(--bg); color: var(--text); font-family: var(--font-sans); }
  .page-header {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 16px; background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .page-header h2 { margin: 0; font-size: 15px; font-weight: 600; color: var(--text); }
  .count { font-size: 11px; color: var(--text-faint); }

  .list { flex: 1; overflow-y: auto; }

  .group-header {
    padding: 8px 16px 4px;
    font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--text-faint); background: var(--bg); position: sticky; top: 0;
  }
  .group-header.urgent { color: var(--danger); }
  .group-divider { height: 8px; background: var(--bg); }

  .empty { padding: 40px 20px; text-align: center; color: var(--text-faint); font-size: 13px; line-height: 1.6; }
</style>
```

(The `.row`, `.emoji`, `.name`, `.location`, `.due`, `.note-input`, `.done-btn`, `.cancel-btn`, and their mobile `@media` rules are intentionally dropped — they now live in `ChoreRow.svelte`.)

- [ ] **Step 3: Run the full test suite to verify nothing broke**

Run: `cd packages/editor && npm run test`
Expected: PASS — all existing tests pass (no test file directly exercises `ChoreListPage.svelte`'s old internals).

- [ ] **Step 4: Typecheck**

Run: `cd packages/editor && npm run typecheck`
Expected: No errors. (Confirms `getRoomName`/`displayName`/`formatDue`/`ChoreRow` prop types line up.)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ChoreListPage.svelte
git commit -m "refactor(chores): use shared ChoreRow and choreFormat in ChoreListPage"
```

---

## Task 6: `DonutChart.svelte` — generic donut/pie component

**Files:**
- Create: `packages/editor/src/lib/components/DonutChart.svelte`
- Test: `packages/editor/test/DonutChart.test.ts`

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/DonutChart.test.ts`:

```ts
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import DonutChart from "../src/lib/components/DonutChart.svelte";

const segments = [
  { id: "a", label: "Fuel", emoji: "⛽", color: "#e76f51", valueLabel: "300 €", pct: 60 },
  { id: "b", label: "Tax", emoji: "🏛️", color: "#2a9d8f", valueLabel: "200 €", pct: 40 },
];

describe("DonutChart", () => {
  it("renders one slice path per segment", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(DonutChart, {
      target,
      props: { segments, centerLabel: "Total", centerValue: "500 €" },
    });

    expect(target.querySelectorAll("svg path")).toHaveLength(2);

    unmount(comp);
    target.remove();
  });

  it("renders the center label and value", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(DonutChart, {
      target,
      props: { segments, centerLabel: "Total", centerValue: "500 €" },
    });

    expect(target.textContent).toContain("Total");
    expect(target.textContent).toContain("500 €");

    unmount(comp);
    target.remove();
  });

  it("does not render connector-line labels by default", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(DonutChart, {
      target,
      props: { segments, centerLabel: "Total", centerValue: "500 €" },
    });

    expect(target.textContent).not.toContain("Fuel");

    unmount(comp);
    target.remove();
  });

  it("renders connector-line labels when showLabels is true", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(DonutChart, {
      target,
      props: { segments, centerLabel: "Total", centerValue: "500 €", showLabels: true },
    });

    expect(target.textContent).toContain("Fuel");
    expect(target.textContent).toContain("Tax");

    unmount(comp);
    target.remove();
  });

  it("calls onsliceclick with the segment id when a slice is clicked", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onsliceclick = vi.fn();
    const comp = mount(DonutChart, {
      target,
      props: { segments, centerLabel: "Total", centerValue: "500 €", onsliceclick },
    });

    (target.querySelectorAll("svg path")[0] as SVGPathElement).dispatchEvent(
      new MouseEvent("click", { bubbles: true })
    );
    flushSync();

    expect(onsliceclick).toHaveBeenCalledWith("a");

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/DonutChart.test.ts`
Expected: FAIL — `../src/lib/components/DonutChart.svelte` does not exist.

- [ ] **Step 3: Implement `DonutChart.svelte`**

Create `packages/editor/src/lib/components/DonutChart.svelte`:

```svelte
<script lang="ts">
  export interface DonutSegment {
    id: string;
    label: string;
    emoji: string;
    color: string;
    valueLabel: string;
    pct: number;
  }

  interface Slice {
    seg: DonutSegment;
    startDeg: number;
    endDeg: number;
    midDeg: number;
  }

  interface Props {
    segments: DonutSegment[];
    centerLabel: string;
    centerValue: string;
    showLabels?: boolean;
    onsliceclick?: (id: string) => void;
  }
  let { segments, centerLabel, centerValue, showLabels = false, onsliceclick }: Props = $props();

  const CX = 155;
  const CY = 110;
  const OUTER_R = 70;
  const INNER_R = 28;

  function polarPoint(cx: number, cy: number, r: number, angleDeg: number) {
    const rad = (angleDeg * Math.PI) / 180;
    return { x: cx + r * Math.sin(rad), y: cy - r * Math.cos(rad) };
  }

  function donutPath(cx: number, cy: number, outerR: number, innerR: number, startDeg: number, endDeg: number): string {
    const clampedEnd = Math.min(startDeg + 359.99, endDeg);
    const os = polarPoint(cx, cy, outerR, startDeg);
    const oe = polarPoint(cx, cy, outerR, clampedEnd);
    const is = polarPoint(cx, cy, innerR, startDeg);
    const ie = polarPoint(cx, cy, innerR, clampedEnd);
    const large = clampedEnd - startDeg > 180 ? 1 : 0;
    return [
      `M ${os.x.toFixed(2)} ${os.y.toFixed(2)}`,
      `A ${outerR} ${outerR} 0 ${large} 1 ${oe.x.toFixed(2)} ${oe.y.toFixed(2)}`,
      `L ${ie.x.toFixed(2)} ${ie.y.toFixed(2)}`,
      `A ${innerR} ${innerR} 0 ${large} 0 ${is.x.toFixed(2)} ${is.y.toFixed(2)}`,
      "Z",
    ].join(" ");
  }

  const slices = $derived((() => {
    let angle = 0;
    return segments.map((seg) => {
      const start = angle;
      const span = (seg.pct / 100) * 360;
      angle += span;
      return { seg, startDeg: start, endDeg: angle, midDeg: start + span / 2 } as Slice;
    });
  })());
</script>

<svg viewBox="0 0 310 220" width="310" height="220" style="overflow:visible">
  {#each slices as s (s.seg.id)}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <path
      d={donutPath(CX, CY, OUTER_R, INNER_R, s.startDeg, s.endDeg)}
      fill={s.seg.color}
      opacity="0.9"
      style="cursor:{onsliceclick ? 'pointer' : 'default'}"
      onclick={() => onsliceclick?.(s.seg.id)}
    />
  {/each}

  <circle cx={CX} cy={CY} r={INNER_R} fill="var(--surface)" />
  <text x={CX} y={CY - 6} text-anchor="middle" fill="var(--text-muted)" font-size="8" font-family="sans-serif">{centerLabel}</text>
  <text x={CX} y={CY + 8} text-anchor="middle" fill="var(--text)" font-size="11" font-family="sans-serif" font-weight="600">{centerValue}</text>

  {#if showLabels}
    {#each slices as s (s.seg.id + "-label")}
      {@const mid = polarPoint(CX, CY, OUTER_R + 4, s.midDeg)}
      {@const elbow = polarPoint(CX, CY, OUTER_R + 18, s.midDeg)}
      {@const isRight = elbow.x >= CX}
      {@const lineEnd = { x: elbow.x + (isRight ? 28 : -28), y: elbow.y }}
      {@const textX = lineEnd.x + (isRight ? 4 : -4)}
      <line x1={mid.x} y1={mid.y} x2={elbow.x} y2={elbow.y} stroke={s.seg.color} stroke-width="1" opacity="0.7" />
      <line x1={elbow.x} y1={elbow.y} x2={lineEnd.x} y2={lineEnd.y} stroke={s.seg.color} stroke-width="1" opacity="0.7" />
      <circle cx={mid.x} cy={mid.y} r="2" fill={s.seg.color} />
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <text
        x={textX}
        y={elbow.y - 3}
        text-anchor={isRight ? "start" : "end"}
        fill={s.seg.color}
        font-size="9"
        font-family="sans-serif"
        font-weight="600"
        style="cursor:{onsliceclick ? 'pointer' : 'default'}"
        onclick={() => onsliceclick?.(s.seg.id)}
      >{s.seg.emoji} {s.seg.label}</text>
      <text
        x={textX}
        y={elbow.y + 9}
        text-anchor={isRight ? "start" : "end"}
        fill="var(--text-faint)"
        font-size="8"
        font-family="sans-serif"
      >{s.seg.valueLabel} · {s.seg.pct.toFixed(0)}%</text>
    {/each}
  {/if}
</svg>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/DonutChart.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/DonutChart.svelte packages/editor/test/DonutChart.test.ts
git commit -m "feat: add generic DonutChart component"
```

---

## Task 7: Refactor `CostsPage.svelte` to use `DonutChart`

**Files:**
- Modify: `packages/editor/src/lib/components/CostsPage.svelte:96-143` (remove chart helpers), `:198-254` (replace SVG with `<DonutChart>`), `:1-10` (add import)

No new test file — `CostsPage.svelte` has no existing dedicated test file; the extracted chart logic is covered by `DonutChart.test.ts` (Task 6). Manual verification happens in the final task.

- [ ] **Step 1: Add the `DonutChart` import**

In `packages/editor/src/lib/components/CostsPage.svelte`, after the existing `import Card from "./ui/Card.svelte";` (line 10), add:

```svelte
  import DonutChart from "./DonutChart.svelte";
```

- [ ] **Step 2: Remove the now-unused chart helpers**

Delete lines 96-129 (the `// --- Chart helpers ---` comment through the `PIE_INNER_R` constant) and lines 135-143 (the `slices` `$derived` block), i.e. remove:

```ts
  // --- Chart helpers ---

  interface Slice {
    cat: CategoryBreakdown;
    startDeg: number;
    endDeg: number;
    midDeg: number;
  }

  function polarPoint(cx: number, cy: number, r: number, angleDeg: number) {
    const rad = angleDeg * Math.PI / 180;
    return { x: cx + r * Math.sin(rad), y: cy - r * Math.cos(rad) };
  }

  function donutPath(cx: number, cy: number, outerR: number, innerR: number, startDeg: number, endDeg: number): string {
    const clampedEnd = Math.min(startDeg + 359.99, endDeg);
    const os = polarPoint(cx, cy, outerR, startDeg);
    const oe = polarPoint(cx, cy, outerR, clampedEnd);
    const is = polarPoint(cx, cy, innerR, startDeg);
    const ie = polarPoint(cx, cy, innerR, clampedEnd);
    const large = (clampedEnd - startDeg) > 180 ? 1 : 0;
    return [
      `M ${os.x.toFixed(2)} ${os.y.toFixed(2)}`,
      `A ${outerR} ${outerR} 0 ${large} 1 ${oe.x.toFixed(2)} ${oe.y.toFixed(2)}`,
      `L ${ie.x.toFixed(2)} ${ie.y.toFixed(2)}`,
      `A ${innerR} ${innerR} 0 ${large} 0 ${is.x.toFixed(2)} ${is.y.toFixed(2)}`,
      "Z",
    ].join(" ");
  }

  const PIE_CX = 155;
  const PIE_CY = 110;
  const PIE_OUTER_R = 70;
  const PIE_INNER_R = 28;
```

and:

```ts
  const slices = $derived((() => {
    let angle = 0;
    return breakdown.map(cat => {
      const start = angle;
      const span = (cat.pct / 100) * 360;
      angle += span;
      return { cat, startDeg: start, endDeg: angle, midDeg: start + span / 2 } as Slice;
    });
  })());
```

leaving `breakdown`, `yearlyTotals`, and `lastCompleteYearNum` (the three `$derived` lines directly between the removed blocks) in place.

- [ ] **Step 3: Replace the `<svg>` block with `<DonutChart>`**

Replace the entire `<svg viewBox="0 0 310 220" ...> ... </svg>` block (originally lines 198-254) with:

```svelte
            <DonutChart
              segments={breakdown.map((b) => ({
                id: b.categoryId,
                label: b.name,
                emoji: b.emoji,
                color: b.color,
                valueLabel: `${b.totalAmount.toLocaleString(undefined, { maximumFractionDigits: 0 })} €`,
                pct: b.pct,
              }))}
              centerLabel="Total"
              centerValue={`${breakdown.reduce((a, b) => a + b.totalAmount, 0).toLocaleString(undefined, { maximumFractionDigits: 0 })} €`}
              showLabels={true}
              onsliceclick={(id) => { chartModalCategoryId = id; }}
            />
```

- [ ] **Step 4: Run the full test suite to verify nothing broke**

Run: `cd packages/editor && npm run test`
Expected: PASS

- [ ] **Step 5: Typecheck**

Run: `cd packages/editor && npm run typecheck`
Expected: No errors.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/CostsPage.svelte
git commit -m "refactor(costs): use shared DonutChart in CostsPage"
```

---

## Task 8: `HomeMapWidget.svelte` — read-only floor map widget

**Files:**
- Create: `packages/editor/src/lib/components/HomeMapWidget.svelte`
- Test: `packages/editor/test/HomeMapWidget.test.ts`

**Design note (the deviation mentioned at the top of this plan):** this widget reuses `ChoreOverlay`/`InventoryOverlay`/`CostsOverlay`/`WorksOverlay` directly with `choreMode={false}` / `active={false}` and no-op `onclick`/`ondragend` callbacks, instead of extracting new pin-rendering functions — those components already render pins without interactivity when given `active=false`/`choreMode=false`. The widget also intentionally does not support the "🏠 All" floor pseudo-mode that `FloorSwitcher` exposes (clicking it is a no-op here) since there is no all-floor map rendering anywhere in the app to reuse; `+ Floor`/rename/delete are wired to the real `floorStore` mutations (identical to how the editor topbar's own `FloorSwitcher` instance behaves), so the widget's `FloorSwitcher` is genuinely "reused as-is".

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/HomeMapWidget.test.ts`:

```ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import HomeMapWidget from "../src/lib/components/HomeMapWidget.svelte";
import { createHouseStore } from "../src/lib/houseStore.svelte";
import { createChoreStore } from "../src/lib/choreStore.svelte";
import { createInventoryStore } from "../src/lib/inventoryStore.svelte";
import { createSettingsStore } from "../src/lib/settingsStore.svelte";
import { createCostsStore } from "../src/lib/costsStore.svelte";
import { createWorksStore } from "../src/lib/worksStore.svelte";

function makeFetch() {
  return vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => undefined });
}

function makeStores() {
  vi.stubGlobal("fetch", makeFetch());
  return {
    floorStore: createHouseStore(),
    choreStore: createChoreStore(),
    inventoryStore: createInventoryStore(),
    settingsStore: createSettingsStore(),
    costsStore: createCostsStore(),
    worksStore: createWorksStore(),
  };
}

afterEach(() => vi.unstubAllGlobals());

describe("HomeMapWidget", () => {
  it("renders a read-only canvas with no grid lines", async () => {
    const stores = makeStores();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onnavigate = vi.fn();
    const comp = mount(HomeMapWidget, { target, props: { ...stores, onnavigate } });
    await tick();
    flushSync();

    const svg = target.querySelector("svg.canvas");
    expect(svg).not.toBeNull();
    expect(svg!.querySelectorAll("line.grid-line")).toHaveLength(0);

    unmount(comp);
    target.remove();
  });

  it("renders a floor switcher and layers dropdown", async () => {
    const stores = makeStores();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeMapWidget, { target, props: { ...stores, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".floor-switcher")).not.toBeNull();
    expect(target.querySelector(".layers-dropdown")).not.toBeNull();

    unmount(comp);
    target.remove();
  });

  it("clicking the map area calls onnavigate", async () => {
    const stores = makeStores();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onnavigate = vi.fn();
    const comp = mount(HomeMapWidget, { target, props: { ...stores, onnavigate } });
    await tick();
    flushSync();

    (target.querySelector(".map-area") as HTMLElement).dispatchEvent(
      new MouseEvent("click", { bubbles: true })
    );
    flushSync();

    expect(onnavigate).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });

  it("clicking the floor switcher does not call onnavigate", async () => {
    const stores = makeStores();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onnavigate = vi.fn();
    const comp = mount(HomeMapWidget, { target, props: { ...stores, onnavigate } });
    await tick();
    flushSync();

    (target.querySelector(".floor-switcher .floor-label") as HTMLElement).dispatchEvent(
      new MouseEvent("click", { bubbles: true })
    );
    flushSync();

    expect(onnavigate).not.toHaveBeenCalled();

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/HomeMapWidget.test.ts`
Expected: FAIL — `../src/lib/components/HomeMapWidget.svelte` does not exist.

- [ ] **Step 3: Implement `HomeMapWidget.svelte`**

Create `packages/editor/src/lib/components/HomeMapWidget.svelte`:

```svelte
<script lang="ts">
  import type { createHouseStore } from "../houseStore.svelte";
  import type { createChoreStore } from "../choreStore.svelte";
  import type { createInventoryStore } from "../inventoryStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { createCostsStore } from "../costsStore.svelte";
  import type { createWorksStore } from "../worksStore.svelte";
  import { DEFAULT_VIEWPORT } from "../viewportStore.svelte";
  import { fitViewportToFloor } from "../viewportFit";
  import Card from "./ui/Card.svelte";
  import Canvas from "./Canvas.svelte";
  import FloorSwitcher from "./FloorSwitcher.svelte";
  import LayersDropdown from "./LayersDropdown.svelte";
  import ChoreOverlay from "./ChoreOverlay.svelte";
  import InventoryOverlay from "./InventoryOverlay.svelte";
  import CostsOverlay from "./CostsOverlay.svelte";
  import WorksOverlay from "./WorksOverlay.svelte";

  type HouseStore = ReturnType<typeof createHouseStore>;
  type ChoreStore = ReturnType<typeof createChoreStore>;
  type InventoryStore = ReturnType<typeof createInventoryStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;
  type CostsStore = ReturnType<typeof createCostsStore>;
  type WorksStore = ReturnType<typeof createWorksStore>;

  interface Props {
    floorStore: HouseStore;
    choreStore: ChoreStore;
    inventoryStore: InventoryStore;
    settingsStore: SettingsStore;
    costsStore: CostsStore;
    worksStore: WorksStore;
    onnavigate: () => void;
  }
  let { floorStore, choreStore, inventoryStore, settingsStore, costsStore, worksStore, onnavigate }: Props =
    $props();

  const ALL_FLOOR_ID = "__all__";

  let selectedFloorId = $state<string | null>(null);
  let activeLayers = $state<Set<string>>(new Set(["chores"]));
  let mapWidth = $state(400);
  let mapHeight = $state(240);

  const effectiveFloorId = $derived(
    selectedFloorId && floorStore.floors.some((f) => f.id === selectedFloorId)
      ? selectedFloorId
      : floorStore.floors[0]?.id ?? null
  );
  const currentFloor = $derived(floorStore.floors.find((f) => f.id === effectiveFloorId) ?? null);

  const viewport = $derived(
    currentFloor ? fitViewportToFloor(currentFloor, mapWidth, mapHeight) : DEFAULT_VIEWPORT
  );

  const floorRoomIds = $derived(new Set(currentFloor?.rooms.map((r) => r.id) ?? []));
  const floorAssignments = $derived(
    choreStore.assignments.filter((a) => a.roomId !== null && floorRoomIds.has(a.roomId))
  );
  const floorInventoryItems = $derived(
    inventoryStore.items.filter((i) => i.placement?.floorId === effectiveFloorId)
  );
  const floorCostCategories = $derived(
    settingsStore.costCategories.filter((c) => c.placement?.floorId === effectiveFloorId)
  );
  const floorWorks = $derived(
    worksStore.works.filter((w) => w.placement?.floorId === effectiveFloorId)
  );

  function handleSwitchFloor(id: string): void {
    if (id === ALL_FLOOR_ID) return;
    selectedFloorId = id;
  }

  function handleAddFloor(name: string): void {
    floorStore.addFloor(name);
    selectedFloorId = floorStore.currentFloorId;
  }

  function handleRemoveFloor(id: string): void {
    floorStore.removeFloor(id);
    if (selectedFloorId === id) selectedFloorId = floorStore.currentFloorId;
  }

  function handleRenameFloor(id: string, name: string): void {
    floorStore.renameFloor(id, name);
  }

  function toggleLayer(layer: string): void {
    const next = new Set(activeLayers);
    if (next.has(layer)) next.delete(layer);
    else next.add(layer);
    activeLayers = next;
  }

  function noop(): void {}
</script>

<Card>
  <div class="map-widget-body">
    <div class="map-toolbar">
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <div onclick={(e) => e.stopPropagation()}>
        <FloorSwitcher
          floors={floorStore.floors}
          currentFloorId={effectiveFloorId ?? ""}
          onswitchfloor={handleSwitchFloor}
          onaddfloor={handleAddFloor}
          onrenamefloor={handleRenameFloor}
          onremovefloor={handleRemoveFloor}
        />
      </div>
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <div onclick={(e) => e.stopPropagation()}>
        <LayersDropdown {activeLayers} ontoggle={toggleLayer} />
      </div>
    </div>

    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div class="map-area" bind:clientWidth={mapWidth} bind:clientHeight={mapHeight} onclick={onnavigate}>
      {#if currentFloor}
        <Canvas floor={currentFloor} {viewport} width={mapWidth} height={mapHeight} showGrid={false} />
        {#if activeLayers.has("chores")}
          <ChoreOverlay
            chores={choreStore.chores}
            assignments={floorAssignments}
            {viewport}
            choreMode={false}
            width={mapWidth}
            height={mapHeight}
            onclick={noop}
            ondragend={noop}
          />
        {/if}
        {#if activeLayers.has("inventory")}
          <InventoryOverlay
            items={floorInventoryItems}
            {viewport}
            active={false}
            width={mapWidth}
            height={mapHeight}
            onclick={noop}
            ondragend={noop}
          />
        {/if}
        {#if activeLayers.has("costs")}
          <CostsOverlay
            categories={floorCostCategories}
            {viewport}
            active={false}
            width={mapWidth}
            height={mapHeight}
            onclick={noop}
            ondragend={noop}
          />
        {/if}
        {#if activeLayers.has("works")}
          <WorksOverlay
            works={floorWorks}
            {settingsStore}
            {viewport}
            active={false}
            width={mapWidth}
            height={mapHeight}
            onclick={noop}
            ondragend={noop}
          />
        {/if}
      {:else}
        <div class="empty">No floors yet.</div>
      {/if}
    </div>
  </div>
</Card>

<style>
  .map-widget-body { display: flex; flex-direction: column; gap: var(--space-2); }
  .map-toolbar { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); flex-wrap: wrap; }
  .map-area {
    position: relative; overflow: hidden; height: 220px;
    border-radius: var(--radius-md); background: var(--canvas-bg); cursor: pointer;
  }
  .empty {
    display: flex; align-items: center; justify-content: center; height: 100%;
    color: var(--text-faint); font-size: 12px;
  }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/HomeMapWidget.test.ts`
Expected: PASS

- [ ] **Step 5: Typecheck**

Run: `cd packages/editor && npm run typecheck`
Expected: No errors.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/HomeMapWidget.svelte packages/editor/test/HomeMapWidget.test.ts
git commit -m "feat: add HomeMapWidget read-only floor map"
```

---

## Task 9: `HomeChoresWidget.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/HomeChoresWidget.svelte`
- Test: `packages/editor/test/HomeChoresWidget.test.ts`

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/HomeChoresWidget.test.ts`:

```ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import HomeChoresWidget from "../src/lib/components/HomeChoresWidget.svelte";
import { createChoreStore } from "../src/lib/choreStore.svelte";

const sampleDoc = {
  version: 1,
  chores: [
    { id: "c1", donetickId: null, name: "🧹 Sweep", emoji: "🧹", periodDays: 14, nextDueDate: new Date(Date.now() - 5 * 86400000).toISOString(), description: "" },
    { id: "c2", donetickId: null, name: "🪟 Windows", emoji: "🪟", periodDays: 365, nextDueDate: new Date(Date.now() + 300 * 86400000).toISOString(), description: "" },
  ],
  assignments: [
    { id: "a1", choreId: "c1", roomId: "r1", position: { x: 1, y: 2 }, nextDueDate: new Date(Date.now() - 5 * 86400000).toISOString() },
    { id: "a2", choreId: "c2", roomId: null, position: null, nextDueDate: new Date(Date.now() + 300 * 86400000).toISOString() },
  ],
  completions: [],
};

function makeStore() {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => sampleDoc }));
  return createChoreStore();
}

afterEach(() => vi.unstubAllGlobals());

describe("HomeChoresWidget", () => {
  it("shows the active and overdue counts", async () => {
    const store = makeStore();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeChoresWidget, { target, props: { store, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.textContent).toContain("2");
    expect(target.querySelector(".stat-item.overdue")!.textContent).toContain("1");

    unmount(comp);
    target.remove();
  });

  it("renders the most urgent assignment first", async () => {
    const store = makeStore();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeChoresWidget, { target, props: { store, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    const names = Array.from(target.querySelectorAll(".name")).map((el) => el.textContent);
    expect(names[0]).toBe("Sweep");

    unmount(comp);
    target.remove();
  });

  it("quick-completing a row calls store.completeAssignment", async () => {
    const store = makeStore();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeChoresWidget, { target, props: { store, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();
    (target.querySelector(".done-btn.confirm") as HTMLButtonElement).click();
    flushSync();
    await tick();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/complete"),
      expect.objectContaining({ method: "POST" })
    );

    unmount(comp);
    target.remove();
  });

  it("clicking the widget body calls onnavigate", async () => {
    const store = makeStore();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onnavigate = vi.fn();
    const comp = mount(HomeChoresWidget, { target, props: { store, onnavigate } });
    await tick();
    flushSync();

    (target.querySelector(".widget") as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(onnavigate).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/HomeChoresWidget.test.ts`
Expected: FAIL — `../src/lib/components/HomeChoresWidget.svelte` does not exist.

- [ ] **Step 3: Implement `HomeChoresWidget.svelte`**

Create `packages/editor/src/lib/components/HomeChoresWidget.svelte`:

```svelte
<script lang="ts">
  import type { createChoreStore } from "../choreStore.svelte";
  import { displayName, formatDue } from "../choreFormat";
  import Card from "./ui/Card.svelte";
  import ChoreRow from "./ChoreRow.svelte";

  type ChoreStore = ReturnType<typeof createChoreStore>;

  interface Props {
    store: ChoreStore;
    onnavigate: () => void;
  }
  let { store, onnavigate }: Props = $props();

  interface Row {
    id: string;
    pct: number;
    emoji: string;
    name: string;
    dueLabel: string;
    dueColor: string;
  }

  const rows = $derived(
    store.assignments
      .map((a) => {
        const chore = store.chores.find((c) => c.id === a.choreId);
        if (!chore) return null;
        const pct = store.getProgress(a, chore);
        return {
          id: a.id,
          pct,
          emoji: chore.emoji,
          name: displayName(chore),
          dueLabel: formatDue(a.nextDueDate),
          dueColor: store.getColor(pct),
        } as Row;
      })
      .filter((r): r is Row => r !== null)
      .sort((a, b) => a.pct - b.pct)
  );

  const overdueCount = $derived(rows.filter((r) => r.pct <= 0.25).length);
  const onTrackPct = $derived(
    rows.length > 0 ? Math.round((rows.filter((r) => r.pct > 0.25).length / rows.length) * 100) : 0
  );
  const topFive = $derived(rows.slice(0, 5));
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="widget" onclick={onnavigate}>
  <Card>
    <div class="header">
      <h3>✅ Chores</h3>
    </div>
    <div class="stats">
      <div class="stat-item"><b>{rows.length}</b> active</div>
      <div class="stat-item overdue"><b>{overdueCount}</b> overdue</div>
      <div class="stat-item ontrack"><b>{onTrackPct}%</b> on track</div>
    </div>
    {#if topFive.length === 0}
      <p class="empty">No chore assignments yet.</p>
    {:else}
      <div class="rows">
        {#each topFive as row (row.id)}
          <ChoreRow
            emoji={row.emoji}
            name={row.name}
            dueLabel={row.dueLabel}
            dueColor={row.dueColor}
            oncomplete={(notes) => store.completeAssignment(row.id, notes)}
          />
        {/each}
      </div>
    {/if}
  </Card>
</div>

<style>
  .widget { cursor: pointer; }
  .header { margin-bottom: var(--space-2); }
  .header h3 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text); }
  .stats { display: flex; gap: var(--space-3); font-size: 12px; color: var(--text-muted); margin-bottom: var(--space-2); }
  .stat-item b { color: var(--text); }
  .stat-item.overdue b { color: var(--danger); }
  .stat-item.ontrack b { color: var(--success); }
  .rows { display: flex; flex-direction: column; }
  .empty { font-size: 12px; color: var(--text-faint); text-align: center; padding: var(--space-4) 0; margin: 0; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/HomeChoresWidget.test.ts`
Expected: PASS

- [ ] **Step 5: Typecheck**

Run: `cd packages/editor && npm run typecheck`
Expected: No errors.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/HomeChoresWidget.svelte packages/editor/test/HomeChoresWidget.test.ts
git commit -m "feat: add HomeChoresWidget with quick-complete"
```

---

## Task 10: `HomeCostsWidget.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/HomeCostsWidget.svelte`
- Test: `packages/editor/test/HomeCostsWidget.test.ts`

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/HomeCostsWidget.test.ts`:

```ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import HomeCostsWidget from "../src/lib/components/HomeCostsWidget.svelte";
import { createCostsStore } from "../src/lib/costsStore.svelte";
import { createSettingsStore } from "../src/lib/settingsStore.svelte";

const lastYear = new Date().getFullYear() - 1;

function makeStores(withEntries: boolean) {
  const costsDoc = {
    version: 1,
    entries: withEntries
      ? [{ id: "e1", categoryId: "cat1", date: `${lastYear}-03-01`, totalAmount: 300, quantity: null, unitPrice: null, supplierId: null, notes: "", roomId: null }]
      : [],
  };
  const settingsDoc = {
    version: 1,
    costCategories: [{ id: "cat1", name: "Fuel", emoji: "⛽", unit: "L", color: "#e76f51" }],
    inventoryCategories: [],
    workCategories: [],
    suppliers: [],
  };
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((url: string) => {
      if (url === "/api/costs") return Promise.resolve({ ok: true, status: 200, json: async () => costsDoc });
      if (url === "/api/settings") return Promise.resolve({ ok: true, status: 200, json: async () => settingsDoc });
      return Promise.resolve({ ok: false, status: 404, json: async () => undefined });
    })
  );
  return { costsStore: createCostsStore(), settingsStore: createSettingsStore() };
}

afterEach(() => vi.unstubAllGlobals());

describe("HomeCostsWidget", () => {
  it("renders a donut chart when there are entries", async () => {
    const stores = makeStores(true);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeCostsWidget, { target, props: { ...stores, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelectorAll("svg path")).toHaveLength(1);

    unmount(comp);
    target.remove();
  });

  it("shows an empty state when there are no entries", async () => {
    const stores = makeStores(false);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeCostsWidget, { target, props: { ...stores, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".empty")).not.toBeNull();
    expect(target.querySelectorAll("svg path")).toHaveLength(0);

    unmount(comp);
    target.remove();
  });

  it("clicking the widget calls onnavigate", async () => {
    const stores = makeStores(true);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onnavigate = vi.fn();
    const comp = mount(HomeCostsWidget, { target, props: { ...stores, onnavigate } });
    await tick();
    flushSync();

    (target.querySelector(".widget") as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(onnavigate).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/HomeCostsWidget.test.ts`
Expected: FAIL — `../src/lib/components/HomeCostsWidget.svelte` does not exist.

- [ ] **Step 3: Implement `HomeCostsWidget.svelte`**

Create `packages/editor/src/lib/components/HomeCostsWidget.svelte`:

```svelte
<script lang="ts">
  import type { createCostsStore } from "../costsStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import Card from "./ui/Card.svelte";
  import DonutChart from "./DonutChart.svelte";

  type CostsStore = ReturnType<typeof createCostsStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    costsStore: CostsStore;
    settingsStore: SettingsStore;
    onnavigate: () => void;
  }
  let { costsStore, settingsStore, onnavigate }: Props = $props();

  const breakdown = $derived(costsStore.breakdownLastCompleteYear(settingsStore.costCategories));
  const lastCompleteYearNum = $derived(costsStore.lastCompleteYear());
  const total = $derived(breakdown.reduce((a, b) => a + b.totalAmount, 0));

  const segments = $derived(
    breakdown.map((b) => ({
      id: b.categoryId,
      label: b.name,
      emoji: b.emoji,
      color: b.color,
      valueLabel: `${b.totalAmount.toLocaleString(undefined, { maximumFractionDigits: 0 })} €`,
      pct: b.pct,
    }))
  );
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="widget" onclick={onnavigate}>
  <Card>
    <div class="header">
      <h3>💶 Costs</h3>
      <span class="sub">{lastCompleteYearNum}</span>
    </div>
    {#if breakdown.length === 0}
      <p class="empty">No cost entries yet.</p>
    {:else}
      <div class="chart-wrap">
        <DonutChart
          {segments}
          centerLabel="Total"
          centerValue={`${total.toLocaleString(undefined, { maximumFractionDigits: 0 })} €`}
        />
      </div>
    {/if}
  </Card>
</div>

<style>
  .widget { cursor: pointer; }
  .header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: var(--space-2); }
  .header h3 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text); }
  .sub { font-size: 11px; color: var(--text-faint); }
  .chart-wrap { display: flex; justify-content: center; }
  .empty { font-size: 12px; color: var(--text-faint); text-align: center; padding: var(--space-4) 0; margin: 0; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/HomeCostsWidget.test.ts`
Expected: PASS

- [ ] **Step 5: Typecheck**

Run: `cd packages/editor && npm run typecheck`
Expected: No errors.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/HomeCostsWidget.svelte packages/editor/test/HomeCostsWidget.test.ts
git commit -m "feat: add HomeCostsWidget donut chart"
```

---

## Task 11: `HomeInventoryWidget.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/HomeInventoryWidget.svelte`
- Test: `packages/editor/test/HomeInventoryWidget.test.ts`

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/HomeInventoryWidget.test.ts`:

```ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import HomeInventoryWidget from "../src/lib/components/HomeInventoryWidget.svelte";
import { createInventoryStore } from "../src/lib/inventoryStore.svelte";

const sampleDoc = {
  items: [
    { id: "i1", name: "Drill", emoji: "🔧", category: "Tools", brand: null, model: null, serialNumber: null, purchaseDate: null, purchasePrice: null, warrantyExpiryDate: null, notes: "", attachments: [], placement: null },
    { id: "i2", name: "Saw", emoji: "🪚", category: "Tools", brand: null, model: null, serialNumber: null, purchaseDate: null, purchasePrice: null, warrantyExpiryDate: null, notes: "", attachments: [], placement: null },
    { id: "i3", name: "Sofa", emoji: "🛋️", category: "Furniture", brand: null, model: null, serialNumber: null, purchaseDate: null, purchasePrice: null, warrantyExpiryDate: null, notes: "", attachments: [], placement: null },
  ],
};

function makeStore(empty = false) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => (empty ? { items: [] } : sampleDoc) })
  );
  return createInventoryStore();
}

afterEach(() => vi.unstubAllGlobals());

describe("HomeInventoryWidget", () => {
  it("renders a donut slice per category", async () => {
    const inventoryStore = makeStore();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeInventoryWidget, { target, props: { inventoryStore, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelectorAll("svg path")).toHaveLength(2);

    unmount(comp);
    target.remove();
  });

  it("shows per-category counts", async () => {
    const inventoryStore = makeStore();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeInventoryWidget, { target, props: { inventoryStore, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    const text = target.querySelector(".counts")!.textContent;
    expect(text).toContain("Tools");
    expect(text).toContain("2");
    expect(text).toContain("Furniture");
    expect(text).toContain("1");

    unmount(comp);
    target.remove();
  });

  it("shows an empty state with no items", async () => {
    const inventoryStore = makeStore(true);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeInventoryWidget, { target, props: { inventoryStore, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".empty")).not.toBeNull();

    unmount(comp);
    target.remove();
  });

  it("clicking the widget calls onnavigate", async () => {
    const inventoryStore = makeStore();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onnavigate = vi.fn();
    const comp = mount(HomeInventoryWidget, { target, props: { inventoryStore, onnavigate } });
    await tick();
    flushSync();

    (target.querySelector(".widget") as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(onnavigate).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/HomeInventoryWidget.test.ts`
Expected: FAIL — `../src/lib/components/HomeInventoryWidget.svelte` does not exist.

- [ ] **Step 3: Implement `HomeInventoryWidget.svelte`**

Create `packages/editor/src/lib/components/HomeInventoryWidget.svelte`:

```svelte
<script lang="ts">
  import type { createInventoryStore } from "../inventoryStore.svelte";
  import Card from "./ui/Card.svelte";
  import DonutChart from "./DonutChart.svelte";

  type InventoryStore = ReturnType<typeof createInventoryStore>;

  interface Props {
    inventoryStore: InventoryStore;
    onnavigate: () => void;
  }
  let { inventoryStore, onnavigate }: Props = $props();

  const PALETTE = ["#5b8def", "#f2994a", "#27ae60", "#eb5757", "#9b51e0", "#17a2b8", "#f2c94c", "#bdbdbd"];

  interface CategoryCount {
    category: string;
    count: number;
  }

  const categoryCounts = $derived((() => {
    const counts = new Map<string, number>();
    for (const item of inventoryStore.items) {
      const key = item.category || "Uncategorized";
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return [...counts.entries()]
      .map(([category, count]): CategoryCount => ({ category, count }))
      .sort((a, b) => b.count - a.count);
  })());

  const total = $derived(categoryCounts.reduce((a, c) => a + c.count, 0));

  const segments = $derived(
    categoryCounts.map((c, i) => ({
      id: c.category,
      label: c.category,
      emoji: "📦",
      color: PALETTE[i % PALETTE.length],
      valueLabel: `${c.count}`,
      pct: total > 0 ? (c.count / total) * 100 : 0,
    }))
  );

  function colorFor(category: string): string {
    return segments.find((s) => s.id === category)?.color ?? PALETTE[0];
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="widget" onclick={onnavigate}>
  <Card>
    <div class="header">
      <h3>📦 Inventory</h3>
      <span class="sub">{total} items</span>
    </div>
    {#if categoryCounts.length === 0}
      <p class="empty">No inventory items yet.</p>
    {:else}
      <div class="body">
        <div class="chart-wrap">
          <DonutChart {segments} centerLabel="Items" centerValue={`${total}`} />
        </div>
        <ul class="counts">
          {#each categoryCounts as c (c.category)}
            <li>
              <span class="dot" style="background:{colorFor(c.category)}"></span>
              {c.category} <b>{c.count}</b>
            </li>
          {/each}
        </ul>
      </div>
    {/if}
  </Card>
</div>

<style>
  .widget { cursor: pointer; }
  .header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: var(--space-2); }
  .header h3 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text); }
  .sub { font-size: 11px; color: var(--text-faint); }
  .body { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); }
  .chart-wrap { display: flex; justify-content: center; }
  .counts { list-style: none; margin: 0; padding: 0; width: 100%; font-size: 12px; color: var(--text-muted); display: flex; flex-direction: column; gap: 4px; }
  .counts li { display: flex; align-items: center; gap: 6px; }
  .counts b { margin-left: auto; color: var(--text); }
  .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .empty { font-size: 12px; color: var(--text-faint); text-align: center; padding: var(--space-4) 0; margin: 0; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/HomeInventoryWidget.test.ts`
Expected: PASS

- [ ] **Step 5: Typecheck**

Run: `cd packages/editor && npm run typecheck`
Expected: No errors.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/HomeInventoryWidget.svelte packages/editor/test/HomeInventoryWidget.test.ts
git commit -m "feat: add HomeInventoryWidget pie chart with per-category counts"
```

---

## Task 12: `HomeWorksWidget.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/HomeWorksWidget.svelte`
- Test: `packages/editor/test/HomeWorksWidget.test.ts`

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/HomeWorksWidget.test.ts`:

```ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import HomeWorksWidget from "../src/lib/components/HomeWorksWidget.svelte";
import { createWorksStore } from "../src/lib/worksStore.svelte";

const sampleDoc = {
  version: 1,
  works: [
    { id: "w1", title: "Repaint fence", description: "", status: "done", categoryId: null, date: "2026-01-10", totalCost: 150, supplierId: null, notes: "", attachments: [], placement: null },
    { id: "w2", title: "Fix roof leak", description: "", status: "in_progress", categoryId: null, date: "2026-05-01", totalCost: 400, supplierId: null, notes: "", attachments: [], placement: null },
    { id: "w3", title: "New deck", description: "", status: "planned", categoryId: null, date: "2026-08-01", totalCost: null, supplierId: null, notes: "", attachments: [], placement: null },
  ],
};

function makeStore() {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => sampleDoc }));
  return createWorksStore();
}

afterEach(() => vi.unstubAllGlobals());

describe("HomeWorksWidget", () => {
  it("shows counts per status", async () => {
    const worksStore = makeStore();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeWorksWidget, { target, props: { worksStore, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    const stats = Array.from(target.querySelectorAll(".stat-value")).map((el) => el.textContent);
    expect(stats).toEqual(["1", "1", "1"]);

    unmount(comp);
    target.remove();
  });

  it("shows the total cost across all works", async () => {
    const worksStore = makeStore();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeWorksWidget, { target, props: { worksStore, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".sub")!.textContent).toContain("550");

    unmount(comp);
    target.remove();
  });

  it("lists the 5 most recent works, newest first", async () => {
    const worksStore = makeStore();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeWorksWidget, { target, props: { worksStore, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    const titles = Array.from(target.querySelectorAll(".title")).map((el) => el.textContent);
    expect(titles).toEqual(["New deck", "Fix roof leak", "Repaint fence"]);

    unmount(comp);
    target.remove();
  });

  it("clicking the widget calls onnavigate", async () => {
    const worksStore = makeStore();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onnavigate = vi.fn();
    const comp = mount(HomeWorksWidget, { target, props: { worksStore, onnavigate } });
    await tick();
    flushSync();

    (target.querySelector(".widget") as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(onnavigate).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/HomeWorksWidget.test.ts`
Expected: FAIL — `../src/lib/components/HomeWorksWidget.svelte` does not exist.

- [ ] **Step 3: Implement `HomeWorksWidget.svelte`**

Create `packages/editor/src/lib/components/HomeWorksWidget.svelte`:

```svelte
<script lang="ts">
  import type { createWorksStore, Work } from "../worksStore.svelte";
  import Card from "./ui/Card.svelte";

  type WorksStore = ReturnType<typeof createWorksStore>;

  interface Props {
    worksStore: WorksStore;
    onnavigate: () => void;
  }
  let { worksStore, onnavigate }: Props = $props();

  const plannedCount = $derived(worksStore.works.filter((w) => w.status === "planned").length);
  const inProgressCount = $derived(worksStore.works.filter((w) => w.status === "in_progress").length);
  const doneCount = $derived(worksStore.works.filter((w) => w.status === "done").length);
  const totalCost = $derived(worksStore.works.reduce((sum, w) => sum + (w.totalCost ?? 0), 0));

  const recentWorks = $derived(
    [...worksStore.works].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()).slice(0, 5)
  );

  function formatDate(iso: string): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  }

  function statusLabel(status: Work["status"]): string {
    if (status === "planned") return "Planned";
    if (status === "in_progress") return "In progress";
    return "Done";
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="widget" onclick={onnavigate}>
  <Card>
    <div class="header">
      <h3>🔧 Works</h3>
      <span class="sub">{totalCost.toLocaleString(undefined, { maximumFractionDigits: 0 })} € total</span>
    </div>
    <div class="stats">
      <div class="stat"><div class="stat-value">{plannedCount}</div><div class="stat-label">Planned</div></div>
      <div class="stat"><div class="stat-value">{inProgressCount}</div><div class="stat-label">In progress</div></div>
      <div class="stat"><div class="stat-value">{doneCount}</div><div class="stat-label">Done</div></div>
    </div>
    {#if recentWorks.length === 0}
      <p class="empty">No works logged yet.</p>
    {:else}
      <ul class="list">
        {#each recentWorks as work (work.id)}
          <li>
            <span class="title">{work.title}</span>
            <span class="status status-{work.status}">{statusLabel(work.status)}</span>
            <span class="date">{formatDate(work.date)}</span>
          </li>
        {/each}
      </ul>
    {/if}
  </Card>
</div>

<style>
  .widget { cursor: pointer; }
  .header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: var(--space-3); }
  .header h3 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text); }
  .sub { font-size: 11px; color: var(--text-faint); }
  .stats { display: flex; gap: var(--space-2); margin-bottom: var(--space-3); }
  .stat { flex: 1; text-align: center; }
  .stat-value { font-size: 18px; font-weight: 700; color: var(--text); }
  .stat-label { font-size: 10px; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.05em; }
  .list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
  .list li { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-muted); }
  .title { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text); font-weight: 500; }
  .status { font-size: 10px; padding: 2px 6px; border-radius: var(--radius-pill); background: var(--surface-alt); white-space: nowrap; }
  .status-done { color: var(--success); }
  .status-in_progress { color: var(--warning); }
  .status-planned { color: var(--text-faint); }
  .date { font-size: 11px; color: var(--text-faint); white-space: nowrap; }
  .empty { font-size: 12px; color: var(--text-faint); text-align: center; padding: var(--space-4) 0; margin: 0; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/HomeWorksWidget.test.ts`
Expected: PASS

- [ ] **Step 5: Typecheck**

Run: `cd packages/editor && npm run typecheck`
Expected: No errors.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/HomeWorksWidget.svelte packages/editor/test/HomeWorksWidget.test.ts
git commit -m "feat: add HomeWorksWidget status stats and recent list"
```

---

## Task 13: `HomePage.svelte` — assemble the dashboard

**Files:**
- Create: `packages/editor/src/lib/components/HomePage.svelte`
- Test: `packages/editor/test/HomePage.test.ts`

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/HomePage.test.ts`:

```ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import HomePage from "../src/lib/components/HomePage.svelte";
import { createHouseStore } from "../src/lib/houseStore.svelte";
import { createChoreStore } from "../src/lib/choreStore.svelte";
import { createInventoryStore } from "../src/lib/inventoryStore.svelte";
import { createSettingsStore } from "../src/lib/settingsStore.svelte";
import { createCostsStore } from "../src/lib/costsStore.svelte";
import { createWorksStore } from "../src/lib/worksStore.svelte";

function makeStores() {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => undefined }));
  return {
    floorStore: createHouseStore(),
    choreStore: createChoreStore(),
    inventoryStore: createInventoryStore(),
    settingsStore: createSettingsStore(),
    costsStore: createCostsStore(),
    worksStore: createWorksStore(),
  };
}

afterEach(() => vi.unstubAllGlobals());

describe("HomePage", () => {
  it("renders all five widgets", async () => {
    const stores = makeStores();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomePage, { target, props: stores });
    await tick();
    flushSync();

    expect(target.querySelector(".home-page")).not.toBeNull();
    expect(target.querySelector(".map-area")).not.toBeNull();
    expect(target.textContent).toContain("Chores");
    expect(target.textContent).toContain("Costs");
    expect(target.textContent).toContain("Inventory");
    expect(target.textContent).toContain("Works");

    unmount(comp);
    target.remove();
  });

  it("navigates to #/chores when the chores widget is clicked", async () => {
    const stores = makeStores();
    const target = document.createElement("div");
    document.body.appendChild(target);
    window.location.hash = "";
    const comp = mount(HomePage, { target, props: stores });
    await tick();
    flushSync();

    const choresWidget = Array.from(target.querySelectorAll(".widget")).find((w) =>
      w.textContent?.includes("Chores")
    ) as HTMLElement;
    choresWidget.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(window.location.hash).toBe("#/chores");

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/HomePage.test.ts`
Expected: FAIL — `../src/lib/components/HomePage.svelte` does not exist.

- [ ] **Step 3: Implement `HomePage.svelte`**

Create `packages/editor/src/lib/components/HomePage.svelte`:

```svelte
<script lang="ts">
  import type { createHouseStore } from "../houseStore.svelte";
  import type { createChoreStore } from "../choreStore.svelte";
  import type { createInventoryStore } from "../inventoryStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { createCostsStore } from "../costsStore.svelte";
  import type { createWorksStore } from "../worksStore.svelte";
  import HomeMapWidget from "./HomeMapWidget.svelte";
  import HomeChoresWidget from "./HomeChoresWidget.svelte";
  import HomeCostsWidget from "./HomeCostsWidget.svelte";
  import HomeInventoryWidget from "./HomeInventoryWidget.svelte";
  import HomeWorksWidget from "./HomeWorksWidget.svelte";

  type HouseStore = ReturnType<typeof createHouseStore>;
  type ChoreStore = ReturnType<typeof createChoreStore>;
  type InventoryStore = ReturnType<typeof createInventoryStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;
  type CostsStore = ReturnType<typeof createCostsStore>;
  type WorksStore = ReturnType<typeof createWorksStore>;

  interface Props {
    floorStore: HouseStore;
    choreStore: ChoreStore;
    inventoryStore: InventoryStore;
    settingsStore: SettingsStore;
    costsStore: CostsStore;
    worksStore: WorksStore;
  }
  let { floorStore, choreStore, inventoryStore, settingsStore, costsStore, worksStore }: Props = $props();

  function navigate(hash: string): void {
    window.location.hash = hash;
  }
</script>

<div class="home-page">
  <div class="col-main">
    <HomeMapWidget
      {floorStore}
      {choreStore}
      {inventoryStore}
      {settingsStore}
      {costsStore}
      {worksStore}
      onnavigate={() => navigate("#/plan")}
    />
    <HomeChoresWidget store={choreStore} onnavigate={() => navigate("#/chores")} />
  </div>
  <div class="col-side">
    <HomeCostsWidget {costsStore} {settingsStore} onnavigate={() => navigate("#/costs")} />
    <HomeInventoryWidget {inventoryStore} onnavigate={() => navigate("#/inventory")} />
    <HomeWorksWidget {worksStore} onnavigate={() => navigate("#/works")} />
  </div>
</div>

<style>
  .home-page {
    height: 100%;
    overflow-y: auto;
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: var(--space-4);
    padding: var(--space-4);
    box-sizing: border-box;
  }
  .col-main, .col-side {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    min-width: 0;
  }

  @media (max-width: 600px) {
    .home-page { grid-template-columns: 1fr; }
  }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/HomePage.test.ts`
Expected: PASS

- [ ] **Step 5: Typecheck**

Run: `cd packages/editor && npm run typecheck`
Expected: No errors.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/HomePage.svelte packages/editor/test/HomePage.test.ts
git commit -m "feat: add HomePage assembling the dashboard widgets"
```

---

## Task 14: `NavMenu.svelte` — add Home, repoint Floor Plan to `#/plan`

**Files:**
- Modify: `packages/editor/src/lib/components/NavMenu.svelte:9-16`
- Test: `packages/editor/test/NavMenu.test.ts` (new file — none existed before)

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/NavMenu.test.ts`:

```ts
import { describe, it, expect, vi } from "vitest";
import { mount, unmount } from "svelte";
import NavMenu from "../src/lib/components/NavMenu.svelte";

describe("NavMenu", () => {
  it("lists Home before Floor Plan, pointing at # and #/plan", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(NavMenu, {
      target,
      props: { currentRoute: "#/", expanded: true, onclose: vi.fn() },
    });

    const links = Array.from(target.querySelectorAll(".nav-item")).map((a) => ({
      href: (a as HTMLAnchorElement).getAttribute("href"),
      label: a.querySelector(".nav-label")?.textContent,
    }));

    expect(links[0]).toEqual({ href: "#/", label: "Home" });
    expect(links[1]).toEqual({ href: "#/plan", label: "Floor Plan" });

    unmount(comp);
    target.remove();
  });

  it("marks Home active at the default route and Floor Plan active at #/plan", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(NavMenu, {
      target,
      props: { currentRoute: "#/plan", expanded: true, onclose: vi.fn() },
    });

    const items = Array.from(target.querySelectorAll(".nav-item"));
    const home = items.find((a) => a.querySelector(".nav-label")?.textContent === "Home")!;
    const plan = items.find((a) => a.querySelector(".nav-label")?.textContent === "Floor Plan")!;
    expect(home.classList.contains("active")).toBe(false);
    expect(plan.classList.contains("active")).toBe(true);

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/NavMenu.test.ts`
Expected: FAIL — the first nav item is currently `{ href: "#/", label: "Floor Plan" }`, and there is no `#/plan` entry.

- [ ] **Step 3: Update the `modules` array**

In `packages/editor/src/lib/components/NavMenu.svelte`, replace lines 9-16:

```ts
  const modules = [
    { href: "#/",            icon: "🏠", label: "Floor Plan"   },
    { href: "#/chores",      icon: "✅", label: "Chores"       },
    { href: "#/inventory",   icon: "📦", label: "Inventory"    },
    { href: "#/consumables", icon: "🛒", label: "Consumables"  },
    { href: "#/works",       icon: "🔧", label: "Works"        },
    { href: "#/costs",       icon: "💶", label: "Costs"        },
  ];
```

with:

```ts
  const modules = [
    { href: "#/",            icon: "🏡", label: "Home"         },
    { href: "#/plan",        icon: "🏠", label: "Floor Plan"   },
    { href: "#/chores",      icon: "✅", label: "Chores"       },
    { href: "#/inventory",   icon: "📦", label: "Inventory"    },
    { href: "#/consumables", icon: "🛒", label: "Consumables"  },
    { href: "#/works",       icon: "🔧", label: "Works"        },
    { href: "#/costs",       icon: "💶", label: "Costs"        },
  ];
```

`isActive` (lines 20-23) needs no change: its `href === "#/"` special case already makes "Home" active for both `"#/"` and `""`, and `"#/plan"` is matched by the generic `currentRoute.startsWith(href)` branch.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/NavMenu.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/NavMenu.svelte packages/editor/test/NavMenu.test.ts
git commit -m "feat(nav): add Home entry, move Floor Plan to #/plan"
```

---

## Task 15: `App.svelte` routing — `#/` renders `HomePage`, editor moves to `#/plan`

**Files:**
- Modify: `packages/editor/src/App.svelte:21` (import), `:179` (isFloorPlan), `:846-848` (new branch)
- Modify: `packages/editor/test/App.test.ts:38-45` (`mountAndLoad` route param), `:323` (room panel test), new `describe("App — home dashboard routing", ...)` block

- [ ] **Step 1: Write the failing tests**

In `packages/editor/test/App.test.ts`, change the `mountAndLoad` helper (lines 38-45) from:

```ts
async function mountAndLoad(target: HTMLElement): Promise<ReturnType<typeof mount>> {
  const app = mount(App, { target });
  // Let the fetch micro-tasks resolve (init() awaits fetch then sets loaded=true)
  await tick();
  await tick();
  flushSync();
  return app;
}
```

to:

```ts
async function mountAndLoad(target: HTMLElement, route = "#/plan"): Promise<ReturnType<typeof mount>> {
  window.location.hash = route;
  const app = mount(App, { target });
  // Let the fetch micro-tasks resolve (init() awaits fetch then sets loaded=true)
  await tick();
  await tick();
  flushSync();
  return app;
}
```

This default preserves every existing call site (none of them pass a `route` argument, so they keep exercising the floor-plan editor exactly as before).

Then fix the one test that mounts `App` directly instead of through `mountAndLoad` — in the `describe("App — room panel", ...)` block, change:

```ts
  it("room panel is not visible initially", async () => {
    stubFetch404();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(App, { target });
```

to:

```ts
  it("room panel is not visible initially", async () => {
    stubFetch404();
    window.location.hash = "#/plan";
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(App, { target });
```

Finally, add a new `describe` block at the end of the file (after the closing `});` of `describe("App — item picker visibility across floor modes", ...)`):

```ts
describe("App — home dashboard routing", () => {
  beforeEach(() => {
    stubFetch404();
  });

  it("renders the home dashboard at the default route", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = await mountAndLoad(target, "#/");

    expect(target.querySelector(".home-page")).not.toBeNull();
    expect(target.querySelector("svg.canvas")).toBeNull();

    unmount(app);
    target.remove();
  });

  it("renders the floor plan editor at #/plan", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = await mountAndLoad(target, "#/plan");

    expect(target.querySelector("svg.canvas")).not.toBeNull();
    expect(target.querySelector(".home-page")).toBeNull();

    unmount(app);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "home dashboard routing"`
Expected: FAIL — `#/` currently still renders the floor-plan editor, so `.home-page` is null and `svg.canvas` is present; `#/plan` doesn't match `isFloorPlan` yet (which is still `currentRoute === "#/" || currentRoute === ""`), so neither test passes.

- [ ] **Step 3: Import `HomePage` in `App.svelte`**

In `packages/editor/src/App.svelte`, after the existing `import NavMenu from "./lib/components/NavMenu.svelte";` (line 21), add:

```svelte
  import HomePage from "./lib/components/HomePage.svelte";
```

- [ ] **Step 4: Repoint `isFloorPlan` and add `isHome`**

Change line 179 from:

```ts
  const isFloorPlan = $derived(currentRoute === "#/" || currentRoute === "");
```

to:

```ts
  const isFloorPlan = $derived(currentRoute === "#/plan");
  const isHome = $derived(currentRoute === "#/" || currentRoute === "");
```

- [ ] **Step 5: Add the `HomePage` route branch**

In the main route switch inside `<div class="content">`, insert a new `{:else if isHome}` branch right after the floor-plan block closes and before the chores branch. Currently (lines 846-848):

```svelte
        </div>

      {:else if currentRoute === "#/chores"}
```

becomes:

```svelte
        </div>

      {:else if isHome}
        <HomePage
          {floorStore}
          {choreStore}
          {inventoryStore}
          {settingsStore}
          {costsStore}
          {worksStore}
        />

      {:else if currentRoute === "#/chores"}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/App.test.ts`
Expected: PASS — all tests in the file, including the two new routing tests.

- [ ] **Step 7: Run the full test suite and typecheck**

Run: `cd packages/editor && npm run test && npm run typecheck`
Expected: All tests PASS, no type errors.

- [ ] **Step 8: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/test/App.test.ts
git commit -m "feat(routing): render HomePage at #/, move floor-plan editor to #/plan"
```

---

## Task 16: Final validation

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `cd packages/editor && npm run test`
Expected: All tests PASS (existing + all new files from Tasks 1-15).

- [ ] **Step 2: Run the typechecker**

Run: `cd packages/editor && npm run typecheck`
Expected: No errors.

- [ ] **Step 3: Manual browser check**

Run: `cd packages/editor && npm run dev`, then open the printed local URL.

Check:
- `#/` shows the dashboard: map widget (floor switcher + layer dropdown, no grid, chores pins by default), chores widget below it with a working quick-complete, and the costs/inventory/works widgets in the right column.
- Clicking each widget's non-interactive area navigates to its full page (`#/plan`, `#/chores`, `#/costs`, `#/inventory`, `#/works`).
- Clicking the map widget's floor switcher / layer dropdown does **not** navigate away.
- Resizing the browser narrower than 600px collapses the dashboard to a single column, in order: Map, Chores, Costs, Inventory, Works.
- The page itself scrolls when content overflows; individual widget cards do not scroll internally.
- The nav menu shows "Home" (🏡) above "Floor Plan" (🏠, now pointing at `#/plan`), and both highlight correctly when active.

(The backend serves `/api/*` from `localhost:8000` — if no backend is running, every store falls back to its empty/error state, which the widgets already render gracefully; the layout and navigation can still be fully verified.)

- [ ] **Step 4: Stop the dev server**

No commit for this task — it's verification only. If manual testing surfaces a bug, fix it as a small follow-up commit referencing the affected task above.
