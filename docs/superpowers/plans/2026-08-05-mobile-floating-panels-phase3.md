# Mobile Responsiveness Phase 3: Floating Panels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the floor-plan editor's floating panels (floating toolbar, Room panel, Item picker, Furniture library) touch-draggable on desktop-mode, and turn them into a fixed bottom icon bar + docked bottom sheets below 480px instead of small free-floating boxes that would overlap on a phone screen.

**Architecture:** Two independent changes. (1) The shared `floatingDrag.svelte.ts` helper converts from `MouseEvent`/`window.mousemove`/`mouseup` to `PointerEvent`/`window.pointermove`/`pointerup`, and every call site's drag-handle switches `onmousedown` to `onpointerdown` — this alone makes free-floating drag-to-reposition work on touch at any viewport width. (2) New `@media (max-width: 480px)` CSS in `App.svelte` (for the wrapper positioning) and in each of the three panel components (for their own fixed pixel width) converts the floating-toolbar to a fixed bottom bar and the three panels to bottom sheets docked above it. This is spec Phase 3 of `docs/superpowers/specs/2026-08-05-mobile-responsive-audit-design.md`.

**Tech Stack:** Svelte 5, vitest (jsdom). Same jsdom constraint as Phase 2: `@media` queries aren't evaluated by jsdom, so the bottom-sheet/bottom-bar layout itself can only be verified in a real browser (final Playwright task). The Pointer Events conversion (Tasks 1-2), by contrast, **is** meaningfully unit-testable, since it's plain JS/TS logic, not CSS.

## Global Constraints

- Every new `@media` block uses the literal value `480px` with a `/* --bp-mobile */` comment, per this project's breakpoint convention (`packages/editor/src/lib/theme.css:53`).
- `floatingDrag.svelte.ts`'s converted `startDrag` does **not** call `setPointerCapture`, unlike the pin/badge overlay components (`ChoreOverlay.svelte` etc.) it otherwise mirrors. Reason: `onMove`/`onUp` are attached to `window`, not to the drag-handle element itself, so pointer capture (which exists to keep an *element-scoped* listener receiving events once the pointer leaves its bounds) has no effect here — `window` listeners already receive every pointer event regardless of capture state. Calling `setPointerCapture` anyway would also break the existing `floatingDrag.test.ts`, since jsdom does not implement that method at all (confirmed: `typeof element.setPointerCapture === "undefined"` in this project's jsdom version) and the test constructs a plain jsdom element as the event's `currentTarget`.
- Don't change any panel's props, data flow, or non-drag-related markup — every change in Tasks 1-6 is either an event-type swap (Mouse→Pointer) or additive CSS.

---

### Task 1: Convert `floatingDrag.svelte.ts` to Pointer Events

**Files:**
- Modify: `packages/editor/src/lib/floatingDrag.svelte.ts`
- Modify: `packages/editor/test/floatingDrag.test.ts`

**Interfaces:**
- Produces: `createFloatingDrag(selector).startDrag` now takes a `PointerEvent` instead of a `MouseEvent`. Return shape (`{ pos, startDrag }`) is unchanged. Tasks 2-6 depend on this signature change.

- [ ] **Step 1: Update the existing tests to construct `PointerEvent`s**

Replace the full contents of `packages/editor/test/floatingDrag.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { createFloatingDrag } from "../src/lib/floatingDrag.svelte";

function setUpDom(): { container: HTMLElement; panel: HTMLElement } {
  const container = document.createElement("div");
  container.style.cssText = "position:relative;width:800px;height:600px;";
  document.body.appendChild(container);
  const panel = document.createElement("div");
  panel.className = "test-panel";
  panel.style.cssText = "width:100px;height:50px;";
  container.appendChild(panel);
  container.getBoundingClientRect = () => ({ left: 0, top: 0, width: 800, height: 600, right: 800, bottom: 600, x: 0, y: 0, toJSON() {} });
  // Positioned away from the container's bottom-right edge so a normal-sized
  // drag delta doesn't accidentally land on the clamp boundary.
  panel.getBoundingClientRect = () => ({ left: 300, top: 200, width: 100, height: 50, right: 400, bottom: 250, x: 300, y: 200, toJSON() {} });
  return { container, panel };
}

describe("createFloatingDrag", () => {
  it("pos starts null", () => {
    const drag = createFloatingDrag(".test-panel");
    expect(drag.pos).toBeNull();
  });

  it("dragging moves pos by the pointer delta, clamped to the container bounds", () => {
    const { container, panel } = setUpDom();
    const drag = createFloatingDrag(".test-panel");
    const pointerdown = new PointerEvent("pointerdown", { bubbles: true, clientX: 350, clientY: 225 });
    Object.defineProperty(pointerdown, "currentTarget", { value: panel });
    drag.startDrag(pointerdown);
    window.dispatchEvent(new PointerEvent("pointermove", { clientX: 370, clientY: 245 }));
    // initX=300, initY=200, delta=(20,20) -> (320, 220), well within the 800x600 container.
    expect(drag.pos).toEqual({ x: 320, y: 220 });
    window.dispatchEvent(new PointerEvent("pointerup"));
    panel.remove();
    container.remove();
  });

  it("clamps to the container's bottom-right when dragged past it", () => {
    const { container, panel } = setUpDom();
    const drag = createFloatingDrag(".test-panel");
    const pointerdown = new PointerEvent("pointerdown", { bubbles: true, clientX: 350, clientY: 225 });
    Object.defineProperty(pointerdown, "currentTarget", { value: panel });
    drag.startDrag(pointerdown);
    window.dispatchEvent(new PointerEvent("pointermove", { clientX: 5000, clientY: 5000 }));
    // container width(800) - panel width(100) = 700 max x; height(600) - 50 = 550 max y.
    expect(drag.pos).toEqual({ x: 700, y: 550 });
    window.dispatchEvent(new PointerEvent("pointerup"));
    panel.remove();
    container.remove();
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm test -w @myhome/editor -- floatingDrag --run`
Expected: FAIL — `startDrag`'s parameter type is still `MouseEvent` and the implementation still listens for `mousemove`/`mouseup`, so dispatching `PointerEvent("pointermove"/"pointerup")` never reaches it and `drag.pos` stays `null`.

- [ ] **Step 3: Convert the implementation**

Replace the full contents of `packages/editor/src/lib/floatingDrag.svelte.ts`:

```ts
export function createFloatingDrag(selector: string) {
  let pos = $state<{ x: number; y: number } | null>(null);

  function startDrag(e: PointerEvent): void {
    e.preventDefault();
    const el = (e.currentTarget as HTMLElement).closest(selector) as HTMLElement;
    const rect = el.getBoundingClientRect();
    const canvasRect = (el.parentElement as HTMLElement).getBoundingClientRect();
    const initX = rect.left - canvasRect.left;
    const initY = rect.top - canvasRect.top;
    const startX = e.clientX;
    const startY = e.clientY;
    function onMove(me: PointerEvent): void {
      pos = {
        x: Math.max(0, Math.min(canvasRect.width - rect.width, initX + me.clientX - startX)),
        y: Math.max(0, Math.min(canvasRect.height - rect.height, initY + me.clientY - startY)),
      };
    }
    function onUp(): void {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    }
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  }

  return {
    get pos() { return pos; },
    startDrag,
  };
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test -w @myhome/editor -- floatingDrag --run`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/floatingDrag.svelte.ts packages/editor/test/floatingDrag.test.ts
git commit -m "feat(floor-plan): convert floatingDrag to Pointer Events for touch support"
```

---

### Task 2: Wire `onpointerdown` on all four drag handles

**Files:**
- Modify: `packages/editor/src/lib/components/RoomPanel.svelte:9,15,47`
- Modify: `packages/editor/src/lib/components/ItemPickerPanel.svelte:22,80`
- Modify: `packages/editor/src/lib/components/FurnitureLibraryPanel.svelte:10,44`
- Modify: `packages/editor/src/App.svelte:1140`

**Interfaces:**
- Consumes: `createFloatingDrag(...).startDrag` now typed `(e: PointerEvent) => void` (Task 1).
- Produces: all four `onstartdrag` props are now typed `(e: PointerEvent) => void`; no change to any other prop.

- [ ] **Step 1: `RoomPanel.svelte`**

Change line 15 (prop type):
```ts
    onstartdrag?: (e: PointerEvent) => void;
```

Change line 47 (event binding):
```svelte
      <div class="drag-handle" onpointerdown={onstartdrag} title={$_('floorPlan.itemPicker.dragToReposition')}>⠿</div>
```

- [ ] **Step 2: `ItemPickerPanel.svelte`**

Change the `onstartdrag?: (e: MouseEvent) => void;` prop type to `onstartdrag?: (e: PointerEvent) => void;`.

Change `<div class="drag-handle" onmousedown={onstartdrag} title={$_('floorPlan.itemPicker.dragToReposition')}>⠿</div>` to use `onpointerdown={onstartdrag}` instead of `onmousedown={onstartdrag}`.

- [ ] **Step 3: `FurnitureLibraryPanel.svelte`**

Change line 10's prop type:
```ts
  let { onstartdrag, ondismiss }: { onstartdrag?: (e: PointerEvent) => void; ondismiss?: () => void } = $props();
```

Change line 44's event binding to `onpointerdown={onstartdrag}` instead of `onmousedown={onstartdrag}`.

- [ ] **Step 4: `App.svelte`**

Change line 1140's floating-toolbar handle:
```svelte
              <div class="ft-handle" onpointerdown={ftDrag.startDrag} title={$_('floorPlan.itemPicker.dragToReposition')}>⠿</div>
```

- [ ] **Step 5: Typecheck and run the full test suite**

Run: `npm run typecheck -w @myhome/editor`
Expected: PASS (no type errors — `ftDrag.startDrag`/`rpDrag.startDrag`/`ipDrag.startDrag`/`fpDrag.startDrag` are all `(e: PointerEvent) => void` after Task 1, matching every call site's now-updated prop type).

Run: `npm test -w @myhome/editor -- --run`
Expected: PASS — `RoomPanel.test.ts:42-49`'s two tests only check for the `.drag-handle` element's *presence* based on whether `onstartdrag` is provided, not which DOM event attribute it's bound to, so they're unaffected by the `onmousedown`→`onpointerdown` swap.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/RoomPanel.svelte packages/editor/src/lib/components/ItemPickerPanel.svelte packages/editor/src/lib/components/FurnitureLibraryPanel.svelte packages/editor/src/App.svelte
git commit -m "feat(floor-plan): switch all floating-panel drag handles to pointer events"
```

---

### Task 3: Floating toolbar → fixed bottom bar below 480px

**Files:**
- Modify: `packages/editor/src/App.svelte:1464-1508` (`.floating-toolbar`, `.ft-handle`, `.ft-btn`, `.ft-label`, `.ft-sep` rules)

**Interfaces:**
- None — CSS-only. The toolbar's markup, buttons, and click handlers are all unchanged; only its position/layout/icon-vs-label visibility changes at the breakpoint.

- [ ] **Step 1: Add the media query**

In `packages/editor/src/App.svelte`, after the existing `.ft-sep { height: 1px; background: var(--border); flex-shrink: 0; margin: 2px 0; }` rule (around line 1508, verify against current file), add:

```css

  @media (max-width: 480px) { /* --bp-mobile */
    .floating-toolbar {
      position: fixed;
      left: 0; right: 0; bottom: 0; top: auto;
      transform: none !important;
      width: 100%;
      height: 48px;
      flex-direction: row;
      align-items: center;
      gap: 0;
      border-radius: 0;
      border-left: none; border-right: none; border-bottom: none;
      overflow-x: auto;
      z-index: 30;
    }
    .ft-handle { display: none; }
    .ft-btn {
      width: auto;
      flex-direction: column;
      gap: 1px;
      font-size: 10px;
    }
    .ft-label { font-size: 8px; }
    .ft-sep { width: 1px; height: 24px; margin: 0 2px; }
  }
```

Note: this keeps `.ft-label` visible (shrunk to 8px, stacked under the icon) rather than hiding it outright — with 14 buttons the bar will need `overflow-x: auto` regardless of whether labels show, so there's no width-budget reason to drop them, and keeping them preserves discoverability for tools users don't touch often (wall/divider/door/window/delete). If Task 7's real-browser check shows this reads as too cramped, drop `.ft-label` at this breakpoint instead (`display: none`) as a one-line follow-up — call this out explicitly when reporting Task 7's results.

- [ ] **Step 2: Verify**

Run: `grep -n "floating-toolbar {" -A3 packages/editor/src/App.svelte`
Expected: two rules now exist — the base rule and the one inside the new `@media (max-width: 480px)` block.

- [ ] **Step 3: Run the full frontend test suite to confirm no regression**

Run: `npm test -w @myhome/editor -- --run`
Expected: PASS — no existing test asserts on `.floating-toolbar`'s CSS properties (confirmed: no `App.test.ts` assertion references `.floating-toolbar`'s style/position), only on button presence/click behavior, which this task doesn't touch.

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/App.svelte
git commit -m "feat(floor-plan): floating toolbar becomes a fixed bottom bar below 480px"
```

---

### Task 4: Room panel → bottom sheet below 480px

**Files:**
- Modify: `packages/editor/src/App.svelte:1459-1462` (`.room-panel-float` rule)
- Modify: `packages/editor/src/lib/components/RoomPanel.svelte:87-98` (`.room-panel` rule)

**Interfaces:**
- None — CSS-only.

- [ ] **Step 1: Add the media query in `App.svelte`**

After the `.room-panel-float { position: absolute; right: 120px; top: 50%; transform: translateY(-50%); z-index: 21; }` rule, add:

```css

  @media (max-width: 480px) { /* --bp-mobile */
    .room-panel-float {
      position: fixed;
      left: 0; right: 0; bottom: 48px; top: auto;
      transform: none !important;
      width: 100%;
      max-height: 45vh;
      z-index: 26;
    }
  }
```

(`bottom: 48px` docks it directly above the fixed toolbar bar added in Task 3, whose mobile height is also `48px` — these two values must stay in sync if either changes later.)

- [ ] **Step 2: Add the media query in `RoomPanel.svelte`**

After the `.room-panel { width: 200px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); box-shadow: var(--shadow-md); padding: var(--space-3); display: flex; flex-direction: column; gap: var(--space-3); overflow-y: auto; }` rule, add:

```css

  @media (max-width: 480px) { /* --bp-mobile */
    .room-panel {
      width: 100%;
      height: 100%;
      border-radius: 0;
      border-left: none; border-right: none; border-bottom: none;
    }
  }
```

- [ ] **Step 3: Verify**

Run: `grep -n "room-panel-float {" -A3 packages/editor/src/App.svelte && grep -n "\.room-panel {" -A3 packages/editor/src/lib/components/RoomPanel.svelte`
Expected: two rules each (base + the new `@media` block).

- [ ] **Step 4: Run the full frontend test suite to confirm no regression**

Run: `npm test -w @myhome/editor -- --run`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/src/lib/components/RoomPanel.svelte
git commit -m "feat(floor-plan): room panel becomes a bottom sheet below 480px"
```

---

### Task 5: Item picker panel → bottom sheet below 480px

**Files:**
- Modify: `packages/editor/src/App.svelte:1439-1447` (`.picker-float` rule)
- Modify: `packages/editor/src/lib/components/ItemPickerPanel.svelte` (`.panel` rule, around line 149)

**Interfaces:**
- None — CSS-only.

- [ ] **Step 1: Add the media query in `App.svelte`**

After the `.picker-float { position: absolute; right: 120px; top: 50%; transform: translateY(-50%); max-height: min(460px, calc(100% - 16px)); display: flex; flex-direction: column; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); box-shadow: var(--shadow-md); z-index: 20; overflow: hidden; }` rule, add:

```css

  @media (max-width: 480px) { /* --bp-mobile */
    .picker-float {
      position: fixed;
      left: 0; right: 0; bottom: 48px; top: auto;
      transform: none !important;
      width: 100%;
      max-height: 45vh;
      border-radius: 0;
      border-left: none; border-right: none; border-bottom: none;
      z-index: 26;
    }
  }
```

- [ ] **Step 2: Add the media query in `ItemPickerPanel.svelte`**

After the `.panel { width: 220px; display: flex; flex-direction: column; font-size: 12px; color: var(--text-muted); overflow: hidden; }` rule, add:

```css

  @media (max-width: 480px) { /* --bp-mobile */
    .panel { width: 100%; }
  }
```

- [ ] **Step 3: Verify**

Run: `grep -n "picker-float {" -A3 packages/editor/src/App.svelte && grep -n "\.panel {" -A3 packages/editor/src/lib/components/ItemPickerPanel.svelte`
Expected: two rules each.

- [ ] **Step 4: Run the full frontend test suite to confirm no regression**

Run: `npm test -w @myhome/editor -- --run`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/src/lib/components/ItemPickerPanel.svelte
git commit -m "feat(floor-plan): item picker panel becomes a bottom sheet below 480px"
```

---

### Task 6: Furniture library panel → bottom sheet below 480px

**Files:**
- Modify: `packages/editor/src/App.svelte:1449-1457` (`.furniture-float` rule)
- Modify: `packages/editor/src/lib/components/FurnitureLibraryPanel.svelte` (`.furniture-panel` rule, around line 87)

**Interfaces:**
- None — CSS-only.

- [ ] **Step 1: Add the media query in `App.svelte`**

After the `.furniture-float { position: absolute; right: 120px; top: 50%; transform: translateY(-50%); max-height: min(460px, calc(100% - 16px)); display: flex; flex-direction: column; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 0; box-shadow: var(--shadow-md); z-index: 20; overflow: hidden; }` rule, add:

```css

  @media (max-width: 480px) { /* --bp-mobile */
    .furniture-float {
      position: fixed;
      left: 0; right: 0; bottom: 48px; top: auto;
      transform: none !important;
      width: 100%;
      max-height: 45vh;
      border-radius: 0;
      border-left: none; border-right: none; border-bottom: none;
      z-index: 26;
    }
  }
```

- [ ] **Step 2: Add the media query in `FurnitureLibraryPanel.svelte`**

After the `.furniture-panel { width: 200px; display: flex; flex-direction: column; overflow: hidden; }` rule, add:

```css

  @media (max-width: 480px) { /* --bp-mobile */
    .furniture-panel { width: 100%; }
  }
```

- [ ] **Step 3: Verify**

Run: `grep -n "furniture-float {" -A3 packages/editor/src/App.svelte && grep -n "\.furniture-panel {" -A3 packages/editor/src/lib/components/FurnitureLibraryPanel.svelte`
Expected: two rules each.

- [ ] **Step 4: Run the full frontend test suite to confirm no regression**

Run: `npm test -w @myhome/editor -- --run`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/src/lib/components/FurnitureLibraryPanel.svelte
git commit -m "feat(floor-plan): furniture library panel becomes a bottom sheet below 480px"
```

---

### Task 7: Real-browser verification

**Files:**
- None modified — verification-only, using the `webapp-testing` skill (Playwright) against an isolated instance, same recipe as Phases 1-2 (fresh `DATA_DIR`, alternate backend/frontend ports, temporary `vite.config.ts` proxy edit reverted afterward).

**Interfaces:**
- Consumes: all CSS from Tasks 3-6, the Pointer Events conversion from Tasks 1-2.

- [ ] **Step 1: Start an isolated instance and open a demo home's floor plan**

Log in, create (or reuse) a "Demo home" (pre-seeded with a floor plan), navigate to `#/plan`.

- [ ] **Step 2: Verify the toolbar at 375×667**

1. Set viewport to 375×667, `hasTouch: true`.
2. Assert `.floating-toolbar`'s bounding box: `bottom` edge at the viewport's bottom, full width, height ~48px.
3. Assert `.ft-handle` has `display: none`.
4. Take a screenshot.
5. Judgment call flagged in Task 3: assess whether the icon+label buttons read as cramped at this width — if so, apply the one-line `.ft-label { display: none }` follow-up noted in Task 3 and re-screenshot.

- [ ] **Step 3: Verify the Room panel as a bottom sheet**

1. At a wider viewport (e.g. 1280×900), click a room on the canvas to select it (opens the Room panel).
2. Resize the viewport to 375×667 (simulates rotating/using an already-open panel on a phone — the more realistic mobile flow is opening at 375px directly, but a live floor plan requires clicking a room on the canvas, which is easier to do reliably at a larger size first; both should produce the same CSS result since it's a pure media-query response, not viewport-at-mount-time logic).
3. Assert `.room-panel-float`'s bounding box: `left: 0`, full width, `bottom` edge sitting at the toolbar's top edge (i.e. `.room-panel-float`'s bottom ≈ `.floating-toolbar`'s top, no gap or overlap).
4. Assert `.room-panel-float`'s height is `<= 45vh` (300px at 667px viewport height).
5. Test the drag-to-dismiss handle still responds to a pointer-event drag (dispatch `pointerdown`/`pointermove`/`pointerup` at the `.drag-handle`, or simulate via Playwright's touch/mouse API) — since Task 1-2 converted this to pointer events, this exercises that conversion in a real browser, not just jsdom.
6. Take a screenshot.

- [ ] **Step 4: Verify the Item picker and Furniture library panels the same way**

Repeat Step 3's approach (open at a wide viewport via the toolbar's picker/furniture toggle buttons, resize to 375×667, assert bounding box docks above the toolbar, take a screenshot) for `.picker-float` and `.furniture-float`.

- [ ] **Step 5: Fix any real issues found**

Same pattern as Phase 1's Task 13 and Phase 2's Task 4 — if a panel doesn't dock correctly (e.g. the inline drag-position style from `rpDrag.pos`/`ipDrag.pos`/`fpDrag.pos` isn't fully overridden by the `!important` rules, or the `bottom: 48px` offset doesn't match the toolbar's actual rendered height), diagnose with the systematic-debugging skill and commit the fix following the same commit-per-fix pattern as the earlier tasks.

- [ ] **Step 6: Clean up the isolated instance**

Revert `vite.config.ts`, kill only the PIDs started in Step 1, remove the temporary `DATA_DIR`.
