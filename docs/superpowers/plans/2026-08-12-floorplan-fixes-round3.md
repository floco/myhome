# Floor Plan Fixes Round 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix five independent floor-plan editor issues: chore pins can't open the full chore modal, zone labels overlap child rooms, mobile drag-and-drop of picker/furniture items silently fails, stairs furniture has no shape variant, and the mobile toolbar's Edit/View toggle shifts position when it's tapped.

**Architecture:** Each fix is scoped to its own files with no cross-task dependencies; tasks can be done in any order. Two touch geometry: `packages/geometry` (pure functions, no Svelte) for the new label-placement algorithm, and `packages/editor` (Svelte components + `furnitureLibrary.ts` + locale JSON) for everything else.

**Tech Stack:** Svelte 5 (runes), TypeScript, Vitest, npm workspaces (`@myhome/geometry`, `@myhome/editor`).

## Global Constraints

- Follow existing code style: no comments unless explaining non-obvious WHY; 2-space indent; existing `mount`/`unmount`/`flushSync` raw-Svelte test pattern (no `@testing-library`).
- Every new/changed user-facing string needs both `en.json` and `fr.json` entries (see `src/lib/locales/`).
- Component tests: attach the mount target to `document.body` before mounting and remove it after (jsdom event delegation requires this — see existing tests for the pattern).
- Run tests with `npm test -w @myhome/geometry` and `npm test -w @myhome/editor` from the repo root (`/projects/myhome/.claude/worktrees/floorplan-picker-popover`). Both map to `vitest run`; pass a path to scope to one file, e.g. `npm test -w @myhome/editor -- test/BadgePopup.test.ts`.

---

## Task 1: Chore pin — open full chore modal from BadgePopup

**Files:**
- Modify: `packages/editor/src/lib/components/BadgePopup.svelte`
- Modify: `packages/editor/src/App.svelte:23` (import), `App.svelte:300` (state), `App.svelte:1083-1104` (wiring)
- Modify: `packages/editor/src/lib/locales/en.json:425-431`, `packages/editor/src/lib/locales/fr.json:425-431`
- Test: `packages/editor/test/BadgePopup.test.ts`

**Interfaces:**
- Produces: `BadgePopup` gains an `ondetails: () => void` prop and renders a "🔍" details button that calls it.
- Consumes (from existing code, unchanged): `ChoreEditModal` props `chore: Chore | null`, `store: ChoreStore`, `rooms: Array<{ id: string; label: string; polygon: Point[] | null }>`, `onclose: () => void`.

- [ ] **Step 1: Write the failing test for the new details button**

Add to `packages/editor/test/BadgePopup.test.ts`, inside the `"BadgePopup — existing behavior"` describe block:

```ts
  it("calls ondetails when the details button is clicked", () => {
    const el = target();
    const ondetails = vi.fn();
    const comp = mount(BadgePopup, { target: el, props: baseProps({ ondetails }) });
    flushSync();
    (el.querySelector(".details-btn") as HTMLButtonElement).click();
    expect(ondetails).toHaveBeenCalledOnce();
    unmount(comp);
    el.remove();
  });
```

Also add `ondetails: vi.fn()` to the `baseProps()` defaults object (it's a required prop, so every existing `mount` call needs it satisfied — adding it to the shared `baseProps()` helper covers all of them).

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -w @myhome/editor -- test/BadgePopup.test.ts`
Expected: FAIL — `ondetails` is not a valid prop / `.details-btn` not found.

- [ ] **Step 3: Add the details button to BadgePopup.svelte**

In `packages/editor/src/lib/components/BadgePopup.svelte`, update the `Props` interface and destructure (lines 6-18):

```ts
  interface Props {
    chore: Chore;
    assignment: Assignment;
    screenX: number;
    screenY: number;
    oncomplete: () => void;
    oncompleteall: () => void;
    onremove: () => void;
    onclose: () => void;
    onlabelchange: (label: string) => void;
    ondetails: () => void;
  }

  let { chore, assignment, screenX, screenY, oncomplete, oncompleteall, onremove, onclose, onlabelchange, ondetails }: Props = $props();
```

Add a details button to `.popup-actions` (replace lines 50-55):

```svelte
  <div class="popup-actions">
    <button class="details-btn" onclick={ondetails} title={$_('chores.badgePopup.details')}>🔍 {$_('chores.badgePopup.details')}</button>
    <button onclick={oncompleteall}>✓ {$_('chores.badgePopup.allDone')}</button>
    <button onclick={oncomplete}>✓ {$_('chores.badgePopup.thisRoom')}</button>
    <button onclick={onremove}>✕ {$_('chores.badgePopup.remove')}</button>
    <button class="close-btn" onclick={onclose}>✕</button>
  </div>
```

- [ ] **Step 4: Add the `details` i18n key**

In `packages/editor/src/lib/locales/en.json`, inside `chores.badgePopup` (lines 425-431), add after `"due": "Due",`:

```json
      "due": "Due",
      "details": "Details",
```

In `packages/editor/src/lib/locales/fr.json`, same location:

```json
      "due": "Échéance",
      "details": "Détails",
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm test -w @myhome/editor -- test/BadgePopup.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/BadgePopup.svelte packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/BadgePopup.test.ts
git commit -m "feat(floorplan): add details button to chore badge popup"
```

- [ ] **Step 7: Write the failing test for App.svelte wiring**

Create `packages/editor/test/App.badgeDetails.test.ts`. This seeds a real house document (one floor, four walls forming a 4x3 room, and a `rooms` entry with a fixed id `"room-1"`) plus a real chore document (one chore with an assignment already placed at world `(2, 1.5)`, inside that room) — mirroring the fixture style `App.viewportAutoFit.test.ts` uses for house docs and the `/api/chores` shape `App.test.ts`'s "item picker visibility" test uses. Providing the room's polygon in the fixture (rather than drawing walls live and discovering a random UUID) works because `matchRooms` (in `packages/geometry/src/roomMatching.ts`) preserves an existing room's `id` whenever the newly-detected polygon's centroid falls inside that existing room's polygon — the fixture's `(0,0)-(4,0)-(4,3)-(0,3)` room comfortably contains the centroid of whatever `detectRooms` produces from the matching walls, regardless of wall-thickness insets.

```ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import App from "../src/App.svelte";

const HOME = { id: "home-1", name: "Main House", type: "existing", enabledModules: [], createdAt: "2026-01-01T00:00:00.000Z" };

const HOUSE_DOC = {
  version: 1,
  house: { name: "Main House", units: "m", gridSnap: 0.1 },
  floors: [
    {
      id: "gf-1",
      name: "Ground Floor",
      order: 0,
      walls: [
        { id: "w1", type: "wall", thickness: 0.1, start: { x: 0, y: 0 }, end: { x: 4, y: 0 } },
        { id: "w2", type: "wall", thickness: 0.1, start: { x: 4, y: 0 }, end: { x: 4, y: 3 } },
        { id: "w3", type: "wall", thickness: 0.1, start: { x: 4, y: 3 }, end: { x: 0, y: 3 } },
        { id: "w4", type: "wall", thickness: 0.1, start: { x: 0, y: 3 }, end: { x: 0, y: 0 } },
      ],
      openings: [],
      rooms: [
        { id: "room-1", label: "Room 1", haAreaId: null, polygon: [{ x: 0, y: 0 }, { x: 4, y: 0 }, { x: 4, y: 3 }, { x: 0, y: 3 }], areaM2: 12 },
      ],
      furnitureObjects: [],
    },
  ],
  currentFloorId: "gf-1",
};

const CHORE_DOC = {
  version: 1,
  chores: [{ id: "c1", donetickId: null, name: "Water plants", emoji: "💧", periodDays: 7, frequencyType: "interval", frequency: 7, frequencyMetadata: {}, scheduleFromDue: false, nextDueDate: "2026-07-01", description: "" }],
  assignments: [{ id: "a1", choreId: "c1", roomId: "room-1", position: { x: 2, y: 1.5 }, nextDueDate: "2026-07-01", label: null }],
  completions: [],
};

function stubFetch() {
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
    const handlers: Record<string, unknown> = {
      "/api/auth/me": { id: "u1", username: "admin", role: "admin" },
      "/api/homes": [HOME],
      [`/api/homes/${HOME.id}/house`]: HOUSE_DOC,
      [`/api/homes/${HOME.id}/chores`]: CHORE_DOC,
    };
    if (url in handlers) {
      return Promise.resolve({ ok: true, status: 200, json: async () => handlers[url] });
    }
    return Promise.resolve({ ok: false, status: 404, json: async () => undefined });
  }));
}

async function mountApp(target: HTMLElement): Promise<ReturnType<typeof mount>> {
  window.location.hash = "#/plan";
  const app = mount(App, { target });
  // Same 10-tick budget App.viewportAutoFit.test.ts documents: authStore resolves,
  // then homesStore loads, then floorStore.reload() AND choreStore.reload() both
  // do a real fetch here, beyond the plain-404 test files' smaller tick budgets.
  for (let i = 0; i < 10; i++) await tick();
  flushSync();
  return app;
}

function findChoreBadge(target: HTMLElement): SVGGElement | undefined {
  return Array.from(target.querySelectorAll("g")).find(
    (g) => g.querySelector("text")?.textContent === "💧",
  ) as SVGGElement | undefined;
}

describe("App — badge popup details button", () => {
  let target: HTMLElement;
  let app: ReturnType<typeof mount> | undefined;

  afterEach(() => {
    if (app) { unmount(app); app = undefined; }
    target?.remove();
    vi.unstubAllGlobals();
  });

  it("opens the full ChoreEditModal when the badge popup's details button is clicked", async () => {
    stubFetch();
    target = document.createElement("div");
    document.body.appendChild(target);
    app = await mountApp(target);

    // Activate the "chores" layer via the Layers dropdown, same pattern as
    // App.test.ts's "keeps the item picker panel visible" test.
    (target.querySelector('button[title="Toggle map layers"]') as HTMLButtonElement).click();
    await tick();
    flushSync();
    const choresRow = Array.from(document.querySelectorAll(".layer-row")).find(
      (r) => r.textContent?.includes("Chores"),
    ) as HTMLElement;
    (choresRow.querySelector('input[type="checkbox"]') as HTMLInputElement).click();
    await tick();
    flushSync();

    // The badge sits at world (2, 1.5). The default (unfitted, since jsdom
    // reports clientWidth 0) viewport is zoom=100, panX=400, panY=300 --
    // same mapping App.test.ts's drawWalls() helper documents -- so its
    // screen position is (2*100+400, 1.5*100+300) = (600, 450).
    const badge = findChoreBadge(target);
    expect(badge).toBeDefined();
    badge!.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, pointerId: 1, clientX: 600, clientY: 450 }));
    flushSync();
    badge!.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, pointerId: 1, clientX: 600, clientY: 450 }));
    flushSync();

    expect(target.querySelector(".popup-name")?.textContent).toBe("Water plants");
    const detailsBtn = target.querySelector(".details-btn") as HTMLButtonElement;
    expect(detailsBtn).not.toBeNull();

    detailsBtn.click();
    flushSync();

    expect(target.querySelector(".popup-name")).toBeNull();
    expect(target.querySelectorAll(".tab").length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 8: Run test to verify it fails**

Run: `npm test -w @myhome/editor -- test/App.badgeDetails.test.ts`
Expected: FAIL — no `ChoreEditModal` renders yet (details button doesn't do anything in `App.svelte`).

- [ ] **Step 9: Wire ChoreEditModal into App.svelte**

Add the import near the other page/modal imports (after line 23, next to the existing `BadgePopup` import):

```ts
import ChoreEditModal from "./lib/components/ChoreEditModal.svelte";
```

Add state near `selectedBadge` (line 300):

```ts
  let mapEditChore = $state<Chore | null>(null);
```

(`Chore` is already imported via `type { Assignment }` at line 19 — extend that import to `import type { Assignment, Chore } from "./lib/choreStore.svelte";`.)

Add an `ondetails` handler to the existing `BadgePopup` usage (inside the block at lines 1090-1100), and render `ChoreEditModal` when `mapEditChore` is set. Replace the existing block:

```svelte
                    <BadgePopup
                      {chore}
                      assignment={badge.assignment}
                      screenX={badge.screenX}
                      screenY={badge.screenY}
                      oncomplete={async () => { await choreStore.completeAssignment(badge.assignment.id); selectedBadge = null; }}
                      oncompleteall={async () => { await choreStore.completeChore(chore.id); selectedBadge = null; }}
                      onremove={async () => { await choreStore.deleteAssignment(badge.assignment.id); selectedBadge = null; }}
                      onlabelchange={(label) => choreStore.updateAssignmentLabel(badge.assignment.id, label)}
                      onclose={() => { selectedBadge = null; }}
                      ondetails={() => { mapEditChore = chore; selectedBadge = null; }}
                    />
```

Immediately after the closing `{/if}{/if}{/if}` of that block (line 1104), add:

```svelte
            {#if mapEditChore}
              <ChoreEditModal
                chore={mapEditChore}
                store={choreStore}
                rooms={floorStore.floors.flatMap((f) => f.rooms)}
                onclose={() => { mapEditChore = null; }}
              />
            {/if}
```

- [ ] **Step 10: Run test to verify it passes**

Run: `npm test -w @myhome/editor -- test/App.badgeDetails.test.ts`
Expected: PASS

- [ ] **Step 11: Run the full editor test suite to check for regressions**

Run: `npm test -w @myhome/editor`
Expected: PASS (all existing + new tests)

- [ ] **Step 12: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/test/App.badgeDetails.test.ts
git commit -m "feat(floorplan): open full chore modal from the map badge popup"
```

---

## Task 2: `computeLabelPosition` geometry helper

**Files:**
- Modify: `packages/geometry/src/geometry.ts`
- Test: `packages/geometry/test/geometry.test.ts`

**Interfaces:**
- Produces: `computeLabelPosition(room: Room, allRooms: Room[]): Point`, exported from `packages/geometry/src/geometry.ts` (and re-exported via `packages/geometry/src/index.ts`, which already does `export * from "./geometry"`).
- Consumes: existing `pointInPolygon(point: Point, polygon: Point[]): boolean`, `polygonCentroid(points: Point[]): Point`, `EPSILON`, and `Room` from `./types`.

- [ ] **Step 1: Write the failing tests**

Add to `packages/geometry/test/geometry.test.ts` (new `describe` block, after the existing `pointInPolygon` tests):

```ts
import { computeLabelPosition } from "../src/geometry";
import type { Room, Point } from "../src/types";

function makeRoom(id: string, polygon: Point[] | null): Room {
  return { id, label: id, haAreaId: null, polygon, areaM2: 0 };
}

describe("computeLabelPosition", () => {
  const outerSquare: Point[] = [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }, { x: 0, y: 10 }];

  it("returns the plain centroid when no other room is contained inside it", () => {
    const room = makeRoom("outer", outerSquare);
    const other = makeRoom("far", [{ x: 20, y: 20 }, { x: 22, y: 20 }, { x: 22, y: 22 }, { x: 20, y: 22 }]);
    const pos = computeLabelPosition(room, [room, other]);
    expect(pos.x).toBeCloseTo(5, 5);
    expect(pos.y).toBeCloseTo(5, 5);
  });

  it("ignores a room that only barely overlaps (below the 50% containment threshold)", () => {
    const room = makeRoom("outer", outerSquare);
    // 12x12 room overlapping the outer square only in its bottom-left 2x2 corner (~2.8% of its own area)
    const sliver = makeRoom("sliver", [{ x: 8, y: 8 }, { x: 20, y: 8 }, { x: 20, y: 20 }, { x: 8, y: 20 }]);
    const pos = computeLabelPosition(room, [room, sliver]);
    expect(pos.x).toBeCloseTo(5, 5);
    expect(pos.y).toBeCloseTo(5, 5);
  });

  it("moves the label off a fully-contained child room's area", () => {
    const room = makeRoom("zone", outerSquare);
    // Fully inside the outer square, and it covers the outer square's own centroid (5,5).
    const child = makeRoom("child", [{ x: 3, y: 3 }, { x: 7, y: 3 }, { x: 7, y: 7 }, { x: 3, y: 7 }]);
    const pos = computeLabelPosition(room, [room, child]);
    expect(pointInPolygon(pos, child.polygon!)).toBe(false);
    expect(pointInPolygon(pos, room.polygon!)).toBe(true);
    // The plain centroid (5,5) would have landed inside the child -- confirm we moved off it.
    expect(pos.x === 5 && pos.y === 5).toBe(false);
  });

  it("returns {x:0,y:0} when the room has no polygon", () => {
    const room = makeRoom("unresolved", null);
    expect(computeLabelPosition(room, [room])).toEqual({ x: 0, y: 0 });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -w @myhome/geometry -- test/geometry.test.ts`
Expected: FAIL — `computeLabelPosition` is not exported.

- [ ] **Step 3: Implement `computeLabelPosition` in geometry.ts**

In `packages/geometry/src/geometry.ts`, change the top import line 1 to also pull in `Room`:

```ts
import type { Point, Room } from "./types";
```

Append at the end of the file (after `pointInPolygon`):

```ts

interface Bounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

function polygonBounds(polygon: Point[]): Bounds {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const p of polygon) {
    if (p.x < minX) minX = p.x;
    if (p.x > maxX) maxX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.y > maxY) maxY = p.y;
  }
  return { minX, maxX, minY, maxY };
}

const CONTAINMENT_GRID_STEPS = 12;
const CONTAINMENT_THRESHOLD = 0.5;

/** Fraction (0-1) of `inner`'s own area, estimated via grid sampling, that lies inside `outer`. */
function estimateContainmentRatio(outer: Point[], inner: Point[]): number {
  const b = polygonBounds(inner);
  let total = 0;
  let contained = 0;
  for (let i = 0; i <= CONTAINMENT_GRID_STEPS; i++) {
    for (let j = 0; j <= CONTAINMENT_GRID_STEPS; j++) {
      const point = {
        x: b.minX + ((b.maxX - b.minX) * i) / CONTAINMENT_GRID_STEPS,
        y: b.minY + ((b.maxY - b.minY) * j) / CONTAINMENT_GRID_STEPS,
      };
      if (!pointInPolygon(point, inner)) continue;
      total++;
      if (pointInPolygon(point, outer)) contained++;
    }
  }
  return total === 0 ? 0 : contained / total;
}

function distanceToSegment(p: Point, a: Point, b: Point): number {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const lenSq = dx * dx + dy * dy;
  if (lenSq < EPSILON) return Math.hypot(p.x - a.x, p.y - a.y);
  let t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / lenSq;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
}

function distanceToPolygon(point: Point, polygon: Point[]): number {
  let min = Infinity;
  const n = polygon.length;
  for (let i = 0, j = n - 1; i < n; j = i++) {
    min = Math.min(min, distanceToSegment(point, polygon[j], polygon[i]));
  }
  return min;
}

const LABEL_GRID_STEPS = 20;

/** Grid-samples `outer` for the point farthest (in min-distance terms) from every polygon in `children`, skipping points inside any child. Returns null if no valid point survives. */
function findOpenPoint(outer: Point[], children: Point[][]): Point | null {
  const b = polygonBounds(outer);
  let best: Point | null = null;
  let bestScore = -Infinity;
  for (let i = 0; i <= LABEL_GRID_STEPS; i++) {
    for (let j = 0; j <= LABEL_GRID_STEPS; j++) {
      const point = {
        x: b.minX + ((b.maxX - b.minX) * i) / LABEL_GRID_STEPS,
        y: b.minY + ((b.maxY - b.minY) * j) / LABEL_GRID_STEPS,
      };
      if (!pointInPolygon(point, outer)) continue;
      if (children.some((c) => pointInPolygon(point, c))) continue;
      const score = children.reduce((min, c) => Math.min(min, distanceToPolygon(point, c)), Infinity);
      if (score > bestScore) {
        bestScore = score;
        best = point;
      }
    }
  }
  return best;
}

/**
 * Where to draw a room's label. If other rooms' polygons are substantially
 * contained inside this room's polygon (a "zone" spanning child rooms), the
 * label is moved to the most open point of the zone's polygon that isn't
 * covered by any child room, instead of the zone's own (likely obscured)
 * centroid.
 */
export function computeLabelPosition(room: Room, allRooms: Room[]): Point {
  if (!room.polygon) return { x: 0, y: 0 };
  const children = allRooms
    .filter((other) => other.id !== room.id && other.polygon)
    .filter((other) => estimateContainmentRatio(room.polygon!, other.polygon!) >= CONTAINMENT_THRESHOLD)
    .map((other) => other.polygon!);

  if (children.length === 0) return polygonCentroid(room.polygon);

  return findOpenPoint(room.polygon, children) ?? polygonCentroid(room.polygon);
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test -w @myhome/geometry -- test/geometry.test.ts`
Expected: PASS

- [ ] **Step 5: Run the full geometry test suite to check for regressions**

Run: `npm test -w @myhome/geometry`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/geometry/src/geometry.ts packages/geometry/test/geometry.test.ts
git commit -m "feat(geometry): add computeLabelPosition for zone rooms containing child rooms"
```

---

## Task 3: Wire `computeLabelPosition` into RoomShape

**Files:**
- Modify: `packages/editor/src/lib/components/RoomShape.svelte`
- Modify: `packages/editor/src/lib/components/Canvas.svelte:285-290`
- Test: `packages/editor/test/RoomShape.test.ts` (new file)

**Interfaces:**
- Consumes: `computeLabelPosition(room: Room, allRooms: Room[]): Point` from `@myhome/geometry` (Task 2).
- Produces: `RoomShape` gains a required `allRooms: Room[]` prop.

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/RoomShape.test.ts`:

```ts
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import RoomShape from "../src/lib/components/RoomShape.svelte";
import type { Room } from "@myhome/geometry";
import { createViewportStore } from "../src/lib/viewportStore.svelte";

let target: HTMLElement;

beforeEach(() => {
  target = document.createElement("div");
  document.body.appendChild(target);
});
afterEach(() => {
  target.remove();
});

function identityViewport() {
  const store = createViewportStore();
  store.viewport.zoom = 1;
  store.viewport.panX = 0;
  store.viewport.panY = 0;
  return store.viewport;
}

describe("RoomShape — label placement", () => {
  it("places the label at the plain centroid when no other room is contained", () => {
    const room: Room = {
      id: "r1", label: "Living Room", haAreaId: null, areaM2: 100,
      polygon: [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }, { x: 0, y: 10 }],
    };
    const comp = mount(RoomShape, { target, props: { room, allRooms: [room], viewport: identityViewport() } });
    flushSync();
    const text = target.querySelector("text.room-label") as SVGTextElement;
    expect(Number(text.getAttribute("x"))).toBeCloseTo(5, 5);
    expect(Number(text.getAttribute("y"))).toBeCloseTo(5, 5);
    unmount(comp);
  });

  it("moves the label off a fully-contained child room", () => {
    const zone: Room = {
      id: "zone", label: "Zone", haAreaId: null, areaM2: 100,
      polygon: [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }, { x: 0, y: 10 }],
    };
    const child: Room = {
      id: "child", label: "Child", haAreaId: null, areaM2: 16,
      polygon: [{ x: 3, y: 3 }, { x: 7, y: 3 }, { x: 7, y: 7 }, { x: 3, y: 7 }],
    };
    const comp = mount(RoomShape, { target, props: { room: zone, allRooms: [zone, child], viewport: identityViewport() } });
    flushSync();
    const text = target.querySelector("text.room-label") as SVGTextElement;
    const x = Number(text.getAttribute("x"));
    const y = Number(text.getAttribute("y"));
    // Plain centroid (5,5) sits inside the child room; confirm the label moved off it.
    expect(x === 5 && y === 5).toBe(false);
    unmount(comp);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -w @myhome/editor -- test/RoomShape.test.ts`
Expected: FAIL — `allRooms` prop doesn't exist yet / label position unchanged for the second test.

- [ ] **Step 3: Update RoomShape.svelte**

Replace the script block's props and `labelPos` derivation (lines 1-35):

```svelte
<script lang="ts">
  import type { Room } from "@myhome/geometry";
  import { computeLabelPosition } from "@myhome/geometry";
  import type { ViewportState } from "../viewportStore.svelte";
  import type { ToolType } from "../toolStore.svelte";

  let {
    room,
    allRooms,
    viewport,
    tool = "select",
    selected = false,
    onselectroom,
  }: {
    room: Room;
    allRooms: Room[];
    viewport: ViewportState;
    tool?: ToolType;
    selected?: boolean;
    onselectroom?: (id: string) => void;
  } = $props();

  const screenPoints = $derived.by(() => {
    if (!room.polygon) return [];
    return room.polygon.map((p) => ({
      x: p.x * viewport.zoom + viewport.panX,
      y: p.y * viewport.zoom + viewport.panY,
    }));
  });

  const points = $derived(screenPoints.map((p) => `${p.x},${p.y}`).join(" "));

  const labelWorldPos = $derived.by(() => {
    if (!room.polygon) return { x: 0, y: 0 };
    return computeLabelPosition(room, allRooms);
  });

  const labelPos = $derived.by(() => {
    const c = labelWorldPos;
    return { x: c.x * viewport.zoom + viewport.panX, y: c.y * viewport.zoom + viewport.panY };
  });

  function handleClick(event: MouseEvent): void {
    if (tool !== "select") return;
    event.stopPropagation();
    onselectroom?.(room.id);
  }
</script>
```

- [ ] **Step 4: Pass `allRooms` from Canvas.svelte**

In `packages/editor/src/lib/components/Canvas.svelte`, update the `{#each}` block (lines 285-292):

```svelte
  {#each floor.rooms as room (room.id)}
    <RoomShape
      {room}
      allRooms={floor.rooms}
      {viewport}
      {tool}
      selected={room.id === selectedRoomId}
      onselectroom={(id) => onselectroom?.(id)}
    />
  {/each}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm test -w @myhome/editor -- test/RoomShape.test.ts`
Expected: PASS

- [ ] **Step 6: Run the full editor test suite to check for regressions**

Run: `npm test -w @myhome/editor`
Expected: PASS (Canvas.test.ts in particular, since it renders RoomShape)

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/components/RoomShape.svelte packages/editor/src/lib/components/Canvas.svelte packages/editor/test/RoomShape.test.ts
git commit -m "feat(floorplan): move zone room labels off contained child rooms"
```

---

## Task 4: Fix mobile drag-and-drop (`touch-action: none` on picker/furniture rows)

**Files:**
- Modify: `packages/editor/src/lib/components/ItemPickerPanel.svelte:201-204`
- Modify: `packages/editor/src/lib/components/FurnitureLibraryPanel.svelte:166-178`
- Test: `packages/editor/test/ItemPickerPanel.test.ts`, `packages/editor/test/FurnitureLibraryPanel.test.ts`

**Interfaces:** None — pure CSS fix, no prop/signature changes.

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/ItemPickerPanel.test.ts` (new test in the `describe("ItemPickerPanel", ...)` block):

```ts
  it("sets touch-action: none on item rows so mobile drag isn't hijacked by scroll", () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: null, onitempointerdown: vi.fn() },
    });
    flushSync();
    const row = target.querySelector(".item-row") as HTMLElement;
    expect(row).not.toBeNull();
    expect(getComputedStyle(row).touchAction).toBe("none");
    unmount(app);
  });
```

Add to `packages/editor/test/FurnitureLibraryPanel.test.ts` (check the file first for its existing mount/target pattern and mirror it):

```ts
  it("sets touch-action: none on furniture items so mobile drag isn't hijacked by scroll", () => {
    // mount FurnitureLibraryPanel using this file's existing target/mount helper
    flushSync();
    const item = target.querySelector(".furniture-item") as HTMLElement;
    expect(item).not.toBeNull();
    expect(getComputedStyle(item).touchAction).toBe("none");
    // unmount per this file's existing pattern
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -w @myhome/editor -- test/ItemPickerPanel.test.ts test/FurnitureLibraryPanel.test.ts`
Expected: FAIL — `touchAction` computes to `"auto"` (the default), not `"none"`.

- [ ] **Step 3: Add `touch-action: none` to `.item-row` in ItemPickerPanel.svelte**

Replace (lines 201-204):

```css
  .item-row {
    display: flex; align-items: center; gap: 8px; padding: 5px 10px;
    cursor: grab; user-select: none; border-radius: var(--radius-sm); margin: 1px 4px;
    touch-action: none;
  }
```

- [ ] **Step 4: Add `touch-action: none` to `.furniture-item` in FurnitureLibraryPanel.svelte**

Replace (lines 166-178):

```css
  .furniture-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-end;
    gap: 2px;
    padding: 4px;
    border-radius: var(--radius-sm);
    cursor: grab;
    user-select: none;
    min-height: 64px;
    min-width: 0;
    touch-action: none;
  }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `npm test -w @myhome/editor -- test/ItemPickerPanel.test.ts test/FurnitureLibraryPanel.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/ItemPickerPanel.svelte packages/editor/src/lib/components/FurnitureLibraryPanel.svelte packages/editor/test/ItemPickerPanel.test.ts packages/editor/test/FurnitureLibraryPanel.test.ts
git commit -m "fix(floorplan): stop mobile scroll from hijacking picker/furniture drag"
```

- [ ] **Step 7: Manual verification note**

This fix can't be fully verified by jsdom (real touch-scroll hijacking isn't simulated). After merging, do a manual check on an actual phone or Chrome DevTools device emulation with touch simulation: open the Picker or Furniture popover on the mobile floor-plan view, touch-and-drag an item onto the canvas, and confirm it places instead of doing nothing.

---

## Task 5: Stairs furniture — straight / L-shaped variant

**Files:**
- Modify: `packages/editor/src/lib/furnitureLibrary.ts:599-615` (stairs entry), append new `renderStairs` function
- Modify: `packages/editor/src/lib/locales/en.json:350-362`, `packages/editor/src/lib/locales/fr.json:350-362`
- Modify: `packages/editor/test/furnitureLibrary.test.ts:58-65` (existing "no params" assertion is now wrong)

**Interfaces:**
- Produces: stairs template now has `params: FurnitureParamDef[]` (`shape`: `straight`|`l-shaped`, `corner`: `nw`|`ne`|`se`|`sw`) and `render: renderStairs`. No new exports beyond what `resolveFurnitureSvg`/`defaultFurnitureParams` already provide generically.

- [ ] **Step 1: Update the now-outdated "stairs has no params" test**

In `packages/editor/test/furnitureLibrary.test.ts`, replace the test at lines 58-65:

```ts
  it("includes the structural category with a Stairs template", () => {
    expect(FURNITURE_CATEGORIES).toContain("structural");
    const stairs = getTemplate("stairs");
    expect(stairs).toBeDefined();
    expect(stairs?.category).toBe("structural");
  });
```

- [ ] **Step 2: Write the new failing tests for stairs variants**

Add after the sofa tests (after line 154, before the `computeDeckPlankLayout` tests):

```ts
  it("stairs declares shape and corner params, with shape defaulting to straight", () => {
    const t = getTemplate("stairs")!;
    expect(defaultFurnitureParams(t)).toEqual({ shape: "straight", corner: "se" });
  });

  it("stairs corner param is visibleWhen shape is l-shaped", () => {
    const t = getTemplate("stairs")!;
    const corner = t.params?.find((p) => p.id === "corner") as Extract<FurnitureParamDef, { type: "enum" }> | undefined;
    expect(corner?.visibleWhen).toEqual({ paramId: "shape", equals: "l-shaped" });
  });

  it("renders straight tread lines when shape is straight", () => {
    const t = getTemplate("stairs")!;
    const obj: FurnitureObject = { id: "f1", templateId: "stairs", x: 0, y: 0, width: 1.0, height: 3.0, rotation: 0, params: { shape: "straight" } };
    const svg = resolveFurnitureSvg(t, obj);
    expect(svg).toContain('x="5" y="5" width="90" height="90"');
    expect((svg.match(/<line/g) ?? []).length).toBeGreaterThan(1);
  });

  it("renders an L-shaped stair with the landing at the requested corner", () => {
    const t = getTemplate("stairs")!;
    const nw: FurnitureObject = { id: "f2", templateId: "stairs", x: 0, y: 0, width: 2.0, height: 2.0, rotation: 0, params: { shape: "l-shaped", corner: "nw" } };
    const se: FurnitureObject = { id: "f3", templateId: "stairs", x: 0, y: 0, width: 2.0, height: 2.0, rotation: 0, params: { shape: "l-shaped", corner: "se" } };
    const svgNw = resolveFurnitureSvg(t, nw);
    const svgSe = resolveFurnitureSvg(t, se);
    expect(svgNw).toContain('x="5" y="5" width="90" height="40"'); // horizontal arm at top
    expect(svgNw).toContain('x="5" y="5" width="40" height="90"'); // vertical arm at left
    expect(svgSe).toContain('x="5" y="55" width="90" height="40"'); // horizontal arm at bottom
    expect(svgSe).toContain('x="55" y="5" width="40" height="90"'); // vertical arm at right
    // The two corners should produce visibly different tread markup.
    expect(svgNw).not.toBe(svgSe);
  });
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `npm test -w @myhome/editor -- test/furnitureLibrary.test.ts`
Expected: FAIL — stairs has no `params`/`render` yet.

- [ ] **Step 4: Add params + render to the stairs template**

In `packages/editor/src/lib/furnitureLibrary.ts`, replace the stairs entry (lines 599-615):

```ts
  {
    id: "stairs",
    label: "Stairs",
    category: "structural",
    defaultWidth: 1.0,
    defaultHeight: 3.0,
    svgContent: `
      <rect x="5" y="5" width="90" height="90" rx="2"/>
      <line x1="5" y1="76" x2="24" y2="76" fill="none"/>
      <line x1="24" y1="76" x2="24" y2="57" fill="none"/>
      <line x1="24" y1="57" x2="43" y2="57" fill="none"/>
      <line x1="43" y1="57" x2="43" y2="38" fill="none"/>
      <line x1="43" y1="38" x2="62" y2="38" fill="none"/>
      <line x1="62" y1="38" x2="62" y2="19" fill="none"/>
      <line x1="62" y1="19" x2="81" y2="19" fill="none"/>
    `,
    params: [
      {
        id: "shape",
        type: "enum",
        labelKey: "floorPlan.furnitureLibrary.params.stairsShape",
        options: [
          { value: "straight", labelKey: "floorPlan.furnitureLibrary.params.stairsShapeStraight" },
          { value: "l-shaped", labelKey: "floorPlan.furnitureLibrary.params.stairsShapeLShaped" },
        ],
        default: "straight",
      },
      {
        id: "corner",
        type: "enum",
        labelKey: "floorPlan.furnitureLibrary.params.stairsCorner",
        options: [
          { value: "nw", labelKey: "floorPlan.furnitureLibrary.params.cornerNw" },
          { value: "ne", labelKey: "floorPlan.furnitureLibrary.params.cornerNe" },
          { value: "se", labelKey: "floorPlan.furnitureLibrary.params.cornerSe" },
          { value: "sw", labelKey: "floorPlan.furnitureLibrary.params.cornerSw" },
        ],
        default: "se",
        visibleWhen: { paramId: "shape", equals: "l-shaped" },
      },
    ],
    render: renderStairs,
  },
];
```

(Note: the closing `];` of `FURNITURE_TEMPLATES` moves to right after this entry, same as before — only the object body changes.)

Add `renderStairs` next to `renderSofa` (after the `renderSofa` function, i.e. after line 719):

```ts
function renderStairs(ctx: FurnitureRenderContext): string {
  const shape = ctx.params.shape === "l-shaped" ? "l-shaped" : "straight";
  if (shape === "straight") {
    const parts = [`<rect x="5" y="5" width="90" height="90" rx="2"/>`];
    const steps = 8;
    for (let i = 1; i < steps; i++) {
      const y = 5 + (90 / steps) * i;
      parts.push(`<line x1="5" y1="${y.toFixed(2)}" x2="95" y2="${y.toFixed(2)}" fill="none"/>`);
    }
    return parts.join("\n");
  }
  const corner = typeof ctx.params.corner === "string" ? ctx.params.corner : "se";
  const north = corner === "nw" || corner === "ne";
  const west = corner === "nw" || corner === "sw";
  const armY = north ? 5 : 55;
  const armX = west ? 5 : 55;
  const parts = [
    `<rect x="5" y="${armY}" width="90" height="40" rx="2"/>`,
    `<rect x="${armX}" y="5" width="40" height="90" rx="2"/>`,
  ];
  const steps = 5;
  for (let i = 1; i < steps; i++) {
    const x = 5 + (90 / steps) * i;
    parts.push(`<line x1="${x.toFixed(2)}" y1="${armY}" x2="${x.toFixed(2)}" y2="${armY + 40}" fill="none"/>`);
  }
  for (let i = 1; i < steps; i++) {
    const y = 5 + (90 / steps) * i;
    parts.push(`<line x1="${armX}" y1="${y.toFixed(2)}" x2="${armX + 40}" y2="${y.toFixed(2)}" fill="none"/>`);
  }
  return parts.join("\n");
}
```

- [ ] **Step 5: Add i18n keys**

In `packages/editor/src/lib/locales/en.json`, inside `floorPlan.furnitureLibrary.params` (lines 350-362), add after `"cornerSw": "Bottom-left",`:

```json
        "cornerSw": "Bottom-left",
        "stairsShape": "Shape",
        "stairsShapeStraight": "Straight",
        "stairsShapeLShaped": "L-shaped",
        "stairsCorner": "Landing corner",
```

In `packages/editor/src/lib/locales/fr.json`, same location:

```json
        "cornerSw": "Bas-gauche",
        "stairsShape": "Forme",
        "stairsShapeStraight": "Droit",
        "stairsShapeLShaped": "En L",
        "stairsCorner": "Coin du palier",
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `npm test -w @myhome/editor -- test/furnitureLibrary.test.ts`
Expected: PASS

- [ ] **Step 7: Run the full editor test suite to check for regressions**

Run: `npm test -w @myhome/editor`
Expected: PASS (`FurnitureParamsPanel.test.ts`, `FurnitureShape.test.ts` in particular, since they may enumerate all templates)

- [ ] **Step 8: Commit**

```bash
git add packages/editor/src/lib/furnitureLibrary.ts packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/furnitureLibrary.test.ts
git commit -m "feat(floorplan): add straight/L-shaped variant to stairs furniture"
```

---

## Task 6: Mobile toolbar — stable Edit/View toggle position

**Files:**
- Modify: `packages/editor/src/App.svelte:1344-1368`
- Test: existing App toolbar tests — check `find packages/editor/test -iname "App*.test.ts"` for one that renders `.floating-toolbar`; if none targets button order specifically, add a new one.

**Interfaces:** None — pure markup reorder, no prop/signature changes.

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/App.toolbarOrder.test.ts`, using the same `stubFetch404`/`mountAndLoad`/`toolbarBtn` helpers `App.test.ts` defines (copy their definitions — they're plain top-level functions in that file, not exports, so they must be duplicated here rather than imported):

```ts
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import App from "../src/App.svelte";

function stubFetch404() {
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
    if (url === "/api/auth/me") {
      return Promise.resolve({ ok: true, status: 200, json: async () => ({ id: "u1", username: "admin", role: "admin" }) });
    }
    return Promise.resolve({ ok: false, status: 404, json: async () => undefined });
  }));
}

async function mountAndLoad(target: HTMLElement, route = "#/plan"): Promise<ReturnType<typeof mount>> {
  window.location.hash = route;
  const app = mount(App, { target });
  await tick(); await tick();
  flushSync();
  return app;
}

describe("App — floating toolbar button order", () => {
  it("keeps the Edit/View toggle button in a fixed slot, before Picker/Furniture", async () => {
    stubFetch404();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = await mountAndLoad(target);

    // Edit mode is the default on load, so Picker/Furniture are both present.
    const toolbar = target.querySelector(".floating-toolbar") as HTMLElement;
    const buttons = Array.from(toolbar.querySelectorAll(":scope > button.ft-btn"));
    const toggleIndex = buttons.findIndex((b) => b.querySelector(".mode-icon") !== null);
    const pickerIndex = buttons.findIndex((b) => (b as HTMLButtonElement).title === "Toggle item picker");
    const furnitureIndex = buttons.findIndex((b) => (b as HTMLButtonElement).title === "Toggle furniture library");

    expect(toggleIndex).toBeGreaterThanOrEqual(0);
    expect(pickerIndex).toBeGreaterThan(toggleIndex);
    expect(furnitureIndex).toBeGreaterThan(toggleIndex);

    unmount(app);
    target.remove();
  });

  it("does not shift the toggle button's index when switching to view mode", async () => {
    stubFetch404();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = await mountAndLoad(target);

    const toolbar = target.querySelector(".floating-toolbar") as HTMLElement;
    const indexOfToggle = () =>
      Array.from(toolbar.querySelectorAll(":scope > button.ft-btn")).findIndex(
        (b) => b.querySelector(".mode-icon") !== null,
      );

    const editModeIndex = indexOfToggle();
    const toggleBtn = Array.from(toolbar.querySelectorAll(":scope > button.ft-btn")).find(
      (b) => b.querySelector(".mode-icon") !== null,
    ) as HTMLButtonElement;
    toggleBtn.click();
    flushSync();

    expect(indexOfToggle()).toBe(editModeIndex);

    unmount(app);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -w @myhome/editor -- test/App.toolbarOrder.test.ts`
Expected: FAIL — Picker/Furniture buttons currently precede the toggle button in edit mode.

- [ ] **Step 3: Reorder the toolbar markup in App.svelte**

Replace the block from the `LayersDropdown` through the toggle button (lines 1344-1368):

```svelte
              <LayersDropdown {activeLayers} ontoggle={toggleLayer} popoverAlign="left" variant="toolbar" />
              <div class="ft-sep"></div>
              <button
                class="ft-btn"
                class:active={viewMode}
                title={viewMode ? $_('app.floatingToolbar.switchToEditMode') : $_('app.floatingToolbar.switchToViewMode')}
                onclick={toggleViewMode}
              ><span class="mode-icon" class:crossed={viewMode}>✏️</span> <span class="ft-label">{viewMode ? $_('app.floatingToolbar.viewMode') : $_('app.floatingToolbar.editMode')}</span></button>
              {#if !viewMode}
                <button
                  class="ft-btn"
                  class:active={pickerOpen}
                  disabled={pickerLayers.length === 0}
                  bind:this={pickerTriggerEl}
                  title={$_('app.floatingToolbar.togglePicker')}
                  onclick={() => { pickerOpen = !pickerOpen; }}
                >📋 <span class="ft-label">{$_('app.floatingToolbar.picker')}</span></button>
                <button
                  class="ft-btn"
                  class:active={furnitureLibraryOpen}
                  bind:this={furnitureTriggerEl}
                  title={$_('app.floatingToolbar.toggleFurniture')}
                  onclick={() => { furnitureLibraryOpen = !furnitureLibraryOpen; }}
                >🪑 <span class="ft-label">{$_('app.floatingToolbar.furniture')}</span></button>
              {/if}
```

(This is the same set of buttons as before — only the toggle button block has moved from after the `{#if !viewMode}...{/if}` group to before it. The `Save` button and everything after stays exactly where it was, immediately following this block.)

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -w @myhome/editor -- test/App.toolbarOrder.test.ts`
Expected: PASS

- [ ] **Step 5: Run the full editor test suite to check for regressions**

Run: `npm test -w @myhome/editor`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/test/App.toolbarOrder.test.ts
git commit -m "fix(floorplan): keep Edit/View toggle in a stable toolbar position"
```

---

## Final check

- [ ] **Run the full monorepo test suite once more from the repo root**

Run: `npm test -w @myhome/geometry && npm test -w @myhome/editor`
Expected: PASS, no regressions across all 6 tasks.

- [ ] **Manual browser check**

Per Task 4 Step 7 and the design spec's Testing section: items 3 (mobile DnD) and 5/6... (toolbar stability) benefit from a real-device or DevTools-touch-emulation check, since jsdom can't simulate actual touch-scroll hijacking or visually confirm the toolbar doesn't jump. Do this after all tasks are merged.
