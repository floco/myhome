# Floor Plan Mobile Toolbar Popover Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On the floor plan editor's mobile toolbar, remove the small text labels under every primary-row icon, make every button (including the floor switcher) a uniform bigger square, and replace the View/Draw/Actions full-screen `Modal` grids with a small anchored popover (like `EmojiPicker`/`LayersDropdown`) showing a vertical list of icon+label rows.

**Architecture:** All primary-row sizing/label changes are pure CSS inside the existing `@media (max-width: 480px)` blocks (no new JS state, no DOM structure change) — flexbox (`flex: 1 1 0; max-width: 44px; aspect-ratio: 1/1`) makes buttons shrink evenly to fit any screen width, which is what removes the need for `overflow-x: auto`. The View/Draw/Actions groups get a new shared `ui/Popover.svelte` (open/anchorEl/onclose/children, modeled on `Modal.svelte`'s prop shape but positioned near its trigger like the existing copy-pasted popover pattern in `EmojiPicker.svelte`/`LayersDropdown.svelte`, extracted once here instead of copy-pasted a 4th time) replacing the 3 `<Modal>` usages.

**Tech Stack:** Svelte 5 (runes), TypeScript, Vitest, svelte-i18n.

## Global Constraints

- Scope is mobile-only (`@media (max-width: 480px)`) — desktop (`>480px`) rendering and behavior must not change.
- Every existing per-item visibility guard (`!viewMode`, `!choreLayerActive && !allFloorsMode`) must be preserved exactly when moving Draw/View/Actions content from `Modal` to `Popover`.
- CSS-only changes (label hiding, button sizing, chevron hiding) are not observable in jsdom (it doesn't evaluate `@media` or compute real layout) — for those steps, confirm the existing test suite stays green rather than writing a new failing test, and rely on the manual browser-verification task (Task 6) for actual visual confirmation.
- Run `cd packages/editor && npx vitest run` after every task; all pre-existing tests must stay green in addition to new ones.

---

### Task 1: New shared `ui/Popover.svelte` component

**Files:**
- Create: `packages/editor/src/lib/components/ui/Popover.svelte`
- Test: `packages/editor/test/Popover.test.ts`

**Interfaces:**
- Produces: `Popover` component with props `open: boolean`, `anchorEl: HTMLElement | null`, `onclose: () => void`, `children?: Snippet` — consumed by Task 5's View/Draw/Actions replacement.

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/Popover.test.ts`:

```ts
import { describe, it, expect, vi } from "vitest";
import { mount, unmount } from "svelte";
import Popover from "../src/lib/components/ui/Popover.svelte";

describe("ui/Popover", () => {
  it("renders nothing when closed", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const anchor = document.createElement("button");
    document.body.appendChild(anchor);
    const comp = mount(Popover, { target, props: { open: false, anchorEl: anchor, onclose: vi.fn() } });

    expect(document.querySelector(".ui-popover")).toBeNull();

    unmount(comp);
    target.remove();
    anchor.remove();
  });

  it("renders the panel when open", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const anchor = document.createElement("button");
    document.body.appendChild(anchor);
    const comp = mount(Popover, { target, props: { open: true, anchorEl: anchor, onclose: vi.fn() } });

    expect(document.querySelector(".ui-popover")).not.toBeNull();

    unmount(comp);
    target.remove();
    anchor.remove();
  });

  it("calls onclose when clicking outside the panel and the anchor", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const anchor = document.createElement("button");
    document.body.appendChild(anchor);
    const onclose = vi.fn();
    const comp = mount(Popover, { target, props: { open: true, anchorEl: anchor, onclose } });

    document.body.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(onclose).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
    anchor.remove();
  });

  it("calls onclose on Escape", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const anchor = document.createElement("button");
    document.body.appendChild(anchor);
    const onclose = vi.fn();
    const comp = mount(Popover, { target, props: { open: true, anchorEl: anchor, onclose } });

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    expect(onclose).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
    anchor.remove();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/Popover.test.ts`
Expected: FAIL — the component file doesn't exist yet (import error).

- [ ] **Step 3: Create the component**

Create `packages/editor/src/lib/components/ui/Popover.svelte`:

```svelte
<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    open: boolean;
    anchorEl: HTMLElement | null;
    onclose: () => void;
    children?: Snippet;
  }
  let { open, anchorEl, onclose, children }: Props = $props();

  const PANEL_WIDTH = 200;

  let panelEl = $state<HTMLElement | null>(null);
  let panelTop = $state<number | null>(null);
  let panelBottom = $state<number | null>(null);
  let panelLeft = $state(0);

  // Teleport to <body> so position:fixed isn't affected by an ancestor's
  // CSS transform or overflow -- same mechanism as EmojiPicker.svelte's
  // and LayersDropdown.svelte's portal actions.
  function portal(node: HTMLElement): { destroy(): void } {
    document.body.appendChild(node);
    return {
      destroy() {
        if (document.body.contains(node)) document.body.removeChild(node);
      },
    };
  }

  $effect(() => {
    if (open && anchorEl) {
      const rect = anchorEl.getBoundingClientRect();
      if (rect.top > window.innerHeight / 2) {
        panelBottom = window.innerHeight - rect.top + 4;
        panelTop = null;
      } else {
        panelTop = rect.bottom + 4;
        panelBottom = null;
      }
      panelLeft = Math.max(4, Math.min(rect.left, window.innerWidth - PANEL_WIDTH - 4));
    }
  });

  function handleClickOutside(e: MouseEvent): void {
    if (!open) return;
    const target = e.target as Node;
    if (anchorEl?.contains(target) || panelEl?.contains(target)) return;
    onclose();
  }

  function handleKeydown(e: KeyboardEvent): void {
    if (open && e.key === "Escape") onclose();
  }
</script>

<svelte:window onclick={handleClickOutside} onkeydown={handleKeydown} />

{#if open}
  <div
    class="ui-popover"
    style="left:{panelLeft}px;{panelTop !== null ? `top:${panelTop}px;` : ''}{panelBottom !== null ? `bottom:${panelBottom}px;` : ''}"
    bind:this={panelEl}
    use:portal
  >
    {@render children?.()}
  </div>
{/if}

<style>
  .ui-popover {
    position: fixed; z-index: 9999;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); box-shadow: var(--shadow-md);
    padding: 6px; min-width: 160px;
    display: flex; flex-direction: column; gap: 2px;
    max-height: 60vh; overflow-y: auto;
  }
</style>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/Popover.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/Popover.svelte packages/editor/test/Popover.test.ts
git commit -m "feat(ui): add shared anchored Popover component"
```

---

### Task 2: FloorSwitcher — hide chevron and match uniform mobile button size

**Files:**
- Modify: `packages/editor/src/lib/components/FloorSwitcher.svelte` (mobile media query, currently lines 218-221; wrapper/trigger CSS around lines 204-216)

**Interfaces:**
- Consumes/produces: nothing new — pure CSS, no prop/behavior change.

- [ ] **Step 1: Confirm the existing test baseline still passes (no test changes needed for this CSS-only step)**

Run: `cd packages/editor && npx vitest run test/FloorSwitcher.test.ts`
Expected: PASS — this locks in the current baseline (icon + label both present in the DOM) before making a CSS-only change that jsdom cannot observe.

- [ ] **Step 2: Update the mobile CSS**

In `FloorSwitcher.svelte`, the compact-trigger wrapper is `<div class="compact-switcher" bind:this={compactWrapper}>` containing `<button class="compact-btn">` — since `.compact-switcher` is the actual flex child of `.floating-toolbar` on mobile (not `.compact-btn` directly), the uniform sizing must go on the wrapper. Change the existing mobile block (lines 218-221):

```css
  @media (max-width: 480px) { /* --bp-mobile */
    .compact-icon { display: inline-block; }
    .compact-label { display: none; }
  }
```

to:

```css
  @media (max-width: 480px) { /* --bp-mobile */
    .compact-switcher { flex: 1 1 0; max-width: 44px; aspect-ratio: 1 / 1; }
    .compact-btn { width: 100%; height: 100%; padding: 0; }
    .compact-icon { display: inline-block; font-size: 22px; }
    .compact-label { display: none; }
    .compact-chevron { display: none; }
  }
```

- [ ] **Step 3: Run tests to confirm no regression**

Run: `cd packages/editor && npx vitest run test/FloorSwitcher.test.ts`
Expected: PASS — markup unchanged, only CSS values changed.

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/FloorSwitcher.svelte
git commit -m "feat(floorplan): hide FloorSwitcher chevron and match uniform mobile button size"
```

---

### Task 3: LayersDropdown — match uniform mobile button size

**Files:**
- Modify: `packages/editor/src/lib/components/LayersDropdown.svelte` (mobile media query, currently lines 141-144)

**Interfaces:**
- Consumes/produces: nothing new — pure CSS, no prop/behavior change.

- [ ] **Step 1: Confirm the existing test baseline still passes**

Run: `cd packages/editor && npx vitest run test/LayersDropdown.test.ts`
Expected: PASS.

- [ ] **Step 2: Update the mobile CSS**

The trigger `<button class="layers-btn">` is wrapped in `<div class="layers-dropdown" bind:this={wrapper}>` — that wrapper is the actual flex child of `.floating-toolbar`. Change the existing mobile block (lines 141-144):

```css
  @media (max-width: 480px) { /* --bp-mobile */
    .layers-btn.toolbar { width: auto; flex-direction: column; gap: 1px; font-size: 10px; height: auto; }
    .layers-btn.toolbar .ft-label { display: none; }
  }
```

to:

```css
  @media (max-width: 480px) { /* --bp-mobile */
    .layers-dropdown { flex: 1 1 0; max-width: 44px; aspect-ratio: 1 / 1; }
    .layers-btn.toolbar { width: 100%; height: 100%; font-size: 22px; justify-content: center; }
    .layers-btn.toolbar .ft-label { display: none; }
  }
```

- [ ] **Step 3: Run tests to confirm no regression**

Run: `cd packages/editor && npx vitest run test/LayersDropdown.test.ts`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/LayersDropdown.svelte
git commit -m "feat(floorplan): match LayersDropdown to uniform mobile button size"
```

---

### Task 4: App.svelte primary row — hide labels, uniform bigger icons, drop scroll fallback

**Files:**
- Modify: `packages/editor/src/App.svelte` (style block: `.floating-toolbar`, `.ft-btn`, `.ft-label` mobile rules, currently within `@media (max-width: 480px)` at lines 1849-1883)

**Interfaces:**
- Consumes/produces: nothing new — pure CSS on existing classes already used by every primary-row button.

- [ ] **Step 1: Confirm the existing test baseline still passes**

Run: `cd packages/editor && npx vitest run test/App.test.ts`
Expected: PASS — this is a CSS-only change to classes already asserted on (title lists, `.active` classes); no DOM structure changes.

- [ ] **Step 2: Update the mobile CSS**

Change the existing block (lines 1849-1883):

```css
  @media (max-width: 480px) { /* --bp-mobile */
    .floating-toolbar {
      position: fixed;
      left: 0; right: 0; bottom: 0; top: auto;
      transform: none !important;
      box-sizing: border-box;
      width: 100%;
      height: 48px;
      padding: 4px;
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
    .ft-desktop-item { display: none; }
    .ft-mobile-item { display: flex; }
    .ft-tool-indicator {
      display: flex; align-items: center; justify-content: center;
      position: fixed; right: 8px; bottom: 56px;
      width: 40px; height: 40px;
      z-index: 31;
    }
  }
```

to:

```css
  @media (max-width: 480px) { /* --bp-mobile */
    .floating-toolbar {
      position: fixed;
      left: 0; right: 0; bottom: 0; top: auto;
      transform: none !important;
      box-sizing: border-box;
      width: 100%;
      height: 48px;
      padding: 4px;
      flex-direction: row;
      align-items: center;
      gap: 0;
      border-radius: 0;
      border-left: none; border-right: none; border-bottom: none;
      z-index: 30;
    }
    .ft-handle { display: none; }
    .ft-btn {
      flex: 1 1 0;
      max-width: 44px;
      width: auto;
      aspect-ratio: 1 / 1;
      justify-content: center;
      font-size: 22px;
    }
    .ft-label { display: none; }
    .ft-sep { width: 1px; height: 24px; margin: 0 2px; flex-shrink: 0; }
    .ft-desktop-item { display: none; }
    .ft-mobile-item { display: flex; }
    .ft-tool-indicator {
      display: flex; align-items: center; justify-content: center;
      position: fixed; right: 8px; bottom: 56px;
      width: 40px; height: 40px;
      z-index: 31;
    }
  }
```

(Removed `overflow-x: auto` from `.floating-toolbar` — no longer needed since `flex: 1 1 0` on every `.ft-btn` makes them shrink to always fit the row exactly. Removed `flex-direction: column; gap: 1px;` from `.ft-btn` since there's no label to stack under the icon anymore. Changed `.ft-label { font-size: 8px }` to `display: none` so it applies uniformly to every primary-row button, not just the ones with a manually-hidden label.)

- [ ] **Step 3: Run tests to confirm no regression**

Run: `cd packages/editor && npx vitest run test/App.test.ts`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/App.svelte
git commit -m "feat(floorplan): bigger uniform icon buttons on mobile toolbar, no scroll needed"
```

---

### Task 5: App.svelte — View/Draw/Actions become Popover row lists instead of Modal grids

**Files:**
- Modify: `packages/editor/src/App.svelte` (import near line 71, new `bind:this` state near line 310, trigger buttons at lines 1365-1372, the 3 `<Modal>` blocks at lines 1374-1402, style block: remove `.ft-modal-grid`/`.ft-modal-btn*` rules at lines 1833-1847, add `.ft-popover-row`/`.ft-popover-icon`)
- Test: `packages/editor/test/App.test.ts`

**Interfaces:**
- Consumes: `Popover` from Task 1 (`open`, `anchorEl`, `onclose`, `children`).
- Produces: nothing new consumed elsewhere — this is the last functional task.

- [ ] **Step 1: Update the failing tests first**

In `packages/editor/test/App.test.ts`, the 3 existing tests that open a group and the floating-indicator test all query `.ui-modal` — change them to query `.ui-popover` instead. Replace:

```ts
  it("opens the View tools modal and selects Pan from it", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = await mountAndLoad(target);

    toolbarBtn(target, "View tools").click();
    flushSync();

    const modal = target.querySelector(".ui-modal");
    expect(modal?.textContent).toContain("View tools");

    const panBtn = Array.from(modal!.querySelectorAll("button")).find(
      (b) => b.textContent?.includes("Pan"),
    ) as HTMLButtonElement;
    panBtn.click();
    flushSync();

    expect(target.querySelector(".ui-modal")).toBeNull();
    expect(toolbarBtn(target, "Pan").className).toContain("active");
  });

  it("opens the Draw tools modal and selects Wall from it", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = await mountAndLoad(target);

    toolbarBtn(target, "Draw tools").click();
    flushSync();

    const modal = target.querySelector(".ui-modal");
    expect(modal?.textContent).toContain("Draw tools");

    const wallBtn = Array.from(modal!.querySelectorAll("button")).find(
      (b) => b.textContent?.includes("Wall"),
    ) as HTMLButtonElement;
    wallBtn.click();
    flushSync();

    expect(target.querySelector(".ui-modal")).toBeNull();
    expect(toolbarBtn(target, "Wall").className).toContain("active");
  });

  it("opens the Actions modal and triggers Undo from it", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = await mountAndLoad(target);
    drawWalls(target, SAMPLE_RECT_CORNERS);

    const wallsBefore = target.querySelectorAll("polygon.wall").length;

    toolbarBtn(target, "Actions").click();
    flushSync();

    const modal = target.querySelector(".ui-modal");
    expect(modal?.textContent).toContain("Actions");

    const undoBtn = Array.from(modal!.querySelectorAll("button")).find(
      (b) => b.textContent?.includes("Undo"),
    ) as HTMLButtonElement;
    undoBtn.click();
    flushSync();

    expect(target.querySelector(".ui-modal")).toBeNull();
    expect(target.querySelectorAll("polygon.wall").length).toBe(wallsBefore - 1);
  });
```

with:

```ts
  it("opens the View tools popover and selects Pan from it", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = await mountAndLoad(target);

    toolbarBtn(target, "View tools").click();
    flushSync();

    const popover = document.querySelector(".ui-popover");
    expect(popover?.textContent).toContain("Pan");

    const panBtn = Array.from(popover!.querySelectorAll("button")).find(
      (b) => b.textContent?.includes("Pan"),
    ) as HTMLButtonElement;
    panBtn.click();
    flushSync();

    expect(document.querySelector(".ui-popover")).toBeNull();
    expect(toolbarBtn(target, "Pan").className).toContain("active");
  });

  it("opens the Draw tools popover and selects Wall from it", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = await mountAndLoad(target);

    toolbarBtn(target, "Draw tools").click();
    flushSync();

    const popover = document.querySelector(".ui-popover");
    expect(popover?.textContent).toContain("Wall");

    const wallBtn = Array.from(popover!.querySelectorAll("button")).find(
      (b) => b.textContent?.includes("Wall"),
    ) as HTMLButtonElement;
    wallBtn.click();
    flushSync();

    expect(document.querySelector(".ui-popover")).toBeNull();
    expect(toolbarBtn(target, "Wall").className).toContain("active");
  });

  it("opens the Actions popover and triggers Undo from it", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = await mountAndLoad(target);
    drawWalls(target, SAMPLE_RECT_CORNERS);

    const wallsBefore = target.querySelectorAll("polygon.wall").length;

    toolbarBtn(target, "Actions").click();
    flushSync();

    const popover = document.querySelector(".ui-popover");
    expect(popover?.textContent).toContain("Undo");

    const undoBtn = Array.from(popover!.querySelectorAll("button")).find(
      (b) => b.textContent?.includes("Undo"),
    ) as HTMLButtonElement;
    undoBtn.click();
    flushSync();

    expect(document.querySelector(".ui-popover")).toBeNull();
    expect(target.querySelectorAll("polygon.wall").length).toBe(wallsBefore - 1);
  });
```

Also update the floating-indicator test — change:

```ts
    expect(target.querySelector(".ui-modal")?.textContent).toContain("View tools");
```

to:

```ts
    expect(document.querySelector(".ui-popover")?.textContent).toContain("Pan");
```

(Note: `Popover` teleports its panel to `document.body` via the portal action, same as `EmojiPicker`/`LayersDropdown` — query with `document.querySelector`, not `target.querySelector`, for the popover content. `target.querySelector` still works for toolbar buttons since those aren't portaled.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "opens the"`
Expected: FAIL — `.ui-popover` doesn't exist yet, the code still renders `.ui-modal`.

- [ ] **Step 3: Import Popover and add trigger-element bindings**

Add the import next to the existing `Modal` import (App.svelte line 71):

```ts
  import Modal from "./lib/components/ui/Modal.svelte";
  import Popover from "./lib/components/ui/Popover.svelte";
```

Near `let openGroup = $state<"view" | "draw" | "actions" | null>(null);` (line 310), add:

```ts
  let viewTriggerEl = $state<HTMLButtonElement | null>(null);
  let drawTriggerEl = $state<HTMLButtonElement | null>(null);
  let actionsTriggerEl = $state<HTMLButtonElement | null>(null);
```

- [ ] **Step 4: Bind the trigger buttons**

Change the 3 trigger buttons (lines 1365-1372) from:

```svelte
              <div class="ft-sep ft-mobile-item"></div>
              <button class="ft-btn ft-mobile-item" title={$_('app.floatingToolbar.viewGroup')} onclick={() => { openGroup = "view"; }}>👁 <span class="ft-label">{$_('app.floatingToolbar.viewGroup')}</span></button>
              {#if !choreLayerActive && !allFloorsMode && !viewMode}
                <button class="ft-btn ft-mobile-item" title={$_('app.floatingToolbar.drawGroup')} onclick={() => { openGroup = "draw"; }}>📐 <span class="ft-label">{$_('app.floatingToolbar.drawGroup')}</span></button>
              {/if}
              {#if !viewMode}
                <button class="ft-btn ft-mobile-item" title={$_('app.floatingToolbar.actionsGroup')} onclick={() => { openGroup = "actions"; }}>⚡ <span class="ft-label">{$_('app.floatingToolbar.actionsGroup')}</span></button>
              {/if}
```

to:

```svelte
              <div class="ft-sep ft-mobile-item"></div>
              <button class="ft-btn ft-mobile-item" bind:this={viewTriggerEl} title={$_('app.floatingToolbar.viewGroup')} onclick={() => { openGroup = "view"; }}>👁 <span class="ft-label">{$_('app.floatingToolbar.viewGroup')}</span></button>
              {#if !choreLayerActive && !allFloorsMode && !viewMode}
                <button class="ft-btn ft-mobile-item" bind:this={drawTriggerEl} title={$_('app.floatingToolbar.drawGroup')} onclick={() => { openGroup = "draw"; }}>📐 <span class="ft-label">{$_('app.floatingToolbar.drawGroup')}</span></button>
              {/if}
              {#if !viewMode}
                <button class="ft-btn ft-mobile-item" bind:this={actionsTriggerEl} title={$_('app.floatingToolbar.actionsGroup')} onclick={() => { openGroup = "actions"; }}>⚡ <span class="ft-label">{$_('app.floatingToolbar.actionsGroup')}</span></button>
              {/if}
```

- [ ] **Step 5: Replace the 3 Modal blocks with Popover row lists**

Change (lines 1374-1402):

```svelte
            <Modal open={openGroup === "view"} title={$_('app.floatingToolbar.viewGroup')} onclose={() => { openGroup = null; }}>
              <div class="ft-modal-grid">
                {#if !choreLayerActive && !allFloorsMode}
                  <button class="ft-modal-btn" class:active={toolStore.state.tool === "pan"} onclick={() => { toolStore.setTool("pan"); openGroup = null; }}>✋ <span>{$_('floorPlan.tools.pan')}</span></button>
                  {#if !viewMode}
                    <button class="ft-modal-btn" class:active={toolStore.state.tool === "select"} onclick={() => { toolStore.setTool("select"); openGroup = null; }}>🖱 <span>{$_('floorPlan.tools.select')}</span></button>
                  {/if}
                {/if}
                <button class="ft-modal-btn" onclick={() => { viewportStore.reset(floorStore.floor, canvasWidth, canvasHeight); openGroup = null; }}>↺ <span>{$_('app.floatingToolbar.reset')}</span></button>
              </div>
            </Modal>
            <Modal open={openGroup === "draw"} title={$_('app.floatingToolbar.drawGroup')} onclose={() => { openGroup = null; }}>
              <div class="ft-modal-grid">
                <button class="ft-modal-btn" class:active={toolStore.state.tool === "wall"} onclick={() => { toolStore.setTool("wall"); openGroup = null; }}>🧱 <span>{$_('floorPlan.tools.wall')}</span></button>
                <button class="ft-modal-btn" class:active={toolStore.state.tool === "divider"} onclick={() => { toolStore.setTool("divider"); openGroup = null; }}>╌ <span>{$_('floorPlan.tools.divider')}</span></button>
                <button class="ft-modal-btn" class:active={toolStore.state.tool === "garden"} onclick={() => { toolStore.setTool("garden"); openGroup = null; }}>🌿 <span>{$_('floorPlan.tools.garden')}</span></button>
                <button class="ft-modal-btn" class:active={toolStore.state.tool === "door"} onclick={() => { toolStore.setTool("door"); openGroup = null; }}>🚪 <span>{$_('floorPlan.tools.door')}</span></button>
                <button class="ft-modal-btn" class:active={toolStore.state.tool === "window"} onclick={() => { toolStore.setTool("window"); openGroup = null; }}>🪟 <span>{$_('floorPlan.tools.window')}</span></button>
              </div>
            </Modal>
            <Modal open={openGroup === "actions"} title={$_('app.floatingToolbar.actionsGroup')} onclose={() => { openGroup = null; }}>
              <div class="ft-modal-grid">
                <button class="ft-modal-btn" disabled={!floorStore.hasUndo} onclick={() => { handleUndo(); openGroup = null; }}>↩ <span>{$_('app.floatingToolbar.undo')}</span></button>
                <button class="ft-modal-btn" disabled={!floorStore.hasRedo} onclick={() => { handleRedo(); openGroup = null; }}>↪ <span>{$_('app.floatingToolbar.redo')}</span></button>
                {#if !choreLayerActive && !allFloorsMode}
                  <button class="ft-modal-btn ft-modal-danger" disabled={!hasSelection} onclick={() => { handleDelete(); openGroup = null; }}>🗑 <span>{$_('app.floatingToolbar.delete')}</span></button>
                {/if}
              </div>
            </Modal>
```

to:

```svelte
            <Popover open={openGroup === "view"} anchorEl={viewTriggerEl} onclose={() => { openGroup = null; }}>
              {#if !choreLayerActive && !allFloorsMode}
                <button class="ft-popover-row" class:active={toolStore.state.tool === "pan"} onclick={() => { toolStore.setTool("pan"); openGroup = null; }}><span class="ft-popover-icon">✋</span><span>{$_('floorPlan.tools.pan')}</span></button>
                {#if !viewMode}
                  <button class="ft-popover-row" class:active={toolStore.state.tool === "select"} onclick={() => { toolStore.setTool("select"); openGroup = null; }}><span class="ft-popover-icon">🖱</span><span>{$_('floorPlan.tools.select')}</span></button>
                {/if}
              {/if}
              <button class="ft-popover-row" onclick={() => { viewportStore.reset(floorStore.floor, canvasWidth, canvasHeight); openGroup = null; }}><span class="ft-popover-icon">↺</span><span>{$_('app.floatingToolbar.reset')}</span></button>
            </Popover>
            <Popover open={openGroup === "draw"} anchorEl={drawTriggerEl} onclose={() => { openGroup = null; }}>
              <button class="ft-popover-row" class:active={toolStore.state.tool === "wall"} onclick={() => { toolStore.setTool("wall"); openGroup = null; }}><span class="ft-popover-icon">🧱</span><span>{$_('floorPlan.tools.wall')}</span></button>
              <button class="ft-popover-row" class:active={toolStore.state.tool === "divider"} onclick={() => { toolStore.setTool("divider"); openGroup = null; }}><span class="ft-popover-icon">╌</span><span>{$_('floorPlan.tools.divider')}</span></button>
              <button class="ft-popover-row" class:active={toolStore.state.tool === "garden"} onclick={() => { toolStore.setTool("garden"); openGroup = null; }}><span class="ft-popover-icon">🌿</span><span>{$_('floorPlan.tools.garden')}</span></button>
              <button class="ft-popover-row" class:active={toolStore.state.tool === "door"} onclick={() => { toolStore.setTool("door"); openGroup = null; }}><span class="ft-popover-icon">🚪</span><span>{$_('floorPlan.tools.door')}</span></button>
              <button class="ft-popover-row" class:active={toolStore.state.tool === "window"} onclick={() => { toolStore.setTool("window"); openGroup = null; }}><span class="ft-popover-icon">🪟</span><span>{$_('floorPlan.tools.window')}</span></button>
            </Popover>
            <Popover open={openGroup === "actions"} anchorEl={actionsTriggerEl} onclose={() => { openGroup = null; }}>
              <button class="ft-popover-row" disabled={!floorStore.hasUndo} onclick={() => { handleUndo(); openGroup = null; }}><span class="ft-popover-icon">↩</span><span>{$_('app.floatingToolbar.undo')}</span></button>
              <button class="ft-popover-row" disabled={!floorStore.hasRedo} onclick={() => { handleRedo(); openGroup = null; }}><span class="ft-popover-icon">↪</span><span>{$_('app.floatingToolbar.redo')}</span></button>
              {#if !choreLayerActive && !allFloorsMode}
                <button class="ft-popover-row ft-popover-danger" disabled={!hasSelection} onclick={() => { handleDelete(); openGroup = null; }}><span class="ft-popover-icon">🗑</span><span>{$_('app.floatingToolbar.delete')}</span></button>
              {/if}
            </Popover>
```

- [ ] **Step 6: Replace the modal-grid CSS with popover-row CSS**

Change (lines 1833-1847):

```css
  .ft-modal-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(84px, 1fr));
    gap: 8px;
  }
  .ft-modal-btn {
    display: flex; flex-direction: column; align-items: center; gap: 4px;
    padding: 10px 4px; min-height: 44px;
    border: 1px solid var(--border); border-radius: var(--radius-md);
    background: var(--surface); color: var(--text);
    font-size: 12px; cursor: pointer;
  }
  .ft-modal-btn:hover:not(:disabled) { background: var(--surface-hover); }
  .ft-modal-btn.active { border-color: var(--accent); color: var(--accent); }
  .ft-modal-btn:disabled { opacity: 0.35; cursor: default; }
  .ft-modal-btn.ft-modal-danger { color: var(--danger); }
```

to:

```css
  .ft-popover-row {
    display: flex; align-items: center; gap: 10px; width: 100%;
    padding: 10px 12px; min-height: 44px;
    border: none; border-radius: var(--radius-sm);
    background: transparent; color: var(--text);
    font-size: 14px; cursor: pointer; text-align: left;
  }
  .ft-popover-row:hover:not(:disabled) { background: var(--surface-hover); }
  .ft-popover-row.active { background: var(--surface-hover); color: var(--accent); }
  .ft-popover-row:disabled { opacity: 0.35; cursor: default; }
  .ft-popover-row.ft-popover-danger { color: var(--danger); }
  .ft-popover-icon { font-size: 20px; width: 24px; text-align: center; flex-shrink: 0; }
```

- [ ] **Step 7: Run the updated tests**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "opens the"`
Expected: PASS

- [ ] **Step 8: Run the full App.test.ts suite**

Run: `cd packages/editor && npx vitest run test/App.test.ts`
Expected: PASS (including the updated floating-indicator test)

- [ ] **Step 9: Run the full editor package test suite**

Run: `cd packages/editor && npx vitest run`
Expected: PASS — confirms nothing else broke.

- [ ] **Step 10: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/test/App.test.ts
git commit -m "feat(floorplan): View/Draw/Actions open as an anchored popover instead of a full-screen modal"
```

---

### Task 6: Manual mobile-viewport verification in a real browser

**Files:** none (verification only)

- [ ] **Step 1: Spin up an isolated dev instance**

Reuse the isolated-instance recipe (fresh `DATA_DIR`, alt backend port, temporarily repointed `vite.config.ts` proxy, alt frontend port) documented in project memory `project_demo_home_status` / used for the previous floorplan-mobile-toolbar verification — a persistent main dev backend/frontend may already be running with an unknown admin password, so don't reuse it. Revert `vite.config.ts` and kill only the specific PIDs started, when done.

- [ ] **Step 2: Load the webapp-testing skill and verify at a 375×667 mobile viewport**

Log in (or create a Demo home if starting from a fresh `DATA_DIR`), navigate to the floor plan editor (`#/plan`), and screenshot the toolbar. Confirm: every primary-row button (Floor, Layers, Picker, Furniture, Edit, Save, View, Draw, Actions) is icon-only with no text underneath, visibly bigger than before, roughly uniform in size including the floor switcher, and all fit on one row with no horizontal scrollbar.

- [ ] **Step 3: Verify each popover**

Tap the View icon — confirm a small anchored panel opens near the icon (not a full-screen overlay) showing Pan/Select/Reset as a vertical list, each row with an icon on the left and text on the right. Tap "Wall" from the Draw popover — confirm it closes and the canvas enters wall-drawing mode. Tap Actions and tap "Undo" (after drawing something) — confirm it closes and undoes.

- [ ] **Step 4: Verify the floating indicator still works**

Confirm the floating active-tool-indicator chip still appears and reopens the correct popover when tapped.

- [ ] **Step 5: Verify desktop is unaffected**

Resize to a desktop width (e.g. 1024px) and confirm the toolbar still renders as the original full inline layout with labels, unaffected by any of this session's changes.

- [ ] **Step 6: Report and fix findings**

If anything looks wrong (popover positioned off-screen, buttons not quite fitting, icons too big/small), fix it in the relevant task's file and rerun that task's automated tests before re-verifying visually.

---

## Post-plan check

```bash
cd packages/editor && npx vitest run
```

Expected: PASS, 0 failures.
