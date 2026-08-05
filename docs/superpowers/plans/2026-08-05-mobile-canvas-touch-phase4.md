# Mobile Responsiveness Phase 4: Canvas Touch Gestures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the floor-plan canvas's draw/select/drag interactions work via touch (matching mouse behavior exactly), and add two-finger pan + pinch-to-zoom as a touch-only replacement for middle-click-drag/space-drag panning and scroll-wheel zooming, neither of which exist on touch.

**Architecture:** `Canvas.svelte`'s own `<svg>` event bindings and all four downstream drag-handle components (`SelectionHandles`, `OpeningShape`, `FurnitureShape`, `FurnitureHandles`) convert from `MouseEvent`-based (`onmousedown`/`onmousemove`/`onmouseup`) to `PointerEvent`-based (`onpointerdown`/`onpointermove`/`onpointerup`) bindings — Pointer Events unify mouse and touch input, so this conversion alone makes drawing, selecting, and dragging work identically via touch with no new code paths. A new multi-pointer gesture tracker inside `Canvas.svelte` adds 2-finger pan/pinch-zoom, which has no mouse equivalent to convert (pure addition). `App.svelte`'s single `svelte:window onmouseup` (which ends every in-progress drag, regardless of type) becomes `onpointerup`. This is spec Phase 4 of `docs/superpowers/specs/2026-08-05-mobile-responsive-audit-design.md`.

**Tech Stack:** Svelte 5, vitest (jsdom). Unlike Phases 2-3's CSS-only work, this phase's logic **is** meaningfully unit-testable in jsdom — `PointerEvent` construction, dispatch, and the resulting callback invocations are plain JS/DOM behavior that jsdom supports fully (no layout or `@media` evaluation required). Only the very last task (real touch-hardware gesture feel) needs a real browser.

## Global Constraints

- Every drag-related event listener conversion is a straight swap: `onmousedown`→`onpointerdown`, `onmousemove`→`onpointermove`, `onmouseup`→`onpointerup`. No `setPointerCapture` calls are added anywhere in this phase — none of the converted listeners are scoped to a small element with page-wide drag continuation the way the pin/badge overlays are; they're already either bound directly to `window`/the full-size `<svg>` (which receives events regardless of capture) or forwarded through props to code that behaves identically for `PointerEvent` and `MouseEvent` (see Task 2).
- `PointerEvent` extends `MouseEvent` in the DOM type hierarchy, so any prop/parameter still typed `MouseEvent` continues to compile and behave correctly if a `PointerEvent` flows through it (structural subtyping — a more specific type satisfies a less specific one). This plan still updates type annotations to `PointerEvent` wherever the annotation is attached to a listener that changes from `onmousedown` to `onpointerdown`, purely for documentation accuracy (a reader shouldn't see `MouseEvent` and wrongly conclude "doesn't fire for touch") — never because it's required for correctness.
- Don't rename any prop or handler function (`onbodymousedown`, `onmovefurniturestart`, `handleMoveFurnitureStart`, etc. keep their existing names even though the DOM event they originate from is no longer literally a `mousedown`) — only the DOM attribute bound in the template and the event parameter's declared type change. Renaming would touch many more call sites for zero behavioral benefit.
- Desktop mouse behavior must be pixel-identical after this phase — every existing mouse-driven test (click-to-select, click-to-place, middle-click pan, wheel zoom, double-click chain-end) must keep passing unmodified in its *assertions*, only its event-dispatch calls change from `MouseEvent`/`mouse*` to `PointerEvent`/`pointer*`.
- **Task ordering note discovered during planning:** `Canvas.svelte`'s own SVG-level event bindings and the four drag-handle components' bindings cannot be converted in separate, independently-green tasks the way Phase 1's per-module table tasks were. `Canvas.test.ts`'s `"notifies on endpoint drag start, pointer move, and drag end"` test dispatches its initial `mousedown` on `circle.handle` (rendered by `SelectionHandles.svelte`) and its subsequent `mousemove`/`mouseup` directly on `svg.canvas` (`Canvas.svelte`'s own binding) — one continuous interaction spanning both components. Converting either component alone leaves that test failing no matter which event types are dispatched. Task 1 below therefore converts `Canvas.svelte` and all four drag-handle components together.

---

### Task 1: Convert `Canvas.svelte` and all four drag-handle components to Pointer Events

**Files:**
- Modify: `packages/editor/src/lib/components/Canvas.svelte`
- Modify: `packages/editor/src/lib/components/SelectionHandles.svelte:15,34,41`
- Modify: `packages/editor/src/lib/components/OpeningShape.svelte:22,148,157`
- Modify: `packages/editor/src/lib/components/FurnitureShape.svelte:23,35,46`
- Modify: `packages/editor/src/lib/components/FurnitureHandles.svelte:17,18,54,59,73,83`
- Modify: `packages/editor/test/Canvas.test.ts`
- Modify: `packages/editor/test/FurnitureHandles.test.ts`

**Interfaces:**
- Produces: `<svg class="canvas">` now listens for `onpointerdown`/`onpointermove`/`onpointerup` instead of `onmousedown`/`onmousemove`/`onmouseup`. `onclick`, `ondblclick`, `onwheel` are unchanged. `SelectionHandles.ondragstart`, `OpeningShape.ondraghandlestart`, `FurnitureShape.onbodymousedown`, `FurnitureHandles.onresizestart`/`onrotatestart` are all now typed to receive `PointerEvent` and bound via `onpointerdown`. All existing props on `Canvas` (`onpan`, `onzoom`, `onpointermove` — the semantic world-cursor-position prop, unrelated to the DOM attribute of the same name — `ondragstart`, `ondragend`) keep their exact same call signatures and timing relative to mouse input; touch input now triggers the same calls. Task 2 (`App.svelte`) consumes the `PointerEvent`-carrying props produced here.

- [ ] **Step 1: Update the failing tests**

In `packages/editor/test/Canvas.test.ts`, replace the `"notifies on endpoint drag start, pointer move, and drag end"` test's body (lines 168-211) — every event dispatch converts, since both the handle (Task 1 converts `SelectionHandles`) and the canvas (Task 1 converts `Canvas`) change together:

```ts
  it("notifies on endpoint drag start, pointer move, and drag end", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    const floor = createSampleFloor();
    const events: string[] = [];
    let dragStartPoint: Point | null = null;
    let lastPointerWorld: Point | null = null;

    app = mount(Canvas, {
      target,
      props: {
        floor,
        viewport: { ...DEFAULT_VIEWPORT },
        width: 800,
        height: 600,
        selectedId: "wall-1",
        onpointermove: (p: Point) => {
          lastPointerWorld = p;
          events.push("move");
        },
        ondragstart: (p: Point) => {
          dragStartPoint = p;
          events.push("dragstart");
        },
        ondragend: () => events.push("dragend"),
      },
    });
    flushSync();

    const handle = target.querySelectorAll("circle.handle")[0]!;
    handle.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, pointerId: 1 }));
    flushSync();
    expect(dragStartPoint).toEqual({ x: 0, y: 0 });

    const svg = target.querySelector("svg.canvas")!;
    svg.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, pointerId: 1, clientX: 410, clientY: 300 }));
    flushSync();
    expect(lastPointerWorld).toEqual({ x: 0.1, y: 0 });

    svg.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, pointerId: 1 }));
    flushSync();
    expect(events).toEqual(["dragstart", "move", "dragend"]);
  });
```

Replace the `"middle-mouse drag reports pan deltas instead of pointer moves"` test's two dispatch lines (lines 237-242):

```ts
    const svg = target.querySelector("svg.canvas")!;
    svg.dispatchEvent(
      new PointerEvent("pointerdown", { bubbles: true, pointerId: 1, button: 1, clientX: 100, clientY: 100 }),
    );
    svg.dispatchEvent(
      new PointerEvent("pointermove", { bubbles: true, pointerId: 1, button: 1, clientX: 120, clientY: 90 }),
    );
```

In `packages/editor/test/FurnitureHandles.test.ts`, replace the two `mousedown`-dispatching tests (lines 47-66):

```ts
  it("calls onresizestart when a corner handle is pointerdown'd", () => {
    const onresizestart = vi.fn();
    const object = makeSofa();
    setup({ object, viewport: VP, onresizestart });
    const handle = svg.querySelector("rect.corner-handle")!;
    handle.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, pointerId: 1 }));
    expect(onresizestart).toHaveBeenCalled();
    const [id, corner] = onresizestart.mock.calls[0];
    expect(id).toBe("f1");
    expect(typeof corner).toBe("string");
  });

  it("calls onrotatestart when the rotate handle is pointerdown'd", () => {
    const onrotatestart = vi.fn();
    const object = makeSofa();
    setup({ object, viewport: VP, onrotatestart });
    const handle = svg.querySelector("circle.rotate-handle")!;
    handle.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, pointerId: 1 }));
    expect(onrotatestart).toHaveBeenCalledWith("f1", expect.any(PointerEvent));
  });
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm test -w @myhome/editor -- Canvas FurnitureHandles --run`
Expected: FAIL — none of the production files are converted yet, so the dispatched `PointerEvent`s never reach any handler.

- [ ] **Step 3: Convert `Canvas.svelte`**

Replace the four handler functions (lines 120-153):

```ts
  function toWorld(event: PointerEvent): Point {
    const rect = (event.currentTarget as SVGSVGElement).getBoundingClientRect();
    return {
      x: (event.clientX - rect.left - viewport.panX) / viewport.zoom,
      y: (event.clientY - rect.top - viewport.panY) / viewport.zoom,
    };
  }

  function handlePointerDown(event: PointerEvent): void {
    if (event.button === 1 || (event.button === 0 && spacePressed)) {
      event.preventDefault();
      panState = { x: event.clientX, y: event.clientY };
      suppressNextClick = true;
    }
  }

  function handlePointerMove(event: PointerEvent): void {
    if (panState) {
      const dx = event.clientX - panState.x;
      const dy = event.clientY - panState.y;
      onpan?.(dx, dy);
      panState = { x: event.clientX, y: event.clientY };
      return;
    }
    onpointermove?.(toWorld(event));
  }

  function handlePointerUp(): void {
    const wasPanning = panState !== null;
    panState = null;
    if (!wasPanning) {
      ondragend?.();
    }
  }
```

Replace the `handleDragStart` function (lines 205-208):

```ts
  function handleDragStart(point: Point, event: PointerEvent): void {
    event.stopPropagation();
    ondragstart?.(point);
  }
```

Replace the `<svg>` opening tag (lines 211-221):

```svelte
<svg
  {width}
  {height}
  class="canvas"
  onclick={handleClick}
  onpointerdown={handlePointerDown}
  onpointermove={handlePointerMove}
  onpointerup={handlePointerUp}
  ondblclick={() => ondblclick?.()}
  onwheel={handleWheel}
>
```

In the `<style>` block, update `.canvas` to add `touch-action: none`:

```css
  .canvas {
    background: var(--canvas-bg);
    display: block;
    touch-action: none;
  }
```

(Without this, a real mobile browser reserves multi-touch gestures over the canvas for native page pinch-zoom/scroll, so they'd never reach the pointer handlers added in Task 3 — jsdom doesn't evaluate this at all, so it has no effect on this task's own tests, but it's foundational for Task 3/4.)

- [ ] **Step 4: Convert `SelectionHandles.svelte`**

Change the `ondragstart` prop type (line 15):
```ts
    ondragstart: (point: Point, event: PointerEvent) => void;
```

Change both handle bindings (lines 34, 41):
```svelte
    onpointerdown={(e) => ondragstart(wall.start, e)}
```
```svelte
    onpointerdown={(e) => ondragstart(wall.end, e)}
```

- [ ] **Step 5: Convert `OpeningShape.svelte`**

Change the `ondraghandlestart` prop type (line 22):
```ts
    ondraghandlestart?: (openingId: string, side: "start" | "end", event: PointerEvent) => void;
```

Change both handle bindings (lines 148, 157):
```svelte
      onpointerdown={(e) => { e.stopPropagation(); ondraghandlestart?.(opening.id, "start", e); }}
```
```svelte
      onpointerdown={(e) => { e.stopPropagation(); ondraghandlestart?.(opening.id, "end", e); }}
```

- [ ] **Step 6: Convert `FurnitureShape.svelte`**

Change the `onbodymousedown` prop type (line 23):
```ts
    onbodymousedown?: (id: string, e: PointerEvent) => void;
```

Change `handleMousedown`'s parameter type (line 35):
```ts
  function handleMousedown(e: PointerEvent) {
```

Change the body binding (line 46):
```svelte
  onpointerdown={handleMousedown}
```

- [ ] **Step 7: Convert `FurnitureHandles.svelte`**

Change both prop types (lines 17-18):
```ts
    onresizestart?: (id: string, corner: Corner, e: PointerEvent) => void;
    onrotatestart?: (id: string, e: PointerEvent) => void;
```

Change both handler parameter types (lines 54, 59):
```ts
  function handleCornerDown(corner: Corner, e: PointerEvent) {
```
```ts
  function handleRotateDown(e: PointerEvent) {
```

Change both handle bindings (lines 73, 83):
```svelte
    onpointerdown={(e) => handleCornerDown(c.key, e)}
```
```svelte
  onpointerdown={handleRotateDown}
```

- [ ] **Step 8: Run the tests to verify they pass**

Run: `npm test -w @myhome/editor -- Canvas FurnitureHandles --run`
Expected: PASS (every test in both files, including the two converted in `Canvas.test.ts`, the two converted in `FurnitureHandles.test.ts`, and every untouched click/wheel/dblclick test in `Canvas.test.ts` — `SelectionHandles.test.ts` doesn't dispatch `mousedown` at all so it's unaffected; no `OpeningShape.test.ts` exists; `FurnitureShape.test.ts` only dispatches `click`, unaffected).

Run: `npm test -w @myhome/editor -- --run`
Expected: PASS (full suite).

- [ ] **Step 9: Commit**

```bash
git add packages/editor/src/lib/components/Canvas.svelte packages/editor/src/lib/components/SelectionHandles.svelte packages/editor/src/lib/components/OpeningShape.svelte packages/editor/src/lib/components/FurnitureShape.svelte packages/editor/src/lib/components/FurnitureHandles.svelte packages/editor/test/Canvas.test.ts packages/editor/test/FurnitureHandles.test.ts
git commit -m "feat(floor-plan): convert canvas draw/select/drag interactions to pointer events"
```

---

### Task 2: Convert `App.svelte`'s drag-continuation wiring

**Files:**
- Modify: `packages/editor/src/App.svelte:538,551,566,761`
- Modify: `packages/editor/test/App.test.ts`

**Interfaces:**
- Consumes: `FurnitureShape.onbodymousedown`, `FurnitureHandles.onresizestart`/`onrotatestart` now deliver `PointerEvent` (Task 1).
- Produces: no change to any function's behavior — `handleMoveFurnitureStart`/`handleResizeFurnitureStart`/`handleRotateFurnitureStart`'s bodies are untouched (they only use `.target`/`.clientX`/`.clientY`, all present identically on `PointerEvent`); only their declared parameter type changes, and the `svelte:window` listener that ends every drag switches from `mouseup` to `pointerup`.

- [ ] **Step 1: Update the failing tests**

In `packages/editor/test/App.test.ts`, every `new MouseEvent("mousedown"/"mousemove"/"mouseup", ...)` call becomes the equivalent `PointerEvent`. Run these three targeted replacements (safe: they only match the exact event-name string immediately following `new MouseEvent(`, so `"click"`/`"dblclick"` dispatches elsewhere in the same file are untouched):

```bash
sed -i 's/new MouseEvent("mousemove"/new PointerEvent("pointermove"/g' packages/editor/test/App.test.ts
sed -i 's/new MouseEvent("mousedown"/new PointerEvent("pointerdown"/g' packages/editor/test/App.test.ts
sed -i 's/new MouseEvent("mouseup"/new PointerEvent("pointerup"/g' packages/editor/test/App.test.ts
```

Every converted `PointerEvent(...)` call also needs a `pointerId` in its options object — `Canvas.svelte`'s single-pointer path (Task 1) doesn't branch on the exact id, but `activePointers` tracking added in Task 3 keys off it, so establish the convention here. Open the file and add `pointerId: 1,` as the first property inside every options object that was just converted (16 call sites — search for `PointerEvent(` after running the seds above to find them all). For example:

```ts
    svg.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, pointerId: 1, clientX: screen.x, clientY: screen.y }));
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm test -w @myhome/editor -- App --run`
Expected: FAIL — `Canvas.svelte` and the drag-handle components (converted in Task 1) already listen for pointer events, but `App.svelte`'s own `svelte:window onmouseup` still listens for `mouseup`, so drags started via the now-working `pointerdown` chain never get cleanly ended when the tests dispatch `pointerup`. The two endpoint-drag tests and the space-pan test fail without this task's `App.svelte` change; wall-drawing tests that only use `pointermove`-then-`click` sequences should already pass since `click` is unchanged.

- [ ] **Step 3: Convert the implementation**

In `packages/editor/src/App.svelte`, change the three handler signatures:

```ts
  function handleMoveFurnitureStart(id: string, e: PointerEvent): void {
```
```ts
  function handleResizeFurnitureStart(id: string, corner: string, _e: PointerEvent): void {
```
```ts
  function handleRotateFurnitureStart(id: string, _e: PointerEvent): void {
```

Change the `svelte:window` block:

```svelte
<svelte:window
  onkeydown={handleKeydown}
  onkeyup={handleKeyup}
  onblur={() => { spacePressed = false; }}
  onpointerup={() => { handleDragEnd(); endFurnitureDrag(); }}
/>
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test -w @myhome/editor -- App --run`
Expected: PASS

Run: `npm test -w @myhome/editor -- --run`
Expected: PASS (full suite).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/test/App.test.ts
git commit -m "feat(floor-plan): convert App drag-continuation wiring to pointer events"
```

---

### Task 3: Two-finger pan + pinch-zoom gesture tracker

**Files:**
- Modify: `packages/editor/src/lib/components/Canvas.svelte`
- Modify: `packages/editor/test/Canvas.test.ts`

**Interfaces:**
- Consumes: `handlePointerDown`/`handlePointerMove`/`handlePointerUp` from Task 1 (extended, not replaced).
- Produces: no new props — reuses the existing `onpan(dx, dy)` and `onzoom(screen, factor)` props exactly as middle-click-drag and wheel-zoom already do, so `App.svelte`'s `handlePan`/`handleZoom` (already wired) need no changes at all.

- [ ] **Step 1: Write the failing tests**

Append to `packages/editor/test/Canvas.test.ts`, inside the top-level `describe("Canvas", ...)` block (after the last existing `it(...)`, before the closing `});`):

```ts
  it("two active pointers report a pan delta and a zoom factor from their centroid/distance change", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    const floor = createSampleFloor();
    let panDelta: { dx: number; dy: number } | null = null;
    let zoomCall: { screen: Point; factor: number } | null = null;
    let moveCount = 0;

    app = mount(Canvas, {
      target,
      props: {
        floor,
        viewport: { ...DEFAULT_VIEWPORT },
        width: 800,
        height: 600,
        onpan: (dx: number, dy: number) => { panDelta = { dx, dy }; },
        onzoom: (screen: Point, factor: number) => { zoomCall = { screen, factor }; },
        onpointermove: () => moveCount++,
      },
    });
    flushSync();

    const svg = target.querySelector("svg.canvas")!;
    svg.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, pointerId: 1, clientX: 100, clientY: 100 }));
    svg.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, pointerId: 2, clientX: 300, clientY: 100 }));
    // centroid (200,100), distance 200
    svg.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, pointerId: 1, clientX: 150, clientY: 100 }));
    // pointer 1 moved to (150,100); pointer 2 unchanged at (300,100)
    // new centroid (225,100), new distance 150
    flushSync();

    expect(panDelta).toEqual({ dx: 25, dy: 0 }); // 225 - 200
    expect(zoomCall!.factor).toBe(0.75); // 150 / 200
    expect(zoomCall!.screen).toEqual({ x: 225, y: 100 }); // jsdom's default getBoundingClientRect is all-zero
    expect(moveCount).toBe(0); // single-pointer world-cursor reporting is suppressed during a 2-finger gesture

    svg.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, pointerId: 1 }));
    svg.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, pointerId: 2 }));
  });

  it("returns to single-pointer mode once a second pointer lifts", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    const floor = createSampleFloor();
    let moveCount = 0;

    app = mount(Canvas, {
      target,
      props: {
        floor,
        viewport: { ...DEFAULT_VIEWPORT },
        width: 800,
        height: 600,
        onpointermove: () => moveCount++,
      },
    });
    flushSync();

    const svg = target.querySelector("svg.canvas")!;
    svg.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, pointerId: 1, clientX: 100, clientY: 100 }));
    svg.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, pointerId: 2, clientX: 300, clientY: 100 }));
    svg.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, pointerId: 2 }));
    flushSync();

    // Back to a single active pointer (id 1) — its move should report a world position again.
    svg.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, pointerId: 1, clientX: 120, clientY: 110 }));
    flushSync();

    expect(moveCount).toBe(1);
  });
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm test -w @myhome/editor -- Canvas --run`
Expected: FAIL — `Canvas.svelte` has no multi-pointer tracking yet, so a second `pointerdown` doesn't change any behavior and the move handler falls through to the single-pointer `onpointermove?.(toWorld(event))` path, calling it once per move (failing the `moveCount === 0` assertion) with no `onpan`/`onzoom` calls at all.

- [ ] **Step 3: Implement the gesture tracker**

In `packages/editor/src/lib/components/Canvas.svelte`, add state and helpers after the existing `let panState = $state<Point | null>(null);` line and its neighboring `let` declarations:

```ts
  const activePointers = new Map<number, Point>();
  let gestureBase: { centroid: Point; distance: number } | null = null;

  function gesturePoints(): Point[] {
    return [...activePointers.values()].slice(0, 2);
  }

  function centroidOf(pts: Point[]): Point {
    return { x: (pts[0].x + pts[1].x) / 2, y: (pts[0].y + pts[1].y) / 2 };
  }

  function distanceOf(pts: Point[]): number {
    return Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
  }

  function rebaseGesture(): void {
    const pts = gesturePoints();
    gestureBase = pts.length >= 2 ? { centroid: centroidOf(pts), distance: distanceOf(pts) } : null;
  }
```

Replace `handlePointerDown` (from Task 1) with a version that tracks multiple pointers:

```ts
  function handlePointerDown(event: PointerEvent): void {
    activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (activePointers.size >= 2) {
      rebaseGesture();
      panState = null;
      suppressNextClick = true;
      return;
    }
    if (event.button === 1 || (event.button === 0 && spacePressed)) {
      event.preventDefault();
      panState = { x: event.clientX, y: event.clientY };
      suppressNextClick = true;
    }
  }
```

Replace `handlePointerMove`:

```ts
  function handlePointerMove(event: PointerEvent): void {
    if (activePointers.has(event.pointerId)) {
      activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    }
    if (activePointers.size >= 2) {
      const pts = gesturePoints();
      const centroid = centroidOf(pts);
      const dist = distanceOf(pts);
      if (gestureBase) {
        const dx = centroid.x - gestureBase.centroid.x;
        const dy = centroid.y - gestureBase.centroid.y;
        if (dx !== 0 || dy !== 0) onpan?.(dx, dy);
        if (gestureBase.distance > 0 && dist > 0) {
          const rect = (event.currentTarget as SVGSVGElement).getBoundingClientRect();
          onzoom?.({ x: centroid.x - rect.left, y: centroid.y - rect.top }, dist / gestureBase.distance);
        }
      }
      gestureBase = { centroid, distance: dist };
      return;
    }
    if (panState) {
      const dx = event.clientX - panState.x;
      const dy = event.clientY - panState.y;
      onpan?.(dx, dy);
      panState = { x: event.clientX, y: event.clientY };
      return;
    }
    onpointermove?.(toWorld(event));
  }
```

Replace `handlePointerUp` (it now needs the `event` parameter, to read `event.pointerId` — the `<svg onpointerup={handlePointerUp}>` binding from Task 1 already passes the event through, so no template change is needed):

```ts
  function handlePointerUp(event: PointerEvent): void {
    activePointers.delete(event.pointerId);
    rebaseGesture();
    const wasPanning = panState !== null;
    panState = null;
    if (!wasPanning) {
      ondragend?.();
    }
  }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test -w @myhome/editor -- Canvas --run`
Expected: PASS (all tests, including the two new ones and every pre-existing one — single-pointer behavior is a strict subset of the new `activePointers.size < 2` path, unchanged from Task 1).

- [ ] **Step 5: Run the full suite and typecheck**

Run: `npm test -w @myhome/editor -- --run`
Expected: PASS

Run: `npm run build -w @myhome/editor`
Expected: succeeds

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/Canvas.svelte packages/editor/test/Canvas.test.ts
git commit -m "feat(floor-plan): add two-finger pan and pinch-to-zoom to Canvas"
```

---

### Task 4: Real-browser verification

**Files:**
- None modified — verification-only, using the `webapp-testing` skill (Playwright), same isolated-instance recipe as Phases 1-3.

**Interfaces:**
- Consumes: all of Tasks 1-3.

- [ ] **Step 1: Start an isolated instance and open a demo home's floor plan**

Log in, create (or reuse) a "Demo home", navigate to `#/plan`.

- [ ] **Step 2: Verify touch drawing and selection**

Using a touch-enabled Playwright context (`hasTouch: true`), dispatch a `PointerEvent`-based tap-and-hold-drag sequence (Playwright's `page.touchscreen` API only covers taps/swipes, not the precise multi-pointer control this needs — drive it via `page.evaluate` dispatching real `PointerEvent`s with `pointerType: "touch"`, mirroring the vitest tests' event shapes but against the live DOM):

1. Select the Wall tool.
2. Dispatch `pointerdown`/`pointerup` (a tap) at two different canvas positions to draw one wall segment; assert a new `polygon.wall` appears.
3. Switch to the Select tool, tap the new wall to select it, assert `circle.handle` elements appear.
4. Dispatch `pointerdown` on a handle, `pointermove` to a new position, `pointerup`; assert the wall's polygon points changed.

- [ ] **Step 3: Verify two-finger pan and pinch-zoom**

1. Record `viewport.panX`/`panY`/`zoom` (read via `toolStore`/`viewportStore`'s exposed state, or infer from a wall's rendered screen position before/after).
2. Dispatch two simultaneous `pointerdown`s (distinct `pointerId`s) over the canvas, then `pointermove` both together by the same delta (pan) — assert the floor plan visually shifted (e.g. a wall's screen-space bounding box moved by the same delta).
3. Repeat with the two pointers moving apart (pinch out) — assert the floor plan visually scaled up (a wall's screen-space bounding box grew).
4. Take screenshots for the record.

- [ ] **Step 4: Verify furniture drag via touch**

1. Ensure at least one furniture object exists on the demo floor (place one via the Furniture Library panel if none pre-exist).
2. Tap it to select (assert `rect.corner-handle`/`circle.rotate-handle` appear).
3. `pointerdown` on the furniture body, `pointermove` to a new position, `pointerup`; assert the object's rendered position changed.

- [ ] **Step 5: Fix any real issues found**

Same pattern as every prior phase's final task — diagnose with the systematic-debugging skill, commit fixes individually.

- [ ] **Step 6: Clean up the isolated instance**

Revert `vite.config.ts`, kill only the PIDs started in Step 1, remove the temporary `DATA_DIR`.
