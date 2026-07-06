# Wall Rendering Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two visual issues in the floor plan canvas — walls appear slightly thicker than their actual geometry because of a 1px SVG stroke, and at 90° corners the independent wall rectangles visually overlap instead of miter-joining cleanly.

**Architecture:** Add a `computeMiterCorners` pure-geometry helper to `@myhome/geometry`; add a `findAdjacentWall` helper to the editor's `geometry-helpers.ts`; update `WallShape.svelte` to pass miter corners and drop the stroke; update `Canvas.svelte` to pass adjacent-wall props; and apply the same miter logic to `svgRender.ts` so SVG exports are consistent.

**Tech Stack:** Svelte 5, TypeScript, Vitest

---

### Task 1: Add `computeMiterCorners` to the geometry package + tests

**Files:**
- Modify: `packages/geometry/src/geometry.ts`
- Modify: `packages/geometry/test/geometry.test.ts` (or create if absent — check with `ls packages/geometry/test/`)

#### Background

Two walls share endpoint `P`. Each wall has a unit direction vector `dir` (from its `.start` to its `.end`) and a perpendicular `perp = (-dir.y, dir.x) * halfThick`. The "flat cap" corners at `P` for wall A are `P ± perpA`. With a miter join, those corners are replaced by the intersections of the extended lateral edge lines of both walls.

- **plus** corner: intersection of line `(P + perpA, direction dirA)` and line `(P + perpB, direction dirB)`
- **minus** corner: intersection of line `(P - perpA, direction dirA)` and line `(P - perpB, direction dirB)`

The formula is the same whether `P` is the `.start` or `.end` of either wall.

- [ ] **Step 1: Check for existing geometry test file**

```bash
ls /projects/myhome/packages/geometry/test/
```

- [ ] **Step 2: Add `computeMiterCorners` to `packages/geometry/src/geometry.ts`**

Append to the end of the existing file:

```typescript
/**
 * Computes the two miter corner points where two walls share endpoint P.
 * dirA and dirB are unit vectors along each wall's centerline (start → end).
 * halfThickA / halfThickB are wall.thickness / 2 for each wall.
 *
 * Returns { plus, minus } — intersections of the +perp and -perp edge lines —
 * or null if walls are parallel, or if the miter would spike further than
 * 8 × max(halfThickA, halfThickB) from P (very acute angle fallback).
 */
export function computeMiterCorners(
  P: Point,
  dirA: Point,
  halfThickA: number,
  dirB: Point,
  halfThickB: number,
): { plus: Point; minus: Point } | null {
  const pAx = -dirA.y * halfThickA;
  const pAy = dirA.x * halfThickA;
  const pBx = -dirB.y * halfThickB;
  const pBy = dirB.x * halfThickB;

  const plus = _linesIntersect(
    { x: P.x + pAx, y: P.y + pAy }, dirA,
    { x: P.x + pBx, y: P.y + pBy }, dirB,
  );
  const minus = _linesIntersect(
    { x: P.x - pAx, y: P.y - pAy }, dirA,
    { x: P.x - pBx, y: P.y - pBy }, dirB,
  );
  if (!plus || !minus) return null;

  const limit = 8 * Math.max(halfThickA, halfThickB);
  if (Math.hypot(plus.x - P.x, plus.y - P.y) > limit) return null;

  return { plus, minus };
}

/** Intersection of two infinite lines (point + direction). Internal helper. */
function _linesIntersect(p1: Point, d1: Point, p2: Point, d2: Point): Point | null {
  const det = d1.x * (-d2.y) - d1.y * (-d2.x);
  if (Math.abs(det) < 1e-9) return null;
  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;
  const t = (dx * (-d2.y) - dy * (-d2.x)) / det;
  return { x: p1.x + t * d1.x, y: p1.y + t * d1.y };
}
```

- [ ] **Step 3: Write failing tests**

Add to `packages/geometry/test/geometry.test.ts` (create the file if it doesn't exist; use the existing test files in the same directory as a model for the import path):

```typescript
import { describe, it, expect } from "vitest";
import { computeMiterCorners } from "../src/geometry";

describe("computeMiterCorners", () => {
  const P = { x: 0, y: 0 };

  it("90° corner: wall going right meeting wall going up", () => {
    // dirA = (1,0) right, dirB = (0,-1) up (decreasing y), both thickness 0.2m
    const result = computeMiterCorners(P, { x: 1, y: 0 }, 0.1, { x: 0, y: -1 }, 0.1);
    expect(result).not.toBeNull();
    expect(result!.plus.x).toBeCloseTo(0.1);
    expect(result!.plus.y).toBeCloseTo(0.1);
    expect(result!.minus.x).toBeCloseTo(-0.1);
    expect(result!.minus.y).toBeCloseTo(-0.1);
  });

  it("90° corner: different thicknesses", () => {
    // wall A halfThick=0.1, wall B halfThick=0.15
    const result = computeMiterCorners(P, { x: 1, y: 0 }, 0.1, { x: 0, y: -1 }, 0.15);
    expect(result).not.toBeNull();
    // plus: A's top edge y=0.1 meets B's right edge x=0.15
    expect(result!.plus.x).toBeCloseTo(0.15);
    expect(result!.plus.y).toBeCloseTo(0.1);
    // minus: A's bottom edge y=-0.1 meets B's left edge x=-0.15
    expect(result!.minus.x).toBeCloseTo(-0.15);
    expect(result!.minus.y).toBeCloseTo(-0.1);
  });

  it("parallel walls return null", () => {
    // both going in same direction — no valid intersection
    const result = computeMiterCorners(P, { x: 1, y: 0 }, 0.1, { x: 1, y: 0 }, 0.1);
    expect(result).toBeNull();
  });

  it("anti-parallel walls (180°) return null (parallel laterals)", () => {
    const result = computeMiterCorners(P, { x: 1, y: 0 }, 0.1, { x: -1, y: 0 }, 0.1);
    expect(result).toBeNull();
  });

  it("45° corner", () => {
    const s = Math.SQRT2 / 2;
    const result = computeMiterCorners(P, { x: 1, y: 0 }, 0.1, { x: s, y: -s }, 0.1);
    expect(result).not.toBeNull();
    // miter point is farther from P than for 90° but within the spike limit
    expect(Math.hypot(result!.plus.x - P.x, result!.plus.y - P.y)).toBeGreaterThan(0.1);
  });

  it("very acute angle (near 0°) returns null due to spike limit", () => {
    // nearly collinear walls — miter would spike very far
    const eps = 0.01;
    const result = computeMiterCorners(
      P, { x: 1, y: 0 }, 0.1,
      { x: Math.cos(eps), y: -Math.sin(eps) }, 0.1,
    );
    // Either null (parallel check) or null (spike limit)
    expect(result).toBeNull();
  });
});
```

- [ ] **Step 4: Run tests to confirm they fail**

```bash
cd /projects/myhome/packages/geometry && npx vitest run
```

Expected: `computeMiterCorners is not a function` or `cannot find 'computeMiterCorners'`

- [ ] **Step 5: Run tests to confirm they pass after the implementation**

```bash
cd /projects/myhome/packages/geometry && npx vitest run
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
cd /projects/myhome
git add packages/geometry/src/geometry.ts packages/geometry/test/geometry.test.ts
git commit -m "feat: add computeMiterCorners geometry helper"
```

---

### Task 2: Add `findAdjacentWall` to editor geometry-helpers + tests

**Files:**
- Modify: `packages/editor/src/lib/geometry-helpers.ts`
- Modify: `packages/editor/test/geometry-helpers.test.ts`

This helper returns the single other `wall`-type wall that shares an endpoint with the target wall. If zero or more than one share the endpoint, it returns `null` (fall back to flat cap).

- [ ] **Step 1: Write the failing test**

Add to `packages/editor/test/geometry-helpers.test.ts`:

```typescript
import { findAdjacentWall } from "../src/lib/geometry-helpers";
// (add to existing imports)

function makeWall2(id: string, x0: number, y0: number, x1: number, y1: number): Wall {
  return { id, start: { x: x0, y: y0 }, end: { x: x1, y: y1 }, thickness: 0.2, type: "wall" };
}

describe("findAdjacentWall", () => {
  const wA = makeWall2("A", 0, 0, 4, 0);   // goes right, ends at (4,0)
  const wB = makeWall2("B", 4, 0, 4, 4);   // starts at (4,0), goes down
  const wC = makeWall2("C", 4, 0, 8, 0);   // also starts at (4,0) — creates ambiguity

  it("returns the single adjacent wall at the end", () => {
    expect(findAdjacentWall([wA, wB], wA, true)).toBe(wB);
  });

  it("returns the single adjacent wall at the start", () => {
    expect(findAdjacentWall([wA, wB], wB, false)).toBe(wA);
  });

  it("returns null when no wall shares the endpoint", () => {
    expect(findAdjacentWall([wA, wB], wA, false)).toBeNull(); // wA.start=(0,0), nobody there
  });

  it("returns null when more than one wall shares the endpoint (T/multi-junction)", () => {
    expect(findAdjacentWall([wA, wB, wC], wA, true)).toBeNull(); // both wB and wC share (4,0)
  });

  it("ignores dividers", () => {
    const divider: Wall = { id: "D", start: { x: 4, y: 0 }, end: { x: 4, y: 4 }, type: "divider" };
    expect(findAdjacentWall([wA, divider], wA, true)).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /projects/myhome/packages/editor && npx vitest run test/geometry-helpers.test.ts
```

Expected: FAIL — `findAdjacentWall is not a function`

- [ ] **Step 3: Add `findAdjacentWall` to `packages/editor/src/lib/geometry-helpers.ts`**

Add the import for `pointsEqual` at the top (it's already exported from `@myhome/geometry`):

```typescript
import type { Point, Wall } from "@myhome/geometry";
import { pointsEqual } from "@myhome/geometry";
```

Append the function at the end of the file:

```typescript
/**
 * Returns the single other wall-type wall that shares an endpoint with target.
 * Returns null if zero or more than one wall shares that endpoint
 * (T-junction / no connection → fall back to a flat cap).
 */
export function findAdjacentWall(walls: Wall[], target: Wall, atEnd: boolean): Wall | null {
  const P = atEnd ? target.end : target.start;
  let found: Wall | null = null;
  let count = 0;
  for (const w of walls) {
    if (w.id === target.id || w.type !== "wall") continue;
    if (pointsEqual(w.start, P) || pointsEqual(w.end, P)) {
      found = w;
      count++;
    }
  }
  return count === 1 ? found : null;
}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /projects/myhome/packages/editor && npx vitest run test/geometry-helpers.test.ts
```

Expected: all geometry-helpers tests pass.

- [ ] **Step 5: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/geometry-helpers.ts packages/editor/test/geometry-helpers.test.ts
git commit -m "feat: add findAdjacentWall helper"
```

---

### Task 3: Update `WallShape.svelte` — miter corners + remove stroke

**Files:**
- Modify: `packages/editor/src/lib/components/WallShape.svelte`

The `corners` derived value currently computes 4 flat-cap polygon points. This task replaces the start/end cap points with miter corners when adjacent wall props are provided, and removes the visual stroke bloat.

- [ ] **Step 1: Replace `WallShape.svelte` content**

Full replacement of `packages/editor/src/lib/components/WallShape.svelte`:

```svelte
<script lang="ts">
  import type { Wall, Point } from "@myhome/geometry";
  import { computeMiterCorners } from "@myhome/geometry";
  import { worldToScreen, type ViewportState } from "../viewportStore.svelte";
  import type { ToolType } from "../toolStore.svelte";

  let {
    wall,
    wallAtStart = null,
    wallAtEnd = null,
    viewport,
    tool = "select",
    selected = false,
    onselect,
  }: {
    wall: Wall;
    wallAtStart?: Wall | null;
    wallAtEnd?: Wall | null;
    viewport: ViewportState;
    tool?: ToolType;
    selected?: boolean;
    onselect?: (id: string) => void;
  } = $props();

  const thickness = $derived(wall.thickness ?? 0.1);

  const corners = $derived.by(() => {
    const dx = wall.end.x - wall.start.x;
    const dy = wall.end.y - wall.start.y;
    const len = Math.hypot(dx, dy);
    if (len < 1e-9) return [];
    const dirX = dx / len;
    const dirY = dy / len;
    const halfThick = thickness / 2;
    const dir = { x: dirX, y: dirY };
    const px = -dirY * halfThick;
    const py = dirX * halfThick;

    let startTop: Point = { x: wall.start.x + px, y: wall.start.y + py };
    let startBot: Point = { x: wall.start.x - px, y: wall.start.y - py };
    let endTop: Point   = { x: wall.end.x   + px, y: wall.end.y   + py };
    let endBot: Point   = { x: wall.end.x   - px, y: wall.end.y   - py };

    if (wallAtStart) {
      const ndx = wallAtStart.end.x - wallAtStart.start.x;
      const ndy = wallAtStart.end.y - wallAtStart.start.y;
      const nlen = Math.hypot(ndx, ndy);
      if (nlen > 1e-9) {
        const miter = computeMiterCorners(
          wall.start, dir, halfThick,
          { x: ndx / nlen, y: ndy / nlen }, (wallAtStart.thickness ?? 0.1) / 2,
        );
        if (miter) { startTop = miter.plus; startBot = miter.minus; }
      }
    }

    if (wallAtEnd) {
      const ndx = wallAtEnd.end.x - wallAtEnd.start.x;
      const ndy = wallAtEnd.end.y - wallAtEnd.start.y;
      const nlen = Math.hypot(ndx, ndy);
      if (nlen > 1e-9) {
        const miter = computeMiterCorners(
          wall.end, dir, halfThick,
          { x: ndx / nlen, y: ndy / nlen }, (wallAtEnd.thickness ?? 0.1) / 2,
        );
        if (miter) { endTop = miter.plus; endBot = miter.minus; }
      }
    }

    const worldCorners = [startTop, endTop, endBot, startBot];
    return worldCorners.map((p) => worldToScreen(p, viewport));
  });

  const points = $derived(corners.map((c) => `${c.x},${c.y}`).join(" "));

  function handleClick(event: MouseEvent): void {
    if (tool !== "select") return;
    event.stopPropagation();
    onselect?.(wall.id);
  }
</script>

{#if corners.length > 0}
  <polygon {points} class="wall" class:selected onclick={handleClick} role="button" tabindex="0" />
{/if}

<style>
  .wall {
    fill: var(--canvas-wall);
    stroke: none;
    cursor: pointer;
  }
  .wall.selected {
    fill: var(--canvas-wall-selected);
    stroke: none;
  }
</style>
```

- [ ] **Step 2: Run editor tests to verify nothing broke**

```bash
cd /projects/myhome/packages/editor && npx vitest run
```

Expected: all tests pass (WallShape doesn't receive `wallAtStart`/`wallAtEnd` in existing tests yet, so corners fall back to flat-cap — same behavior as before).

- [ ] **Step 3: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/components/WallShape.svelte
git commit -m "feat: miter corners and remove stroke from WallShape"
```

---

### Task 4: Update `Canvas.svelte` to pass adjacent-wall props

**Files:**
- Modify: `packages/editor/src/lib/components/Canvas.svelte`

`Canvas.svelte` already has access to `floor.walls`. For each wall, compute its start/end neighbor and pass them as `wallAtStart` and `wallAtEnd` props.

- [ ] **Step 1: Add `findAdjacentWall` import to `Canvas.svelte`**

At the top of the `<script>` block in `packages/editor/src/lib/components/Canvas.svelte`, the existing import line is:

```typescript
import { computeSnap, allEndpoints } from "../drawingTool";
import { SNAP_RADIUS_PX, hitTestWall, HIT_RADIUS_PX } from "../geometry-helpers";
```

Change to:

```typescript
import { computeSnap, allEndpoints } from "../drawingTool";
import { SNAP_RADIUS_PX, hitTestWall, HIT_RADIUS_PX, findAdjacentWall } from "../geometry-helpers";
```

- [ ] **Step 2: Update the `WallShape` render call in `Canvas.svelte`**

Find this block (around line 216–219):

```svelte
  {#each floor.walls as wall (wall.id)}
    {#if wall.type === "wall"}
      <WallShape {wall} {viewport} {tool} selected={wall.id === selectedId} onselect={(id) => onselect?.(id)} />
    {:else}
```

Replace with:

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
    {:else}
```

- [ ] **Step 3: Run editor tests**

```bash
cd /projects/myhome/packages/editor && npx vitest run
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/components/Canvas.svelte
git commit -m "feat: pass adjacent walls to WallShape for miter joins"
```

---

### Task 5: Apply miter joins to `svgRender.ts` + update tests

**Files:**
- Modify: `packages/geometry/src/svgRender.ts`
- Modify: `packages/geometry/test/svgRender.test.ts`

`renderFloorSvg` calls `renderWall(wall, openings)`. We need to pass neighbor walls so the first/last wall segment gets miter corners. Middle segments (between openings) keep flat caps.

- [ ] **Step 1: Update `renderFloorSvg` to compute and pass neighbors**

In `packages/geometry/src/svgRender.ts`, add this import at the top:

```typescript
import { computeMiterCorners, pointsEqual } from "./geometry";
```

Then replace the `wallsSvg` computation (lines 31–33) with:

```typescript
  const wallsOnly = floor.walls.filter((w) => w.type === "wall");

  const wallsSvg = wallsOnly
    .map((w) => {
      const atStart = _findAdjacentSvg(wallsOnly, w, false);
      const atEnd   = _findAdjacentSvg(wallsOnly, w, true);
      return renderWall(w, floor.openings.filter((o) => o.wallId === w.id), atStart, atEnd);
    })
    .join("\n");
```

- [ ] **Step 2: Add `_findAdjacentSvg` helper inside `svgRender.ts`**

Add just before the `renderWall` function (as a file-private helper):

```typescript
function _findAdjacentSvg(walls: Wall[], target: Wall, atEnd: boolean): Wall | null {
  const P = atEnd ? target.end : target.start;
  let found: Wall | null = null;
  let count = 0;
  for (const w of walls) {
    if (w.id === target.id) continue;
    if (pointsEqual(w.start, P) || pointsEqual(w.end, P)) { found = w; count++; }
  }
  return count === 1 ? found : null;
}
```

- [ ] **Step 3: Update `renderWall` signature and body**

Replace the existing `renderWall` function:

```typescript
function renderWall(wall: Wall, openings: Opening[], wallAtStart: Wall | null, wallAtEnd: Wall | null): string {
  const thickness = wall.thickness ?? 0.1;
  const { dirX, dirY, length } = wallDirection(wall);
  if (length < 1e-9) return "";

  const halfThick = thickness / 2;
  const perpX = -dirY * halfThick;
  const perpY = dirX * halfThick;
  const dir = { x: dirX, y: dirY };

  const gaps = openings
    .map((o) => {
      const from = clamp(o.offset, 0, length);
      const to = clamp(o.offset + o.width, from, length);
      return { from, to };
    })
    .sort((a, b) => a.from - b.from);

  const segments: { from: number; to: number }[] = [];
  let cursor = 0;
  for (const gap of gaps) {
    if (gap.from > cursor) segments.push({ from: cursor, to: gap.from });
    cursor = Math.max(cursor, gap.to);
  }
  if (cursor < length) segments.push({ from: cursor, to: length });

  const isFirst = (seg: { from: number }) => seg.from === 0;
  const isLast  = (seg: { to: number })   => seg.to === length;

  return segments
    .map((seg) => {
      const p1 = pointAlong(wall.start, dirX, dirY, seg.from);
      const p2 = pointAlong(wall.start, dirX, dirY, seg.to);

      let c0: Point = { x: p1.x + perpX, y: p1.y + perpY };
      let c1: Point = { x: p2.x + perpX, y: p2.y + perpY };
      let c2: Point = { x: p2.x - perpX, y: p2.y - perpY };
      let c3: Point = { x: p1.x - perpX, y: p1.y - perpY };

      if (isFirst(seg) && wallAtStart) {
        const ndx = wallAtStart.end.x - wallAtStart.start.x;
        const ndy = wallAtStart.end.y - wallAtStart.start.y;
        const nlen = Math.hypot(ndx, ndy);
        if (nlen > 1e-9) {
          const m = computeMiterCorners(wall.start, dir, halfThick, { x: ndx / nlen, y: ndy / nlen }, (wallAtStart.thickness ?? 0.1) / 2);
          if (m) { c0 = m.plus; c3 = m.minus; }
        }
      }

      if (isLast(seg) && wallAtEnd) {
        const ndx = wallAtEnd.end.x - wallAtEnd.start.x;
        const ndy = wallAtEnd.end.y - wallAtEnd.start.y;
        const nlen = Math.hypot(ndx, ndy);
        if (nlen > 1e-9) {
          const m = computeMiterCorners(wall.end, dir, halfThick, { x: ndx / nlen, y: ndy / nlen }, (wallAtEnd.thickness ?? 0.1) / 2);
          if (m) { c1 = m.plus; c2 = m.minus; }
        }
      }

      return `<path class="wall" d="${polygonToPath([c0, c1, c2, c3])}" />`;
    })
    .join("\n");
}
```

- [ ] **Step 4: Add a `Point` type import if not already present**

`svgRender.ts` already imports `Point` from `./types` — confirm this is at the top:

```typescript
import type { Floor, Wall, Opening, Room, Point, DoorSwing } from "./types";
```

If `Point` is not there, add it.

- [ ] **Step 5: Write a new test for adjacent-wall miter in `svgRender.test.ts`**

Add to `packages/geometry/test/svgRender.test.ts`:

```typescript
  it("two adjacent walls at a 90° corner produce miter-joined path coordinates", () => {
    // Wall A: horizontal (0,0)→(4,0); Wall B: vertical (4,0)→(4,4)
    const wallA: Wall = { id: "wA", start: { x: 0, y: 0 }, end: { x: 4, y: 0 }, thickness: 0.2, type: "wall" };
    const wallB: Wall = { id: "wB", start: { x: 4, y: 0 }, end: { x: 4, y: 4 }, thickness: 0.2, type: "wall" };
    const svg = renderFloorSvg(baseFloor({ walls: [wallA, wallB] }));

    const wallPaths = [...svg.matchAll(/<path class="wall" d="([^"]+)"/g)];
    expect(wallPaths).toHaveLength(2);

    // Wall A's end should be miter-joined with wall B.
    // Wall A ends at (4,0), Wall B starts at (4,0) going down (+y).
    // dirB = (0,1), perpB = (-0.1, 0).
    // Miter plus = intersection of y=0.1 line (A top) and x=4-0.1=3.9 line (B left side)
    //            = (3.9, 0.1)
    // Miter minus = intersection of y=-0.1 line and x=4.1 line = (4.1, -0.1)
    const dA = wallPaths.find(m => m[1].startsWith("M 0 0.1") || m[1].startsWith("M 0 -0.1"))![1];
    expect(dA).toContain("3.9 0.1");   // miter plus end corner of wall A
    expect(dA).toContain("4.1 -0.1");  // miter minus end corner of wall A
  });
```

- [ ] **Step 6: Run geometry tests**

```bash
cd /projects/myhome/packages/geometry && npx vitest run
```

Expected: the new test passes along with all existing tests (isolated-wall tests are unaffected because their neighbors are null).

- [ ] **Step 7: Commit**

```bash
cd /projects/myhome
git add packages/geometry/src/svgRender.ts packages/geometry/test/svgRender.test.ts
git commit -m "feat: miter joins in SVG floor plan export"
```

---

### Task 6: Final check + PR

- [ ] **Step 1: Run all tests in both packages**

```bash
cd /projects/myhome/packages/geometry && npx vitest run && cd ../editor && npx vitest run
```

Expected: all tests pass.

- [ ] **Step 2: Run typecheck**

```bash
cd /projects/myhome/packages/editor && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -5
cd /projects/myhome/packages/geometry && npx tsc --noEmit 2>&1 | tail -5
```

Expected: no errors.

- [ ] **Step 3: Create PR**

```bash
cd /projects/myhome
git checkout -b feat/wall-rendering-improvements
git push -u origin feat/wall-rendering-improvements
gh pr create \
  --title "feat: wall miter joins and stroke removal" \
  --body "$(cat <<'EOF'
## Summary
- Remove 1px SVG stroke from wall polygons — walls now render at their exact geometry width
- Add `computeMiterCorners` geometry helper that computes the lateral-edge intersection point for two walls sharing an endpoint
- Add `findAdjacentWall` editor helper that returns the single adjacent wall at a given endpoint (null for T-junctions and isolated ends)
- `WallShape.svelte` now receives `wallAtStart` / `wallAtEnd` props and uses miter corners instead of flat rectangular caps
- `svgRender.ts` applies the same miter logic so SVG exports are visually consistent

## Test plan
- [ ] All existing geometry and editor tests still pass
- [ ] New `computeMiterCorners` unit tests cover 90°, different thicknesses, parallel fallback, and acute-angle spike limit
- [ ] New `findAdjacentWall` tests cover single neighbor, no neighbor, multi-neighbor, and divider cases
- [ ] New `svgRender` test verifies miter path coordinates for a 90° two-wall corner
- [ ] Open the floor plan editor in a browser and draw an L-shaped room — corners should be clean right angles with no overlap artifact

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
