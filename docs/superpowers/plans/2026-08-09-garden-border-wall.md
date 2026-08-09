# Garden Border Wall Type Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a third `WallType`, `"garden"`, that renders as a dashed garden-boundary line (distinct from the existing `wall` and `divider` styles) and participates in room/area detection exactly like `divider` does today.

**Architecture:** `WallType` is a discriminated string union shared by three independent renderers that must all stay in sync: the Svelte canvas (`Canvas.svelte` + a new `GardenBorderShape.svelte`), the geometry package's exported SVG renderer (`packages/geometry/src/svgRender.ts`), and the backend's Pydantic-validated SVG renderer (`packages/backend/src/myhome/svg_render.py`). Room detection (`detectRooms`) is already type-agnostic and needs no code change — only a regression test to lock in the behavior. This plan touches all three renderers plus the tool-selection UI (toolbar button, `ToolType`, i18n).

**Tech Stack:** TypeScript (Svelte 5 runes, Vitest), Python (Pydantic, pytest).

## Global Constraints

- `WallType` must stay a plain string-literal union (`"wall" | "divider" | "garden"`) — every consumer switches on it directly, no enum wrapper.
- Backend `Wall.type` is a Pydantic `Literal` — adding `"garden"` there is required or saving a floor with a garden-border segment will 422.
- Match existing per-type styling pattern: `divider` gets its own dash pattern and CSS color variable; `garden` must do the same, not reuse `--canvas-divider`.
- No openings (doors/windows) on garden-border segments — this mirrors existing `divider` behavior and requires no new exclusion code (Canvas/geometry-helpers already gate opening logic on `type === "wall"`).
- i18n: every new user-facing string needs both an `en.json` and `fr.json` entry under `floorPlan.tools`.

---

### Task 1: `WallType` union + room-detection regression test

**Files:**
- Modify: `packages/geometry/src/types.ts:6`
- Modify: `packages/geometry/test/roomDetection.test.ts`

**Interfaces:**
- Produces: `WallType = "wall" | "divider" | "garden"` — every other task in this plan depends on this union including `"garden"`.

- [ ] **Step 1: Write the failing test**

Add to `packages/geometry/test/roomDetection.test.ts`, inside the existing `describe("detectRooms", ...)` block (it currently has a `wall()` helper at the top of the file with a `type: "wall" | "divider" = "wall"` parameter — widen that helper's parameter type too, since the new test needs to pass `"garden"` through it):

```ts
function wall(id: string, start: Point, end: Point, type: "wall" | "divider" | "garden" = "wall"): Wall {
  return { id, start, end, thickness: type === "wall" ? 0.15 : undefined, type };
}
```

```ts
it("closes an area from a garden-border loop, same as a divider", () => {
  const walls: Wall[] = [
    wall("g1", { x: 0, y: 0 }, { x: 6, y: 0 }, "garden"),
    wall("g2", { x: 6, y: 0 }, { x: 6, y: 4 }, "garden"),
    wall("g3", { x: 6, y: 4 }, { x: 0, y: 4 }, "garden"),
    wall("g4", { x: 0, y: 4 }, { x: 0, y: 0 }, "garden"),
  ];

  const rooms = detectRooms(walls);

  expect(rooms).toHaveLength(1);
  expect(rooms[0].areaM2).toBeCloseTo(24, 5);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/geometry && npx vitest run test/roomDetection.test.ts`
Expected: FAIL — TypeScript error, `"garden"` is not assignable to the `wall()` helper's type parameter (or to `Wall.type`), since `WallType` doesn't include it yet.

- [ ] **Step 3: Extend the type**

In `packages/geometry/src/types.ts`, change line 6:

```ts
export type WallType = "wall" | "divider" | "garden";
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/geometry && npx vitest run test/roomDetection.test.ts`
Expected: PASS — all tests in the file, including the new one.

- [ ] **Step 5: Commit**

```bash
git add packages/geometry/src/types.ts packages/geometry/test/roomDetection.test.ts
git commit -m "feat(geometry): add garden WallType"
```

---

### Task 2: Geometry package's exported SVG renderer

**Files:**
- Modify: `packages/geometry/src/svgRender.ts`
- Modify: `packages/geometry/test/svgRender.test.ts`

**Interfaces:**
- Consumes: `WallType` (Task 1).
- Produces: `renderFloorSvg()` emits `<path class="garden-border" ...>` elements for `type: "garden"` walls, inside a `<g class="garden-borders">` group — later consumers (none yet in-repo, but this is the package's public exported renderer) can rely on that class name.

- [ ] **Step 1: Write the failing test**

Add to `packages/geometry/test/svgRender.test.ts`, inside (or alongside) the existing `describe("renderFloorSvg - walls and dividers", ...)` block:

```ts
it("renders a garden-border wall as a dashed path, separately from dividers", () => {
  const gardenWall: Wall = {
    id: "gb1",
    start: { x: 0, y: 0 },
    end: { x: 5, y: 0 },
    type: "garden",
  };
  const svg = renderFloorSvg(baseFloor({ walls: [gardenWall] }));

  expect(svg).toContain('<g class="garden-borders">');
  const paths = [...svg.matchAll(/<path class="garden-border" d="([^"]+)"/g)];
  expect(paths).toHaveLength(1);
  expect(paths[0][1]).toBe("M 0 0 L 5 0");
  // Not picked up by the divider or wall groups.
  expect(svg.match(/<path class="divider"/g)).toBeNull();
  expect(svg.match(/<path class="wall"/g)).toBeNull();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/geometry && npx vitest run test/svgRender.test.ts`
Expected: FAIL — `svg` doesn't contain `garden-borders`/`garden-border` (garden walls are currently dropped entirely: they fail the `type === "wall"` and `type === "divider"` filters).

- [ ] **Step 3: Implement**

In `packages/geometry/src/svgRender.ts`, add a `renderGardenBorder` function next to `renderDivider` (around line 117-119):

```ts
function renderGardenBorder(wall: Wall): string {
  return `<path class="garden-border" d="${polylineToPath([wall.start, wall.end])}" stroke-dasharray="0.15 0.1" />`;
}
```

Add the filtered list and SVG group inside `renderFloorSvg`, right after the existing `dividersSvg` block (around line 42-45):

```ts
const gardenBordersSvg = floor.walls
  .filter((w) => w.type === "garden")
  .map(renderGardenBorder)
  .join("\n");
```

And add the group to the returned array (around line 63-65, right after the `dividers` group):

```ts
  `<g class="dividers">`,
  dividersSvg,
  `</g>`,
  `<g class="garden-borders">`,
  gardenBordersSvg,
  `</g>`,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/geometry && npx vitest run test/svgRender.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/geometry/src/svgRender.ts packages/geometry/test/svgRender.test.ts
git commit -m "feat(geometry): render garden-border walls in svgRender"
```

---

### Task 3: Backend model + SVG renderer

**Files:**
- Modify: `packages/backend/src/myhome/models.py:16`
- Modify: `packages/backend/src/myhome/svg_render.py`
- Modify: `packages/backend/tests/test_svg_render.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (separate language/package) — mirrors Task 2's TS implementation 1:1 for consistency.
- Produces: `Wall.type` accepts `"garden"`; `render_floor_svg()` emits `<path class="garden-border" ...>` inside `<g class="garden-borders">`.

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_svg_render.py`, after the existing `test_divider_renders_dashed` test:

```python
def test_garden_border_renders_dashed_separately_from_divider():
    floor = empty_floor()
    floor.walls.append(
        Wall(id="gb1", start=Point(x=0, y=0), end=Point(x=5, y=0), type="garden")
    )
    svg = render_floor_svg(floor)
    assert '<g class="garden-borders">' in svg
    assert 'class="garden-border"' in svg
    assert 'class="divider"' not in svg
    assert 'class="wall"' not in svg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_svg_render.py -v`
Expected: FAIL — first with a Pydantic validation error constructing `Wall(type="garden")` (`Literal["wall", "divider"]` rejects `"garden"`).

- [ ] **Step 3: Implement**

In `packages/backend/src/myhome/models.py`, change line 16:

```python
    type: Literal["wall", "divider", "garden"]
```

In `packages/backend/src/myhome/svg_render.py`, add a `_render_garden_border` function next to `_render_divider` (around line 77-79):

```python
def _render_garden_border(wall: Wall) -> str:
    d = _polyline_to_path([wall.start, wall.end])
    return f'<path class="garden-border" d="{d}" stroke-dasharray="0.15 0.1" />'
```

In `render_floor_svg`, add the filtered list right after `dividers` (around line 14):

```python
    garden_borders = [w for w in floor.walls if w.type == "garden"]
```

and its rendered group (around line 20):

```python
    garden_borders_svg = "\n".join(_render_garden_border(w) for w in garden_borders)
```

Add the group to the returned SVG (right after the `dividers` group, around line 40-42):

```python
        '<g class="dividers">',
        dividers_svg,
        "</g>",
        '<g class="garden-borders">',
        garden_borders_svg,
        "</g>",
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_svg_render.py -v`
Expected: PASS — all tests in the file.

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/models.py packages/backend/src/myhome/svg_render.py packages/backend/tests/test_svg_render.py
git commit -m "feat(backend): accept and render garden-border walls"
```

---

### Task 4: Editor tool type, theme colors, and `GardenBorderShape` component

**Files:**
- Modify: `packages/editor/src/lib/toolStore.svelte.ts:3`
- Modify: `packages/editor/src/lib/theme.css`
- Create: `packages/editor/src/lib/components/GardenBorderShape.svelte`

**Interfaces:**
- Consumes: `WallType` (Task 1), `ViewportState`/`worldToScreen` from `viewportStore.svelte.ts` (existing).
- Produces: `ToolType` includes `"garden"`; CSS vars `--canvas-garden-border` (light + dark); `GardenBorderShape` component with the same prop shape as `DividerShape` (`wall: Wall`, `viewport: ViewportState`, `tool?: ToolType`, `selected?: boolean`, `onselect?: (id: string) => void`), rendering a `<line class="garden-border">`.

- [ ] **Step 1: Extend `ToolType`**

In `packages/editor/src/lib/toolStore.svelte.ts`, change line 3:

```ts
export type ToolType = "select" | "wall" | "divider" | "garden" | "door" | "window";
```

- [ ] **Step 2: Add theme CSS variables**

In `packages/editor/src/lib/theme.css`, add a line right after `--canvas-divider: #5d7a96;` (line 65, light theme block):

```css
  --canvas-garden-border: #3f8f4f;
```

And right after `--canvas-divider: #99aadd;` (line 116, dark theme block):

```css
  --canvas-garden-border: #7fd08f;
```

- [ ] **Step 3: Create `GardenBorderShape.svelte`**

Model this directly on `DividerShape.svelte` (same prop shape, same screen-projection pattern), with its own CSS class and dash pattern:

```svelte
<script lang="ts">
  import type { Wall } from "@myhome/geometry";
  import { worldToScreen, type ViewportState } from "../viewportStore.svelte";
  import type { ToolType } from "../toolStore.svelte";

  let {
    wall,
    viewport,
    tool = "select",
    selected = false,
    onselect,
  }: {
    wall: Wall;
    viewport: ViewportState;
    tool?: ToolType;
    selected?: boolean;
    onselect?: (id: string) => void;
  } = $props();

  const startScreen = $derived(worldToScreen(wall.start, viewport));
  const endScreen = $derived(worldToScreen(wall.end, viewport));
  const x1 = $derived(startScreen.x);
  const y1 = $derived(startScreen.y);
  const x2 = $derived(endScreen.x);
  const y2 = $derived(endScreen.y);

  function handleClick(event: MouseEvent): void {
    if (tool !== "select") return;
    event.stopPropagation();
    onselect?.(wall.id);
  }
</script>

<line
  {x1}
  {y1}
  {x2}
  {y2}
  class="garden-border"
  class:selected
  onclick={handleClick}
  role="button"
  tabindex="0"
/>

<style>
  .garden-border {
    stroke: var(--canvas-garden-border);
    stroke-width: 2;
    stroke-dasharray: 3 3 8 3;
    cursor: pointer;
  }
  .garden-border.selected {
    stroke: var(--canvas-wall-selected);
    stroke-width: 3;
  }
</style>
```

- [ ] **Step 4: Verify it type-checks**

Run: `cd packages/editor && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | grep -i "GardenBorderShape\|toolStore"`
Expected: no output (no errors referencing the new file or the widened `ToolType`).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/toolStore.svelte.ts packages/editor/src/lib/theme.css packages/editor/src/lib/components/GardenBorderShape.svelte
git commit -m "feat(editor): add garden tool type, theme colors, and GardenBorderShape component"
```

---

### Task 5: Wire `GardenBorderShape` into `Canvas.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/Canvas.svelte`
- Modify: `packages/editor/test/Canvas.test.ts`

**Interfaces:**
- Consumes: `GardenBorderShape` (Task 4).
- Produces: Canvas renders `line.garden-border` for `wall.type === "garden"`; drawing (snap-to-grid/endpoint preview) works when `tool === "garden"`, matching `"wall"`/`"divider"` behavior.

- [ ] **Step 1: Write the failing test**

Add to `packages/editor/test/Canvas.test.ts`, as a new `it` inside the top-level `describe("Canvas", ...)` block (after the existing `"renders walls, dividers, and room polygons with area labels"` test):

```ts
it("renders a garden-border wall as a dashed line and supports drawing it", () => {
  target = document.createElement("div");
  document.body.appendChild(target);

  const floor = createSampleFloor();
  floor.walls.push({
    id: "garden-1",
    type: "garden",
    start: { x: 0, y: -1 },
    end: { x: 4, y: -1 },
  });

  app = mount(Canvas, {
    target,
    props: {
      floor,
      viewport: { ...DEFAULT_VIEWPORT },
      width: 800,
      height: 600,
      tool: "garden",
      drawPoints: [{ x: 0, y: 0 }],
      cursorWorld: { x: 2.02, y: 0.01 },
    },
  });
  flushSync();

  const svg = target.querySelector("svg.canvas")!;
  expect(svg.querySelectorAll("line.garden-border")).toHaveLength(1);
  // Same snap/draw-preview behavior as "wall"/"divider" while drawing.
  const preview = target.querySelector("g.draw-preview")!;
  expect(preview.querySelector("line.rubber-band")).not.toBeNull();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/Canvas.test.ts`
Expected: FAIL — `line.garden-border` is absent (garden walls fall into the `{:else}` branch, which currently renders `DividerShape`, producing `line.divider` instead) and/or `g.draw-preview` is absent (the `tool === "wall" || tool === "divider"` guard excludes `"garden"`).

- [ ] **Step 3: Implement**

In `packages/editor/src/lib/components/Canvas.svelte`, add the import near the other shape imports (after `import DividerShape from "./DividerShape.svelte";`, around line 12):

```ts
  import GardenBorderShape from "./GardenBorderShape.svelte";
```

Change the `snapResult` guard (line 92):

```ts
    if (tool !== "wall" && tool !== "divider" && tool !== "garden") return null;
```

Change the wall-rendering loop (lines 316-330) to a three-way branch:

```svelte
  {#each floor.walls as wall (wall.id)}
    {#if wall.type === "wall"}
      <WallShape
          {wall}
          wallAtStart={findAdjacentWall(floor.walls, wall, false)}
          wallAtEnd={findAdjacentWall(floor.walls, wall, true)}
          {viewport}
          {tool}
          selected={wall.id === selectedId}
          onselect={(id) => onselect?.(id)}
        />
    {:else if wall.type === "garden"}
      <GardenBorderShape {wall} {viewport} {tool} selected={wall.id === selectedId} onselect={(id) => onselect?.(id)} />
    {:else}
      <DividerShape {wall} {viewport} {tool} selected={wall.id === selectedId} onselect={(id) => onselect?.(id)} />
    {/if}
  {/each}
```

Change the `DrawPreview` condition (line 351):

```svelte
  {#if tool === "wall" || tool === "divider" || tool === "garden"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/Canvas.test.ts`
Expected: PASS — all tests in the file, including the new one.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/Canvas.svelte packages/editor/test/Canvas.test.ts
git commit -m "feat(editor): render and draw garden-border walls on the canvas"
```

---

### Task 6: Toolbar button, i18n, and App-level drawing test

**Files:**
- Modify: `packages/editor/src/App.svelte`
- Modify: `packages/editor/src/lib/locales/en.json`
- Modify: `packages/editor/src/lib/locales/fr.json`
- Modify: `packages/editor/test/App.test.ts`

**Interfaces:**
- Consumes: `toolStore.setTool("garden")` (existing `setTool`, now accepting the widened `ToolType`); `$_('floorPlan.tools.garden')` i18n key.
- Produces: a floating-toolbar button titled "Garden Border" between "Divider" and "Door"; `App.test.ts`'s fixed button-title assertions updated to include it.

- [ ] **Step 1: Add locale keys**

In `packages/editor/src/lib/locales/en.json`, add a line right after `"divider": "Divider",` (line 228):

```json
      "garden": "Garden Border",
```

In `packages/editor/src/lib/locales/fr.json`, add a line right after `"divider": "Séparation",` (line 228):

```json
      "garden": "Bordure de jardin",
```

- [ ] **Step 2: Write the failing test**

In `packages/editor/test/App.test.ts`, update the existing title-list assertion in `"renders the title and toolbar with the select tool active"` (line 111) to insert `"Garden Border"` between `"Divider"` and `"Door"`:

```ts
    expect(titles).toEqual(["Switch to view mode (read-only)", "Toggle item picker", "Toggle furniture library", "Save", "Reset view", "Undo (Ctrl+Z)", "Redo (Ctrl+Y)", "Select", "Wall", "Divider", "Garden Border", "Door", "Window", "Delete selected (Del)"]);
```

Update the view-mode title list in `"view mode hides editing tools..."` (line 159) to include it too:

```ts
    for (const title of ["Wall", "Divider", "Garden Border", "Door", "Window", "Delete selected (Del)", "Toggle item picker", "Toggle furniture library", "Save"]) {
```

Add a new test after `"drawing a wall chain places points, commits segments, and closes the loop"` (after line 225):

```ts
  it("drawing a garden-border chain places dashed segments of type garden", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = await mountAndLoad(target);

    toolbarBtn(target, "Garden Border").click();
    flushSync();

    const svg = target.querySelector("svg.canvas")!;
    const corners = [
      { x: 10, y: 10 },
      { x: 12, y: 10 },
    ];

    for (const corner of corners) {
      const screen = { x: corner.x * 100 + 400, y: corner.y * 100 + 300 };
      svg.dispatchEvent(
        new PointerEvent("pointermove", { bubbles: true, pointerId: 1, clientX: screen.x, clientY: screen.y }),
      );
      flushSync();
      svg.dispatchEvent(
        new MouseEvent("click", { bubbles: true, clientX: screen.x, clientY: screen.y }),
      );
      flushSync();
    }

    expect(target.querySelectorAll("line.garden-border").length).toBe(1);
  });
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/App.test.ts`
Expected: FAIL — the fixed-title tests fail (no "Garden Border" button exists yet, so the actual titles array is missing it and `toolbarBtn(target, "Garden Border")` returns `undefined` in the new test, whose `.click()` then throws).

- [ ] **Step 4: Implement**

In `packages/editor/src/App.svelte`, add a new floating-toolbar button right after the divider button (after line 1299):

```svelte
                <button class="ft-btn" title={$_('floorPlan.tools.garden')} class:active={toolStore.state.tool === "garden"} onclick={() => toolStore.setTool("garden")}>🌿 <span class="ft-label">{$_('floorPlan.tools.garden')}</span></button>
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/App.test.ts`
Expected: PASS — all tests in the file.

- [ ] **Step 6: Run the full editor and geometry test suites**

Run: `cd packages/editor && npx vitest run && cd ../geometry && npx vitest run`
Expected: PASS — no regressions elsewhere (e.g. any other test enumerating floating-toolbar buttons or `WallType`/`ToolType` exhaustively).

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/App.test.ts
git commit -m "feat(editor): add garden-border toolbar button and i18n"
```

---

## Final verification

- [ ] Run the full test suites for all three touched packages:
  - `cd packages/geometry && npx vitest run`
  - `cd packages/editor && npx vitest run`
  - `cd packages/backend && python -m pytest`
- [ ] Manually smoke-test in the browser (via the `run` skill or `npm run dev` in `packages/editor`): select the new "Garden Border" tool, draw a closed loop around an area outside the existing walls, confirm it renders as a dashed green-ish line distinct from the blue divider dashes, and that a room/area is detected for the enclosed loop.
