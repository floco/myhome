# Visual Redesign Phase 2 (Floor-Plan Editor Panels + Canvas) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate every hardcoded hex/rgb color in the floor-plan editor's own panels (`ItemPickerPanel`, `RoomPanel`, `Toolbar`, `FloorSwitcher`, `LayersDropdown`) and the SVG canvas shape components (`Canvas`, `Grid`, `WallShape`, `DividerShape`, `RoomShape`, `OpeningShape`, `SelectionHandles`, `DrawPreview`) onto the Phase 1 design-token system, so both light and dark themes render correctly across the editor.

**Architecture:** This is a pure CSS/inline-attribute value migration — no markup structure, props, component APIs, or behavior change. Two token families are involved: (1) existing UI chrome tokens from `packages/editor/src/lib/theme.css` (`--surface`, `--surface-alt`, `--surface-hover`, `--border`, `--text`, `--text-muted`, `--text-faint`, `--accent`, `--accent-contrast`, `--danger`, `--radius-sm`, `--space-1` through `--space-3`, `--shadow-md`) applied to the 5 panel/toolbar files; (2) the 5 existing canvas tokens (`--canvas-bg`, `--canvas-grid`, `--canvas-wall`, `--canvas-wall-selected`, `--canvas-room-fill`) plus 7 new canvas tokens this plan adds to `theme.css`, applied to the 8 canvas-shape files. Per the design doc's Density Rule, panel/toolbar files keep their existing tight spacing (no padding increases) — only color/border/radius values move to tokens. Per Canvas Theming, the canvas now follows the active theme (light = "blueprint on paper", dark = current look retained).

**Tech Stack:** Svelte 5 (runes), Vitest, existing `theme.css` token system (Phase 1).

**New canvas tokens added in Task 1** (beyond the 5 that already exist): `--canvas-divider`, `--canvas-opening-door`, `--canvas-opening-window`, `--canvas-room-fill-selected`, `--canvas-label`, `--canvas-draw-preview`, `--canvas-selected-fill`. Selection/interaction accents that don't need their own token reuse existing ones: any "this element is selected/active" stroke or fill reuses `--canvas-wall-selected`; the white/dark contrast halo around selection-handle dots reuses the UI chrome token `--text` (which already flips light/dark correctly); the opening's "gap" background reuses `--canvas-bg`.

All 5 panel/toolbar files also drop several one-off blue-tint accent colors (e.g. `#aaf`, `#ccf`, `#5566cc`) that were vestiges of the old dark-IDE palette — per the redesign's "near-monochrome accent" principle, "active/highlighted" UI state is now signaled via `--accent`/`--text` (full emphasis) the same way `NavMenu`'s active pill works, not via a special hue.

---

## Baseline

Before starting, confirm the worktree is clean:

```bash
cd /projects/myhome/.worktrees/feat/visual-redesign-phase2-canvas/packages/editor
npm test -- --run
```

Expected: `Test Files 20 passed (20)`, `Tests 159 passed (159)`. Every task below ends by re-running this exact command — the count must stay `159 passed (159)` after every task (no new tests are added; this is a styling migration, not a behavior change, so the existing suite is the regression gate).

---

### Task 1: Add Phase 2 canvas tokens to `theme.css`

**Files:**
- Modify: `packages/editor/src/lib/theme.css:40-46` (light `:root` canvas block) and `:68-73` (dark `[data-theme="dark"]` canvas block)

- [ ] **Step 1: Add the 7 new light-theme canvas tokens**

In `packages/editor/src/lib/theme.css`, find this block (lines 40-46):

```css
  /* Floor-plan canvas (tuned separately from UI chrome; consumed in Phase 2) */
  --canvas-bg: #eceef1;
  --canvas-grid: #d8dadf;
  --canvas-wall: #2a2a30;
  --canvas-wall-selected: #111111;
  --canvas-room-fill: #ffffff;
}
```

Replace it with:

```css
  /* Floor-plan canvas (tuned separately from UI chrome) */
  --canvas-bg: #eceef1;
  --canvas-grid: #d8dadf;
  --canvas-wall: #2a2a30;
  --canvas-wall-selected: #111111;
  --canvas-room-fill: #ffffff;
  --canvas-room-fill-selected: #bcdcf0;
  --canvas-divider: #5d7a96;
  --canvas-opening-door: #a6862a;
  --canvas-opening-window: #3b7dd8;
  --canvas-label: #44546b;
  --canvas-draw-preview: #d97f1f;
  --canvas-selected-fill: rgba(17, 17, 17, 0.12);
}
```

- [ ] **Step 2: Add the 7 new dark-theme canvas tokens**

In the same file, find this block (lines 68-73):

```css
  --canvas-bg: #1c1c22;
  --canvas-grid: #2a2a32;
  --canvas-wall: #d8d8dc;
  --canvas-wall-selected: #ffffff;
  --canvas-room-fill: #232328;
}
```

Replace it with:

```css
  --canvas-bg: #1c1c22;
  --canvas-grid: #2a2a32;
  --canvas-wall: #d8d8dc;
  --canvas-wall-selected: #ffffff;
  --canvas-room-fill: #232328;
  --canvas-room-fill-selected: #2a6a8a;
  --canvas-divider: #99aadd;
  --canvas-opening-door: #eea;
  --canvas-opening-window: #8cf;
  --canvas-label: #cde;
  --canvas-draw-preview: #ffb84d;
  --canvas-selected-fill: rgba(85, 170, 255, 0.15);
}
```

- [ ] **Step 3: Verify the file parses and the suite still passes**

Run:
```bash
npm test -- --run
```
Expected: `Tests 159 passed (159)` (adding unused CSS custom properties cannot break any test; this step just confirms nothing else broke).

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/theme.css
git commit -m "feat(theme): add Phase 2 canvas tokens for dividers, openings, selection, and labels"
```

---

### Task 2: Token-migrate `Toolbar.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/Toolbar.svelte:38-78` (entire `<style>` block)

- [ ] **Step 1: Replace the `<style>` block**

Replace the existing `<style>` block (lines 38-78) with:

```svelte
<style>
  .toolbar {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 2px;
    padding: var(--space-1) var(--space-2);
    background: var(--surface-alt);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    height: 36px;
    box-sizing: border-box;
  }
  .sep {
    width: 1px;
    height: 18px;
    background: var(--border);
    margin: 0 4px;
    flex-shrink: 0;
  }
  button {
    width: 30px;
    height: 28px;
    border: none;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    padding: 0;
  }
  button:hover:not(:disabled) { background: var(--surface-hover); color: var(--text); }
  button.active { background: var(--accent); color: var(--accent-contrast); }
  button.delete { color: var(--danger); }
  button.delete:hover:not(:disabled) { background: var(--surface-hover); color: var(--danger); }
  button:disabled { opacity: 0.35; cursor: default; }
</style>
```

- [ ] **Step 2: Run the full suite**

```bash
npm test -- --run
```
Expected: `Tests 159 passed (159)` (no test file exists for `Toolbar.svelte`; this confirms no other suite broke).

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/Toolbar.svelte
git commit -m "feat(editor): token-migrate Toolbar colors"
```

---

### Task 3: Token-migrate `FloorSwitcher.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/FloorSwitcher.svelte:96-173` (entire `<style>` block)

- [ ] **Step 1: Replace the `<style>` block**

Replace the existing `<style>` block (lines 96-173) with:

```svelte
<style>
  .floor-switcher {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .floor-btn {
    display: flex;
    align-items: center;
    border-radius: var(--radius-sm);
    background: var(--surface-alt);
    overflow: hidden;
  }

  .floor-btn.active {
    background: var(--surface-hover);
    outline: 1px solid var(--accent);
  }

  .floor-label {
    padding: 3px 8px;
    border: none;
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 12px;
    white-space: nowrap;
  }

  .floor-btn.active .floor-label {
    color: var(--text);
  }

  .remove-btn {
    padding: 3px 5px;
    border: none;
    border-left: 1px solid var(--border);
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
    font-size: 11px;
    line-height: 1;
  }

  .remove-btn:hover {
    color: var(--danger);
    background: var(--surface-hover);
  }

  .rename-input {
    width: 90px;
    padding: 2px 6px;
    background: var(--surface-alt);
    border: 1px solid var(--accent);
    border-radius: var(--radius-sm);
    color: var(--text);
    font-size: 12px;
  }

  .add-btn {
    padding: 3px 8px;
    border: none;
    border-radius: var(--radius-sm);
    background: var(--surface-alt);
    color: var(--text-muted);
    cursor: pointer;
    font-size: 12px;
  }

  .add-btn:hover {
    background: var(--surface-hover);
    color: var(--text);
  }
</style>
```

Note: the `.all-btn .floor-label` / `.all-btn.active .floor-label` blue-tint rules (`#aaf`/`#ccf`) are intentionally removed — the "All" floor button now reads with the same neutral palette as every other floor button, consistent with the redesign's near-monochrome accent principle.

- [ ] **Step 2: Run the full suite**

```bash
npm test -- --run
```
Expected: `Tests 159 passed (159)` (no test file exists for `FloorSwitcher.svelte`).

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/FloorSwitcher.svelte
git commit -m "feat(editor): token-migrate FloorSwitcher colors"
```

---

### Task 4: Token-migrate `LayersDropdown.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/LayersDropdown.svelte:52-81` (entire `<style>` block)

- [ ] **Step 1: Replace the `<style>` block**

Replace the existing `<style>` block (lines 52-81) with:

```svelte
<style>
  .layers-dropdown { position: relative; }

  .layers-btn {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text-muted);
    padding: 3px 10px; border-radius: var(--radius-sm); font-size: 11px;
    cursor: pointer; display: flex; align-items: center; gap: 5px;
    white-space: nowrap; height: 26px;
  }
  .layers-btn:hover { background: var(--surface-hover); }
  .layers-btn.active { border-color: var(--accent); color: var(--text); }
  .caret { font-size: 9px; }

  .dropdown {
    position: absolute; top: calc(100% + 4px); right: 0;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); padding: 6px; min-width: 160px;
    z-index: 100; box-shadow: var(--shadow-md);
  }

  .layer-row {
    display: flex; align-items: center; gap: 8px;
    padding: 5px 8px; border-radius: var(--radius-sm); cursor: pointer;
    color: var(--text-muted); font-size: 12px;
  }
  .layer-row:hover { background: var(--surface-hover); }
  .layer-row.checked { color: var(--text); }
  .layer-row input { accent-color: var(--accent); cursor: pointer; }
  .layer-icon { font-size: 14px; width: 18px; text-align: center; }
</style>
```

- [ ] **Step 2: Run the full suite**

```bash
npm test -- --run
```
Expected: `Tests 159 passed (159)` (no test file exists for `LayersDropdown.svelte`).

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/LayersDropdown.svelte
git commit -m "feat(editor): token-migrate LayersDropdown colors"
```

---

### Task 5: Token-migrate `RoomPanel.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/RoomPanel.svelte:66-113` (entire `<style>` block)

- [ ] **Step 1: Replace the `<style>` block**

Replace the existing `<style>` block (lines 66-113) with:

```svelte
<style>
  .room-panel {
    width: 200px;
    background: var(--surface);
    border-left: 1px solid var(--border);
    padding: var(--space-3);
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    flex-shrink: 0;
    overflow-y: auto;
  }
  h2 {
    margin: 0;
    font-size: 13px;
    color: var(--text);
    font-weight: 600;
  }
  label {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }
  span {
    font-size: 11px;
    color: var(--text-muted);
  }
  input,
  select {
    background: var(--surface-alt);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text);
    padding: 4px 6px;
    font-size: 12px;
    font-family: inherit;
  }
  input:focus,
  select:focus {
    outline: none;
    border-color: var(--accent);
  }
  .area-display {
    margin: 0;
    font-size: 12px;
    color: var(--text-muted);
  }
</style>
```

- [ ] **Step 2: Run the full suite**

```bash
npm test -- --run
```
Expected: `Tests 159 passed (159)` (no test file exists for `RoomPanel.svelte`).

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/RoomPanel.svelte
git commit -m "feat(editor): token-migrate RoomPanel colors"
```

---

### Task 6: Token-migrate `ItemPickerPanel.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/ItemPickerPanel.svelte:116-152` (entire `<style>` block)
- Test (existing, must keep passing unmodified): `packages/editor/test/ItemPickerPanel.test.ts`

This file has 12 existing tests asserting on class names (`.section-header`, `.section-body`, `.item-row`, `.search`, `.group-title`, `.item-name`, `.item-emoji`, `.dragging`, `.placed`). None of those class names change in this task — only the color/radius/spacing *values* inside the `<style>` block change, so no test code needs editing.

- [ ] **Step 1: Replace the `<style>` block**

Replace the existing `<style>` block (lines 116-152) with:

```svelte
<style>
  .panel {
    width: 220px; height: 100%; background: var(--surface); border-left: 1px solid var(--border);
    display: flex; flex-direction: column; font-size: 12px; color: var(--text-muted);
    flex-shrink: 0; overflow: hidden;
  }
  .search {
    margin: var(--space-2) var(--space-2); padding: var(--space-1) var(--space-2);
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text-muted);
    border-radius: var(--radius-sm); font-size: 11px; flex-shrink: 0;
  }
  .section { border-bottom: 1px solid var(--border); flex: 1; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
  .section-header {
    width: 100%; display: flex; align-items: center; gap: 6px;
    padding: var(--space-2) var(--space-3); background: var(--surface-alt); border: none; color: var(--text);
    cursor: pointer; font-size: 11px; font-weight: 600; text-align: left;
    flex-shrink: 0;
  }
  .section-header:hover { background: var(--surface-hover); }
  .section-count { margin-left: auto; color: var(--text-faint); font-size: 10px; }
  .chevron { color: var(--text-faint); font-size: 9px; flex-shrink: 0; }
  .section-body { overflow-y: auto; flex: 1; min-height: 0; }
  .group-title {
    color: var(--text-faint); font-size: 9px; text-transform: uppercase;
    letter-spacing: .05em; padding: 4px 10px 2px;
  }
  .item-row {
    display: flex; align-items: center; gap: 8px; padding: 5px 10px;
    cursor: grab; user-select: none; border-radius: var(--radius-sm); margin: 1px 4px;
  }
  .item-row:hover { background: var(--surface-hover); }
  .item-row.placed { opacity: .45; }
  .item-row.dragging { opacity: .5; background: var(--surface-hover); }
  .item-emoji { font-size: 14px; flex-shrink: 0; }
  .item-name { font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .empty { color: var(--text-faint); font-size: 10px; padding: 8px 10px; }
</style>
```

- [ ] **Step 2: Run the full suite, confirm `ItemPickerPanel` tests specifically still pass**

```bash
npm test -- --run ItemPickerPanel
```
Expected: `Tests 12 passed (12)` (all `ItemPickerPanel.test.ts` tests, unchanged).

Then run the whole suite:
```bash
npm test -- --run
```
Expected: `Tests 159 passed (159)`.

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/ItemPickerPanel.svelte
git commit -m "feat(editor): token-migrate ItemPickerPanel colors"
```

---

### Task 7: Token-migrate `Grid.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/Grid.svelte:42-47` (entire `<style>` block)

- [ ] **Step 1: Replace the `<style>` block**

Replace the existing `<style>` block (lines 42-47) with:

```svelte
<style>
  .grid-line {
    stroke: var(--canvas-grid);
    stroke-width: 1;
  }
</style>
```

- [ ] **Step 2: Run the full suite**

```bash
npm test -- --run
```
Expected: `Tests 159 passed (159)` (no test file exists for `Grid.svelte`; `Canvas.test.ts` renders `Grid` indirectly but asserts no color values, per the earlier audit of that test file).

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/Grid.svelte
git commit -m "feat(editor): token-migrate Grid stroke color"
```

---

### Task 8: Token-migrate `WallShape.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/WallShape.svelte:53-63` (entire `<style>` block)

- [ ] **Step 1: Replace the `<style>` block**

Replace the existing `<style>` block (lines 53-63) with:

```svelte
<style>
  .wall {
    fill: var(--canvas-wall);
    stroke: var(--canvas-wall);
    cursor: pointer;
  }
  .wall.selected {
    fill: var(--canvas-wall-selected);
    stroke: var(--canvas-wall-selected);
  }
</style>
```

- [ ] **Step 2: Run the full suite**

```bash
npm test -- --run
```
Expected: `Tests 159 passed (159)`.

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/WallShape.svelte
git commit -m "feat(editor): token-migrate WallShape colors"
```

---

### Task 9: Token-migrate `DividerShape.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/DividerShape.svelte:46-57` (entire `<style>` block)

- [ ] **Step 1: Replace the `<style>` block**

Replace the existing `<style>` block (lines 46-57) with:

```svelte
<style>
  .divider {
    stroke: var(--canvas-divider);
    stroke-width: 2;
    stroke-dasharray: 6 4;
    cursor: pointer;
  }
  .divider.selected {
    stroke: var(--canvas-wall-selected);
    stroke-width: 3;
  }
</style>
```

- [ ] **Step 2: Run the full suite**

```bash
npm test -- --run
```
Expected: `Tests 159 passed (159)`.

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/DividerShape.svelte
git commit -m "feat(editor): token-migrate DividerShape colors"
```

---

### Task 10: Token-migrate `RoomShape.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/RoomShape.svelte:64-83` (entire `<style>` block)

- [ ] **Step 1: Replace the `<style>` block**

Replace the existing `<style>` block (lines 64-83) with:

```svelte
<style>
  .room {
    fill: var(--canvas-room-fill);
    fill-opacity: 0.5;
    stroke: none;
    cursor: pointer;
  }
  .room.selected {
    fill: var(--canvas-room-fill-selected);
    fill-opacity: 0.6;
    stroke: var(--canvas-wall-selected);
    stroke-width: 2;
  }
  .room-label {
    fill: var(--canvas-label);
    font-size: 12px;
    dominant-baseline: middle;
    pointer-events: none;
  }
</style>
```

- [ ] **Step 2: Run the full suite**

```bash
npm test -- --run
```
Expected: `Tests 159 passed (159)`.

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/RoomShape.svelte
git commit -m "feat(editor): token-migrate RoomShape colors"
```

---

### Task 11: Token-migrate `OpeningShape.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/OpeningShape.svelte:92-175` (markup `fill`/`stroke` attributes on lines 95, 110, 123, 133, plus the entire `<style>` block on lines 164-175)

- [ ] **Step 1: Update the gap-fill attribute**

Find (line 92-101):

```svelte
{#if dir.length >= 1e-9}
  <polygon
    points={gapPoints}
    fill="#1c1c1c"
    stroke="none"
    class:selected-gap={selected}
    onclick={handleClick}
    role="button"
    tabindex="0"
  />
```

Replace `fill="#1c1c1c"` with `fill="var(--canvas-bg)"`:

```svelte
{#if dir.length >= 1e-9}
  <polygon
    points={gapPoints}
    fill="var(--canvas-bg)"
    stroke="none"
    class:selected-gap={selected}
    onclick={handleClick}
    role="button"
    tabindex="0"
  />
```

- [ ] **Step 2: Update the window stroke attribute**

Find (lines 103-115):

```svelte
  {#if opening.type === "window"}
    <line
      class="window-sym"
      x1={sp1.x}
      y1={sp1.y}
      x2={sp2.x}
      y2={sp2.y}
      stroke={selected ? "#5af" : "#8cf"}
      stroke-width="3"
      onclick={handleClick}
      role="button"
      tabindex="0"
    />
```

Replace the `stroke` line:

```svelte
  {#if opening.type === "window"}
    <line
      class="window-sym"
      x1={sp1.x}
      y1={sp1.y}
      x2={sp2.x}
      y2={sp2.y}
      stroke={selected ? "var(--canvas-wall-selected)" : "var(--canvas-opening-window)"}
      stroke-width="3"
      onclick={handleClick}
      role="button"
      tabindex="0"
    />
```

- [ ] **Step 3: Update the door-leaf and door-arc stroke attributes**

Find (lines 116-139):

```svelte
  {:else if opening.type === "door" && doorData}
    <line
      class="door-leaf"
      x1={doorData.hinge.x}
      y1={doorData.hinge.y}
      x2={doorData.openEnd.x}
      y2={doorData.openEnd.y}
      stroke={selected ? "#5af" : "#eea"}
      stroke-width="2"
      onclick={handleClick}
      role="button"
      tabindex="0"
    />
    <path
      class="door-arc"
      d="M {doorData.other.x} {doorData.other.y} A {doorData.radius} {doorData.radius} 0 0 {doorData.sweep} {doorData.openEnd.x} {doorData.openEnd.y}"
      fill="none"
      stroke={selected ? "#5af" : "#eea"}
      stroke-width="1"
      stroke-dasharray="4 2"
      onclick={handleClick}
      role="button"
      tabindex="0"
    />
  {/if}
```

Replace both `stroke` lines:

```svelte
  {:else if opening.type === "door" && doorData}
    <line
      class="door-leaf"
      x1={doorData.hinge.x}
      y1={doorData.hinge.y}
      x2={doorData.openEnd.x}
      y2={doorData.openEnd.y}
      stroke={selected ? "var(--canvas-wall-selected)" : "var(--canvas-opening-door)"}
      stroke-width="2"
      onclick={handleClick}
      role="button"
      tabindex="0"
    />
    <path
      class="door-arc"
      d="M {doorData.other.x} {doorData.other.y} A {doorData.radius} {doorData.radius} 0 0 {doorData.sweep} {doorData.openEnd.x} {doorData.openEnd.y}"
      fill="none"
      stroke={selected ? "var(--canvas-wall-selected)" : "var(--canvas-opening-door)"}
      stroke-width="1"
      stroke-dasharray="4 2"
      onclick={handleClick}
      role="button"
      tabindex="0"
    />
  {/if}
```

- [ ] **Step 4: Replace the `<style>` block**

Replace the existing `<style>` block (lines 164-175) with:

```svelte
<style>
  .selected-gap {
    fill: var(--canvas-selected-fill);
  }

  .handle {
    fill: var(--canvas-wall-selected);
    stroke: var(--text);
    stroke-width: 1.5;
    cursor: ew-resize;
  }
</style>
```

- [ ] **Step 5: Run the full suite**

```bash
npm test -- --run
```
Expected: `Tests 159 passed (159)`.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/OpeningShape.svelte
git commit -m "feat(editor): token-migrate OpeningShape colors"
```

---

### Task 12: Token-migrate `SelectionHandles.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/SelectionHandles.svelte:40-47` (entire `<style>` block)

- [ ] **Step 1: Replace the `<style>` block**

Replace the existing `<style>` block (lines 40-47) with:

```svelte
<style>
  .handle {
    fill: var(--canvas-wall-selected);
    stroke: var(--text);
    stroke-width: 1;
    cursor: grab;
  }
</style>
```

- [ ] **Step 2: Run the full suite**

```bash
npm test -- --run
```
Expected: `Tests 159 passed (159)`.

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/SelectionHandles.svelte
git commit -m "feat(editor): token-migrate SelectionHandles colors"
```

---

### Task 13: Token-migrate `DrawPreview.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/DrawPreview.svelte:60-78` (entire `<style>` block)

- [ ] **Step 1: Replace the `<style>` block**

Replace the existing `<style>` block (lines 60-78) with:

```svelte
<style>
  .rubber-band {
    stroke: var(--canvas-draw-preview);
    stroke-width: 2;
    stroke-dasharray: 6 4;
  }
  .length-label {
    fill: var(--canvas-label);
    font-size: 11px;
  }
  .chain-start {
    fill: var(--canvas-draw-preview);
  }
  .snap-ring {
    fill: none;
    stroke: var(--canvas-wall-selected);
    stroke-width: 2;
  }
</style>
```

- [ ] **Step 2: Run the full suite**

```bash
npm test -- --run
```
Expected: `Tests 159 passed (159)`.

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/DrawPreview.svelte
git commit -m "feat(editor): token-migrate DrawPreview colors"
```

---

### Task 14: Token-migrate `Canvas.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/Canvas.svelte:243-266` (the `openingPreview` line's `stroke` attribute, and the `<style>` block)
- Test (existing, must keep passing unmodified): `packages/editor/test/Canvas.test.ts`

- [ ] **Step 1: Update the `openingPreview` line's stroke attribute**

Find (lines 243-255):

```svelte
  {#if openingPreview}
    <line
      x1={openingPreview.sp1.x}
      y1={openingPreview.sp1.y}
      x2={openingPreview.sp2.x}
      y2={openingPreview.sp2.y}
      stroke={tool === "door" ? "#eea" : "#8cf"}
      stroke-width="6"
      stroke-dasharray="4 2"
      opacity="0.6"
      pointer-events="none"
    />
  {/if}
```

Replace the `stroke` line:

```svelte
  {#if openingPreview}
    <line
      x1={openingPreview.sp1.x}
      y1={openingPreview.sp1.y}
      x2={openingPreview.sp2.x}
      y2={openingPreview.sp2.y}
      stroke={tool === "door" ? "var(--canvas-opening-door)" : "var(--canvas-opening-window)"}
      stroke-width="6"
      stroke-dasharray="4 2"
      opacity="0.6"
      pointer-events="none"
    />
  {/if}
```

- [ ] **Step 2: Replace the `<style>` block**

Replace the existing `<style>` block (lines 261-266) with:

```svelte
<style>
  .canvas {
    background: var(--canvas-bg);
    display: block;
  }
</style>
```

- [ ] **Step 3: Run the full suite, confirm `Canvas` tests specifically still pass**

```bash
npm test -- --run Canvas.test
```
Expected: all tests in `Canvas.test.ts` pass (count unchanged from baseline).

Then run the whole suite:
```bash
npm test -- --run
```
Expected: `Tests 159 passed (159)`.

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/Canvas.svelte
git commit -m "feat(editor): token-migrate Canvas background and opening-preview stroke"
```

---

## Manual verification (no automated tooling exists for this)

After all 14 tasks are committed, this phase's actual visual correctness can only be confirmed by a human opening the app in a browser, per the design doc's Testing section ("No visual regression tooling exists in this repo today... verification per phase is manual"). Specifically check, in **both** light and dark mode (toggle button in the topbar):

1. Floor-plan canvas background, grid lines, walls, and rooms render with adequate contrast (light mode = pale "blueprint on paper" look; dark mode = same as before this phase).
2. Selecting a wall, divider, room, or opening highlights it clearly in both themes.
3. Drawing a new wall/divider shows the orange rubber-band preview and snap ring clearly in both themes.
4. The selection-handle dots (small circles at wall endpoints, and door/window resize handles) are visible against the canvas in both themes — this is the one spot most likely to need a follow-up tweak, since the halo around each handle now uses `--text`, which the design doc explicitly flagged as needing re-verification.
5. `ItemPickerPanel`, `RoomPanel`, `Toolbar`, `FloorSwitcher`, and `LayersDropdown` all read as part of the same light/dark system as the rest of the chrome (no leftover dark-only colors), while staying visually compact relative to the topbar/modals.

If anything looks wrong, file it as a follow-up — do not block landing this phase on pixel-perfect manual sign-off, since the design doc explicitly defers this kind of tuning to "during implementation" review.

---

## Final task: holistic review and finish

After Task 14, dispatch a final code-reviewer subagent across the whole branch diff (all 14 commits), then use `superpowers:finishing-a-development-branch` to land the work, exactly as was done for Phase 1.
