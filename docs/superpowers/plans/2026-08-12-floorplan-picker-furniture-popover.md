# Floor Plan Picker/Furniture Popover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Disable the floor plan editor's Picker toolbar button when nothing is pickable (it currently silently does nothing), and on mobile make the Picker/Furniture panels render as small anchored popovers (like View/Draw/Actions) instead of a full-width bottom sheet — closing automatically after each successful placement — while leaving desktop's free-floating, draggable, stays-open panel completely unchanged.

**Architecture:** A new reactive `isMobileViewport` flag (`window.matchMedia("(max-width: 480px)")`, the first JS viewport check in this codebase — everything else so far has been pure CSS) drives a real `{#if}/{:else}`-style fork: on mobile the panel renders inside the existing `ui/Popover.svelte` (extended with an optional `width` prop for a wider panel than the 3-5 item tool lists use); on desktop it renders in the existing `.picker-float`/`.furniture-float` free-floating div, byte-for-byte unchanged. `placeDraggedAt` explicitly closes the relevant panel after each successful placement, gated by the same flag.

**Tech Stack:** Svelte 5 (runes), TypeScript, Vitest, svelte-i18n.

## Global Constraints

- Desktop (`>480px`) Picker/Furniture behavior (free-floating position, drag-to-reposition, stays open after placement) must not change in any way.
- `window.matchMedia` is not implemented in this project's jsdom test environment today — confirmed by direct test (`typeof window.matchMedia === "undefined"`, calling it throws `"window.matchMedia is not a function"`). Task 1 adds a polyfill to `test/setup.ts` *before* any source code calls `window.matchMedia`, or every existing test that mounts `App.svelte` will start failing once Task 3 lands.
- Run `cd packages/editor && npx vitest run` after every task; all pre-existing tests must stay green in addition to new ones.

---

### Task 1: `matchMedia` polyfill in test setup

**Files:**
- Modify: `packages/editor/test/setup.ts`

**Interfaces:**
- Produces: a working `window.matchMedia` in every test (defaults to `matches: false`, i.e. "desktop"), consumed by every test in Tasks 3-4 that mounts `App.svelte`. Individual tests may still locally override `window.matchMedia` to simulate mobile (Tasks 3-4).

- [ ] **Step 1: Write the failing check**

Confirm the current failure mode directly:

Run: `cd packages/editor && cat > test/_mq_probe.test.ts << 'EOF'
import { describe, it, expect } from "vitest";
describe("matchMedia probe", () => {
  it("is callable", () => {
    expect(() => window.matchMedia("(max-width: 480px)")).not.toThrow();
  });
});
EOF
npx vitest run test/_mq_probe.test.ts`

Expected: FAIL — `window.matchMedia is not a function`.

- [ ] **Step 2: Add the polyfill**

In `packages/editor/test/setup.ts`, right after the existing `ResizeObserver` polyfill block, add:

```ts
// Polyfill matchMedia for jsdom (used by App.svelte's mobile-viewport check)
(globalThis as any).matchMedia = (globalThis as any).matchMedia || function (query: string) {
  return {
    matches: false,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  };
};
```

- [ ] **Step 3: Run the check to verify it passes**

Run: `cd packages/editor && npx vitest run test/_mq_probe.test.ts`
Expected: PASS

- [ ] **Step 4: Remove the probe test**

Run: `cd packages/editor && rm test/_mq_probe.test.ts`

- [ ] **Step 5: Run the full editor test suite to confirm no regression**

Run: `cd packages/editor && npx vitest run`
Expected: PASS — this is a pure addition, no existing test reads `window.matchMedia` today.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/test/setup.ts
git commit -m "test(editor): polyfill matchMedia for jsdom"
```

---

### Task 2: `Popover` gets an optional `width` prop

**Files:**
- Modify: `packages/editor/src/lib/components/ui/Popover.svelte`
- Test: `packages/editor/test/Popover.test.ts`

**Interfaces:**
- Produces: `Popover` prop `width?: number` (pixels) — consumed by Task 3's Picker/Furniture usages. Existing View/Draw/Actions usages in `App.svelte` omit it and are unaffected.

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/Popover.test.ts`:

```ts
it("applies a custom width when provided", () => {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const anchor = document.createElement("button");
  document.body.appendChild(anchor);
  const comp = mount(Popover, { target, props: { open: true, anchorEl: anchor, onclose: vi.fn(), width: 280 } });

  const panel = document.querySelector(".ui-popover") as HTMLElement;
  expect(panel.style.width).toBe("280px");

  unmount(comp);
  target.remove();
  anchor.remove();
});

it("has no explicit width style when width is omitted", () => {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const anchor = document.createElement("button");
  document.body.appendChild(anchor);
  const comp = mount(Popover, { target, props: { open: true, anchorEl: anchor, onclose: vi.fn() } });

  const panel = document.querySelector(".ui-popover") as HTMLElement;
  expect(panel.style.width).toBe("");

  unmount(comp);
  target.remove();
  anchor.remove();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/Popover.test.ts -t "width"`
Expected: FAIL — `width` prop doesn't exist, panel has no width style either way (first test fails; second passes vacuously — that's fine, it locks in today's baseline).

- [ ] **Step 3: Implement the prop**

In `Popover.svelte`, change the props interface and destructuring (lines 4-10):

```svelte
  interface Props {
    open: boolean;
    anchorEl: HTMLElement | null;
    onclose: () => void;
    children?: Snippet;
  }
  let { open, anchorEl, onclose, children }: Props = $props();
```

to:

```svelte
  interface Props {
    open: boolean;
    anchorEl: HTMLElement | null;
    onclose: () => void;
    width?: number;
    children?: Snippet;
  }
  let { open, anchorEl, onclose, width, children }: Props = $props();
```

Change the clamp math (line 41) from:

```ts
      panelLeft = Math.max(4, Math.min(rect.left, window.innerWidth - PANEL_WIDTH - 4));
```

to:

```ts
      panelLeft = Math.max(4, Math.min(rect.left, window.innerWidth - (width ?? PANEL_WIDTH) - 4));
```

Change the markup's `style` attribute (line 62) from:

```svelte
    style="left:{panelLeft}px;{panelTop !== null ? `top:${panelTop}px;` : ''}{panelBottom !== null ? `bottom:${panelBottom}px;` : ''}"
```

to:

```svelte
    style="left:{panelLeft}px;{width ? `width:${width}px;` : ''}{panelTop !== null ? `top:${panelTop}px;` : ''}{panelBottom !== null ? `bottom:${panelBottom}px;` : ''}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/Popover.test.ts`
Expected: PASS (all 6 tests — 4 existing + 2 new)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/Popover.svelte packages/editor/test/Popover.test.ts
git commit -m "feat(ui): add optional width prop to Popover"
```

---

### Task 3: Disable the Picker button when nothing is pickable

**Files:**
- Modify: `packages/editor/src/App.svelte`
- Test: `packages/editor/test/App.test.ts`

**Interfaces:**
- Consumes: existing `pickerLayers` (`$derived<PickerLayer[]>`, App.svelte:277-283).
- Produces: nothing new consumed elsewhere.

- [ ] **Step 1: Write the failing test**

Add to `packages/editor/test/App.test.ts` (in the main `describe("App", ...)` block):

```ts
it("disables the Picker button when no module layer is active, and enables it once one is", async () => {
  target = document.createElement("div");
  document.body.appendChild(target);
  app = await mountAndLoad(target);

  const pickerBtn = toolbarBtn(target, "Toggle item picker");
  expect(pickerBtn.disabled).toBe(true);

  (target.querySelector('button[title="Toggle map layers"]') as HTMLButtonElement).click();
  flushSync();
  const choresRow = Array.from(document.querySelectorAll(".layer-row")).find(
    (r) => r.textContent?.includes("Chores"),
  ) as HTMLElement;
  (choresRow.querySelector('input[type="checkbox"]') as HTMLInputElement).click();
  flushSync();

  expect(pickerBtn.disabled).toBe(false);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "disables the Picker button"`
Expected: FAIL — the button has no `disabled` attribute yet, so `pickerBtn.disabled` is `false` from the start.

- [ ] **Step 3: Add the disabled binding**

In `App.svelte`, find the Picker button (inside the `{#if !viewMode}` block alongside Furniture, around line 1318-1323):

```svelte
                <button
                  class="ft-btn"
                  class:active={pickerOpen}
                  title={$_('app.floatingToolbar.togglePicker')}
                  onclick={() => { pickerOpen = !pickerOpen; }}
                >📋 <span class="ft-label">{$_('app.floatingToolbar.picker')}</span></button>
```

change to:

```svelte
                <button
                  class="ft-btn"
                  class:active={pickerOpen}
                  disabled={pickerLayers.length === 0}
                  title={$_('app.floatingToolbar.togglePicker')}
                  onclick={() => { pickerOpen = !pickerOpen; }}
                >📋 <span class="ft-label">{$_('app.floatingToolbar.picker')}</span></button>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "disables the Picker button"`
Expected: PASS

- [ ] **Step 5: Run the full App.test.ts suite**

Run: `cd packages/editor && npx vitest run test/App.test.ts`
Expected: PASS. The existing test around line 257 ("view mode hides editing tools...") iterates `["Wall", "Divider", ..., "Toggle item picker", "Toggle furniture library", "Save"]` asserting `toolbarBtn(target, title)` is `undefined` in view mode — that's a presence check (these buttons are wrapped in `{#if !viewMode}` and don't render at all in view mode), not a `disabled` check, so it's unaffected by this task's change and needs no edit.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/test/App.test.ts
git commit -m "feat(floorplan): disable the Picker button when no module layer is active"
```

---

### Task 4: Picker/Furniture render as an anchored Popover on mobile

**Files:**
- Modify: `packages/editor/src/App.svelte`
- Test: `packages/editor/test/App.test.ts`

**Interfaces:**
- Consumes: `Popover` (Task 2's `width` prop), `isMobileViewport` (new, this task).
- Produces: `let isMobileViewport = $state(boolean)` — consumed by Task 5's `placeDraggedAt` changes.

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/App.test.ts`, near the top alongside the other helper functions (after `toolbarBtn`), a reusable mobile-viewport mock:

```ts
const desktopMatchMedia = window.matchMedia;

function mockMobileViewport(): void {
  window.matchMedia = ((query: string) => ({
    matches: true,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  })) as typeof window.matchMedia;
}
```

In the `describe("App", ...)` block's `afterEach` (around line 93-99), add a restore so no test leaks the mock into the next one:

```ts
  afterEach(() => {
    if (app) {
      unmount(app);
      app = undefined;
    }
    target?.remove();
    window.matchMedia = desktopMatchMedia;
  });
```

Then add the new tests:

```ts
it("opens the Furniture panel inside an anchored popover on mobile instead of a full-width float", async () => {
  mockMobileViewport();
  target = document.createElement("div");
  document.body.appendChild(target);
  app = await mountAndLoad(target);

  toolbarBtn(target, "Toggle furniture library").click();
  flushSync();

  expect(target.querySelector(".furniture-float")).toBeNull();
  const popover = document.querySelector(".ui-popover");
  expect(popover).not.toBeNull();
  expect(popover!.querySelector(".furniture-panel")).not.toBeNull();
});

it("opens the Picker panel inside an anchored popover on mobile instead of a full-width float", async () => {
  mockMobileViewport();
  target = document.createElement("div");
  document.body.appendChild(target);
  app = await mountAndLoad(target);

  (target.querySelector('button[title="Toggle map layers"]') as HTMLButtonElement).click();
  flushSync();
  const choresRow = Array.from(document.querySelectorAll(".layer-row")).find(
    (r) => r.textContent?.includes("Chores"),
  ) as HTMLElement;
  (choresRow.querySelector('input[type="checkbox"]') as HTMLInputElement).click();
  flushSync();

  toolbarBtn(target, "Toggle item picker").click();
  flushSync();

  expect(target.querySelector(".picker-float")).toBeNull();
  const popover = document.querySelector(".ui-popover");
  expect(popover).not.toBeNull();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "anchored popover on mobile"`
Expected: FAIL — `.ui-popover` doesn't exist for these panels yet; they still render inside `.furniture-float`/`.picker-float` regardless of `matchMedia`.

- [ ] **Step 3: Add trigger bindings**

`Popover` is already imported in `App.svelte` (`import Popover from "./lib/components/ui/Popover.svelte";`, line 72) from the prior mobile-toolbar-refinement work — no new import needed.

Near the existing `viewTriggerEl`/`drawTriggerEl`/`actionsTriggerEl` declarations, add:

```ts
  let pickerTriggerEl = $state<HTMLButtonElement | null>(null);
  let furnitureTriggerEl = $state<HTMLButtonElement | null>(null);
```

- [ ] **Step 4: Add the `isMobileViewport` flag**

Near `let activeLayers = $state(new Set<string>(["ha"]));` (line 195), add:

```ts
  let isMobileViewport = $state(window.matchMedia("(max-width: 480px)").matches);
  $effect(() => {
    const mq = window.matchMedia("(max-width: 480px)");
    const update = () => { isMobileViewport = mq.matches; };
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  });
```

- [ ] **Step 5: Bind the Picker/Furniture trigger buttons**

Change (from Task 3's edit, the Picker button now has `disabled={pickerLayers.length === 0}`):

```svelte
                <button
                  class="ft-btn"
                  class:active={pickerOpen}
                  disabled={pickerLayers.length === 0}
                  title={$_('app.floatingToolbar.togglePicker')}
                  onclick={() => { pickerOpen = !pickerOpen; }}
                >📋 <span class="ft-label">{$_('app.floatingToolbar.picker')}</span></button>
                <button
                  class="ft-btn"
                  class:active={furnitureLibraryOpen}
                  title={$_('app.floatingToolbar.toggleFurniture')}
                  onclick={() => { furnitureLibraryOpen = !furnitureLibraryOpen; }}
                >🪑 <span class="ft-label">{$_('app.floatingToolbar.furniture')}</span></button>
```

to:

```svelte
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
```

- [ ] **Step 6: Fork the panel rendering**

Change (lines 1265-1281):

```svelte
          {#if pickerOpen && pickerLayers.length > 0}
            <div class="picker-float" style={ipDrag.pos ? `left:${ipDrag.pos.x}px;top:${ipDrag.pos.y}px;right:auto;transform:none` : ''}>
              <ItemPickerPanel
                layers={pickerLayers}
                draggingId={draggingItemId}
                highlightId={pickerHighlightId}
                onstartdrag={ipDrag.startDrag}
                ondismiss={() => { pickerOpen = false; }}
                onitempointerdown={(layerId, item, e) => { pickerHighlightId = null; handleItemPointerDown(layerId, item, e); }}
              />
            </div>
          {/if}
          {#if furnitureLibraryOpen}
            <div class="furniture-float" style={fpDrag.pos ? `left:${fpDrag.pos.x}px;top:${fpDrag.pos.y}px;right:auto;transform:none` : ''}>
              <FurnitureLibraryPanel onstartdrag={fpDrag.startDrag} ondismiss={() => { furnitureLibraryOpen = false; }} onitempointerdown={handleFurniturePointerDown} />
            </div>
          {/if}
```

to:

```svelte
          <Popover open={isMobileViewport && pickerOpen && pickerLayers.length > 0} anchorEl={pickerTriggerEl} onclose={() => { pickerOpen = false; }} width={280}>
            <ItemPickerPanel
              layers={pickerLayers}
              draggingId={draggingItemId}
              highlightId={pickerHighlightId}
              ondismiss={() => { pickerOpen = false; }}
              onitempointerdown={(layerId, item, e) => { pickerHighlightId = null; handleItemPointerDown(layerId, item, e); }}
            />
          </Popover>
          {#if !isMobileViewport && pickerOpen && pickerLayers.length > 0}
            <div class="picker-float" style={ipDrag.pos ? `left:${ipDrag.pos.x}px;top:${ipDrag.pos.y}px;right:auto;transform:none` : ''}>
              <ItemPickerPanel
                layers={pickerLayers}
                draggingId={draggingItemId}
                highlightId={pickerHighlightId}
                onstartdrag={ipDrag.startDrag}
                ondismiss={() => { pickerOpen = false; }}
                onitempointerdown={(layerId, item, e) => { pickerHighlightId = null; handleItemPointerDown(layerId, item, e); }}
              />
            </div>
          {/if}
          <Popover open={isMobileViewport && furnitureLibraryOpen} anchorEl={furnitureTriggerEl} onclose={() => { furnitureLibraryOpen = false; }} width={280}>
            <FurnitureLibraryPanel ondismiss={() => { furnitureLibraryOpen = false; }} onitempointerdown={handleFurniturePointerDown} />
          </Popover>
          {#if !isMobileViewport && furnitureLibraryOpen}
            <div class="furniture-float" style={fpDrag.pos ? `left:${fpDrag.pos.x}px;top:${fpDrag.pos.y}px;right:auto;transform:none` : ''}>
              <FurnitureLibraryPanel onstartdrag={fpDrag.startDrag} ondismiss={() => { furnitureLibraryOpen = false; }} onitempointerdown={handleFurniturePointerDown} />
            </div>
          {/if}
```

- [ ] **Step 7: Remove the now-dead mobile CSS for `.picker-float`/`.furniture-float`**

These `@media (max-width: 480px)` overrides only ever applied to elements that (as of Step 6) no longer render on mobile. In `App.svelte`'s `<style>` block, change (lines 1663-1707):

```css
  .picker-float {
    position: absolute; right: 120px; top: 50%; transform: translateY(-50%);
    max-height: min(460px, calc(100% - 16px));
    display: flex; flex-direction: column;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md); z-index: 20;
    overflow: hidden;
  }

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

  .furniture-float {
    position: absolute; right: 120px; top: 50%; transform: translateY(-50%);
    max-height: min(460px, calc(100% - 16px));
    display: flex; flex-direction: column;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); padding: 0;
    box-shadow: var(--shadow-md); z-index: 20;
    overflow: hidden;
  }

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

to:

```css
  .picker-float {
    position: absolute; right: 120px; top: 50%; transform: translateY(-50%);
    max-height: min(460px, calc(100% - 16px));
    display: flex; flex-direction: column;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md); z-index: 20;
    overflow: hidden;
  }

  .furniture-float {
    position: absolute; right: 120px; top: 50%; transform: translateY(-50%);
    max-height: min(460px, calc(100% - 16px));
    display: flex; flex-direction: column;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); padding: 0;
    box-shadow: var(--shadow-md); z-index: 20;
    overflow: hidden;
  }
```

- [ ] **Step 8: Run the new tests**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "anchored popover on mobile"`
Expected: PASS

- [ ] **Step 9: Run the full App.test.ts and App.furniture.test.ts suites**

Run: `cd packages/editor && npx vitest run test/App.test.ts test/App.furniture.test.ts`
Expected: PASS — every existing test in both files mounts `App` without calling `mockMobileViewport()`, so `isMobileViewport` stays `false` (desktop path), and `.picker-float`/`.furniture-float` continue to render exactly as before for those tests.

- [ ] **Step 10: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/test/App.test.ts
git commit -m "feat(floorplan): Picker/Furniture render as an anchored popover on mobile"
```

---

### Task 5: Auto-close Picker/Furniture after a successful placement, mobile only

**Files:**
- Modify: `packages/editor/src/App.svelte` (`placeDraggedAt`, lines 792-872)
- Test: `packages/editor/test/App.test.ts`

**Interfaces:**
- Consumes: `isMobileViewport` (Task 4).
- Produces: nothing new consumed elsewhere — this is the last functional task.

- [ ] **Step 1: Write the failing test**

Add to `packages/editor/test/App.test.ts`, reusing the click-to-place pattern already established in `test/App.furniture.test.ts`:

```ts
it("closes the Furniture panel after placing an item, on mobile only", async () => {
  mockMobileViewport();
  target = document.createElement("div");
  document.body.appendChild(target);
  app = await mountAndLoad(target);

  toolbarBtn(target, "Toggle furniture library").click();
  flushSync();
  expect(document.querySelector(".furniture-panel")).not.toBeNull();

  const canvasArea = target.querySelector(".canvas-area") as HTMLElement;
  vi.spyOn(canvasArea, "getBoundingClientRect").mockReturnValue({
    left: 0, top: 0, right: 800, bottom: 600, width: 800, height: 600, x: 0, y: 0, toJSON() {},
  } as DOMRect);

  const sofaItem = document.querySelector('.furniture-item[data-template-id="sofa"]') as HTMLElement;
  const clickX = 400, clickY = 300;
  sofaItem.dispatchEvent(new PointerEvent("pointerdown", { clientX: clickX, clientY: clickY, bubbles: true }));
  flushSync();
  canvasArea.dispatchEvent(new PointerEvent("pointerup", { clientX: clickX, clientY: clickY, bubbles: true }));
  flushSync();

  expect(target.querySelectorAll(".furniture-object").length).toBe(1);
  expect(document.querySelector(".furniture-panel")).toBeNull();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "closes the Furniture panel after placing"`
Expected: FAIL — the item is placed (`.furniture-object` count is 1) but `.furniture-panel` is still present since nothing closes it yet.

- [ ] **Step 3: Add the close calls**

In `App.svelte`, change `placeDraggedAt` (lines 792-872) from:

```ts
  function placeDraggedAt(clientX: number, clientY: number): void {
    if (viewMode) return;
    const canvasEl = document.querySelector(".canvas-area") as HTMLElement | null;
    if (!canvasEl) return;
    const rect = canvasEl.getBoundingClientRect();
    if (clientX < rect.left || clientX > rect.right || clientY < rect.top || clientY > rect.bottom) return;

    if (pointerDragFurnitureTemplateId) {
      const template = getTemplate(pointerDragFurnitureTemplateId);
      if (template) {
        const wasClick = furniturePointerDownAt
          ? Math.hypot(clientX - furniturePointerDownAt.x, clientY - furniturePointerDownAt.y) < FURNITURE_CLICK_THRESHOLD_PX
          : false;
        const dropScreenX = wasClick ? rect.left + rect.width / 2 : clientX;
        const dropScreenY = wasClick ? rect.top + rect.height / 2 : clientY;
        const worldX = (dropScreenX - rect.left - viewportStore.viewport.panX) / viewportStore.viewport.zoom;
        const worldY = (dropScreenY - rect.top - viewportStore.viewport.panY) / viewportStore.viewport.zoom;
        floorStore.addFurniture(pointerDragFurnitureTemplateId, worldX, worldY, template.defaultWidth, template.defaultHeight);
      }
      furniturePointerDownAt = null;
      return;
    }

    const layerId = draggingLayerId;
    const itemId = draggingItemId;
    if (!layerId || !itemId) return;

    if (allFloorsMode) {
      if (layerId !== "chores") return;
      const chore = choreStore.chores.find(c => c.id === itemId);
      choreStore.createAssignment({ choreId: itemId, roomId: null, position: null, nextDueDate: chore?.nextDueDate ?? "", label: null });
      return;
    }

    const screenX = clientX - rect.left, screenY = clientY - rect.top;
    const worldX = (screenX - viewportStore.viewport.panX) / viewportStore.viewport.zoom;
    const worldY = (screenY - viewportStore.viewport.panY) / viewportStore.viewport.zoom;

    if (layerId === "inventory") {
      const room = floorStore.floor.rooms.find(r => r.polygon && pointInPolygon({ x: worldX, y: worldY }, r.polygon));
      inventoryStore.setPlacement(itemId, {
        floorId: floorStore.currentFloorId,
        roomId: room?.id ?? null,
        position: { x: worldX, y: worldY },
      });
      return;
    }

    if (layerId === "consumables") {
      const room = floorStore.floor.rooms.find(r => r.polygon && pointInPolygon({ x: worldX, y: worldY }, r.polygon));
      consumableStore.setPlacement(itemId, {
        floorId: floorStore.currentFloorId,
        roomId: room?.id ?? null,
        position: { x: worldX, y: worldY },
      });
      return;
    }

    if (layerId === "costs") {
      settingsStore.placeCostCategory(itemId, {
        floorId: floorStore.currentFloorId,
        position: { x: worldX, y: worldY },
      });
      return;
    }

    if (layerId === "works") {
      worksStore.setPlacement(itemId, {
        floorId: floorStore.currentFloorId,
        position: { x: worldX, y: worldY },
      });
      return;
    }

    if (layerId === "chores") {
      const room = floorStore.floor.rooms.find(r => r.polygon && pointInPolygon({ x: worldX, y: worldY }, r.polygon));
      if (!room) return;
      const chore = choreStore.chores.find(c => c.id === itemId);
      choreStore.createAssignment({ choreId: itemId, roomId: room.id, position: { x: worldX, y: worldY }, nextDueDate: chore?.nextDueDate ?? "", label: null });
    }
  }
```

to:

```ts
  function placeDraggedAt(clientX: number, clientY: number): void {
    if (viewMode) return;
    const canvasEl = document.querySelector(".canvas-area") as HTMLElement | null;
    if (!canvasEl) return;
    const rect = canvasEl.getBoundingClientRect();
    if (clientX < rect.left || clientX > rect.right || clientY < rect.top || clientY > rect.bottom) return;

    if (pointerDragFurnitureTemplateId) {
      const template = getTemplate(pointerDragFurnitureTemplateId);
      if (template) {
        const wasClick = furniturePointerDownAt
          ? Math.hypot(clientX - furniturePointerDownAt.x, clientY - furniturePointerDownAt.y) < FURNITURE_CLICK_THRESHOLD_PX
          : false;
        const dropScreenX = wasClick ? rect.left + rect.width / 2 : clientX;
        const dropScreenY = wasClick ? rect.top + rect.height / 2 : clientY;
        const worldX = (dropScreenX - rect.left - viewportStore.viewport.panX) / viewportStore.viewport.zoom;
        const worldY = (dropScreenY - rect.top - viewportStore.viewport.panY) / viewportStore.viewport.zoom;
        floorStore.addFurniture(pointerDragFurnitureTemplateId, worldX, worldY, template.defaultWidth, template.defaultHeight);
        if (isMobileViewport) furnitureLibraryOpen = false;
      }
      furniturePointerDownAt = null;
      return;
    }

    const layerId = draggingLayerId;
    const itemId = draggingItemId;
    if (!layerId || !itemId) return;

    if (allFloorsMode) {
      if (layerId !== "chores") return;
      const chore = choreStore.chores.find(c => c.id === itemId);
      choreStore.createAssignment({ choreId: itemId, roomId: null, position: null, nextDueDate: chore?.nextDueDate ?? "", label: null });
      if (isMobileViewport) pickerOpen = false;
      return;
    }

    const screenX = clientX - rect.left, screenY = clientY - rect.top;
    const worldX = (screenX - viewportStore.viewport.panX) / viewportStore.viewport.zoom;
    const worldY = (screenY - viewportStore.viewport.panY) / viewportStore.viewport.zoom;

    if (layerId === "inventory") {
      const room = floorStore.floor.rooms.find(r => r.polygon && pointInPolygon({ x: worldX, y: worldY }, r.polygon));
      inventoryStore.setPlacement(itemId, {
        floorId: floorStore.currentFloorId,
        roomId: room?.id ?? null,
        position: { x: worldX, y: worldY },
      });
      if (isMobileViewport) pickerOpen = false;
      return;
    }

    if (layerId === "consumables") {
      const room = floorStore.floor.rooms.find(r => r.polygon && pointInPolygon({ x: worldX, y: worldY }, r.polygon));
      consumableStore.setPlacement(itemId, {
        floorId: floorStore.currentFloorId,
        roomId: room?.id ?? null,
        position: { x: worldX, y: worldY },
      });
      if (isMobileViewport) pickerOpen = false;
      return;
    }

    if (layerId === "costs") {
      settingsStore.placeCostCategory(itemId, {
        floorId: floorStore.currentFloorId,
        position: { x: worldX, y: worldY },
      });
      if (isMobileViewport) pickerOpen = false;
      return;
    }

    if (layerId === "works") {
      worksStore.setPlacement(itemId, {
        floorId: floorStore.currentFloorId,
        position: { x: worldX, y: worldY },
      });
      if (isMobileViewport) pickerOpen = false;
      return;
    }

    if (layerId === "chores") {
      const room = floorStore.floor.rooms.find(r => r.polygon && pointInPolygon({ x: worldX, y: worldY }, r.polygon));
      if (!room) return;
      const chore = choreStore.chores.find(c => c.id === itemId);
      choreStore.createAssignment({ choreId: itemId, roomId: room.id, position: { x: worldX, y: worldY }, nextDueDate: chore?.nextDueDate ?? "", label: null });
      if (isMobileViewport) pickerOpen = false;
    }
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "closes the Furniture panel after placing"`
Expected: PASS

- [ ] **Step 5: Run App.furniture.test.ts to confirm desktop behavior is unaffected**

Run: `cd packages/editor && npx vitest run test/App.furniture.test.ts`
Expected: PASS — none of these tests call `mockMobileViewport()`, so `isMobileViewport` is `false` throughout and the new `if (isMobileViewport) ...` lines never execute; furniture placement behavior (including the existing "drops at canvas center" and "enables Delete button" tests) is unchanged.

- [ ] **Step 6: Run the full editor package test suite**

Run: `cd packages/editor && npx vitest run`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/test/App.test.ts
git commit -m "feat(floorplan): auto-close Picker/Furniture panel after placement on mobile"
```

---

### Task 6: Manual mobile-viewport verification in a real browser

**Files:** none (verification only)

- [ ] **Step 1: Spin up an isolated dev instance**

Reuse the isolated-instance recipe used for the two prior floor-plan-toolbar verifications (fresh `DATA_DIR`, alt backend port, temporarily repointed `vite.config.ts` proxy, alt frontend port — revert and kill only the specific PIDs started when done).

- [ ] **Step 2: Load the webapp-testing skill and verify at a 375×667 mobile viewport**

Log in / create a Demo home, navigate to `#/plan`. Confirm the Picker icon is visibly greyed out/disabled before any module layer is turned on, and tapping it does nothing.

- [ ] **Step 3: Verify Picker becomes usable and opens as a popover**

Tap the Layers icon, enable Chores (or another module with items). Confirm the Picker icon is now enabled. Tap it — confirm a popover (not a full-width bottom sheet) opens near the icon, wide enough to show the search box and item list clearly.

- [ ] **Step 4: Verify Furniture opens as a popover**

Tap the Furniture icon — confirm the same anchored-popover treatment, with the search box and furniture grid usable at the wider size.

- [ ] **Step 5: Verify placement closes the panel**

Drag (or tap) a furniture item onto the canvas — confirm it's placed and the popover closes automatically. Reopen Furniture and confirm it can be reopened normally for a second placement.

- [ ] **Step 6: Verify desktop is unaffected**

Resize to a desktop width (e.g. 1024px). Confirm Picker/Furniture still open as the original free-floating, draggable panel that stays open after placing multiple items, unaffected by any of this session's changes.

- [ ] **Step 7: Report and fix findings**

If anything looks wrong, fix it in the relevant task's file and rerun that task's automated tests before re-verifying visually.

---

## Post-plan check

```bash
cd packages/editor && npx vitest run
```

Expected: PASS, 0 failures.
