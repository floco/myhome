# Viewport Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Fix the floor plan editor's viewport so it never renders blank after a refresh or floor switch, and add a dedicated Pan tool alongside the existing space+drag/middle-click/pinch panning.

**Architecture:** Three independent slices in the `packages/editor` Svelte frontend: (1) an `$effect` in `App.svelte` that auto-fits the viewport whenever the active floor changes, reusing the existing `fitViewportToFloor`/`viewportStore.reset` machinery; (2) a new `"pan"` `ToolType` that reuses `Canvas.svelte`'s existing pan-drag code path (today reachable only via space+drag/middle-click); (3) a verification pass confirming the existing two-pointer pinch/pan gesture code already has adequate regression coverage.

**Tech Stack:** Svelte 5 (runes: `$state`, `$derived`, `$effect`, `untrack`), TypeScript, Vitest + `svelte`'s `mount`/`unmount`/`flushSync` test helpers, `svelte-i18n`.

## Global Constraints

- No persistence of per-floor viewport state — always auto-fit on load/switch (per approved spec, rejected the "remember after" alternative).
- The Pan tool is a persistent toggle (like Select/Wall), not click-and-hold.
- The Pan toolbar button must be visible in both edit mode and view mode (`viewMode`), unlike the other draw/select tools which stay edit-mode-only. It must still be hidden when `choreLayerActive` or `allFloorsMode` is true, matching the existing gating for that whole tool group.
- No change to zoom min/max bounds, the fit-padding constant (`40`, `fitViewportToFloor`'s default), double-tap gestures, or per-floor viewport memory — all explicitly out of scope per the spec.
- Spec source of truth: `docs/superpowers/specs/2026-08-09-viewport-reliability-design.md`.

---

### Task 1: Auto-fit viewport on floor load and floor switch

**Files:**
- Modify: `packages/editor/src/App.svelte` (imports near line 1; new `$effect` near line 389, after the `canvasWidth`/`canvasHeight` declarations)
- Test: `packages/editor/test/App.viewportAutoFit.test.ts` (new file)

**Interfaces:**
- Consumes: `viewportStore.reset(floor: Floor, width: number, height: number): void` (existing, `packages/editor/src/lib/viewportStore.svelte.ts`), `floorStore.currentFloorId: string`, `floorStore.floor: Floor`, `floorStore.loaded: boolean` (existing getters, `packages/editor/src/lib/houseStore.svelte.ts`).
- Produces: nothing new consumed by later tasks — this is a self-contained wiring change.

**Why `untrack` is required:** `viewportStore.reset(floorStore.floor, canvasWidth, canvasHeight)` reads deep into `floor.walls` (via `fitViewportToFloor` → `allEndpoints`), and `canvasWidth`/`canvasHeight` update on every container resize (`bind:clientWidth`/`clientHeight` in the template). If those reads aren't wrapped in `untrack()`, Svelte's `$effect` auto-subscribes to them, and the auto-fit would incorrectly re-fire on every wall edit (disrupting an in-progress edit by yanking the view) and on every browser/window resize (annoying, out of scope). Wrapping the reset call in `untrack()` keeps the effect's only real triggers as `floorStore.currentFloorId` and `floorStore.loaded`, matching the spec's stated behavior exactly.

- [x] **Step 1: Add the `untrack` import**

In `packages/editor/src/App.svelte`, change line 1 from:

```svelte
  import { _ } from "svelte-i18n";
```

to:

```svelte
  import { _ } from "svelte-i18n";
  import { untrack } from "svelte";
```

- [x] **Step 2: Write the failing integration test**

Create `packages/editor/test/App.viewportAutoFit.test.ts`:

```ts
import { describe, it, expect, afterEach, vi } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import App from "../src/App.svelte";

const HOME = { id: "home-1", name: "Main House", type: "existing", enabledModules: [], createdAt: "2026-01-01T00:00:00.000Z" };

// A single divider segment far from world-origin (50,50)-(54,50). DividerShape
// renders a plain <line> at worldToScreen(start/end) with no thickness/miter
// offset, so its rendered x1/y1/x2/y2 let us assert the exact fitted viewport
// without duplicating fitViewportToFloor's math.
// "gf-1", not "floor-1": createEmptyFloor() (the transient placeholder
// floor rendered before any real data loads) hardcodes id "floor-1". If our
// fixture reused that id, currentFloorId would look unchanged once the real
// floor replaces the placeholder, and the auto-fit effect wouldn't re-fire.
const HOUSE_DOC = {
  version: 1,
  house: { name: "Main House", units: "m", gridSnap: 0.1 },
  floors: [
    {
      id: "gf-1",
      name: "Ground Floor",
      order: 0,
      walls: [
        { id: "w1", type: "divider", start: { x: 50, y: 50 }, end: { x: 54, y: 50 } },
      ],
      openings: [],
      rooms: [],
      furnitureObjects: [],
    },
  ],
  currentFloorId: "gf-1",
};

function stubFetch() {
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
    const handlers: Record<string, unknown> = {
      "/api/auth/me": { id: "u1", username: "admin", role: "admin" },
      "/api/homes": [HOME],
      [`/api/homes/${HOME.id}/house`]: HOUSE_DOC,
    };
    if (url in handlers) {
      return Promise.resolve({ ok: true, status: 200, json: async () => handlers[url] });
    }
    return Promise.resolve({ ok: false, status: 404, json: async () => undefined });
  }));
}

// jsdom reports 0 for clientWidth/clientHeight on every element (no real
// layout engine), which is what keeps the auto-fit effect inert in every
// *other* test in this suite (its width/height guard blocks it). Here we
// override it globally for this file so the effect has real dimensions to
// fit against — 1000x700 was chosen so the expected fit below works out to
// round numbers (see the math comment at the first assertion).
let originalClientWidth: PropertyDescriptor | undefined;
let originalClientHeight: PropertyDescriptor | undefined;

function stubContainerSize(): void {
  originalClientWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "clientWidth");
  originalClientHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "clientHeight");
  Object.defineProperty(HTMLElement.prototype, "clientWidth", { configurable: true, value: 1000 });
  Object.defineProperty(HTMLElement.prototype, "clientHeight", { configurable: true, value: 700 });
}

function restoreContainerSize(): void {
  if (originalClientWidth) Object.defineProperty(HTMLElement.prototype, "clientWidth", originalClientWidth);
  if (originalClientHeight) Object.defineProperty(HTMLElement.prototype, "clientHeight", originalClientHeight);
}

async function mountApp(target: HTMLElement): Promise<ReturnType<typeof mount>> {
  window.location.hash = "#/plan";
  const app = mount(App, { target });
  // authStore resolves, then homesStore.loadHomes() fetches and sets
  // activeHomeId, then the $effect watching activeHomeId fires .reload() on
  // every module store — and *this* test also stubs a real /house response,
  // so floorStore.reload() does a second real fetch beyond what
  // CommandPalette.integration.test.ts's 6-tick budget accounted for.
  // Verified empirically: 7 ticks is the minimum that reaches a stable DOM
  // here; 10 leaves margin.
  for (let i = 0; i < 10; i++) await tick();
  flushSync();
  return app;
}

describe("App — viewport auto-fit", () => {
  let target: HTMLElement;
  let app: ReturnType<typeof mount> | undefined;

  afterEach(() => {
    if (app) {
      unmount(app);
      app = undefined;
    }
    target?.remove();
    restoreContainerSize();
    vi.unstubAllGlobals();
  });

  it("fits the viewport to the loaded floor's geometry instead of the hardcoded default", async () => {
    stubContainerSize();
    stubFetch();
    target = document.createElement("div");
    document.body.appendChild(target);
    app = await mountApp(target);

    // fitViewportToFloor(floor, 1000, 700): bounds (50,50)-(54,50), spanX=4,
    // spanY clamped to 0.1, padding=40 default.
    // availW=920, availH=620 -> zoom = min(920/4, 620/0.1) = min(230, 6200) = 230
    // cx=52, cy=50 -> panX = 500 - 52*230 = -11460; panY = 350 - 50*230 = -11150
    // screen(50,50) = (50*230-11460, 50*230-11150) = (40, 350)
    // screen(54,50) = (54*230-11460, 50*230-11150) = (960, 350)
    const line = target.querySelector("line.divider")!;
    expect(line.getAttribute("x1")).toBe("40");
    expect(line.getAttribute("y1")).toBe("350");
    expect(line.getAttribute("x2")).toBe("960");
    expect(line.getAttribute("y2")).toBe("350");
  });

  it("re-fits when switching to a different floor and back", async () => {
    stubContainerSize();
    stubFetch();
    target = document.createElement("div");
    document.body.appendChild(target);
    app = await mountApp(target);

    expect(target.querySelector("line.divider")).not.toBeNull();

    // Add a floor (switches to it automatically; it starts empty, so no
    // divider renders) via the compact FloorSwitcher, matching the pattern
    // in App.test.ts's "house-wide assignments" test.
    (target.querySelector(".compact-btn") as HTMLButtonElement).click();
    flushSync();
    (target.querySelector(".compact-floor-item.add") as HTMLButtonElement).click();
    flushSync();

    expect(target.querySelector("line.divider")).toBeNull();

    // Switch back to Ground Floor.
    (target.querySelector(".compact-btn") as HTMLButtonElement).click();
    flushSync();
    const groundFloorItem = Array.from(target.querySelectorAll(".compact-floor-item")).find(
      (b) => b.textContent?.trim() === "Ground Floor",
    ) as HTMLButtonElement;
    groundFloorItem.click();
    flushSync();

    // Re-fit produces the same numbers as the initial load, proving the
    // effect fires again on every switch, not just once.
    const line = target.querySelector("line.divider")!;
    expect(line.getAttribute("x1")).toBe("40");
    expect(line.getAttribute("y1")).toBe("350");
    expect(line.getAttribute("x2")).toBe("960");
    expect(line.getAttribute("y2")).toBe("350");
  });
});
```

- [x] **Step 3: Run the new tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/App.viewportAutoFit.test.ts`
Expected: FAIL — the divider renders at `x1="5400" y1="5300" x2="5800" y2="5300"` (screen = world*100 + (400,300), the untouched `DEFAULT_VIEWPORT`), not the fitted coordinates.

- [x] **Step 4: Add the auto-fit effect**

In `packages/editor/src/App.svelte`, after line 389 (`let canvasHeight = $state(800);`), insert:

```svelte
  $effect(() => {
    const _currentFloorId = floorStore.currentFloorId;
    const isLoaded = floorStore.loaded;
    if (!isLoaded) return;
    untrack(() => {
      // An empty floor (nothing drawn yet, or the transient placeholder
      // shown before a home's data has loaded) has nothing to fit to —
      // leave the viewport as-is rather than recentering to a meaningless
      // {width/2, height/2} point.
      if (canvasWidth > 0 && canvasHeight > 0 && floorStore.floor.walls.length > 0) {
        viewportStore.reset(floorStore.floor, canvasWidth, canvasHeight);
      }
    });
  });
```

**Discovered during implementation:** without the `floorStore.floor.walls.length > 0` guard, the effect also fires against the transient empty placeholder floor shown before any home's data has loaded (`getHomeId()` returns `null` → `houseStore.init()`'s early-return path sets `loaded = true` immediately with a zero-wall floor). That recentered the viewport to `{width/2, height/2, zoom: 100}` instead of leaving `DEFAULT_VIEWPORT` alone, which broke one pre-existing test (`App.test.ts`'s "wheel-zooms the viewport and Reset View restores it") that asserts exact hardcoded wall coordinates. Skipping the fit when there are no walls avoids the meaningless recenter and fixes it.

Also discovered: the `addFloor()` function in `houseStore.svelte.ts` was missing `furnitureObjects: []` on the new floor object (unlike `init()`'s 404 path, which explicitly backfills it). Reading `floorStore.currentFurniture` on a freshly-added floor lazily mutates it in via `ensureFurniture()`, which Svelte 5 forbids from inside a template-reactive read context (`state_unsafe_mutation`). This is a pre-existing latent bug, exposed by Task 1's second test (the first test to add a floor via the UI and immediately render it). Fixed alongside this task since it directly blocked the test and is a one-line, non-API-changing change:

```ts
    const newFloor: Floor = {
      id: genId(),
      name,
      order: maxOrder + 1,
      walls: [],
      openings: [],
      rooms: [],
      furnitureObjects: [],
    };
```

- [x] **Step 5: Run the tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/App.viewportAutoFit.test.ts`
Expected: PASS (2 tests)

- [x] **Step 6: Run the full editor test suite to check for regressions**

Run: `cd packages/editor && npx vitest run`
Expected: PASS — every other test either doesn't reach `#/plan` with a real container size (so the width/height guard blocks the new effect, per the "Why `untrack` is required" note above and the jsdom-always-reports-0-clientWidth behavior it depends on), or doesn't care what the initial viewport is.

If any pre-existing test fails because it *does* stub `clientWidth`/`clientHeight` (unlikely — grep found none before this task), fix that test's hardcoded screen-coordinate math to match its floor's fitted viewport rather than the old `DEFAULT_VIEWPORT`.

- [x] **Step 7: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/test/App.viewportAutoFit.test.ts
git commit -m "fix(floorplan): auto-fit viewport to floor content on load and floor switch"
```

---

### Task 2: Add the `"pan"` tool type

**Files:**
- Modify: `packages/editor/src/lib/toolStore.svelte.ts:3`
- Test: `packages/editor/test/toolStore.test.ts`

**Interfaces:**
- Produces: `ToolType` now includes `"pan"`. Task 3 and Task 4 depend on this.

- [x] **Step 1: Write the failing test**

Add to the `"toolStore — door/window tools"` describe block in `packages/editor/test/toolStore.test.ts` (after the existing `"setTool('window') is valid"` test, i.e. after line 86):

```ts
  it("setTool('pan') is valid", () => {
    const store = createToolStore();
    store.setTool("pan");
    expect(store.state.tool).toBe("pan");
  });
```

- [x] **Step 2: Run it to verify it fails**

Run: `cd packages/editor && npx vitest run test/toolStore.test.ts`
Expected: FAIL with a TypeScript error — `"pan"` is not assignable to `ToolType`.

- [x] **Step 3: Add `"pan"` to `ToolType`**

In `packages/editor/src/lib/toolStore.svelte.ts:3`, change:

```ts
export type ToolType = "select" | "wall" | "divider" | "garden" | "door" | "window";
```

to:

```ts
export type ToolType = "select" | "wall" | "divider" | "garden" | "door" | "window" | "pan";
```

- [x] **Step 4: Run the test to verify it passes**

Run: `cd packages/editor && npx vitest run test/toolStore.test.ts`
Expected: PASS (18 tests)

- [x] **Step 5: Commit**

```bash
git add packages/editor/src/lib/toolStore.svelte.ts packages/editor/test/toolStore.test.ts
git commit -m "feat(floorplan): add pan tool type"
```

---

### Task 3: Wire the Pan tool into Canvas.svelte's pointer handling and cursor

**Files:**
- Modify: `packages/editor/src/lib/components/Canvas.svelte` (`handlePointerDown` around line 165; `<svg>` class bindings around line 269-279; `<style>` block around line 380-386)
- Test: `packages/editor/test/Canvas.test.ts`

**Interfaces:**
- Consumes: `ToolType` (now including `"pan"`, from Task 2).
- Produces: nothing new consumed by later tasks — Task 4 only needs the `"pan"` tool value to exist (from Task 2) to wire up a button; it doesn't call into Canvas.svelte internals directly.

- [x] **Step 1: Write the failing test**

Add to `packages/editor/test/Canvas.test.ts`, after the `"middle-mouse drag reports pan deltas instead of pointer moves"` test (after line 280):

```ts
  it("left-button drag pans when tool is 'pan', and the canvas shows a grab cursor", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    const floor = createSampleFloor();
    let panDelta: { dx: number; dy: number } | null = null;
    let moveCount = 0;

    app = mount(Canvas, {
      target,
      props: {
        floor,
        viewport: { ...DEFAULT_VIEWPORT },
        width: 800,
        height: 600,
        tool: "pan",
        onpan: (dx: number, dy: number) => {
          panDelta = { dx, dy };
        },
        onpointermove: () => moveCount++,
      },
    });
    flushSync();

    const svg = target.querySelector("svg.canvas")!;
    expect(svg.classList.contains("pan-tool")).toBe(true);
    expect(svg.classList.contains("panning")).toBe(false);

    svg.dispatchEvent(
      new PointerEvent("pointerdown", { bubbles: true, pointerId: 1, button: 0, clientX: 100, clientY: 100 }),
    );
    flushSync();
    expect(svg.classList.contains("panning")).toBe(true);

    svg.dispatchEvent(
      new PointerEvent("pointermove", { bubbles: true, pointerId: 1, button: 0, clientX: 120, clientY: 90 }),
    );
    flushSync();

    expect(panDelta).toEqual({ dx: 20, dy: -10 });
    expect(moveCount).toBe(0);

    svg.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, pointerId: 1 }));
    flushSync();
    expect(svg.classList.contains("panning")).toBe(false);
  });
```

- [x] **Step 2: Run it to verify it fails**

Run: `cd packages/editor && npx vitest run test/Canvas.test.ts`
Expected: FAIL — `panDelta` stays `null` (a left-button drag with `tool: "pan"` currently falls through to the draw/select path since `handlePointerDown` only checks `spacePressed`, not `tool`), and `svg.classList.contains("pan-tool")` is `false` (no such class exists yet).

- [x] **Step 3: Wire `tool === "pan"` into the pan-drag path and add cursor classes**

In `packages/editor/src/lib/components/Canvas.svelte`, change `handlePointerDown` (around line 165):

```ts
    if (event.button === 1 || (event.button === 0 && spacePressed)) {
      event.preventDefault();
      panState = { x: event.clientX, y: event.clientY };
      suppressNextClick = true;
    }
```

to:

```ts
    if (event.button === 1 || (event.button === 0 && (spacePressed || tool === "pan"))) {
      event.preventDefault();
      panState = { x: event.clientX, y: event.clientY };
      suppressNextClick = true;
    }
```

Then change the `<svg>` opening tag (around line 269-279) from:

```svelte
<svg
  {width}
  {height}
  class="canvas"
  onclick={handleClick}
  onpointerdown={handlePointerDown}
  onpointermove={handlePointerMove}
  onpointerup={handlePointerUp}
  ondblclick={() => { if (!readOnly) ondblclick?.(); }}
  onwheel={handleWheel}
>
```

to:

```svelte
<svg
  {width}
  {height}
  class="canvas"
  class:pan-tool={tool === "pan"}
  class:panning={panState !== null}
  onclick={handleClick}
  onpointerdown={handlePointerDown}
  onpointermove={handlePointerMove}
  onpointerup={handlePointerUp}
  ondblclick={() => { if (!readOnly) ondblclick?.(); }}
  onwheel={handleWheel}
>
```

Then change the `<style>` block (around line 380-386) from:

```svelte
<style>
  .canvas {
    background: var(--canvas-bg);
    display: block;
    touch-action: none;
  }
</style>
```

to:

```svelte
<style>
  .canvas {
    background: var(--canvas-bg);
    display: block;
    touch-action: none;
  }

  .canvas.pan-tool {
    cursor: grab;
  }

  .canvas.panning {
    cursor: grabbing;
  }
</style>
```

- [x] **Step 4: Run the test to verify it passes**

Run: `cd packages/editor && npx vitest run test/Canvas.test.ts`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/Canvas.svelte packages/editor/test/Canvas.test.ts
git commit -m "feat(floorplan): pan tool drags the canvas with a grab cursor"
```

---

### Task 4: Add the Pan toolbar button, visible in both edit and view mode

**Files:**
- Modify: `packages/editor/src/App.svelte` (floating toolbar, lines 1295-1305)
- Modify: `packages/editor/src/lib/locales/en.json:223-233`, `packages/editor/src/lib/locales/fr.json:223-233`
- Test: `packages/editor/test/App.test.ts` (extend the test at line 101 and the test at line 143)

**Interfaces:**
- Consumes: `toolStore.setTool("pan")` (existing method, now accepts `"pan"` per Task 2); `toolStore.state.tool` for the `active` class.

- [x] **Step 1: Write the failing tests**

In `packages/editor/test/App.test.ts`, change the assertion at line 111 from:

```ts
    expect(titles).toEqual(["Switch to view mode (read-only)", "Toggle item picker", "Toggle furniture library", "Save", "Reset view", "Undo (Ctrl+Z)", "Redo (Ctrl+Y)", "Select", "Wall", "Divider", "Garden Border", "Door", "Window", "Delete selected (Del)"]);
```

to:

```ts
    expect(titles).toEqual(["Switch to view mode (read-only)", "Toggle item picker", "Toggle furniture library", "Save", "Reset view", "Undo (Ctrl+Z)", "Redo (Ctrl+Y)", "Pan", "Select", "Wall", "Divider", "Garden Border", "Door", "Window", "Delete selected (Del)"]);
```

Then, in the `"view mode hides editing tools..."` test (around line 143-179), add an assertion right after the existing "Editing tools are gone" loop (after line 161):

```ts
    // Pan is not an editing tool — it stays available in view mode.
    expect(toolbarBtn(target, "Pan")).not.toBeUndefined();
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/App.test.ts`
Expected: FAIL — no "Pan" button exists yet, so the title list doesn't match and `toolbarBtn(target, "Pan")` is `undefined`.

- [x] **Step 3: Add the i18n keys**

In `packages/editor/src/lib/locales/en.json`, inside the `"tools"` object (around line 223-233), add a `"pan"` key. Change:

```json
    "tools": {
      "undo": "Undo (Ctrl+Z)",
      "redo": "Redo (Ctrl+Y)",
      "select": "Select",
```

to:

```json
    "tools": {
      "undo": "Undo (Ctrl+Z)",
      "redo": "Redo (Ctrl+Y)",
      "pan": "Pan",
      "select": "Select",
```

In `packages/editor/src/lib/locales/fr.json`, same location, change:

```json
    "tools": {
      "undo": "Annuler (Ctrl+Z)",
      "redo": "Rétablir (Ctrl+Y)",
      "select": "Sélectionner",
```

to:

```json
    "tools": {
      "undo": "Annuler (Ctrl+Z)",
      "redo": "Rétablir (Ctrl+Y)",
      "pan": "Panoramique",
      "select": "Sélectionner",
```

- [x] **Step 4: Add the Pan button and adjust the toolbar's gating**

In `packages/editor/src/App.svelte`, the tool-group block (around lines 1295-1305) currently reads:

```svelte
              {#if !choreLayerActive && !allFloorsMode && !viewMode}
                <div class="ft-sep"></div>
                <button class="ft-btn" title={$_('floorPlan.tools.select')} class:active={toolStore.state.tool === "select"} onclick={() => toolStore.setTool("select")}>🖱 <span class="ft-label">{$_('floorPlan.tools.select')}</span></button>
                <button class="ft-btn" title={$_('floorPlan.tools.wall')} class:active={toolStore.state.tool === "wall"} onclick={() => toolStore.setTool("wall")}>🧱 <span class="ft-label">{$_('floorPlan.tools.wall')}</span></button>
                <button class="ft-btn" title={$_('floorPlan.tools.divider')} class:active={toolStore.state.tool === "divider"} onclick={() => toolStore.setTool("divider")}>╌ <span class="ft-label">{$_('floorPlan.tools.divider')}</span></button>
                <button class="ft-btn" title={$_('floorPlan.tools.garden')} class:active={toolStore.state.tool === "garden"} onclick={() => toolStore.setTool("garden")}>🌿 <span class="ft-label">{$_('floorPlan.tools.garden')}</span></button>
                <button class="ft-btn" title={$_('floorPlan.tools.door')} class:active={toolStore.state.tool === "door"} onclick={() => toolStore.setTool("door")}>🚪 <span class="ft-label">{$_('floorPlan.tools.door')}</span></button>
                <button class="ft-btn" title={$_('floorPlan.tools.window')} class:active={toolStore.state.tool === "window"} onclick={() => toolStore.setTool("window")}>🪟 <span class="ft-label">{$_('floorPlan.tools.window')}</span></button>
                <div class="ft-sep"></div>
                <button class="ft-btn delete" disabled={!hasSelection} onclick={handleDelete} title={$_('floorPlan.tools.delete')}>🗑 <span class="ft-label">{$_('app.floatingToolbar.delete')}</span></button>
              {/if}
```

Change it to:

```svelte
              {#if !choreLayerActive && !allFloorsMode}
                <div class="ft-sep"></div>
                <button class="ft-btn" title={$_('floorPlan.tools.pan')} class:active={toolStore.state.tool === "pan"} onclick={() => toolStore.setTool("pan")}>✋ <span class="ft-label">{$_('floorPlan.tools.pan')}</span></button>
                {#if !viewMode}
                  <button class="ft-btn" title={$_('floorPlan.tools.select')} class:active={toolStore.state.tool === "select"} onclick={() => toolStore.setTool("select")}>🖱 <span class="ft-label">{$_('floorPlan.tools.select')}</span></button>
                  <button class="ft-btn" title={$_('floorPlan.tools.wall')} class:active={toolStore.state.tool === "wall"} onclick={() => toolStore.setTool("wall")}>🧱 <span class="ft-label">{$_('floorPlan.tools.wall')}</span></button>
                  <button class="ft-btn" title={$_('floorPlan.tools.divider')} class:active={toolStore.state.tool === "divider"} onclick={() => toolStore.setTool("divider")}>╌ <span class="ft-label">{$_('floorPlan.tools.divider')}</span></button>
                  <button class="ft-btn" title={$_('floorPlan.tools.garden')} class:active={toolStore.state.tool === "garden"} onclick={() => toolStore.setTool("garden")}>🌿 <span class="ft-label">{$_('floorPlan.tools.garden')}</span></button>
                  <button class="ft-btn" title={$_('floorPlan.tools.door')} class:active={toolStore.state.tool === "door"} onclick={() => toolStore.setTool("door")}>🚪 <span class="ft-label">{$_('floorPlan.tools.door')}</span></button>
                  <button class="ft-btn" title={$_('floorPlan.tools.window')} class:active={toolStore.state.tool === "window"} onclick={() => toolStore.setTool("window")}>🪟 <span class="ft-label">{$_('floorPlan.tools.window')}</span></button>
                  <div class="ft-sep"></div>
                  <button class="ft-btn delete" disabled={!hasSelection} onclick={handleDelete} title={$_('floorPlan.tools.delete')}>🗑 <span class="ft-label">{$_('app.floatingToolbar.delete')}</span></button>
                {/if}
              {/if}
```

- [x] **Step 5: Run the tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/App.test.ts`
Expected: PASS

- [x] **Step 6: Run the full editor test suite to check for regressions**

Run: `cd packages/editor && npx vitest run`
Expected: PASS

- [x] **Step 7: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/App.test.ts
git commit -m "feat(floorplan): add Pan toolbar button, visible in edit and view mode"
```

---

### Task 5: Verify pinch-to-zoom / two-finger pan

**Files:**
- None expected to change. Verification only, per the spec's explicit "verify only, fix bugs if found" scope.

**Interfaces:**
- Consumes: nothing new.

- [x] **Step 1: Confirm existing automated coverage passes**

Run: `cd packages/editor && npx vitest run test/Canvas.test.ts -t "two active pointers"`
Expected: PASS. This is the test `"two active pointers report a pan delta and a zoom factor from their centroid/distance change"` (`packages/editor/test/Canvas.test.ts:493`) — it already drives two synthetic `PointerEvent`s through `Canvas.svelte`'s real `activePointers`/`gestureBase` gesture math and asserts the resulting pan delta and zoom factor, and a companion test (`test/Canvas.test.ts:534`) confirms it reverts to single-pointer mode once a second pointer lifts. Together these are the "automated" verification the spec calls for — no new test is needed.

If either test fails, that's a real regression: stop and debug it with superpowers:systematic-debugging before continuing — do not proceed to Step 2 with known-broken gesture math.

- [ ] **Step 2: Manual verification (does not block the PR, but do it before considering group A fully done)** — NOT DONE: no browser/touch device available in this environment. Left for a human pass before considering group A fully done.

In a real browser with touch input (a tablet/phone, or Chrome DevTools' device toolbar with touch simulation enabled), open the floor plan editor and:
1. Two-finger drag on the canvas — the view should pan smoothly, tracking the midpoint of the two touches.
2. Two-finger pinch in/out — the view should zoom smoothly, centered on the midpoint between the two touches.
3. Lift one finger while still touching with the other — panning/zooming should stop and single-finger drag should resume its normal tool behavior (e.g. drawing, if the Wall tool is active) rather than continuing to pan.

If any of these misbehave, the bug is scoped to `activePointers`/`gestureBase` in `packages/editor/src/lib/components/Canvas.svelte` (`handlePointerDown`/`handlePointerMove`/`rebaseGesture`, lines ~129-210) — fix it there with a regression test alongside the two existing gesture tests, following superpowers:test-driven-development, then repeat this manual check.

Record the manual verification outcome in the PR description (which device/browser was used, or if it could only be checked via DevTools touch emulation) — do not claim "verified on device" if only emulation was available.

---

## Self-Review Notes

- **Spec coverage:** Section 1 (auto-fit) → Task 1. Section 2 (pan tool) → Tasks 2-4. Section 3 (pinch verification) → Task 5. Testing section → covered across all four tasks' test steps.
- **Type consistency:** `ToolType` gains `"pan"` in Task 2; Task 3's `tool === "pan"` check and Task 4's `toolStore.setTool("pan")` call both use that exact literal.
- **Scope:** unchanged from the approved spec — no per-floor viewport memory, no zoom-bound changes, no double-tap gesture.
