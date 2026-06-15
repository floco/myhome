# Floor Plan Geometry Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone, fully-tested TypeScript library that turns a floor's walls/dividers/openings into (a) detected room polygons, (b) room-identity-preserving matches across edits, and (c) an SVG rendering — the shared foundation Plan 2 (backend add-on) and Plan 3 (frontend editor) will both depend on.

**Architecture:** A single npm workspace package, `packages/geometry`, with zero UI or backend dependencies. Five small modules:
- `types.ts` — the House/Floor/Wall/Opening/Room types from the approved data model
- `geometry.ts` — point/segment/polygon math (intersection, area, centroid, point-in-polygon)
- `planarGraph.ts` — builds a planar graph from wall+divider segments, splitting them at every intersection
- `roomDetection.ts` — traces minimal-cycle faces from the planar graph to find room polygons
- `roomMatching.ts` — matches newly-detected polygons against previously-saved rooms to preserve `id`/`label`/`haAreaId`
- `svgRender.ts` — renders a floor (walls, dividers, openings, rooms) to an SVG string

Everything is pure functions over plain data (no classes, no global state), which makes each module independently unit-testable.

**Tech Stack:** TypeScript (strict mode), Vitest, npm workspaces (the repo root becomes a workspace root so Plan 3's frontend can later add `@myhome/geometry` as a dependency).

All algorithms in this plan have been prototyped and verified against the spec's required test cases (rectangle, wall-split, divider-split, L-shape, courtyard/hole, unclosed chains, disconnected groups, T- and X-intersections, room re-matching, and SVG rendering including door-swing arcs) — 58 tests passing. The code below is that verified implementation.

---

## File Structure

- `package.json` (repo root, new) — npm workspace root
- `packages/geometry/package.json` (new)
- `packages/geometry/tsconfig.json` (new)
- `packages/geometry/vitest.config.ts` (new)
- `packages/geometry/src/types.ts` (new) — shared data model types
- `packages/geometry/src/geometry.ts` (new) — point/segment/polygon math helpers
- `packages/geometry/src/planarGraph.ts` (new) — planar graph construction
- `packages/geometry/src/roomDetection.ts` (new) — face-finding room detection
- `packages/geometry/src/roomMatching.ts` (new) — room identity matching across edits
- `packages/geometry/src/svgRender.ts` (new) — SVG templating for a floor
- `packages/geometry/src/index.ts` (new) — public exports
- `packages/geometry/test/*.test.ts` (new) — one Vitest file per module

---

### Task 1: Workspace scaffolding and shared types

**Files:**
- Create: `package.json`
- Create: `packages/geometry/package.json`
- Create: `packages/geometry/tsconfig.json`
- Create: `packages/geometry/vitest.config.ts`
- Create: `packages/geometry/src/types.ts`
- Test: `packages/geometry/test/types.test.ts`

- [ ] **Step 1: Create the npm workspace root**

Create `package.json`:

```json
{
  "name": "myhome",
  "private": true,
  "workspaces": [
    "packages/*"
  ]
}
```

- [ ] **Step 2: Create the geometry package manifest, tsconfig, and Vitest config**

Create `packages/geometry/package.json`:

```json
{
  "name": "@myhome/geometry",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "scripts": {
    "test": "vitest run",
    "typecheck": "tsc --noEmit"
  },
  "devDependencies": {
    "typescript": "^6.0.3",
    "vitest": "^4.1.9"
  }
}
```

Create `packages/geometry/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "skipLibCheck": true
  },
  "include": ["src", "test"]
}
```

Create `packages/geometry/vitest.config.ts`:

```typescript
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
  },
});
```

- [ ] **Step 3: Write the shared data model types**

Create `packages/geometry/src/types.ts`:

```typescript
export interface Point {
  x: number;
  y: number;
}

export type WallType = "wall" | "divider";

export interface Wall {
  id: string;
  start: Point;
  end: Point;
  /** Meters. Only meaningful for type "wall"; dividers have no thickness. */
  thickness?: number;
  type: WallType;
}

export type OpeningType = "door" | "window";

/**
 * Which corner of the opening the door hinges on, and which side of the
 * wall it swings into. "left"/"right" refer to the corner closer to the
 * wall's `start` vs `end` point; "in"/"out" refer to the two sides of the
 * wall, split by the wall's direction vector (start -> end).
 */
export type DoorSwing = "left-in" | "right-in" | "left-out" | "right-out";

export interface Opening {
  id: string;
  wallId: string;
  type: OpeningType;
  /** Distance in meters along the wall from `wall.start`, clamped to the wall's length. */
  offset: number;
  /** Meters. */
  width: number;
  /** Only meaningful for type "door". */
  swing?: DoorSwing;
}

export interface Room {
  id: string;
  label: string;
  haAreaId: string | null;
  /** Cached centerline-based polygon, or null if the room is "unresolved" (see roomMatching). */
  polygon: Point[] | null;
  areaM2: number;
}

export interface Floor {
  id: string;
  name: string;
  order: number;
  walls: Wall[];
  openings: Opening[];
  rooms: Room[];
}

export interface House {
  name: string;
  units: "m";
  gridSnap: number;
}

export interface HouseDocument {
  version: number;
  house: House;
  floors: Floor[];
}
```

- [ ] **Step 4: Write a smoke test that exercises the types**

Create `packages/geometry/test/types.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import type { HouseDocument } from "../src/types";

describe("HouseDocument shape", () => {
  it("accepts a minimal valid document", () => {
    const doc: HouseDocument = {
      version: 1,
      house: { name: "My House", units: "m", gridSnap: 0.1 },
      floors: [
        {
          id: "floor-ground",
          name: "Ground Floor",
          order: 0,
          walls: [],
          openings: [],
          rooms: [],
        },
      ],
    };

    expect(doc.version).toBe(1);
    expect(doc.floors[0].name).toBe("Ground Floor");
  });
});
```

- [ ] **Step 5: Install dependencies and run the smoke test**

Run: `cd packages/geometry && npm install`

Run: `npx vitest run`

Expected: `Test Files  1 passed (1)`, `Tests  1 passed (1)`

- [ ] **Step 6: Commit**

```bash
git add package.json packages/geometry/package.json packages/geometry/package-lock.json \
  packages/geometry/tsconfig.json packages/geometry/vitest.config.ts \
  packages/geometry/src/types.ts packages/geometry/test/types.test.ts
git commit -m "feat(geometry): scaffold workspace and shared data model types"
```

---

### Task 2: Point and segment geometry helpers

**Files:**
- Create: `packages/geometry/src/geometry.ts`
- Test: `packages/geometry/test/geometry.test.ts`

- [ ] **Step 1: Write failing tests for segment intersection and point-on-segment**

Create `packages/geometry/test/geometry.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { segmentsIntersection, pointOnSegmentInterior } from "../src/geometry";

describe("segmentsIntersection", () => {
  it("finds the crossing point of two segments that cross in their interiors", () => {
    const p = segmentsIntersection(
      { x: 0, y: 0 },
      { x: 4, y: 4 },
      { x: 0, y: 4 },
      { x: 4, y: 0 }
    );
    expect(p).not.toBeNull();
    expect(p!.x).toBeCloseTo(2, 5);
    expect(p!.y).toBeCloseTo(2, 5);
  });

  it("returns null for parallel segments", () => {
    const p = segmentsIntersection(
      { x: 0, y: 0 },
      { x: 4, y: 0 },
      { x: 0, y: 1 },
      { x: 4, y: 1 }
    );
    expect(p).toBeNull();
  });

  it("returns null when segments only touch at an endpoint", () => {
    const p = segmentsIntersection(
      { x: 0, y: 0 },
      { x: 4, y: 0 },
      { x: 4, y: 0 },
      { x: 4, y: 4 }
    );
    expect(p).toBeNull();
  });

  it("returns null when segments don't cross within their bounds", () => {
    const p = segmentsIntersection(
      { x: 0, y: 0 },
      { x: 1, y: 1 },
      { x: 5, y: 5 },
      { x: 5, y: -5 }
    );
    expect(p).toBeNull();
  });
});

describe("pointOnSegmentInterior", () => {
  it("returns true for a point strictly between the endpoints", () => {
    expect(pointOnSegmentInterior({ x: 2, y: 0 }, { x: 0, y: 0 }, { x: 4, y: 0 })).toBe(true);
  });

  it("returns false for a point at an endpoint", () => {
    expect(pointOnSegmentInterior({ x: 0, y: 0 }, { x: 0, y: 0 }, { x: 4, y: 0 })).toBe(false);
    expect(pointOnSegmentInterior({ x: 4, y: 0 }, { x: 0, y: 0 }, { x: 4, y: 0 })).toBe(false);
  });

  it("returns false for a point not collinear with the segment", () => {
    expect(pointOnSegmentInterior({ x: 2, y: 1 }, { x: 0, y: 0 }, { x: 4, y: 0 })).toBe(false);
  });

  it("returns false for a point collinear but outside the segment's range", () => {
    expect(pointOnSegmentInterior({ x: 6, y: 0 }, { x: 0, y: 0 }, { x: 4, y: 0 })).toBe(false);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run geometry.test.ts`

Expected: FAIL — `Failed to resolve import "../src/geometry"` (module doesn't exist yet)

- [ ] **Step 3: Implement the segment helpers**

Create `packages/geometry/src/geometry.ts`:

```typescript
import type { Point } from "./types";

export const EPSILON = 1e-6;

export function pointsEqual(a: Point, b: Point, epsilon = EPSILON): boolean {
  return Math.abs(a.x - b.x) < epsilon && Math.abs(a.y - b.y) < epsilon;
}

/**
 * Returns the intersection point of segments (p1,p2) and (p3,p4) if they
 * cross at a point strictly interior to BOTH segments, else null.
 * Endpoint-touching and collinear-overlap cases are deliberately excluded
 * here; those are handled by pointOnSegmentInterior.
 */
export function segmentsIntersection(
  p1: Point,
  p2: Point,
  p3: Point,
  p4: Point
): Point | null {
  const d1x = p2.x - p1.x;
  const d1y = p2.y - p1.y;
  const d2x = p4.x - p3.x;
  const d2y = p4.y - p3.y;
  const denom = d1x * d2y - d1y * d2x;
  if (Math.abs(denom) < EPSILON) return null;

  const t = ((p3.x - p1.x) * d2y - (p3.y - p1.y) * d2x) / denom;
  const u = ((p3.x - p1.x) * d1y - (p3.y - p1.y) * d1x) / denom;
  const eps = 1e-9;
  if (t > eps && t < 1 - eps && u > eps && u < 1 - eps) {
    return { x: p1.x + t * d1x, y: p1.y + t * d1y };
  }
  return null;
}

/**
 * Returns true if point p lies strictly in the interior of segment [a,b]
 * (collinear with, and strictly between, the endpoints).
 */
export function pointOnSegmentInterior(p: Point, a: Point, b: Point): boolean {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const lenSq = dx * dx + dy * dy;
  if (lenSq < EPSILON) return false;

  const cross = dx * (p.y - a.y) - dy * (p.x - a.x);
  if (Math.abs(cross) > EPSILON * Math.sqrt(lenSq)) return false;

  const t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / lenSq;
  const eps = 1e-9;
  return t > eps && t < 1 - eps;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run geometry.test.ts`

Expected: `Tests  8 passed (8)`

- [ ] **Step 5: Commit**

```bash
git add packages/geometry/src/geometry.ts packages/geometry/test/geometry.test.ts
git commit -m "feat(geometry): add segment intersection and point-on-segment helpers"
```

---

### Task 3: Polygon geometry helpers

**Files:**
- Modify: `packages/geometry/src/geometry.ts`
- Modify: `packages/geometry/test/geometry.test.ts`

- [ ] **Step 1: Write failing tests for polygon area, centroid, and point-in-polygon**

Append to `packages/geometry/test/geometry.test.ts`:

```typescript
import {
  polygonSignedArea,
  polygonArea,
  polygonCentroid,
  pointInPolygon,
} from "../src/geometry";

describe("polygonSignedArea / polygonArea", () => {
  it("returns a positive signed area for a counter-clockwise square", () => {
    const square = [
      { x: 0, y: 0 },
      { x: 1, y: 0 },
      { x: 1, y: 1 },
      { x: 0, y: 1 },
    ];
    expect(polygonSignedArea(square)).toBeCloseTo(1, 5);
    expect(polygonArea(square)).toBeCloseTo(1, 5);
  });

  it("returns a negative signed area for the same square traversed clockwise", () => {
    const square = [
      { x: 0, y: 0 },
      { x: 0, y: 1 },
      { x: 1, y: 1 },
      { x: 1, y: 0 },
    ];
    expect(polygonSignedArea(square)).toBeCloseTo(-1, 5);
    expect(polygonArea(square)).toBeCloseTo(1, 5);
  });
});

describe("polygonCentroid", () => {
  it("computes the centroid of a rectangle", () => {
    const rect = [
      { x: 0, y: 0 },
      { x: 4, y: 0 },
      { x: 4, y: 2 },
      { x: 0, y: 2 },
    ];
    const c = polygonCentroid(rect);
    expect(c.x).toBeCloseTo(2, 5);
    expect(c.y).toBeCloseTo(1, 5);
  });

  it("computes the centroid of an L-shape (not the bounding-box center)", () => {
    // L-shape: 4x4 square minus a 2x2 notch from the top-right corner
    const lShape = [
      { x: 0, y: 0 },
      { x: 4, y: 0 },
      { x: 4, y: 2 },
      { x: 2, y: 2 },
      { x: 2, y: 4 },
      { x: 0, y: 4 },
    ];
    const c = polygonCentroid(lShape);
    // The bounding-box center would be (2,2), but the L-shape's mass is
    // skewed toward the bottom-left.
    expect(c.x).toBeLessThan(2);
    expect(c.y).toBeLessThan(2);
    expect(pointInPolygon(c, lShape)).toBe(true);
  });
});

describe("pointInPolygon", () => {
  const square = [
    { x: 0, y: 0 },
    { x: 4, y: 0 },
    { x: 4, y: 4 },
    { x: 0, y: 4 },
  ];

  it("returns true for a point inside the polygon", () => {
    expect(pointInPolygon({ x: 2, y: 2 }, square)).toBe(true);
  });

  it("returns false for a point outside the polygon", () => {
    expect(pointInPolygon({ x: 5, y: 5 }, square)).toBe(false);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run geometry.test.ts`

Expected: FAIL — `polygonSignedArea is not a function` (or similar: not exported yet)

- [ ] **Step 3: Implement the polygon helpers**

Append to `packages/geometry/src/geometry.ts`:

```typescript
/** Signed area via the shoelace formula. Positive = counter-clockwise winding. */
export function polygonSignedArea(points: Point[]): number {
  let sum = 0;
  const n = points.length;
  for (let i = 0; i < n; i++) {
    const a = points[i];
    const b = points[(i + 1) % n];
    sum += a.x * b.y - b.x * a.y;
  }
  return sum / 2;
}

export function polygonArea(points: Point[]): number {
  return Math.abs(polygonSignedArea(points));
}

/** Area-weighted centroid of a simple polygon. */
export function polygonCentroid(points: Point[]): Point {
  let cx = 0;
  let cy = 0;
  let area = 0;
  const n = points.length;
  for (let i = 0; i < n; i++) {
    const a = points[i];
    const b = points[(i + 1) % n];
    const cross = a.x * b.y - b.x * a.y;
    area += cross;
    cx += (a.x + b.x) * cross;
    cy += (a.y + b.y) * cross;
  }
  area = area / 2;
  if (Math.abs(area) < 1e-12) {
    const avgX = points.reduce((s, p) => s + p.x, 0) / n;
    const avgY = points.reduce((s, p) => s + p.y, 0) / n;
    return { x: avgX, y: avgY };
  }
  cx /= 6 * area;
  cy /= 6 * area;
  return { x: cx, y: cy };
}

/** Ray-casting point-in-polygon test. */
export function pointInPolygon(point: Point, polygon: Point[]): boolean {
  let inside = false;
  const n = polygon.length;
  for (let i = 0, j = n - 1; i < n; j = i++) {
    const xi = polygon[i].x;
    const yi = polygon[i].y;
    const xj = polygon[j].x;
    const yj = polygon[j].y;
    if (
      yi > point.y !== yj > point.y &&
      point.x < ((xj - xi) * (point.y - yi)) / (yj - yi) + xi
    ) {
      inside = !inside;
    }
  }
  return inside;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run geometry.test.ts`

Expected: `Tests  14 passed (14)`

- [ ] **Step 5: Commit**

```bash
git add packages/geometry/src/geometry.ts packages/geometry/test/geometry.test.ts
git commit -m "feat(geometry): add polygon area, centroid, and point-in-polygon helpers"
```

---

### Task 4: Planar graph construction

**Files:**
- Create: `packages/geometry/src/planarGraph.ts`
- Test: `packages/geometry/test/planarGraph.test.ts`

- [ ] **Step 1: Write failing tests for planar graph construction**

Create `packages/geometry/test/planarGraph.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { buildPlanarGraph } from "../src/planarGraph";

describe("buildPlanarGraph", () => {
  it("builds 4 nodes with degree 2 for a simple rectangle", () => {
    const segments = [
      { start: { x: 0, y: 0 }, end: { x: 4, y: 0 } },
      { start: { x: 4, y: 0 }, end: { x: 4, y: 2 } },
      { start: { x: 4, y: 2 }, end: { x: 0, y: 2 } },
      { start: { x: 0, y: 2 }, end: { x: 0, y: 0 } },
    ];
    const graph = buildPlanarGraph(segments);

    expect(graph.nodes).toHaveLength(4);
    for (const adj of graph.adjacency) {
      expect(adj).toHaveLength(2);
    }
  });

  it("splits a segment at a T-intersection from another segment's endpoint", () => {
    const segments = [
      { start: { x: 0, y: 0 }, end: { x: 4, y: 0 } }, // long bottom wall
      { start: { x: 2, y: 0 }, end: { x: 2, y: 2 } }, // divider touching its midpoint
    ];
    const graph = buildPlanarGraph(segments);

    // nodes: (0,0), (4,0), (2,0) [split point], (2,2) = 4 nodes
    expect(graph.nodes).toHaveLength(4);

    const splitIdx = graph.nodes.findIndex((p) => p.x === 2 && p.y === 0);
    expect(splitIdx).toBeGreaterThanOrEqual(0);
    // the split node connects to 3 others: (0,0), (4,0), (2,2)
    expect(graph.adjacency[splitIdx]).toHaveLength(3);
  });

  it("splits both segments at a proper X crossing", () => {
    const segments = [
      { start: { x: 0, y: 2 }, end: { x: 4, y: 2 } },
      { start: { x: 2, y: 0 }, end: { x: 2, y: 4 } },
    ];
    const graph = buildPlanarGraph(segments);

    // 4 original endpoints + 1 crossing point = 5 nodes
    expect(graph.nodes).toHaveLength(5);

    const crossIdx = graph.nodes.findIndex((p) => p.x === 2 && p.y === 2);
    expect(crossIdx).toBeGreaterThanOrEqual(0);
    expect(graph.adjacency[crossIdx]).toHaveLength(4);
  });

  it("sorts each node's adjacency by angle ascending", () => {
    // A '+' shape centered at the origin: 4 segments from center to N/E/S/W
    const segments = [
      { start: { x: 0, y: 0 }, end: { x: 1, y: 0 } }, // East, angle 0
      { start: { x: 0, y: 0 }, end: { x: 0, y: 1 } }, // North, angle pi/2
      { start: { x: 0, y: 0 }, end: { x: -1, y: 0 } }, // West, angle pi
      { start: { x: 0, y: 0 }, end: { x: 0, y: -1 } }, // South, angle -pi/2
    ];
    const graph = buildPlanarGraph(segments);

    const centerIdx = graph.nodes.findIndex((p) => p.x === 0 && p.y === 0);
    const neighborAngles = graph.adjacency[centerIdx].map((i) => {
      const p = graph.nodes[i];
      return Math.atan2(p.y, p.x);
    });
    const sorted = [...neighborAngles].sort((a, b) => a - b);
    expect(neighborAngles).toEqual(sorted);
  });

  it("deduplicates coincident endpoints into a single node", () => {
    const segments = [
      { start: { x: 0, y: 0 }, end: { x: 2, y: 0 } },
      { start: { x: 2, y: 0 }, end: { x: 2, y: 2 } },
    ];
    const graph = buildPlanarGraph(segments);

    // (0,0), (2,0), (2,2) - the shared (2,0) endpoint is one node, not two
    expect(graph.nodes).toHaveLength(3);
    const sharedIdx = graph.nodes.findIndex((p) => p.x === 2 && p.y === 0);
    expect(graph.adjacency[sharedIdx]).toHaveLength(2);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run planarGraph.test.ts`

Expected: FAIL — `Failed to resolve import "../src/planarGraph"` (module doesn't exist yet)

- [ ] **Step 3: Implement the planar graph builder**

Create `packages/geometry/src/planarGraph.ts`:

```typescript
import type { Point } from "./types";
import { pointsEqual, segmentsIntersection, pointOnSegmentInterior } from "./geometry";

export interface InputSegment {
  start: Point;
  end: Point;
}

export interface PlanarGraph {
  nodes: Point[];
  /** adjacency[i] = neighbor node indices, sorted by angle ascending (atan2) */
  adjacency: number[][];
}

function pointKey(p: Point): string {
  return `${p.x.toFixed(6)},${p.y.toFixed(6)}`;
}

function splitSegment(seg: InputSegment, splitPoints: Point[]): InputSegment[] {
  const dx = seg.end.x - seg.start.x;
  const dy = seg.end.y - seg.start.y;
  const lenSq = dx * dx + dy * dy;

  const unique: { p: Point; t: number }[] = [];
  for (const p of splitPoints) {
    if (unique.some((u) => pointsEqual(u.p, p))) continue;
    const t = ((p.x - seg.start.x) * dx + (p.y - seg.start.y) * dy) / lenSq;
    unique.push({ p, t });
  }
  unique.sort((a, b) => a.t - b.t);

  const chain: Point[] = [seg.start, ...unique.map((u) => u.p), seg.end];
  const result: InputSegment[] = [];
  for (let i = 0; i < chain.length - 1; i++) {
    if (!pointsEqual(chain[i], chain[i + 1])) {
      result.push({ start: chain[i], end: chain[i + 1] });
    }
  }
  return result;
}

/**
 * Builds a planar graph from a set of line segments: segments are split at
 * every point where they cross or touch another segment, then deduplicated
 * into a node/adjacency representation.
 */
export function buildPlanarGraph(segments: InputSegment[]): PlanarGraph {
  const splitPoints: Point[][] = segments.map(() => []);

  for (let i = 0; i < segments.length; i++) {
    for (let j = i + 1; j < segments.length; j++) {
      const a = segments[i];
      const b = segments[j];

      const cross = segmentsIntersection(a.start, a.end, b.start, b.end);
      if (cross) {
        splitPoints[i].push(cross);
        splitPoints[j].push(cross);
      }

      for (const p of [a.start, a.end]) {
        if (pointOnSegmentInterior(p, b.start, b.end)) splitPoints[j].push(p);
      }
      for (const p of [b.start, b.end]) {
        if (pointOnSegmentInterior(p, a.start, a.end)) splitPoints[i].push(p);
      }
    }
  }

  const subSegments: InputSegment[] = [];
  for (let i = 0; i < segments.length; i++) {
    subSegments.push(...splitSegment(segments[i], splitPoints[i]));
  }

  const nodes: Point[] = [];
  const nodeIndex = new Map<string, number>();
  function getNodeIndex(p: Point): number {
    const key = pointKey(p);
    let idx = nodeIndex.get(key);
    if (idx === undefined) {
      idx = nodes.length;
      nodes.push(p);
      nodeIndex.set(key, idx);
    }
    return idx;
  }

  const edgeSet = new Set<string>();
  const edges: [number, number][] = [];
  for (const seg of subSegments) {
    const ai = getNodeIndex(seg.start);
    const bi = getNodeIndex(seg.end);
    if (ai === bi) continue;
    const key = ai < bi ? `${ai}-${bi}` : `${bi}-${ai}`;
    if (edgeSet.has(key)) continue;
    edgeSet.add(key);
    edges.push([ai, bi]);
  }

  const adjacency: number[][] = nodes.map(() => []);
  for (const [a, b] of edges) {
    adjacency[a].push(b);
    adjacency[b].push(a);
  }
  for (let i = 0; i < nodes.length; i++) {
    adjacency[i].sort((p, q) => {
      const angleP = Math.atan2(nodes[p].y - nodes[i].y, nodes[p].x - nodes[i].x);
      const angleQ = Math.atan2(nodes[q].y - nodes[i].y, nodes[q].x - nodes[i].x);
      return angleP - angleQ;
    });
  }

  return { nodes, adjacency };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run planarGraph.test.ts`

Expected: `Tests  5 passed (5)`

- [ ] **Step 5: Commit**

```bash
git add packages/geometry/src/planarGraph.ts packages/geometry/test/planarGraph.test.ts
git commit -m "feat(geometry): build planar graph from segments split at intersections"
```

---

### Task 5: Room detection (face-finding algorithm)

This is the highest-risk piece of Spec 1: detecting enclosed room polygons from
the planar graph by tracing minimal-cycle "faces". The algorithm:

1. For each directed half-edge `(u, v)` not yet visited, trace a face by
   repeatedly jumping to the neighbor that comes immediately **before** the
   "came-from" node in `v`'s angle-sorted adjacency list (circularly). This
   is the standard "next edge in a planar subdivision" rule.
2. Each undirected edge contributes two directed half-edges, so this
   traversal partitions ALL half-edges into face cycles.
3. Compute each face's signed area (shoelace formula). **Bounded interior
   faces come out with positive signed area; the unbounded exterior face(s)
   come out negative** — this is a property of the traversal rule, verified
   below across 9 scenarios including holes, disconnected groups, and
   T/X intersections.
4. Keep only positive-area faces (above a small epsilon) as candidate rooms.

**Files:**
- Create: `packages/geometry/src/roomDetection.ts`
- Test: `packages/geometry/test/roomDetection.test.ts`

- [ ] **Step 1: Write failing tests covering all required room-detection scenarios**

Create `packages/geometry/test/roomDetection.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { detectRooms } from "../src/roomDetection";
import type { Wall, Point } from "../src/types";
import { polygonArea } from "../src/geometry";

function wall(id: string, start: Point, end: Point, type: "wall" | "divider" = "wall"): Wall {
  return { id, start, end, thickness: type === "wall" ? 0.15 : undefined, type };
}

describe("detectRooms", () => {
  it("detects a single room from a simple rectangle", () => {
    const walls: Wall[] = [
      wall("w1", { x: 0, y: 0 }, { x: 5, y: 0 }),
      wall("w2", { x: 5, y: 0 }, { x: 5, y: 4 }),
      wall("w3", { x: 5, y: 4 }, { x: 0, y: 4 }),
      wall("w4", { x: 0, y: 4 }, { x: 0, y: 0 }),
    ];

    const rooms = detectRooms(walls);

    expect(rooms).toHaveLength(1);
    expect(rooms[0].areaM2).toBeCloseTo(20, 5);
    expect(polygonArea(rooms[0].polygon)).toBeCloseTo(20, 5);
  });

  it("splits two rooms divided by a physical wall", () => {
    // 4x2 outer rectangle split down the middle by a vertical wall at x=2
    const walls: Wall[] = [
      wall("bottom-left", { x: 0, y: 0 }, { x: 2, y: 0 }),
      wall("bottom-right", { x: 2, y: 0 }, { x: 4, y: 0 }),
      wall("right", { x: 4, y: 0 }, { x: 4, y: 2 }),
      wall("top-right", { x: 4, y: 2 }, { x: 2, y: 2 }),
      wall("top-left", { x: 2, y: 2 }, { x: 0, y: 2 }),
      wall("left", { x: 0, y: 2 }, { x: 0, y: 0 }),
      wall("divider-wall", { x: 2, y: 0 }, { x: 2, y: 2 }),
    ];

    const rooms = detectRooms(walls);

    expect(rooms).toHaveLength(2);
    const areas = rooms.map((r) => r.areaM2).sort();
    expect(areas).toEqual([4, 4]);
  });

  it("splits two rooms divided by a virtual divider (same geometry as a wall)", () => {
    const walls: Wall[] = [
      wall("bottom-left", { x: 0, y: 0 }, { x: 2, y: 0 }),
      wall("bottom-right", { x: 2, y: 0 }, { x: 4, y: 0 }),
      wall("right", { x: 4, y: 0 }, { x: 4, y: 2 }),
      wall("top-right", { x: 4, y: 2 }, { x: 2, y: 2 }),
      wall("top-left", { x: 2, y: 2 }, { x: 0, y: 2 }),
      wall("left", { x: 0, y: 2 }, { x: 0, y: 0 }),
      wall("divider", { x: 2, y: 0 }, { x: 2, y: 2 }, "divider"),
    ];

    const rooms = detectRooms(walls);

    expect(rooms).toHaveLength(2);
    const areas = rooms.map((r) => r.areaM2).sort();
    expect(areas).toEqual([4, 4]);
  });

  it("detects an L-shaped room", () => {
    // L-shape: 4x4 square with a 2x2 notch cut from the top-right corner
    const walls: Wall[] = [
      wall("w1", { x: 0, y: 0 }, { x: 4, y: 0 }),
      wall("w2", { x: 4, y: 0 }, { x: 4, y: 2 }),
      wall("w3", { x: 4, y: 2 }, { x: 2, y: 2 }),
      wall("w4", { x: 2, y: 2 }, { x: 2, y: 4 }),
      wall("w5", { x: 2, y: 4 }, { x: 0, y: 4 }),
      wall("w6", { x: 0, y: 4 }, { x: 0, y: 0 }),
    ];

    const rooms = detectRooms(walls);

    expect(rooms).toHaveLength(1);
    // Full 4x4 (16) minus the 2x2 notch (4) = 12
    expect(rooms[0].areaM2).toBeCloseTo(12, 5);
    expect(rooms[0].polygon).toHaveLength(6);
  });

  it("detects a room with a hole (courtyard) as a separate inner face", () => {
    const outer: Wall[] = [
      wall("o1", { x: 0, y: 0 }, { x: 10, y: 0 }),
      wall("o2", { x: 10, y: 0 }, { x: 10, y: 10 }),
      wall("o3", { x: 10, y: 10 }, { x: 0, y: 10 }),
      wall("o4", { x: 0, y: 10 }, { x: 0, y: 0 }),
    ];
    // Inner courtyard, fully disconnected from the outer loop
    const inner: Wall[] = [
      wall("i1", { x: 4, y: 4 }, { x: 6, y: 4 }),
      wall("i2", { x: 6, y: 4 }, { x: 6, y: 6 }),
      wall("i3", { x: 6, y: 6 }, { x: 4, y: 6 }),
      wall("i4", { x: 4, y: 6 }, { x: 4, y: 4 }),
    ];

    const rooms = detectRooms([...outer, ...inner]);

    expect(rooms).toHaveLength(2);
    const areas = rooms.map((r) => r.areaM2).sort((a, b) => a - b);
    // Courtyard interior (2x2=4) and the outer interior (10x10=100, not
    // subtracting the hole - see spec's centerline simplification)
    expect(areas).toEqual([4, 100]);
  });

  it("produces no room for an unclosed chain of walls", () => {
    const walls: Wall[] = [
      wall("w1", { x: 0, y: 0 }, { x: 5, y: 0 }),
      wall("w2", { x: 5, y: 0 }, { x: 5, y: 4 }),
      wall("w3", { x: 5, y: 4 }, { x: 0, y: 4 }),
      // missing the 4th side - chain does not close
    ];

    const rooms = detectRooms(walls);

    expect(rooms).toHaveLength(0);
  });

  it("detects rooms independently in disconnected wall groups", () => {
    const groupA: Wall[] = [
      wall("a1", { x: 0, y: 0 }, { x: 2, y: 0 }),
      wall("a2", { x: 2, y: 0 }, { x: 2, y: 2 }),
      wall("a3", { x: 2, y: 2 }, { x: 0, y: 2 }),
      wall("a4", { x: 0, y: 2 }, { x: 0, y: 0 }),
    ];
    const groupB: Wall[] = [
      wall("b1", { x: 10, y: 10 }, { x: 13, y: 10 }),
      wall("b2", { x: 13, y: 10 }, { x: 13, y: 13 }),
      wall("b3", { x: 13, y: 13 }, { x: 10, y: 13 }),
      wall("b4", { x: 10, y: 13 }, { x: 10, y: 10 }),
    ];

    const rooms = detectRooms([...groupA, ...groupB]);

    expect(rooms).toHaveLength(2);
    const areas = rooms.map((r) => r.areaM2).sort((a, b) => a - b);
    expect(areas).toEqual([4, 9]);
  });

  it("splits a wall at a T-intersection from a perpendicular divider", () => {
    // Same as the "split by divider" case, but the divider's endpoint lands
    // exactly on the midpoint of the top and bottom walls (T-intersections),
    // rather than on pre-split sub-segments.
    const walls: Wall[] = [
      wall("bottom", { x: 0, y: 0 }, { x: 4, y: 0 }),
      wall("right", { x: 4, y: 0 }, { x: 4, y: 2 }),
      wall("top", { x: 4, y: 2 }, { x: 0, y: 2 }),
      wall("left", { x: 0, y: 2 }, { x: 0, y: 0 }),
      wall("divider", { x: 2, y: 0 }, { x: 2, y: 2 }, "divider"),
    ];

    const rooms = detectRooms(walls);

    expect(rooms).toHaveLength(2);
    const areas = rooms.map((r) => r.areaM2).sort();
    expect(areas).toEqual([4, 4]);
  });

  it("splits a wall at a proper crossing (X intersection)", () => {
    // Two dividers crossing in the middle of a 4x4 room, splitting it into 4 quadrants
    const walls: Wall[] = [
      wall("w1", { x: 0, y: 0 }, { x: 4, y: 0 }),
      wall("w2", { x: 4, y: 0 }, { x: 4, y: 4 }),
      wall("w3", { x: 4, y: 4 }, { x: 0, y: 4 }),
      wall("w4", { x: 0, y: 4 }, { x: 0, y: 0 }),
      wall("d1", { x: 2, y: 0 }, { x: 2, y: 4 }, "divider"),
      wall("d2", { x: 0, y: 2 }, { x: 4, y: 2 }, "divider"),
    ];

    const rooms = detectRooms(walls);

    expect(rooms).toHaveLength(4);
    const areas = rooms.map((r) => r.areaM2).sort();
    expect(areas).toEqual([4, 4, 4, 4]);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run roomDetection.test.ts`

Expected: FAIL — `Failed to resolve import "../src/roomDetection"` (module doesn't exist yet)

- [ ] **Step 3: Implement room detection**

Create `packages/geometry/src/roomDetection.ts`:

```typescript
import type { Point, Wall } from "./types";
import { buildPlanarGraph } from "./planarGraph";
import { polygonSignedArea } from "./geometry";

export interface DetectedRoom {
  polygon: Point[];
  areaM2: number;
}

const MIN_AREA_M2 = 1e-4; // 1 cm^2 - filters degenerate/zero-area faces

/**
 * Detects enclosed room faces from a floor's wall + divider centerlines.
 * Returns one polygon per interior face (positive signed area). The
 * unbounded exterior face(s) - which always have non-positive signed area
 * under this traversal - are discarded.
 */
export function detectRooms(walls: Wall[]): DetectedRoom[] {
  const segments = walls.map((w) => ({ start: w.start, end: w.end }));
  const graph = buildPlanarGraph(segments);
  return findInteriorFaces(graph.nodes, graph.adjacency);
}

function findInteriorFaces(nodes: Point[], adjacency: number[][]): DetectedRoom[] {
  const visited = new Set<string>();
  const faces: DetectedRoom[] = [];
  const totalHalfEdges = adjacency.reduce((sum, a) => sum + a.length, 0);

  for (let startU = 0; startU < nodes.length; startU++) {
    for (const startV of adjacency[startU]) {
      const startKey = `${startU}-${startV}`;
      if (visited.has(startKey)) continue;

      const faceNodeIndices: number[] = [];
      let u = startU;
      let v = startV;
      let steps = 0;

      do {
        visited.add(`${u}-${v}`);
        faceNodeIndices.push(u);

        const neighbors = adjacency[v];
        const k = neighbors.indexOf(u);
        const nextIdx = (k - 1 + neighbors.length) % neighbors.length;
        const w = neighbors[nextIdx];

        u = v;
        v = w;
        steps++;
        if (steps > totalHalfEdges + 1) {
          throw new Error("Face trace did not terminate - invalid planar graph");
        }
      } while (!(u === startU && v === startV));

      if (faceNodeIndices.length < 3) continue;

      const polygon = faceNodeIndices.map((i) => nodes[i]);
      const signedArea = polygonSignedArea(polygon);
      if (signedArea > MIN_AREA_M2) {
        faces.push({ polygon, areaM2: Math.round(signedArea * 100) / 100 });
      }
    }
  }

  return faces;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run roomDetection.test.ts`

Expected: `Tests  9 passed (9)`

- [ ] **Step 5: Commit**

```bash
git add packages/geometry/src/roomDetection.ts packages/geometry/test/roomDetection.test.ts
git commit -m "feat(geometry): detect room polygons via planar-graph face tracing"
```

---

### Task 6: Room identity matching across edits

Implements the spec's "Room identity across edits" rule: after re-detection,
match new polygons against existing rooms by centroid-containment. Matched
rooms keep their `id`/`label`/`haAreaId`; unmatched new polygons become new
rooms with a default label; rooms whose polygon disappears are kept with
`polygon: null` in an `unresolved` list.

**Files:**
- Create: `packages/geometry/src/roomMatching.ts`
- Test: `packages/geometry/test/roomMatching.test.ts`

- [ ] **Step 1: Write failing tests for room matching**

Create `packages/geometry/test/roomMatching.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { matchRooms } from "../src/roomMatching";
import type { DetectedRoom } from "../src/roomDetection";
import type { Room, Point } from "../src/types";

function rect(x0: number, y0: number, x1: number, y1: number): Point[] {
  return [
    { x: x0, y: y0 },
    { x: x1, y: y0 },
    { x: x1, y: y1 },
    { x: x0, y: y1 },
  ];
}

describe("matchRooms", () => {
  it("preserves label/haAreaId/id when a room's polygon changes slightly", () => {
    const existing: Room[] = [
      {
        id: "room-living",
        label: "Living Room",
        haAreaId: "living_room",
        polygon: rect(0, 0, 5, 4),
        areaM2: 20,
      },
    ];

    // Slightly enlarged (e.g. user nudged a wall outward)
    const detected: DetectedRoom[] = [{ polygon: rect(0, 0, 5.2, 4), areaM2: 20.8 }];

    const result = matchRooms(detected, existing);

    expect(result.rooms).toHaveLength(1);
    expect(result.rooms[0].id).toBe("room-living");
    expect(result.rooms[0].label).toBe("Living Room");
    expect(result.rooms[0].haAreaId).toBe("living_room");
    expect(result.rooms[0].areaM2).toBeCloseTo(20.8, 5);
    expect(result.unresolved).toHaveLength(0);
  });

  it("creates a new default-labeled room when a polygon has no match", () => {
    const existing: Room[] = [];
    const detected: DetectedRoom[] = [{ polygon: rect(0, 0, 3, 3), areaM2: 9 }];

    const result = matchRooms(detected, existing);

    expect(result.rooms).toHaveLength(1);
    expect(result.rooms[0].label).toBe("Room 1");
    expect(result.rooms[0].haAreaId).toBeNull();
    expect(result.rooms[0].id).toBeTruthy();
    expect(result.unresolved).toHaveLength(0);
  });

  it("when a room is split in two, one half keeps identity and the other becomes a new room", () => {
    const existing: Room[] = [
      {
        id: "room-open-plan",
        label: "Kitchen/Living",
        haAreaId: "downstairs",
        polygon: rect(0, 0, 4, 2),
        areaM2: 8,
      },
    ];

    // A divider at x=2 splits the room into two 2x2 halves
    const detected: DetectedRoom[] = [
      { polygon: rect(0, 0, 2, 2), areaM2: 4 },
      { polygon: rect(2, 0, 4, 2), areaM2: 4 },
    ];

    const result = matchRooms(detected, existing);

    expect(result.rooms).toHaveLength(2);
    const matched = result.rooms.find((r) => r.id === "room-open-plan");
    const created = result.rooms.find((r) => r.id !== "room-open-plan");

    expect(matched).toBeDefined();
    expect(matched!.label).toBe("Kitchen/Living");
    expect(matched!.haAreaId).toBe("downstairs");

    expect(created).toBeDefined();
    expect(created!.label).toBe("Room 1");
    expect(created!.haAreaId).toBeNull();

    expect(result.unresolved).toHaveLength(0);
  });

  it("marks a room as unresolved (polygon: null) when it disappears", () => {
    const existing: Room[] = [
      {
        id: "room-old",
        label: "Old Room",
        haAreaId: "office",
        polygon: rect(0, 0, 3, 3),
        areaM2: 9,
      },
    ];

    // No detected rooms at all (e.g. user deleted the walls)
    const detected: DetectedRoom[] = [];

    const result = matchRooms(detected, existing);

    expect(result.rooms).toHaveLength(1);
    expect(result.rooms[0].id).toBe("room-old");
    expect(result.rooms[0].polygon).toBeNull();
    expect(result.rooms[0].label).toBe("Old Room");
    expect(result.rooms[0].haAreaId).toBe("office");

    expect(result.unresolved).toHaveLength(1);
    expect(result.unresolved[0].id).toBe("room-old");
  });

  it("matches multiple rooms independently by centroid containment", () => {
    const existing: Room[] = [
      { id: "room-a", label: "A", haAreaId: "a", polygon: rect(0, 0, 2, 2), areaM2: 4 },
      { id: "room-b", label: "B", haAreaId: "b", polygon: rect(10, 10, 12, 12), areaM2: 4 },
    ];

    // Both rooms shift slightly, order reversed in the detected list
    const detected: DetectedRoom[] = [
      { polygon: rect(10.1, 10, 12.1, 12), areaM2: 4 },
      { polygon: rect(0.1, 0, 2.1, 2), areaM2: 4 },
    ];

    const result = matchRooms(detected, existing);

    expect(result.rooms).toHaveLength(2);
    const a = result.rooms.find((r) => r.id === "room-a");
    const b = result.rooms.find((r) => r.id === "room-b");
    expect(a!.label).toBe("A");
    expect(b!.label).toBe("B");
    expect(result.unresolved).toHaveLength(0);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run roomMatching.test.ts`

Expected: FAIL — `Failed to resolve import "../src/roomMatching"` (module doesn't exist yet)

- [ ] **Step 3: Implement room matching**

Create `packages/geometry/src/roomMatching.ts`:

```typescript
import type { Room } from "./types";
import { polygonArea, polygonCentroid, pointInPolygon } from "./geometry";
import type { DetectedRoom } from "./roomDetection";

export interface RoomMatchResult {
  /** All rooms after matching: previously-existing rooms that matched a
   *  detected polygon (keeping id/label/haAreaId, updated polygon+areaM2),
   *  newly-created rooms for unmatched detected polygons, and previously
   *  -existing rooms whose polygon disappeared (polygon: null). */
  rooms: Room[];
  /** Subset of `rooms` whose polygon disappeared in this pass. */
  unresolved: Room[];
}

/**
 * Matches newly-detected room polygons against the previous room list.
 *
 * A detected polygon matches an existing room if the detected polygon's
 * centroid falls inside that room's previous polygon. Matched rooms keep
 * their id/label/haAreaId. Unmatched detected polygons become new rooms
 * with a default label and no HA area. Existing rooms with no match keep
 * their id/label/haAreaId but get `polygon: null` and are reported in
 * `unresolved`.
 */
export function matchRooms(detected: DetectedRoom[], existing: Room[]): RoomMatchResult {
  const matchedExistingIds = new Set<string>();
  const rooms: Room[] = [];
  let newRoomCount = 0;

  for (const det of detected) {
    const centroid = polygonCentroid(det.polygon);
    const match = existing.find(
      (r) =>
        !matchedExistingIds.has(r.id) &&
        r.polygon !== null &&
        pointInPolygon(centroid, r.polygon)
    );

    if (match) {
      matchedExistingIds.add(match.id);
      rooms.push({
        ...match,
        polygon: det.polygon,
        areaM2: roundArea(det.polygon),
      });
    } else {
      newRoomCount++;
      rooms.push({
        id: crypto.randomUUID(),
        label: `Room ${newRoomCount}`,
        haAreaId: null,
        polygon: det.polygon,
        areaM2: roundArea(det.polygon),
      });
    }
  }

  const unresolved: Room[] = existing
    .filter((r) => !matchedExistingIds.has(r.id))
    .map((r) => ({ ...r, polygon: null }));

  return { rooms: [...rooms, ...unresolved], unresolved };
}

function roundArea(polygon: { x: number; y: number }[]): number {
  return Math.round(polygonArea(polygon) * 100) / 100;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run roomMatching.test.ts`

Expected: `Tests  5 passed (5)`

- [ ] **Step 5: Commit**

```bash
git add packages/geometry/src/roomMatching.ts packages/geometry/test/roomMatching.test.ts
git commit -m "feat(geometry): preserve room identity across edits via centroid matching"
```

---

### Task 7: SVG rendering — walls and dividers

Per the spec: walls render as `<path class="wall">` with thickness on both
sides of the centerline (split into multiple rectangle segments around any
openings); dividers render as a thin dashed `<path class="divider">`
centerline with no thickness.

**Files:**
- Create: `packages/geometry/src/svgRender.ts`
- Test: `packages/geometry/test/svgRender.test.ts`

- [ ] **Step 1: Write failing tests for wall and divider rendering**

Create `packages/geometry/test/svgRender.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { renderFloorSvg } from "../src/svgRender";
import type { Floor, Wall, Opening } from "../src/types";

function baseFloor(overrides: Partial<Floor> = {}): Floor {
  return {
    id: "floor-1",
    name: "Ground Floor",
    order: 0,
    walls: [],
    openings: [],
    rooms: [],
    ...overrides,
  };
}

describe("renderFloorSvg - walls and dividers", () => {
  it("renders a wall with no openings as a single rectangle path", () => {
    const wall: Wall = {
      id: "w1",
      start: { x: 0, y: 0 },
      end: { x: 4, y: 0 },
      thickness: 0.2,
      type: "wall",
    };
    const svg = renderFloorSvg(baseFloor({ walls: [wall] }));

    // One wall path, a rectangle (M + 3*L + Z = 4 points)
    const wallPaths = [...svg.matchAll(/<path class="wall" d="([^"]+)"/g)];
    expect(wallPaths).toHaveLength(1);
    const d = wallPaths[0][1];
    expect(d.startsWith("M 0 0.1")).toBe(true);
    expect(d).toContain("L 4 0.1");
    expect(d).toContain("L 4 -0.1");
    expect(d).toContain("L 0 -0.1");
    expect(d.endsWith("Z")).toBe(true);
  });

  it("splits a wall into two path segments around a window opening", () => {
    const wall: Wall = {
      id: "w1",
      start: { x: 0, y: 0 },
      end: { x: 4, y: 0 },
      thickness: 0.2,
      type: "wall",
    };
    const opening: Opening = {
      id: "op1",
      wallId: "w1",
      type: "window",
      offset: 1,
      width: 1,
    };
    const svg = renderFloorSvg(baseFloor({ walls: [wall], openings: [opening] }));

    const wallPaths = [...svg.matchAll(/<path class="wall" d="([^"]+)"/g)];
    expect(wallPaths).toHaveLength(2);

    const windowLines = [...svg.matchAll(/<line class="window"[^>]*\/>/g)];
    expect(windowLines).toHaveLength(1);
    expect(windowLines[0][0]).toContain('x1="1"');
    expect(windowLines[0][0]).toContain('x2="2"');
  });

  it("clamps an opening that would overflow the wall length", () => {
    const wall: Wall = {
      id: "w1",
      start: { x: 0, y: 0 },
      end: { x: 4, y: 0 },
      thickness: 0.2,
      type: "wall",
    };
    const opening: Opening = {
      id: "op1",
      wallId: "w1",
      type: "window",
      offset: 3.5,
      width: 1, // would extend to 4.5, beyond the wall's length of 4
    };
    const svg = renderFloorSvg(baseFloor({ walls: [wall], openings: [opening] }));

    const windowLines = [...svg.matchAll(/<line class="window"[^>]*\/>/g)];
    expect(windowLines[0][0]).toContain('x1="3.5"');
    expect(windowLines[0][0]).toContain('x2="4"');

    // Only one wall segment remains (before the opening); nothing after it
    const wallPaths = [...svg.matchAll(/<path class="wall" d="([^"]+)"/g)];
    expect(wallPaths).toHaveLength(1);
  });

  it("renders a divider as a dashed centerline with no thickness", () => {
    const divider: Wall = {
      id: "d1",
      start: { x: 0, y: 0 },
      end: { x: 4, y: 0 },
      type: "divider",
    };
    const svg = renderFloorSvg(baseFloor({ walls: [divider] }));

    expect(svg).toContain('<path class="divider"');
    expect(svg).toContain("stroke-dasharray");
    expect(svg).toContain("M 0 0 L 4 0");
    // dividers must not produce wall rectangles
    expect(svg).not.toContain('<path class="wall"');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run svgRender.test.ts`

Expected: FAIL — `Failed to resolve import "../src/svgRender"` (module doesn't exist yet)

- [ ] **Step 3: Implement the SVG renderer (walls, dividers, and shared helpers)**

Create `packages/geometry/src/svgRender.ts`:

```typescript
import type { Floor, Wall, Opening, Room, Point, DoorSwing } from "./types";

export interface SvgRenderOptions {
  /** Padding (in meters) added around the computed bounding box. Default 0.5. */
  padding?: number;
}

interface Bounds {
  minX: number;
  minY: number;
  width: number;
  height: number;
}

/**
 * Renders a floor (walls, dividers, openings, rooms) as an SVG document.
 * Coordinates are emitted 1:1 in meters; the viewBox is fit to the floor's
 * wall bounding box plus padding, so consumers can scale to pixels via
 * width/height or CSS.
 */
export function renderFloorSvg(floor: Floor, options: SvgRenderOptions = {}): string {
  const padding = options.padding ?? 0.5;
  const bounds = computeBounds(floor.walls, padding);

  const roomsSvg = floor.rooms
    .filter((r): r is Room & { polygon: Point[] } => r.polygon !== null)
    .map(renderRoom)
    .join("\n");

  const wallsSvg = floor.walls
    .filter((w) => w.type === "wall")
    .map((w) => renderWall(w, floor.openings.filter((o) => o.wallId === w.id)))
    .join("\n");

  const dividersSvg = floor.walls
    .filter((w) => w.type === "divider")
    .map(renderDivider)
    .join("\n");

  const openingsSvg = floor.walls
    .flatMap((w) =>
      w.type === "wall"
        ? floor.openings.filter((o) => o.wallId === w.id).map((o) => renderOpening(w, o))
        : []
    )
    .join("\n");

  return [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${fmt(bounds.minX)} ${fmt(bounds.minY)} ${fmt(bounds.width)} ${fmt(bounds.height)}">`,
    `<g class="rooms">`,
    roomsSvg,
    `</g>`,
    `<g class="walls">`,
    wallsSvg,
    `</g>`,
    `<g class="dividers">`,
    dividersSvg,
    `</g>`,
    `<g class="openings">`,
    openingsSvg,
    `</g>`,
    `</svg>`,
  ].join("\n");
}

function computeBounds(walls: Wall[], padding: number): Bounds {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const w of walls) {
    for (const p of [w.start, w.end]) {
      minX = Math.min(minX, p.x);
      minY = Math.min(minY, p.y);
      maxX = Math.max(maxX, p.x);
      maxY = Math.max(maxY, p.y);
    }
  }
  if (!isFinite(minX)) {
    minX = 0;
    minY = 0;
    maxX = 0;
    maxY = 0;
  }
  return {
    minX: minX - padding,
    minY: minY - padding,
    width: maxX - minX + padding * 2,
    height: maxY - minY + padding * 2,
  };
}

function renderRoom(room: Room & { polygon: Point[] }): string {
  const d = polygonToPath(room.polygon);
  const haArea = room.haAreaId ?? "";
  return `<path id="room-${escapeAttr(room.id)}" data-ha-area="${escapeAttr(haArea)}" class="room" d="${d}" />`;
}

function renderDivider(wall: Wall): string {
  return `<path class="divider" d="${polylineToPath([wall.start, wall.end])}" stroke-dasharray="0.1 0.1" />`;
}

function renderWall(wall: Wall, openings: Opening[]): string {
  const thickness = wall.thickness ?? 0.1;
  const { dirX, dirY, length } = wallDirection(wall);
  if (length < 1e-9) return "";

  const perpX = -dirY * (thickness / 2);
  const perpY = dirX * (thickness / 2);

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

  return segments
    .map((seg) => {
      const p1 = pointAlong(wall.start, dirX, dirY, seg.from);
      const p2 = pointAlong(wall.start, dirX, dirY, seg.to);
      const corners: Point[] = [
        { x: p1.x + perpX, y: p1.y + perpY },
        { x: p2.x + perpX, y: p2.y + perpY },
        { x: p2.x - perpX, y: p2.y - perpY },
        { x: p1.x - perpX, y: p1.y - perpY },
      ];
      return `<path class="wall" d="${polygonToPath(corners)}" />`;
    })
    .join("\n");
}

function renderOpening(wall: Wall, opening: Opening): string {
  const { dirX, dirY, length } = wallDirection(wall);
  const offset = clamp(opening.offset, 0, length);
  const width = clamp(opening.width, 0, length - offset);

  const p1 = pointAlong(wall.start, dirX, dirY, offset);
  const p2 = pointAlong(wall.start, dirX, dirY, offset + width);

  if (opening.type === "window") {
    return `<line class="window" x1="${fmt(p1.x)}" y1="${fmt(p1.y)}" x2="${fmt(p2.x)}" y2="${fmt(p2.y)}" />`;
  }

  return renderDoor(p1, p2, dirX, dirY, opening.swing ?? "left-in", width);
}

function renderDoor(
  p1: Point,
  p2: Point,
  dirX: number,
  dirY: number,
  swing: DoorSwing,
  width: number
): string {
  if (width < 1e-9) return "";

  const perpLeft: Point = { x: -dirY, y: dirX };
  const perpRight: Point = { x: dirY, y: -dirX };

  const isLeftHinge = swing === "left-in" || swing === "left-out";
  const isInSwing = swing === "left-in" || swing === "right-in";

  const hinge = isLeftHinge ? p1 : p2;
  const other = isLeftHinge ? p2 : p1;
  const perp = isInSwing ? perpLeft : perpRight;

  const openEnd: Point = {
    x: hinge.x + perp.x * width,
    y: hinge.y + perp.y * width,
  };

  const leaf = `<line class="door-leaf" x1="${fmt(hinge.x)}" y1="${fmt(hinge.y)}" x2="${fmt(openEnd.x)}" y2="${fmt(openEnd.y)}" />`;

  const sweepFlag = chooseSweepFlag(other, openEnd, width, hinge);
  const arc = `<path class="door-swing" d="M ${fmt(other.x)} ${fmt(other.y)} A ${fmt(width)} ${fmt(width)} 0 0 ${sweepFlag} ${fmt(openEnd.x)} ${fmt(openEnd.y)}" />`;

  return `${leaf}\n${arc}`;
}

/**
 * Picks the SVG arc sweep-flag (with large-arc-flag fixed at 0) that makes
 * the resulting arc's center coincide with `desiredCenter`, using the
 * standard endpoint-to-center arc conversion (rx === ry === radius, no
 * rotation). https://www.w3.org/TR/SVG/implnote.html#ArcConversionEndpointToCenter
 */
export function chooseSweepFlag(
  start: Point,
  end: Point,
  radius: number,
  desiredCenter: Point
): 0 | 1 {
  const x1p = (start.x - end.x) / 2;
  const y1p = (start.y - end.y) / 2;
  const midX = (start.x + end.x) / 2;
  const midY = (start.y + end.y) / 2;
  const sumSq = x1p * x1p + y1p * y1p;
  const term = Math.max((radius * radius - sumSq) / sumSq, 0);
  const factor = Math.sqrt(term);

  // sweep-flag 0 -> coefficient = -factor; sweep-flag 1 -> coefficient = +factor
  const center0: Point = { x: midX - factor * y1p, y: midY + factor * x1p };
  const center1: Point = { x: midX + factor * y1p, y: midY - factor * x1p };

  const d0 = Math.hypot(center0.x - desiredCenter.x, center0.y - desiredCenter.y);
  const d1 = Math.hypot(center1.x - desiredCenter.x, center1.y - desiredCenter.y);
  return d0 <= d1 ? 0 : 1;
}

function wallDirection(wall: Wall): { dirX: number; dirY: number; length: number } {
  const dx = wall.end.x - wall.start.x;
  const dy = wall.end.y - wall.start.y;
  const length = Math.hypot(dx, dy);
  if (length < 1e-9) return { dirX: 0, dirY: 0, length };
  return { dirX: dx / length, dirY: dy / length, length };
}

function pointAlong(start: Point, dirX: number, dirY: number, distance: number): Point {
  return { x: start.x + dirX * distance, y: start.y + dirY * distance };
}

function clamp(v: number, min: number, max: number): number {
  return Math.min(Math.max(v, min), Math.max(min, max));
}

function polygonToPath(points: Point[]): string {
  const [first, ...rest] = points;
  const parts = [`M ${fmt(first.x)} ${fmt(first.y)}`];
  for (const p of rest) parts.push(`L ${fmt(p.x)} ${fmt(p.y)}`);
  parts.push("Z");
  return parts.join(" ");
}

function polylineToPath(points: Point[]): string {
  const [first, ...rest] = points;
  const parts = [`M ${fmt(first.x)} ${fmt(first.y)}`];
  for (const p of rest) parts.push(`L ${fmt(p.x)} ${fmt(p.y)}`);
  return parts.join(" ");
}

function fmt(n: number): string {
  return String(Math.round(n * 1000) / 1000);
}

function escapeAttr(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/"/g, "&quot;");
}
```

Note: this step implements the *entire* renderer (including room and door
rendering used by later tasks) because the helpers — `computeBounds`,
`wallDirection`, `polygonToPath`, `fmt`, etc. — are shared by all of it and
`renderFloorSvg` is one function. Tasks 8 and 9 add tests for the
room/opening/door code paths that already exist after this step.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run svgRender.test.ts`

Expected: `Tests  4 passed (4)`

- [ ] **Step 5: Commit**

```bash
git add packages/geometry/src/svgRender.ts packages/geometry/test/svgRender.test.ts
git commit -m "feat(geometry): render floor walls and dividers to SVG"
```

---

### Task 8: SVG rendering — rooms and window openings

**Files:**
- Modify: `packages/geometry/test/svgRender.test.ts`

(No source changes — `renderRoom` and the window branch of `renderOpening`
were implemented in Task 7. This task adds the tests that exercise them.)

- [ ] **Step 1: Write tests for room and window-opening rendering**

Append to `packages/geometry/test/svgRender.test.ts`:

```typescript
import type { Room } from "../src/types";

describe("renderFloorSvg - rooms", () => {
  it("renders a room polygon with its id and HA area data attribute", () => {
    const room: Room = {
      id: "room-1",
      label: "Living Room",
      haAreaId: "living_room",
      polygon: [
        { x: 0, y: 0 },
        { x: 4, y: 0 },
        { x: 4, y: 3 },
        { x: 0, y: 3 },
      ],
      areaM2: 12,
    };
    const svg = renderFloorSvg(baseFloor({ rooms: [room] }));

    expect(svg).toContain('<path id="room-room-1" data-ha-area="living_room" class="room"');
  });

  it("renders an empty data-ha-area attribute for rooms with no assigned area", () => {
    const room: Room = {
      id: "room-2",
      label: "Unassigned",
      haAreaId: null,
      polygon: [
        { x: 0, y: 0 },
        { x: 2, y: 0 },
        { x: 2, y: 2 },
        { x: 0, y: 2 },
      ],
      areaM2: 4,
    };
    const svg = renderFloorSvg(baseFloor({ rooms: [room] }));

    expect(svg).toContain('<path id="room-room-2" data-ha-area="" class="room"');
  });

  it("skips rooms with a null polygon (unresolved rooms)", () => {
    const room: Room = {
      id: "room-3",
      label: "Gone",
      haAreaId: null,
      polygon: null,
      areaM2: 0,
    };
    const svg = renderFloorSvg(baseFloor({ rooms: [room] }));

    expect(svg).not.toContain("room-room-3");
  });
});
```

- [ ] **Step 2: Run tests to verify they pass immediately**

Run: `npx vitest run svgRender.test.ts`

Expected: `Tests  7 passed (7)` (room rendering was already implemented in Task 7)

- [ ] **Step 3: Commit**

```bash
git add packages/geometry/test/svgRender.test.ts
git commit -m "test(geometry): cover room polygon and HA-area rendering"
```

---

### Task 9: SVG rendering — door swing arcs

The door symbol is a leaf line (hinge to the 90°-open position) plus a
quarter-circle arc connecting the open position back to the opening's other
edge. The arc's `sweep-flag` is chosen by `chooseSweepFlag` (Task 7) so the
arc is always centered on the hinge, for all four `DoorSwing` values.

**Files:**
- Modify: `packages/geometry/test/svgRender.test.ts`

(No source changes — `renderDoor` and `chooseSweepFlag` were implemented in
Task 7. This task adds the tests that exercise all four swing directions.)

- [ ] **Step 1: Write tests for all four door-swing directions**

Append to `packages/geometry/test/svgRender.test.ts`:

```typescript
import { chooseSweepFlag } from "../src/svgRender";
import type { DoorSwing, Point } from "../src/types";

describe("door swing rendering", () => {
  const wall: Wall = {
    id: "w1",
    start: { x: 0, y: 0 },
    end: { x: 4, y: 0 },
    thickness: 0.2,
    type: "wall",
  };

  function doorSvg(swing: DoorSwing): string {
    const opening: Opening = {
      id: "op1",
      wallId: "w1",
      type: "door",
      offset: 1,
      width: 0.9,
      swing,
    };
    return renderFloorSvg(baseFloor({ walls: [wall], openings: [opening] }));
  }

  const swings: DoorSwing[] = ["left-in", "right-in", "left-out", "right-out"];

  it.each(swings)("renders a leaf line and an arc for swing=%s", (swing) => {
    const svg = doorSvg(swing);
    expect(svg).toContain('<line class="door-leaf"');
    expect(svg).toContain('<path class="door-swing" d="M');
  });

  it.each(swings)("the door-leaf for swing=%s has length equal to the opening width", (swing) => {
    const svg = doorSvg(swing);
    const match = svg.match(/<line class="door-leaf" x1="([^"]+)" y1="([^"]+)" x2="([^"]+)" y2="([^"]+)"/);
    expect(match).not.toBeNull();
    const [, x1, y1, x2, y2] = match!.map(Number);
    const length = Math.hypot(x2 - x1, y2 - y1);
    expect(length).toBeCloseTo(0.9, 5);
  });

  it.each(swings)("the door-leaf for swing=%s starts at the correct hinge corner", (swing) => {
    const svg = doorSvg(swing);
    const match = svg.match(/<line class="door-leaf" x1="([^"]+)" y1="([^"]+)"/);
    const [, x1, y1] = match!;
    const hingeX = swing.startsWith("left") ? 1 : 1.9;
    expect(Number(x1)).toBeCloseTo(hingeX, 5);
    expect(Number(y1)).toBeCloseTo(0, 5);
  });

  it.each(swings)("the door-swing arc for swing=%s is centered on the hinge point", (swing) => {
    const svg = doorSvg(swing);
    const arcMatch = svg.match(
      /<path class="door-swing" d="M ([\d.-]+) ([\d.-]+) A ([\d.-]+) ([\d.-]+) 0 0 (\d) ([\d.-]+) ([\d.-]+)"/
    );
    expect(arcMatch).not.toBeNull();
    const [, mx, my, rx, , sweep, ex, ey] = arcMatch!;

    const start: Point = { x: Number(mx), y: Number(my) };
    const end: Point = { x: Number(ex), y: Number(ey) };
    const radius = Number(rx);

    const hingeX = swing.startsWith("left") ? 1 : 1.9;
    const hinge: Point = { x: hingeX, y: 0 };

    // Recompute both candidate centers for this (start, end, radius) and
    // confirm the chosen sweep-flag corresponds to the one nearest `hinge`.
    const chosen = chooseSweepFlag(start, end, radius, hinge);
    expect(Number(sweep)).toBe(chosen);

    // And confirm `hinge` really is one of the two candidate centers
    // (i.e. our test's expected hinge matches the geometry under test).
    const x1p = (start.x - end.x) / 2;
    const y1p = (start.y - end.y) / 2;
    const midX = (start.x + end.x) / 2;
    const midY = (start.y + end.y) / 2;
    const sumSq = x1p * x1p + y1p * y1p;
    const factor = Math.sqrt(Math.max((radius * radius - sumSq) / sumSq, 0));
    const center0 = { x: midX - factor * y1p, y: midY + factor * x1p };
    const center1 = { x: midX + factor * y1p, y: midY - factor * x1p };
    const d0 = Math.hypot(center0.x - hinge.x, center0.y - hinge.y);
    const d1 = Math.hypot(center1.x - hinge.x, center1.y - hinge.y);
    expect(Math.min(d0, d1)).toBeCloseTo(0, 5);
  });

  it("produces a different arc end point for each swing direction", () => {
    const ends = swings.map((swing) => {
      const svg = doorSvg(swing);
      const arcMatch = svg.match(/A [\d.-]+ [\d.-]+ 0 0 \d ([\d.-]+) ([\d.-]+)"/);
      return `${arcMatch![1]},${arcMatch![2]}`;
    });
    expect(new Set(ends).size).toBe(4);
  });
});
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `npx vitest run svgRender.test.ts`

Expected: `Tests  24 passed (24)` (door rendering was already implemented in Task 7;
`chooseSweepFlag` makes every swing direction provably centered on its hinge)

- [ ] **Step 3: Commit**

```bash
git add packages/geometry/test/svgRender.test.ts
git commit -m "test(geometry): cover door-swing arc rendering for all 4 swing directions"
```

---

### Task 10: Public exports and final verification

**Files:**
- Create: `packages/geometry/src/index.ts`

- [ ] **Step 1: Write the public exports**

Create `packages/geometry/src/index.ts`:

```typescript
export * from "./types";
export * from "./geometry";
export * from "./planarGraph";
export * from "./roomDetection";
export * from "./roomMatching";
export * from "./svgRender";
```

- [ ] **Step 2: Run the full test suite**

Run: `cd packages/geometry && npx vitest run`

Expected: `Test Files  6 passed (6)`, `Tests  58 passed (58)`

(1 types + 14 geometry + 5 planarGraph + 9 roomDetection + 5 roomMatching + 24 svgRender = 58)

- [ ] **Step 3: Run the TypeScript strict type check**

Run: `npx tsc --noEmit`

Expected: no output, exit code 0

- [ ] **Step 4: Commit**

```bash
git add packages/geometry/src/index.ts
git commit -m "feat(geometry): export public API from index"
```

---

## Spec coverage check

- Real-world scale (meters), centerline-based room polygons → `types.ts`, `roomDetection.ts`
- Walls vs dividers (thickness, render style, room-detection participation) → `types.ts`, `roomDetection.ts` (both participate equally), `svgRender.ts` (different rendering)
- Doors/windows with offset clamping and door `swing` enum → `svgRender.ts` `renderWall`/`renderOpening`/`renderDoor`
- Room detection: rectangle, wall-split, divider-split, L-shape, courtyard/hole, unclosed chains, disconnected groups, T/X intersections → Task 5, all 9 cases passing
- Room identity preservation (matched/new/unresolved) → Task 6
- SVG generation with `<path id="room-{id}" data-ha-area="{haAreaId}">` for Spec 2 → Task 8
- Divider dashed-line rendering → Task 7

Out of scope for this plan (per spec, covered by Plan 2/Plan 3): HA area registry integration, `/data/house.json` persistence, the editor UI, and the backend's independent Python SVG export.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-15-floor-plan-geometry-engine.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
