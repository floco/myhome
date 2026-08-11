# Floor Plan Mobile Toolbar Regrouping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Regroup the floor plan editor's mobile toolbar (`packages/editor/src/App.svelte`) so the ~18 controls in edit mode no longer require horizontal scrolling on phones — group View/Draw/Actions tools behind 3 icon buttons that open a modal, convert Floor/Layers dropdown triggers to icon-only, and add a floating active-tool indicator.

**Architecture:** Pure CSS-driven responsive split (no JS viewport detection, matching the codebase's existing `@media (max-width: 480px)` pattern) — every button already in the toolbar keeps rendering; a new `ft-desktop-item` class hides individual tool buttons on mobile only, while new `ft-mobile-item` category-trigger buttons are hidden on desktop only. Each category trigger opens a shared `Modal.svelte` instance (gated by a local `openGroup` state variable) containing bigger touch-target duplicates of the grouped buttons, wired to the same handler functions. Desktop's layout and behavior are completely unchanged.

**Tech Stack:** Svelte 5 (runes), TypeScript, Vitest + `@testing-library`-style DOM mounting (existing `mount`/`unmount`/`flushSync` pattern), svelte-i18n.

## Global Constraints

- Scope is mobile-only (`@media (max-width: 480px)`) — do not change desktop's (`>480px`) rendering or behavior in any task.
- Every new user-facing string needs both an EN key (`packages/editor/src/lib/locales/en.json`) and matching FR key (`packages/editor/src/lib/locales/fr.json`), following the existing nested-object structure under `app.floatingToolbar` / `floorPlan.tools`.
- No new npm dependencies — reuse `Modal.svelte`, `svelte-i18n`'s `$_`, and existing CSS custom properties (`var(--danger)`, `var(--surface)`, `var(--border)`, `var(--shadow-md)`, `var(--radius-md)`, `var(--radius-sm)`, `var(--accent)`, `var(--text)`, `var(--text-muted)`).
- Preserve every existing per-button visibility guard exactly (`!viewMode`, `!choreLayerActive && !allFloorsMode`) — grouping buttons into a modal must not change *when* a control is available, only *where* it's reachable from.
- Run `npm test` (or the editor package's vitest command — confirm with `cat packages/editor/package.json | grep '"test"'` if unsure) after every task; all pre-existing tests must stay green in addition to new ones.

---

### Task 1: FloorSwitcher — icon-only compact trigger on mobile

**Files:**
- Modify: `packages/editor/src/lib/components/FloorSwitcher.svelte:118-127` (compact trigger markup), `:194-` (style block — add new rules near `.compact-label`/`.compact-chevron`, currently around line 213)
- Test: `packages/editor/test/FloorSwitcher.test.ts` (create if it doesn't exist — confirm first with `ls packages/editor/test/FloorSwitcher.test.ts`)

**Interfaces:**
- Consumes: nothing new — `FloorSwitcher` props are unchanged (`floors`, `currentFloorId`, `onswitchfloor`, `onaddfloor?`, `onrenamefloor?`, `onremovefloor?`, `compact?`).
- Produces: the compact trigger button (`.compact-btn`) now always contains a `<span class="compact-icon" aria-hidden="true">🏢</span>` in addition to the existing `<span class="compact-label">`. No prop/behavior change — later tasks don't depend on anything new here.

- [ ] **Step 1: Check for an existing FloorSwitcher test file**

Run: `ls packages/editor/test/FloorSwitcher.test.ts 2>/dev/null && echo EXISTS || echo MISSING`

If `EXISTS`, read it first and add the new test alongside the existing ones using the same mount pattern. If `MISSING`, create it fresh using the pattern in Step 2.

- [ ] **Step 2: Write the failing test**

If the file is missing, create `packages/editor/test/FloorSwitcher.test.ts`:

```ts
import { describe, it, expect, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import FloorSwitcher from "../src/lib/components/FloorSwitcher.svelte";

describe("FloorSwitcher — compact mobile trigger", () => {
  let target: HTMLElement;
  let app: ReturnType<typeof mount> | undefined;

  afterEach(() => {
    if (app) {
      unmount(app);
      app = undefined;
    }
    target?.remove();
  });

  it("renders an icon alongside the floor-name label in the compact trigger", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = mount(FloorSwitcher, {
      target,
      props: {
        floors: [{ id: "f1", name: "Ground Floor" }],
        currentFloorId: "f1",
        onswitchfloor: () => {},
        compact: true,
      },
    });
    flushSync();

    const btn = target.querySelector(".compact-btn") as HTMLButtonElement;
    expect(btn.querySelector(".compact-icon")?.textContent).toBe("🏢");
    expect(btn.querySelector(".compact-label")?.textContent).toBe("Ground Floor");
  });
});
```

If the file already exists, add this `it(...)` block inside its existing `describe`.

- [ ] **Step 3: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/FloorSwitcher.test.ts`
Expected: FAIL — `.compact-icon` is `null`/not found.

- [ ] **Step 4: Add the icon span and mobile CSS**

In `FloorSwitcher.svelte`, change lines 120-127 from:

```svelte
      <button
        class="compact-btn"
        bind:this={compactTrigger}
        onclick={toggleCompact}
        title={$_('floorPlan.switcher.switchFloor')}
      >
        <span class="compact-label">{currentFloorName}</span>
        <span class="compact-chevron">{compactOpen ? "▴" : "▾"}</span>
      </button>
```

to:

```svelte
      <button
        class="compact-btn"
        bind:this={compactTrigger}
        onclick={toggleCompact}
        title={$_('floorPlan.switcher.switchFloor')}
      >
        <span class="compact-icon" aria-hidden="true">🏢</span>
        <span class="compact-label">{currentFloorName}</span>
        <span class="compact-chevron">{compactOpen ? "▴" : "▾"}</span>
      </button>
```

Then in the `<style>` block, change the existing rules (around line 213):

```css
  .compact-label { max-width: 70px; overflow: hidden; text-overflow: ellipsis; }
  .compact-chevron { font-size: 9px; color: var(--text-muted); flex-shrink: 0; }
```

to:

```css
  .compact-icon { display: none; font-size: 13px; line-height: 1; }
  .compact-label { max-width: 70px; overflow: hidden; text-overflow: ellipsis; }
  .compact-chevron { font-size: 9px; color: var(--text-muted); flex-shrink: 0; }

  @media (max-width: 480px) { /* --bp-mobile */
    .compact-icon { display: inline-block; }
    .compact-label { display: none; }
  }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/FloorSwitcher.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/FloorSwitcher.svelte packages/editor/test/FloorSwitcher.test.ts
git commit -m "feat(floorplan): icon-only FloorSwitcher compact trigger on mobile"
```

---

### Task 2: LayersDropdown — icon-only toolbar trigger on mobile

**Files:**
- Modify: `packages/editor/src/lib/components/LayersDropdown.svelte:141-144` (existing mobile media query block)
- Test: `packages/editor/test/LayersDropdown.test.ts`

**Interfaces:**
- Consumes: nothing new — props unchanged (`activeLayers`, `ontoggle`, `popoverAlign?`, `variant?`).
- Produces: no new prop/behavior; `.layers-btn.toolbar .ft-label` is hidden at `≤480px` via CSS only. Nothing later depends on this.

- [ ] **Step 1: Read the existing test file**

Run: `cat packages/editor/test/LayersDropdown.test.ts`

Confirm the mount pattern (it mounts with default `variant` — verify whether any existing test passes `variant: "toolbar"`; if none do, the new test needs to pass it explicitly since the label-hiding CSS only exists for the toolbar variant).

- [ ] **Step 2: Write the failing test**

Add to `packages/editor/test/LayersDropdown.test.ts` (matching its existing mount helper/imports):

```ts
it("renders the toolbar-variant trigger with both icon and label present in the DOM", () => {
  target = document.createElement("div");
  document.body.appendChild(target);

  app = mount(LayersDropdown, {
    target,
    props: { activeLayers: new Set(), ontoggle: () => {}, variant: "toolbar" },
  });
  flushSync();

  const btn = target.querySelector(".layers-btn.toolbar") as HTMLButtonElement;
  expect(btn.textContent).toContain("🗂️");
  expect(btn.querySelector(".ft-label")?.textContent).toBe("Layers");
});
```

(Adjust the `describe`/`beforeEach`/`afterEach` wiring to match whatever the file already uses — this only asserts markup that already exists today, so it should pass immediately; it's here to lock in the baseline before the CSS-only change in Step 4. If an equivalent assertion already exists, skip adding a duplicate and proceed to Step 4.)

- [ ] **Step 3: Run test to verify it passes as a baseline**

Run: `cd packages/editor && npx vitest run test/LayersDropdown.test.ts`
Expected: PASS (this step confirms the DOM structure the CSS change in Step 4 will target still contains both elements — jsdom does not evaluate `@media` queries, so hiding `.ft-label` via CSS is not independently testable here; this test guards the markup, not the visual hiding).

- [ ] **Step 4: Hide the label at mobile width**

In `LayersDropdown.svelte`, change the existing mobile block (lines 141-144):

```css
  @media (max-width: 480px) { /* --bp-mobile */
    .layers-btn.toolbar { width: auto; flex-direction: column; gap: 1px; font-size: 10px; height: auto; }
    .layers-btn.toolbar .ft-label { font-size: 8px; }
  }
```

to:

```css
  @media (max-width: 480px) { /* --bp-mobile */
    .layers-btn.toolbar { width: auto; flex-direction: column; gap: 1px; font-size: 10px; height: auto; }
    .layers-btn.toolbar .ft-label { display: none; }
  }
```

- [ ] **Step 5: Run the full LayersDropdown test suite to confirm no regression**

Run: `cd packages/editor && npx vitest run test/LayersDropdown.test.ts`
Expected: PASS (all tests, including any pre-existing ones)

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/LayersDropdown.svelte packages/editor/test/LayersDropdown.test.ts
git commit -m "feat(floorplan): hide LayersDropdown toolbar label on mobile"
```

---

### Task 3: App.svelte — mode toggle icon (pencil + slash overlay for view mode)

**Files:**
- Modify: `packages/editor/src/App.svelte:1317-1322` (mode toggle button markup), style block near line 1744 (`.ft-label` rule)
- Test: `packages/editor/test/App.test.ts`

**Interfaces:**
- Consumes: existing `viewMode` (`$state<boolean>`, App.svelte:300) and `toggleViewMode()` (App.svelte:302-309) — unchanged.
- Produces: a `.mode-icon` span (with conditional `.crossed` class) inside the existing mode-toggle `.ft-btn`. No new prop — this is purely internal markup that Task 5/6 do not depend on.

- [ ] **Step 1: Write the failing test**

Add to `packages/editor/test/App.test.ts` (in the main `describe("App", ...)` block, using the existing `mountAndLoad` / `toolbarBtn` helpers already defined at the top of the file):

```ts
it("shows a slashed pencil icon on the mode toggle when in view mode, and a plain pencil in edit mode", async () => {
  target = document.createElement("div");
  document.body.appendChild(target);

  app = await mountAndLoad(target);

  const editBtn = toolbarBtn(target, "Switch to view mode (read-only)");
  expect(editBtn.querySelector(".mode-icon")?.className).not.toContain("crossed");

  editBtn.click();
  flushSync();

  const viewBtn = toolbarBtn(target, "Switch to edit mode");
  expect(viewBtn.querySelector(".mode-icon")?.className).toContain("crossed");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "slashed pencil"`
Expected: FAIL — `.mode-icon` not found (querySelector returns `null`, `?.className` is `undefined`, `undefined` does not contain `"crossed"` so the *first* assertion actually passes vacuously; the second assertion after clicking will FAIL because `undefined` does not contain `"crossed"` either — confirm the failure is specifically about `.mode-icon` being absent, not a false positive. If both assertions pass vacuously, that's a test bug — tighten the first assertion to `expect(editBtn.querySelector(".mode-icon")).toBeTruthy()` first, rerun, confirm THAT fails, then proceed.)

- [ ] **Step 3: Implement the icon markup and CSS**

In `App.svelte`, change lines 1317-1322 from:

```svelte
              <button
                class="ft-btn"
                class:active={viewMode}
                title={viewMode ? $_('app.floatingToolbar.switchToEditMode') : $_('app.floatingToolbar.switchToViewMode')}
                onclick={toggleViewMode}
              >{viewMode ? '👁' : '✏️'} <span class="ft-label">{viewMode ? $_('app.floatingToolbar.viewMode') : $_('app.floatingToolbar.editMode')}</span></button>
```

to:

```svelte
              <button
                class="ft-btn"
                class:active={viewMode}
                title={viewMode ? $_('app.floatingToolbar.switchToEditMode') : $_('app.floatingToolbar.switchToViewMode')}
                onclick={toggleViewMode}
              ><span class="mode-icon" class:crossed={viewMode}>✏️</span> <span class="ft-label">{viewMode ? $_('app.floatingToolbar.viewMode') : $_('app.floatingToolbar.editMode')}</span></button>
```

In the `<style>` block, right after the existing `.ft-label { font-size: 11px; font-weight: 500; }` rule (line 1744), add:

```css
  .mode-icon {
    position: relative;
    display: inline-block;
    line-height: 1;
  }
  .mode-icon.crossed::after {
    content: '';
    position: absolute;
    left: -2px; right: -2px; top: 50%;
    height: 2px;
    background: var(--danger);
    transform: translateY(-50%) rotate(-45deg);
    border-radius: 1px;
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "slashed pencil"`
Expected: PASS

- [ ] **Step 5: Run the full App.test.ts suite to confirm no regression**

Run: `cd packages/editor && npx vitest run test/App.test.ts`
Expected: PASS — the icon markup change does not alter button `title` attributes or the `.floating-toolbar .ft-btn` title-list order, so the existing exact-list assertion (around line 111) must still pass unmodified.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/test/App.test.ts
git commit -m "feat(floorplan): slashed-pencil icon for view mode instead of eye glyph"
```

---

### Task 4: App.svelte — mobile category triggers (View/Draw/Actions) wired to modals

This is the core task. It adds 3 new always-in-DOM buttons visible only on mobile (`ft-mobile-item`), hides the individual tool buttons they replace on mobile only (`ft-desktop-item`), and wires each trigger to a `Modal.svelte` instance containing bigger-touch-target duplicates of the grouped controls.

**Files:**
- Modify: `packages/editor/src/App.svelte` (imports near line 8, state declarations near line 297-309, toolbar markup lines 1334-1353, style block lines 1721-1776)
- Modify: `packages/editor/src/lib/locales/en.json` (`app.floatingToolbar` object, around line 1298)
- Modify: `packages/editor/src/lib/locales/fr.json` (`app.floatingToolbar` object, same nesting)
- Test: `packages/editor/test/App.test.ts`

**Interfaces:**
- Consumes: `toolStore.setTool(tool: ToolType)`, `toolStore.state.tool`, `handleUndo()` (App.svelte:539), `handleRedo()` (App.svelte:543), `handleDelete()` (App.svelte:528), `hasSelection` (`$derived<boolean>`, App.svelte:445), `floorStore.hasUndo` / `floorStore.hasRedo`, `viewportStore.reset(floor, canvasWidth, canvasHeight)`, `viewMode`, `allFloorsMode`, `choreLayerActive` (`$derived`, App.svelte:195) — all pre-existing, unchanged signatures.
- Produces: new local `let openGroup = $state<"view" | "draw" | "actions" | null>(null);` — Task 5 (floating indicator) reads and writes this same variable, so its name and type must match exactly.

- [ ] **Step 1: Add the new i18n keys**

In `packages/editor/src/lib/locales/en.json`, inside the `app.floatingToolbar` object (find it with `grep -n '"floatingToolbar"' packages/editor/src/lib/locales/en.json`), add 3 new keys. For example if the object currently ends with:

```json
      "switchToViewMode": "Switch to view mode (read-only)",
      "switchToEditMode": "Switch to edit mode"
    },
```

change it to:

```json
      "switchToViewMode": "Switch to view mode (read-only)",
      "switchToEditMode": "Switch to edit mode",
      "viewGroup": "View tools",
      "drawGroup": "Draw tools",
      "actionsGroup": "Actions"
    },
```

In `packages/editor/src/lib/locales/fr.json`, inside the matching `app.floatingToolbar` object, make the equivalent change:

```json
      "switchToViewMode": "Passer en mode lecture seule",
      "switchToEditMode": "Passer en mode édition",
      "viewGroup": "Outils de vue",
      "drawGroup": "Outils de dessin",
      "actionsGroup": "Actions"
    },
```

Validate both files are still valid JSON: `node -e "JSON.parse(require('fs').readFileSync('packages/editor/src/lib/locales/en.json'))" && node -e "JSON.parse(require('fs').readFileSync('packages/editor/src/lib/locales/fr.json'))" && echo OK`

- [ ] **Step 2: Write the failing test for the 3 new trigger buttons**

In `packages/editor/test/App.test.ts`, find the existing test `"renders the title and toolbar with the select tool active"` (around line 101-118) and change the `titles` assertion (line 111) from:

```ts
    expect(titles).toEqual(["Toggle item picker", "Toggle furniture library", "Switch to view mode (read-only)", "Save", "Reset view", "Undo (Ctrl+Z)", "Redo (Ctrl+Y)", "Pan", "Select", "Wall", "Divider", "Garden Border", "Door", "Window", "Delete selected (Del)"]);
```

to:

```ts
    expect(titles).toEqual(["Toggle item picker", "Toggle furniture library", "Switch to view mode (read-only)", "Save", "Reset view", "Undo (Ctrl+Z)", "Redo (Ctrl+Y)", "Pan", "Select", "Wall", "Divider", "Garden Border", "Door", "Window", "Delete selected (Del)", "View tools", "Draw tools", "Actions"]);
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "renders the title and toolbar"`
Expected: FAIL — actual array is missing the 3 new trailing titles.

- [ ] **Step 4: Add `openGroup` state and the `ToolType` import**

In `App.svelte`, change the import at line 8 from:

```ts
  import { createToolStore } from "./lib/toolStore.svelte";
```

to:

```ts
  import { createToolStore, type ToolType } from "./lib/toolStore.svelte";
```

Near the other `$state` toolbar-related declarations (right after `let viewMode = $state(false);` at line 300), add:

```ts
  let openGroup = $state<"view" | "draw" | "actions" | null>(null);
```

In `toggleViewMode()` (lines 302-309), reset it when leaving edit mode so a stale modal can't stay open with now-hidden triggers:

```ts
  function toggleViewMode(): void {
    viewMode = !viewMode;
    openGroup = null;
    if (viewMode) {
      toolStore.setTool("select");
      pickerOpen = false;
      furnitureLibraryOpen = false;
    }
  }
```

- [ ] **Step 5: Tag the existing grouped buttons with `ft-desktop-item` and add the 3 trigger buttons**

In `App.svelte`, replace the block from the Reset button through the closing of the tools `{#if}` (lines 1334-1353) — currently:

```svelte
              <button class="ft-btn" title={$_('app.floatingToolbar.resetView')} onclick={() => viewportStore.reset(floorStore.floor, canvasWidth, canvasHeight)}>↺ <span class="ft-label">{$_('app.floatingToolbar.reset')}</span></button>
              {#if !viewMode}
                <div class="ft-sep"></div>
                <button class="ft-btn" title={$_('floorPlan.tools.undo')} disabled={!floorStore.hasUndo} onclick={handleUndo}>↩ <span class="ft-label">{$_('app.floatingToolbar.undo')}</span></button>
                <button class="ft-btn" title={$_('floorPlan.tools.redo')} disabled={!floorStore.hasRedo} onclick={handleRedo}>↪ <span class="ft-label">{$_('app.floatingToolbar.redo')}</span></button>
              {/if}
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

with:

```svelte
              <button class="ft-btn ft-desktop-item" title={$_('app.floatingToolbar.resetView')} onclick={() => viewportStore.reset(floorStore.floor, canvasWidth, canvasHeight)}>↺ <span class="ft-label">{$_('app.floatingToolbar.reset')}</span></button>
              {#if !viewMode}
                <div class="ft-sep ft-desktop-item"></div>
                <button class="ft-btn ft-desktop-item" title={$_('floorPlan.tools.undo')} disabled={!floorStore.hasUndo} onclick={handleUndo}>↩ <span class="ft-label">{$_('app.floatingToolbar.undo')}</span></button>
                <button class="ft-btn ft-desktop-item" title={$_('floorPlan.tools.redo')} disabled={!floorStore.hasRedo} onclick={handleRedo}>↪ <span class="ft-label">{$_('app.floatingToolbar.redo')}</span></button>
              {/if}
              {#if !choreLayerActive && !allFloorsMode}
                <div class="ft-sep ft-desktop-item"></div>
                <button class="ft-btn ft-desktop-item" title={$_('floorPlan.tools.pan')} class:active={toolStore.state.tool === "pan"} onclick={() => toolStore.setTool("pan")}>✋ <span class="ft-label">{$_('floorPlan.tools.pan')}</span></button>
                {#if !viewMode}
                  <button class="ft-btn ft-desktop-item" title={$_('floorPlan.tools.select')} class:active={toolStore.state.tool === "select"} onclick={() => toolStore.setTool("select")}>🖱 <span class="ft-label">{$_('floorPlan.tools.select')}</span></button>
                  <button class="ft-btn ft-desktop-item" title={$_('floorPlan.tools.wall')} class:active={toolStore.state.tool === "wall"} onclick={() => toolStore.setTool("wall")}>🧱 <span class="ft-label">{$_('floorPlan.tools.wall')}</span></button>
                  <button class="ft-btn ft-desktop-item" title={$_('floorPlan.tools.divider')} class:active={toolStore.state.tool === "divider"} onclick={() => toolStore.setTool("divider")}>╌ <span class="ft-label">{$_('floorPlan.tools.divider')}</span></button>
                  <button class="ft-btn ft-desktop-item" title={$_('floorPlan.tools.garden')} class:active={toolStore.state.tool === "garden"} onclick={() => toolStore.setTool("garden")}>🌿 <span class="ft-label">{$_('floorPlan.tools.garden')}</span></button>
                  <button class="ft-btn ft-desktop-item" title={$_('floorPlan.tools.door')} class:active={toolStore.state.tool === "door"} onclick={() => toolStore.setTool("door")}>🚪 <span class="ft-label">{$_('floorPlan.tools.door')}</span></button>
                  <button class="ft-btn ft-desktop-item" title={$_('floorPlan.tools.window')} class:active={toolStore.state.tool === "window"} onclick={() => toolStore.setTool("window")}>🪟 <span class="ft-label">{$_('floorPlan.tools.window')}</span></button>
                  <div class="ft-sep ft-desktop-item"></div>
                  <button class="ft-btn ft-desktop-item delete" disabled={!hasSelection} onclick={handleDelete} title={$_('floorPlan.tools.delete')}>🗑 <span class="ft-label">{$_('app.floatingToolbar.delete')}</span></button>
                {/if}
              {/if}
              <div class="ft-sep ft-mobile-item"></div>
              <button class="ft-btn ft-mobile-item" title={$_('app.floatingToolbar.viewGroup')} onclick={() => { openGroup = "view"; }}>👁 <span class="ft-label">{$_('app.floatingToolbar.viewGroup')}</span></button>
              {#if !choreLayerActive && !allFloorsMode && !viewMode}
                <button class="ft-btn ft-mobile-item" title={$_('app.floatingToolbar.drawGroup')} onclick={() => { openGroup = "draw"; }}>📐 <span class="ft-label">{$_('app.floatingToolbar.drawGroup')}</span></button>
              {/if}
              {#if !viewMode}
                <button class="ft-btn ft-mobile-item" title={$_('app.floatingToolbar.actionsGroup')} onclick={() => { openGroup = "actions"; }}>⚡ <span class="ft-label">{$_('app.floatingToolbar.actionsGroup')}</span></button>
              {/if}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "renders the title and toolbar"`
Expected: PASS

- [ ] **Step 7: Run the full App.test.ts suite to catch any other title-list assertions**

Run: `cd packages/editor && npx vitest run test/App.test.ts`
Expected: some tests may fail if they assert `.floating-toolbar .ft-btn` counts/titles elsewhere (e.g. in view mode or all-floors mode). Search for other occurrences: `grep -n "titles).toEqual\|querySelectorAll(\".floating-toolbar" packages/editor/test/App.test.ts`. Fix any other failing assertion the same way — append `"View tools"` (and `"Draw tools"`/`"Actions"` if that mode's guards allow them) to its expected array, matching the guard logic added in Step 5 above (e.g. in view mode, only `"View tools"` is appended, not `"Draw tools"` or `"Actions"`).

- [ ] **Step 8: Write the failing tests for opening each modal**

Add to `packages/editor/test/App.test.ts`:

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

(`drawWalls` and `SAMPLE_RECT_CORNERS` are existing helpers already used elsewhere in this file — confirm their exact names with `grep -n "function drawWalls\|SAMPLE_RECT_CORNERS =" packages/editor/test/App.test.ts` and adjust the import/reference if they differ slightly.)

- [ ] **Step 9: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "opens the"`
Expected: FAIL — no `.ui-modal` is rendered yet since the modals don't exist.

- [ ] **Step 10: Import Modal and add the 3 modal instances**

Find the `Modal` import used elsewhere (e.g. in `NewChoreModal.svelte`: `import Modal from "./ui/Modal.svelte";`). Add the equivalent import to `App.svelte`'s script block, adjusting the relative path (App.svelte lives in `src/`, so it's `./lib/components/ui/Modal.svelte`):

```ts
  import Modal from "./lib/components/ui/Modal.svelte";
```

Immediately after the closing `</div>` of `.floating-toolbar` (end of the block edited in Step 5, still inside the `{#if floorStore.loaded}` guard from line 1267), add:

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

- [ ] **Step 11: Add the CSS for `.ft-desktop-item`/`.ft-mobile-item` and the modal grid**

In `App.svelte`'s `<style>` block, right after `.ft-sep { height: 1px; background: var(--border); flex-shrink: 0; margin: 2px 0; }` (line 1746-1748), add:

```css
  .ft-mobile-item { display: none; }

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

Then inside the existing `@media (max-width: 480px)` block (lines 1750-1776), add these 2 lines (anywhere inside the block, e.g. right after the opening `.floating-toolbar { ... }` rule closes):

```css
    .ft-desktop-item { display: none; }
    .ft-mobile-item { display: flex; }
```

- [ ] **Step 12: Run the new modal tests**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "opens the"`
Expected: PASS

- [ ] **Step 13: Run the full App.test.ts suite**

Run: `cd packages/editor && npx vitest run test/App.test.ts`
Expected: PASS (all tests, including the Step 7 fixes)

- [ ] **Step 14: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/App.test.ts
git commit -m "feat(floorplan): group mobile toolbar tools into View/Draw/Actions modals"
```

---

### Task 5: App.svelte — floating active-tool indicator

**Files:**
- Modify: `packages/editor/src/App.svelte` (add `TOOL_ICONS` map near the top of the script block, markup right after `.floating-toolbar`'s closing `</div>`, style block)
- Test: `packages/editor/test/App.test.ts`

**Interfaces:**
- Consumes: `toolStore.state.tool` (`ToolType`), `openGroup` (`$state` from Task 4 — same variable, same 4 possible values), `viewMode`, `choreLayerActive`, `allFloorsMode` — all pre-existing/already introduced.
- Produces: nothing new consumed by later tasks — this is the last functional task.

- [ ] **Step 1: Write the failing test**

Add to `packages/editor/test/App.test.ts`:

```ts
it("shows a floating active-tool indicator that reopens the owning group's modal", async () => {
  target = document.createElement("div");
  document.body.appendChild(target);

  app = await mountAndLoad(target);

  const indicator = target.querySelector(".ft-tool-indicator") as HTMLButtonElement;
  expect(indicator).toBeTruthy();
  expect(indicator.title).toBe("Select");

  indicator.click();
  flushSync();

  expect(target.querySelector(".ui-modal")?.textContent).toContain("View tools");
});

it("hides the floating active-tool indicator in view mode", async () => {
  target = document.createElement("div");
  document.body.appendChild(target);

  app = await mountAndLoad(target);

  toolbarBtn(target, "Switch to view mode (read-only)").click();
  flushSync();

  expect(target.querySelector(".ft-tool-indicator")).toBeNull();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "floating active-tool indicator"`
Expected: FAIL — `.ft-tool-indicator` does not exist yet.

- [ ] **Step 3: Add the `TOOL_ICONS` map**

In `App.svelte`'s script block, near the `ALL_FLOOR_ID` constant (line 298), add a module-level-style constant (place it right before the `<script>` block's closing, or alongside other top-level `const` declarations such as line 298):

```ts
  const TOOL_ICONS: Record<ToolType, string> = {
    pan: "✋",
    select: "🖱",
    wall: "🧱",
    divider: "╌",
    garden: "🌿",
    door: "🚪",
    window: "🪟",
  };
```

- [ ] **Step 4: Add the indicator markup**

Right after the `Modal` instances added in Task 4 Step 10 (still inside the `{#if floorStore.loaded}` block, before its closing `{/if}` at line 1355), add:

```svelte
            {#if !viewMode && !choreLayerActive && !allFloorsMode}
              <button
                class="ft-tool-indicator"
                title={$_(`floorPlan.tools.${toolStore.state.tool}`)}
                onclick={() => { openGroup = (toolStore.state.tool === "pan" || toolStore.state.tool === "select") ? "view" : "draw"; }}
              >{TOOL_ICONS[toolStore.state.tool]}</button>
            {/if}
```

- [ ] **Step 5: Add the CSS**

In the `<style>` block, right after the `.ft-mobile-item { display: none; }` rule added in Task 4 Step 11, add:

```css
  .ft-tool-indicator {
    display: none;
    padding: 0;
    border: 1px solid var(--border);
    border-radius: 50%;
    background: var(--surface);
    box-shadow: var(--shadow-md);
    font-size: 18px;
    cursor: pointer;
  }
```

Inside the existing `@media (max-width: 480px)` block (where `.ft-desktop-item`/`.ft-mobile-item` were added in Task 4 Step 11), add:

```css
    .ft-tool-indicator {
      display: flex; align-items: center; justify-content: center;
      position: fixed; right: 8px; bottom: 56px;
      width: 40px; height: 40px;
      z-index: 31;
    }
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "floating active-tool indicator"`
Expected: PASS

- [ ] **Step 7: Run the full App.test.ts suite**

Run: `cd packages/editor && npx vitest run test/App.test.ts`
Expected: PASS

- [ ] **Step 8: Run the full editor package test suite**

Run: `cd packages/editor && npx vitest run`
Expected: PASS — confirms no other test file (e.g. `App.viewportAutoFit.test.ts`, `App.furniture.test.ts`) broke from the toolbar restructuring across Tasks 3-5.

- [ ] **Step 9: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/test/App.test.ts
git commit -m "feat(floorplan): floating active-tool indicator on mobile"
```

---

### Task 6: Manual mobile-viewport verification in a real browser

Automated tests confirm DOM structure and click-wiring, but cannot verify actual visual layout since jsdom doesn't evaluate `@media` queries or compute real layout — the `display: none`/`flex` CSS toggling that makes this whole feature work has not been visually verified by any automated test in this plan. This task closes that gap.

**Files:** none (verification only)

- [ ] **Step 1: Start the dev server**

Check for a project-specific run skill/script first: `ls .claude/skills/run* 2>/dev/null; cat packages/editor/package.json | grep '"dev"'`. Start it (typically `npm run dev` from the repo root or `packages/editor`), and note the local URL (e.g. `http://localhost:5173`).

- [ ] **Step 2: Load the skill for browser testing**

Use the `webapp-testing` skill (Playwright-based) to drive a real browser. Set the viewport to a narrow mobile width (375px × 667px, matching a typical phone) and navigate to the floor plan editor route (`#/plan`), logging in if the dev instance requires it.

- [ ] **Step 3: Verify the primary row**

Screenshot the toolbar at the bottom of the screen. Confirm: no horizontal scrollbar/overflow is needed to see all primary-row icons (drag handle is hidden on mobile per existing behavior — confirm it's absent), Floor switcher and Layers show icon-only (no visible text label), Picker/Furniture/Mode/Save icons are present with their small labels, and 👁/📐/⚡ (View/Draw/Actions) are the last 3 icons.

- [ ] **Step 4: Verify each category modal**

Tap the 👁 View icon — confirm a modal opens listing Pan, Select, Reset with legible 44px+ touch targets. Tap "Wall" from the 📐 Draw modal — confirm the modal closes and the canvas is now in wall-drawing mode. Tap the ⚡ Actions icon and tap "Undo" — confirm it closes and undoes the last action (draw a wall first if needed to have something to undo).

- [ ] **Step 5: Verify the floating indicator**

After selecting a tool (e.g. Wall) from the Draw modal, confirm a small round indicator chip appears near the bottom-right, above the toolbar, showing the 🧱 icon. Tap it and confirm the Draw modal reopens.

- [ ] **Step 6: Verify the mode-toggle icon**

Tap the Edit/View mode toggle. Confirm the pencil icon gains a visible diagonal slash overlay in view mode, and the View/Draw/Actions icons that shouldn't apply in view mode (Draw, Actions) are no longer present, per the guards added in Task 4.

- [ ] **Step 7: Verify desktop is unaffected**

Resize the browser viewport back above 480px width (e.g. 1024px). Confirm the toolbar reverts to the original full inline layout with all buttons visible and no category icons/modals present.

- [ ] **Step 8: Report findings**

If any visual issue is found (icons overlapping, modal grid too cramped, indicator overlapping other floating panels like the picker/furniture float), fix it in the relevant task's file and rerun that task's automated tests before re-verifying visually. Do not commit new fixes without rerunning the affected test file.

---

## Post-plan check

After Task 6, run the complete test suite one more time to confirm nothing regressed end-to-end:

```bash
cd packages/editor && npx vitest run
```

Expected: PASS, 0 failures.
