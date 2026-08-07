# Compact Module Toolbars + KPI Rows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the toolbar (search, filters, quick toggle, add button) and the KPI/chart row above each module's table fit on far fewer lines on mobile, by consolidating dropdown filters behind a shared filter-icon button + modal and switching the Add button to icon-only.

**Architecture:** Two new/changed shared `ui/` atoms (`Button` gets an `iconOnly` size variant, new `FilterButton` opens a `Modal` containing a page's dropdown filters) plus a centralized responsive fix in `StatTileRow`. Each of the 8 module pages (Chores, Consumables, Inventory, Works, Costs, Contacts, Properties, Insurance) then gets the same toolbar shape and, where it has a chart + loose stat tiles, a KPI markup tweak so the tiles wrap onto one row instead of stacking one-per-line. `BuildPage` needs no page-level change — it already uses `StatTileRow direction="row"` and benefits automatically from the centralized fix.

**Tech Stack:** Svelte 5 (runes), TypeScript, Vitest + `svelte`'s `mount`/`unmount`/`flushSync` test harness (no Testing Library). Run tests from `packages/editor` with `npx vitest run <path>`.

## Global Constraints

- Filtering *logic* (which items match which filter) must not change anywhere — only where the filter controls render.
- Keep using existing i18n keys (`svelte-i18n`, `$_('key')`) for all copy; the one new key needed (`common.filters`) must be added to both `packages/editor/src/lib/locales/en.json` and `fr.json`.
- No new dependencies / icon library — the filter icon is a small inline SVG using `stroke="currentColor"` so it follows the current theme.
- This is a layout/markup refactor with no new business logic, so most tasks are implement-then-verify-with-the-existing-suite rather than red/green TDD; tasks that add real conditional behavior (`Button` `iconOnly`, the new `FilterButton`) do get a written test first.
- Every page task must end with `npx vitest run test/<Page>.test.ts` passing before commit.

---

### Task 1: `Button.svelte` — icon-only sizing

**Files:**
- Modify: `packages/editor/src/lib/components/ui/Button.svelte`
- Test: `packages/editor/test/Button.test.ts`

**Interfaces:**
- Produces: `Button` gains an `iconOnly?: boolean` prop (default `false`). When `true`, the rendered `<button>` additionally has class `ui-button-icon`.

- [ ] **Step 1: Write the failing test**

Add to `packages/editor/test/Button.test.ts`, inside the `describe("ui/Button", ...)` block:

```ts
  it("applies icon-only sizing when iconOnly is set", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Button, { target, props: { iconOnly: true } });

    const btn = target.querySelector("button")!;
    expect(btn.classList.contains("ui-button-icon")).toBe(true);

    unmount(comp);
    target.remove();
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/Button.test.ts`
Expected: FAIL — `ui-button-icon` class not present (unknown prop `iconOnly` is currently just ignored).

- [ ] **Step 3: Implement**

Replace the full contents of `packages/editor/src/lib/components/ui/Button.svelte` with:

```svelte
<!-- packages/editor/src/lib/components/ui/Button.svelte -->
<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    variant?: "primary" | "secondary" | "ghost" | "danger";
    onclick?: () => void;
    disabled?: boolean;
    title?: string;
    iconOnly?: boolean;
    children?: Snippet;
  }
  let { variant = "primary", onclick, disabled = false, title, iconOnly = false, children }: Props = $props();
</script>

<button
  type="button"
  class="ui-button ui-button-{variant}"
  class:ui-button-icon={iconOnly}
  {disabled}
  {title}
  {onclick}
>
  {@render children?.()}
</button>

<style>
  .ui-button {
    font-family: var(--font-sans);
    font-size: 12px; font-weight: 600;
    border: none; border-radius: var(--radius-pill);
    padding: 8px 18px; cursor: pointer;
    display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  }
  .ui-button:disabled { opacity: 0.5; cursor: default; }

  .ui-button-icon {
    padding: 0;
    width: 36px; height: 36px; min-width: 36px;
    font-size: 15px;
    flex-shrink: 0;
  }

  .ui-button-primary { background: var(--accent); color: var(--accent-contrast); }
  .ui-button-primary:hover:not(:disabled) { opacity: 0.85; }

  .ui-button-secondary {
    background: var(--surface); color: var(--text);
    border: 1px solid var(--border);
  }
  .ui-button-secondary:hover:not(:disabled) { background: var(--surface-hover); }

  .ui-button-ghost { background: transparent; color: var(--text-muted); }
  .ui-button-ghost:hover:not(:disabled) { background: var(--surface-hover); color: var(--text); }

  .ui-button-danger { background: var(--danger); color: var(--accent-contrast); }
  .ui-button-danger:hover:not(:disabled) { opacity: 0.85; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/Button.test.ts`
Expected: PASS (all 5 tests, including the new one).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/Button.svelte packages/editor/test/Button.test.ts
git commit -m "feat(ui): add icon-only sizing variant to Button"
```

---

### Task 2: New `FilterButton.svelte` shared component

**Files:**
- Create: `packages/editor/src/lib/components/ui/FilterButton.svelte`
- Test: Create `packages/editor/test/FilterButton.test.ts`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `FilterButton` component with props `{ active?: boolean; onclick: () => void; title: string }`. Renders a `<button aria-label={title} title={title}>` containing a funnel SVG icon and, when `active` is true, a `<span class="badge">`. Later page tasks import this from `./ui/FilterButton.svelte`.

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/FilterButton.test.ts`:

```ts
import { describe, it, expect, vi } from "vitest";
import { mount, unmount } from "svelte";
import FilterButton from "../src/lib/components/ui/FilterButton.svelte";

describe("ui/FilterButton", () => {
  it("calls onclick when clicked", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onclick = vi.fn();
    const comp = mount(FilterButton, { target, props: { onclick, title: "Filters" } });

    target.querySelector("button")!.click();
    expect(onclick).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });

  it("shows no badge by default", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(FilterButton, { target, props: { onclick: () => {}, title: "Filters" } });

    expect(target.querySelector(".badge")).toBeNull();

    unmount(comp);
    target.remove();
  });

  it("shows a badge when active", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(FilterButton, { target, props: { onclick: () => {}, title: "Filters", active: true } });

    expect(target.querySelector(".badge")).not.toBeNull();

    unmount(comp);
    target.remove();
  });

  it("sets title and aria-label for accessibility", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(FilterButton, { target, props: { onclick: () => {}, title: "Filters" } });

    const btn = target.querySelector("button")!;
    expect(btn.getAttribute("title")).toBe("Filters");
    expect(btn.getAttribute("aria-label")).toBe("Filters");

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/FilterButton.test.ts`
Expected: FAIL — cannot find module `../src/lib/components/ui/FilterButton.svelte`.

- [ ] **Step 3: Implement**

Create `packages/editor/src/lib/components/ui/FilterButton.svelte`:

```svelte
<!-- packages/editor/src/lib/components/ui/FilterButton.svelte -->
<script lang="ts">
  interface Props {
    active?: boolean;
    onclick: () => void;
    title: string;
  }
  let { active = false, onclick, title }: Props = $props();
</script>

<button type="button" class="ui-filter-button" class:active {onclick} {title} aria-label={title}>
  <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
    <path
      d="M2 3h12l-4.5 5.5v4l-3 1.5v-5.5z"
      fill="none" stroke="currentColor" stroke-width="1.4"
      stroke-linecap="round" stroke-linejoin="round"
    />
  </svg>
  {#if active}<span class="badge"></span>{/if}
</button>

<style>
  .ui-filter-button {
    position: relative;
    display: inline-flex; align-items: center; justify-content: center;
    width: 36px; height: 36px; flex-shrink: 0;
    background: var(--surface-alt); border: 1px solid var(--border); border-radius: var(--radius-md);
    color: var(--text-muted); cursor: pointer;
  }
  .ui-filter-button:hover { background: var(--surface-hover); color: var(--text); }
  .ui-filter-button.active { color: var(--accent); border-color: var(--accent); }
  .badge {
    position: absolute; top: -3px; right: -3px;
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--accent); border: 1.5px solid var(--surface);
  }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/FilterButton.test.ts`
Expected: PASS (all 4 tests).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/FilterButton.svelte packages/editor/test/FilterButton.test.ts
git commit -m "feat(ui): add FilterButton component for consolidated filter modals"
```

---

### Task 3: `StatTileRow.svelte` — mobile wrap fix + tighter grid

**Files:**
- Modify: `packages/editor/src/lib/components/ui/StatTileRow.svelte`

**Interfaces:**
- Consumes: nothing new.
- Produces: no prop/markup changes — `direction="column"` rows now wrap into a horizontal flex-wrap row at `max-width: 700px` instead of stacking vertically; `direction="row"` (the default) rows use a tighter `minmax(110px, 1fr)` grid track so more tiles fit per line on narrow phones. Existing consumers (`InsurancePage`, `InventoryPage`, `WorksPage` before Task 7, `PropertiesPage`, `ContactsPage`, `BuildPage`) get this for free.

- [ ] **Step 1: Implement**

Replace the `<style>` block of `packages/editor/src/lib/components/ui/StatTileRow.svelte` with:

```svelte
<style>
  .ui-stat-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
    gap: var(--space-3);
  }
  .ui-stat-row.column {
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    width: 200px;
  }
  @media (max-width: 700px) {
    .ui-stat-row.column {
      flex-direction: row;
      flex-wrap: wrap;
      width: auto;
    }
    .ui-stat-row.column :global(.ui-stat-tile) {
      flex: 1 1 90px;
    }
  }
</style>
```

(The `<script>` and markup above it are unchanged.)

- [ ] **Step 2: Verify existing tests still pass**

Run: `cd packages/editor && npx vitest run test/StatTileRow.test.ts`
Expected: PASS — these tests only assert the `.column` class is applied, which is unchanged; the new behavior is a `@media` rule not exercised by jsdom's default viewport, so no existing assertion can regress.

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/ui/StatTileRow.svelte
git commit -m "fix(ui): wrap StatTileRow column tiles into a row on mobile"
```

---

### Task 4: Add `common.filters` i18n key

**Files:**
- Modify: `packages/editor/src/lib/locales/en.json:170`
- Modify: `packages/editor/src/lib/locales/fr.json:170`

**Interfaces:**
- Produces: `$_('common.filters')` resolves to `"Filters"` (en) / `"Filtres"` (fr). Every page task below uses this key for the `FilterButton` `title` and the filter `Modal` `title`.

- [ ] **Step 1: Implement**

In `packages/editor/src/lib/locales/en.json`, inside the `"common"` object, change:

```json
    "add": "Add",
```

to:

```json
    "add": "Add",
    "filters": "Filters",
```

In `packages/editor/src/lib/locales/fr.json`, inside the `"common"` object, change:

```json
    "add": "Ajouter",
```

to:

```json
    "add": "Ajouter",
    "filters": "Filtres",
```

- [ ] **Step 2: Verify**

Run: `cd packages/editor && npx vitest run test/i18nCompleteness.test.ts`
Expected: PASS — confirms the new key exists with the same shape in both locale files.

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json
git commit -m "i18n: add common.filters key"
```

---

### Task 5: `ChoresPage.svelte` — compact toolbar + KPI row

**Files:**
- Modify: `packages/editor/src/lib/components/ChoresPage.svelte`
- Test: `packages/editor/test/ChoresPage.test.ts`

**Interfaces:**
- Consumes: `FilterButton` (Task 2), `Button` `iconOnly` (Task 1), `common.filters` (Task 4).

- [ ] **Step 1: Add imports and state**

In `packages/editor/src/lib/components/ChoresPage.svelte`, add to the import block (after the `Button`/`Input` imports around line 6-7):

```ts
  import Modal from "./ui/Modal.svelte";
  import FilterButton from "./ui/FilterButton.svelte";
```

After the existing `let dueFilter = $state<"all" | "attention">("attention");` (around line 45), add:

```ts
  let filterModalOpen = $state(false);
  const filtersActive = $derived(roomFilter !== "" || scheduleFilter !== "");
```

- [ ] **Step 2: Restructure the KPI row markup**

Replace (around lines 203-212):

```svelte
    <div class="chart-card-wrap">
      <Card style="flex:1; min-width:0;">
        <div class="chart-label">{$_('chores.page.scheduleHealth')}</div>
        <HorizontalBarChart segments={healthBreakdown} />
      </Card>
      <StatTile label={$_('chores.page.active')} value={totalAssignments} />
      <StatTile label={$_('chores.page.overdue')} value={`${overduePct}%`} variant="danger" />
      <StatTile label={$_('chores.page.onTrack')} value={`${onTrackPct}%`} variant="success" />
    </div>
```

with:

```svelte
    <div class="chart-card-wrap">
      <Card style="flex:1; min-width:0;">
        <div class="chart-label">{$_('chores.page.scheduleHealth')}</div>
        <HorizontalBarChart segments={healthBreakdown} />
      </Card>
      <div class="stat-tiles">
        <StatTile label={$_('chores.page.active')} value={totalAssignments} />
        <StatTile label={$_('chores.page.overdue')} value={`${overduePct}%`} variant="danger" />
        <StatTile label={$_('chores.page.onTrack')} value={`${onTrackPct}%`} variant="success" />
      </div>
    </div>
```

- [ ] **Step 3: Replace the toolbar and add the filter modal**

Replace (around lines 216-238):

```svelte
    <div class="toolbar">
      <Input placeholder={$_('chores.page.search')} bind:value={searchQuery} />
      <select class="native-input" bind:value={roomFilter}>
        <option value="">{$_('chores.page.allRooms')}</option>
        {#each allRooms as room}
          <option value={room.id}>{room.label}</option>
        {/each}
      </select>
      <select class="native-input" bind:value={scheduleFilter}>
        <option value="">{$_('chores.page.allSchedules')}</option>
        <option value="daily">{$_('chores.schedule.daily')}</option>
        <option value="weekly">{$_('chores.schedule.weekly')}</option>
        <option value="monthly">{$_('chores.schedule.monthly')}</option>
        <option value="nth_weekday">{$_('chores.schedule.nthWeekday')}</option>
        <option value="yearly">{$_('chores.schedule.yearly')}</option>
        <option value="adaptive">{$_('chores.schedule.adaptive')}</option>
      </select>
      <div class="filter-toggle">
        <button class="toggle-btn" class:active={dueFilter === "all"} title={$_('chores.page.allChores')} onclick={() => { dueFilter = "all"; }}>☰</button>
        <button class="toggle-btn" class:active={dueFilter === "attention"} title={$_('chores.page.needsAttentionTitle')} onclick={() => { dueFilter = "attention"; }}>⚠</button>
      </div>
      <Button onclick={() => onnewchore?.()}>＋ {$_('chores.page.addChore')}</Button>
    </div>
```

with:

```svelte
    <div class="toolbar">
      <Input placeholder={$_('chores.page.search')} bind:value={searchQuery} />
      <FilterButton active={filtersActive} title={$_('common.filters')} onclick={() => { filterModalOpen = true; }} />
      <div class="filter-toggle">
        <button class="toggle-btn" class:active={dueFilter === "all"} title={$_('chores.page.allChores')} onclick={() => { dueFilter = "all"; }}>☰</button>
        <button class="toggle-btn" class:active={dueFilter === "attention"} title={$_('chores.page.needsAttentionTitle')} onclick={() => { dueFilter = "attention"; }}>⚠</button>
      </div>
      <Button iconOnly title={$_('chores.page.addChore')} onclick={() => onnewchore?.()}>＋</Button>
    </div>

    <Modal open={filterModalOpen} title={$_('common.filters')} onclose={() => { filterModalOpen = false; }} width="360px">
      <div class="filter-modal-body">
        <select class="native-input" bind:value={roomFilter}>
          <option value="">{$_('chores.page.allRooms')}</option>
          {#each allRooms as room}
            <option value={room.id}>{room.label}</option>
          {/each}
        </select>
        <select class="native-input" bind:value={scheduleFilter}>
          <option value="">{$_('chores.page.allSchedules')}</option>
          <option value="daily">{$_('chores.schedule.daily')}</option>
          <option value="weekly">{$_('chores.schedule.weekly')}</option>
          <option value="monthly">{$_('chores.schedule.monthly')}</option>
          <option value="nth_weekday">{$_('chores.schedule.nthWeekday')}</option>
          <option value="yearly">{$_('chores.schedule.yearly')}</option>
          <option value="adaptive">{$_('chores.schedule.adaptive')}</option>
        </select>
      </div>
    </Modal>
```

- [ ] **Step 4: Update the CSS**

Replace (around lines 358-374):

```css
  .chart-card-wrap { display: flex; gap: var(--space-3); align-items: stretch; padding: var(--space-4); flex-shrink: 0; }
  .chart-card-wrap > :global(.ui-stat-tile) { flex: 0 0 140px; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }

  @media (max-width: 700px) {
    .chart-card-wrap { flex-direction: column; }
    .chart-card-wrap > :global(.ui-stat-tile) { flex: 0 0 auto; }
    .page { overflow-y: auto; }
    .table-card-wrap { flex: none; min-height: auto; }
    .table-card-wrap :global(.ui-card) { flex: none !important; width: 100%; overflow: visible !important; min-height: auto !important; }
    .table-wrapper { flex: none !important; overflow-y: visible !important; }
  }
```

with:

```css
  .chart-card-wrap { display: flex; gap: var(--space-3); align-items: stretch; padding: var(--space-4); flex-shrink: 0; }
  .stat-tiles { display: flex; gap: var(--space-3); flex-shrink: 0; }
  .stat-tiles :global(.ui-stat-tile) { flex: 0 0 140px; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }

  .filter-modal-body { display: flex; flex-direction: column; gap: var(--space-3); }
  .filter-modal-body .native-input { width: 100%; }

  @media (max-width: 700px) {
    .chart-card-wrap { flex-direction: column; }
    .stat-tiles { flex-wrap: wrap; }
    .stat-tiles :global(.ui-stat-tile) { flex: 1 1 90px; }
    .page { overflow-y: auto; }
    .table-card-wrap { flex: none; min-height: auto; }
    .table-card-wrap :global(.ui-card) { flex: none !important; width: 100%; overflow: visible !important; min-height: auto !important; }
    .table-wrapper { flex: none !important; overflow-y: visible !important; }
  }
```

- [ ] **Step 5: Update the "schedule filter" test to open the filter modal first**

In `packages/editor/test/ChoresPage.test.ts`, in the `"ChoresPage — schedule filter"` describe block, after `flushSync();` (the one right after `mount`, around line 159) and before the `const scheduleSelect = ...` line, insert:

```ts
    (target.querySelector('button[aria-label="Filters"]') as HTMLButtonElement).click();
    flushSync();
```

So the test body reads:

```ts
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    (target.querySelector('button[aria-label="Filters"]') as HTMLButtonElement).click();
    flushSync();

    const scheduleSelect = Array.from(target.querySelectorAll("select")).find(
      (s) => Array.from(s.options).some((o) => o.value === "adaptive"),
    ) as HTMLSelectElement;
```

- [ ] **Step 6: Run the full test file**

Run: `cd packages/editor && npx vitest run test/ChoresPage.test.ts`
Expected: PASS (all tests, including the updated schedule-filter test).

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/components/ChoresPage.svelte packages/editor/test/ChoresPage.test.ts
git commit -m "feat(chores): compact toolbar behind filter modal, wrap stat tiles on mobile"
```

---

### Task 6: `ConsumablesPage.svelte` — compact toolbar + KPI row

**Files:**
- Modify: `packages/editor/src/lib/components/ConsumablesPage.svelte`

**Interfaces:**
- Consumes: `FilterButton` (Task 2), `Button` `iconOnly` (Task 1), `common.filters` (Task 4).

- [ ] **Step 1: Add imports and state**

Add to the imports (after `Card`/`HorizontalBarChart`/`StatTile` imports, around line 11-13):

```ts
  import Modal from "./ui/Modal.svelte";
  import FilterButton from "./ui/FilterButton.svelte";
```

After `let attentionFilter = $state(false);` (around line 30), add:

```ts
  let filterModalOpen = $state(false);
  const filtersActive = $derived(categoryFilter !== "");
```

- [ ] **Step 2: Restructure the KPI row markup**

Replace (around lines 116-123):

```svelte
    <div class="chart-card-wrap">
      <Card style="flex:1; min-width:0;">
        <div class="chart-label">{$_('consumables.page.stockStatus', { values: { n: store.consumables.length } })}</div>
        <HorizontalBarChart segments={stockBreakdown} />
      </Card>
      <StatTile label={$_('consumables.page.low')} value={lowStockCount} variant="warning" />
      <StatTile label={$_('consumables.page.empty')} value={emptyStockCount} variant="danger" />
    </div>
```

with:

```svelte
    <div class="chart-card-wrap">
      <Card style="flex:1; min-width:0;">
        <div class="chart-label">{$_('consumables.page.stockStatus', { values: { n: store.consumables.length } })}</div>
        <HorizontalBarChart segments={stockBreakdown} />
      </Card>
      <div class="stat-tiles">
        <StatTile label={$_('consumables.page.low')} value={lowStockCount} variant="warning" />
        <StatTile label={$_('consumables.page.empty')} value={emptyStockCount} variant="danger" />
      </div>
    </div>
```

- [ ] **Step 3: Replace the toolbar and add the filter modal**

Replace (around lines 128-151):

```svelte
    <div class="toolbar">
      <Input placeholder={$_('chores.page.search')} bind:value={searchQuery} />
      <select class="native-select" bind:value={categoryFilter}>
        <option value="">{$_('costs.page.allCategories')}</option>
        {#each settingsStore.consumableCategories as cat}
          <option value={cat.id}>{cat.emoji} {cat.name}</option>
        {/each}
      </select>
      <div class="filter-toggle">
        <button
          class="toggle-btn"
          class:active={!attentionFilter}
          onclick={() => { attentionFilter = false; }}
          title={$_('consumables.page.all')}
        >☰</button>
        <button
          class="toggle-btn"
          class:active={attentionFilter}
          onclick={() => { attentionFilter = true; }}
          title={$_('chores.page.needsAttentionTitle')}
        >⚠</button>
      </div>
      <Button onclick={() => { showCreate = true; }}>＋ {$_('consumables.page.addConsumable')}</Button>
    </div>
```

with:

```svelte
    <div class="toolbar">
      <Input placeholder={$_('chores.page.search')} bind:value={searchQuery} />
      <FilterButton active={filtersActive} title={$_('common.filters')} onclick={() => { filterModalOpen = true; }} />
      <div class="filter-toggle">
        <button
          class="toggle-btn"
          class:active={!attentionFilter}
          onclick={() => { attentionFilter = false; }}
          title={$_('consumables.page.all')}
        >☰</button>
        <button
          class="toggle-btn"
          class:active={attentionFilter}
          onclick={() => { attentionFilter = true; }}
          title={$_('chores.page.needsAttentionTitle')}
        >⚠</button>
      </div>
      <Button iconOnly title={$_('consumables.page.addConsumable')} onclick={() => { showCreate = true; }}>＋</Button>
    </div>

    <Modal open={filterModalOpen} title={$_('common.filters')} onclose={() => { filterModalOpen = false; }} width="360px">
      <div class="filter-modal-body">
        <select class="native-select" bind:value={categoryFilter}>
          <option value="">{$_('costs.page.allCategories')}</option>
          {#each settingsStore.consumableCategories as cat}
            <option value={cat.id}>{cat.emoji} {cat.name}</option>
          {/each}
        </select>
      </div>
    </Modal>
```

- [ ] **Step 4: Update the CSS**

Replace (around lines 238-254):

```css
  .chart-card-wrap { display: flex; gap: var(--space-3); align-items: stretch; padding: var(--space-4); flex-shrink: 0; }
  .chart-card-wrap > :global(.ui-stat-tile) { flex: 0 0 140px; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }

  @media (max-width: 700px) {
    .chart-card-wrap { flex-direction: column; }
    .chart-card-wrap > :global(.ui-stat-tile) { flex: 0 0 auto; }
    .page { overflow-y: auto; }
    .table-card-wrap { flex: none; min-height: auto; }
    .table-card-wrap :global(.ui-card) { flex: none !important; width: 100%; overflow: visible !important; min-height: auto !important; }
    .table-wrapper { flex: none !important; overflow-y: visible !important; }
  }
```

with:

```css
  .chart-card-wrap { display: flex; gap: var(--space-3); align-items: stretch; padding: var(--space-4); flex-shrink: 0; }
  .stat-tiles { display: flex; gap: var(--space-3); flex-shrink: 0; }
  .stat-tiles :global(.ui-stat-tile) { flex: 0 0 140px; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }

  .filter-modal-body { display: flex; flex-direction: column; gap: var(--space-3); }
  .filter-modal-body .native-select { width: 100%; }

  @media (max-width: 700px) {
    .chart-card-wrap { flex-direction: column; }
    .stat-tiles { flex-wrap: wrap; }
    .stat-tiles :global(.ui-stat-tile) { flex: 1 1 90px; }
    .page { overflow-y: auto; }
    .table-card-wrap { flex: none; min-height: auto; }
    .table-card-wrap :global(.ui-card) { flex: none !important; width: 100%; overflow: visible !important; min-height: auto !important; }
    .table-wrapper { flex: none !important; overflow-y: visible !important; }
  }
```

- [ ] **Step 5: Run the full test file**

Run: `cd packages/editor && npx vitest run test/ConsumablesPage.test.ts`
Expected: PASS with no changes needed to the test file (it only interacts with the attention toggle by button text, which stays inline).

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/ConsumablesPage.svelte
git commit -m "feat(consumables): compact toolbar behind filter modal, wrap stat tiles on mobile"
```

---

### Task 7: `InventoryPage.svelte` — compact toolbar

**Files:**
- Modify: `packages/editor/src/lib/components/InventoryPage.svelte`
- Test: `packages/editor/test/InventoryPage.test.ts`

**Interfaces:**
- Consumes: `FilterButton` (Task 2), `Button` `iconOnly` (Task 1), `common.filters` (Task 4), the mobile wrap fix from Task 3 (this page's KPI row already uses `StatTileRow direction="column"`, so no KPI markup change is needed here).

- [ ] **Step 1: Add imports and state**

Add to the imports (after `Card`/`StatTile`/`StatTileRow`/`DonutChart` imports, around line 11-14):

```ts
  import Modal from "./ui/Modal.svelte";
  import FilterButton from "./ui/FilterButton.svelte";
```

After `let storeFilter = $state("");` (around line 58), add:

```ts
  let filterModalOpen = $state(false);
  const filtersActive = $derived(
    roomFilter !== "" || categoryFilter !== "" || ownerFilter !== "" || storeFilter !== ""
  );
```

- [ ] **Step 2: Replace the toolbar and add the filter modal**

Replace (around lines 204-231):

```svelte
    <div class="toolbar">
      <Input bind:value={searchQuery} placeholder={$_('inventory.page.searchItems')} />
      <select class="native-input" bind:value={roomFilter}>
        <option value="">{$_('chores.page.allRooms')}</option>
        {#each allRooms as room}
          <option value={room.id}>{room.label}</option>
        {/each}
      </select>
      <select class="native-input" bind:value={categoryFilter}>
        <option value="">{$_('costs.page.allCategories')}</option>
        {#each allCategories as id}
          <option value={id}>{categoryName(id)}</option>
        {/each}
      </select>
      <select class="native-input" bind:value={ownerFilter}>
        <option value="">{$_('inventory.page.allOwners')}</option>
        {#each allOwnerIds as id}
          <option value={id}>{ownerName(id)}</option>
        {/each}
      </select>
      <select class="native-input" bind:value={storeFilter}>
        <option value="">{$_('inventory.page.allStores')}</option>
        {#each allStoreIds as id}
          <option value={id}>{storeName(id)}</option>
        {/each}
      </select>
      <Button onclick={() => { modalItem = "create"; }}>＋ {$_('inventory.page.addItem')}</Button>
    </div>
```

with:

```svelte
    <div class="toolbar">
      <Input bind:value={searchQuery} placeholder={$_('inventory.page.searchItems')} />
      <FilterButton active={filtersActive} title={$_('common.filters')} onclick={() => { filterModalOpen = true; }} />
      <Button iconOnly title={$_('inventory.page.addItem')} onclick={() => { modalItem = "create"; }}>＋</Button>
    </div>

    <Modal open={filterModalOpen} title={$_('common.filters')} onclose={() => { filterModalOpen = false; }} width="360px">
      <div class="filter-modal-body">
        <select class="native-input" bind:value={roomFilter}>
          <option value="">{$_('chores.page.allRooms')}</option>
          {#each allRooms as room}
            <option value={room.id}>{room.label}</option>
          {/each}
        </select>
        <select class="native-input" bind:value={categoryFilter}>
          <option value="">{$_('costs.page.allCategories')}</option>
          {#each allCategories as id}
            <option value={id}>{categoryName(id)}</option>
          {/each}
        </select>
        <select class="native-input" bind:value={ownerFilter}>
          <option value="">{$_('inventory.page.allOwners')}</option>
          {#each allOwnerIds as id}
            <option value={id}>{ownerName(id)}</option>
          {/each}
        </select>
        <select class="native-input" bind:value={storeFilter}>
          <option value="">{$_('inventory.page.allStores')}</option>
          {#each allStoreIds as id}
            <option value={id}>{storeName(id)}</option>
          {/each}
        </select>
      </div>
    </Modal>
```

- [ ] **Step 3: Update the CSS**

After the `.toolbar :global(.ui-input) { flex: 1; }` rule (around line 346), add:

```css
  .filter-modal-body { display: flex; flex-direction: column; gap: var(--space-3); }
  .filter-modal-body .native-input { width: 100%; }
```

- [ ] **Step 4: Update the owner-filter test to open the filter modal first**

In `packages/editor/test/InventoryPage.test.ts`, in the `"InventoryPage — owner/store filters and columns"` test (around line 117), after `flushSync();` and before `expect(target.textContent).toContain("Alice");`, insert:

```ts
    (target.querySelector('button[aria-label="Filters"]') as HTMLButtonElement).click();
    flushSync();
```

So the relevant part reads:

```ts
    flushSync();
    (target.querySelector('button[aria-label="Filters"]') as HTMLButtonElement).click();
    flushSync();
    expect(target.textContent).toContain("Alice");
    expect(target.textContent).toContain("Bob");
    const ownerSelects = Array.from(target.querySelectorAll("select")).filter((s) =>
      Array.from(s.querySelectorAll("option")).some((o) => o.textContent === "Alice"),
    );
    expect(ownerSelects.length).toBe(1);
```

- [ ] **Step 5: Run the full test file**

Run: `cd packages/editor && npx vitest run test/InventoryPage.test.ts`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/InventoryPage.svelte packages/editor/test/InventoryPage.test.ts
git commit -m "feat(inventory): compact toolbar behind filter modal"
```

---

### Task 8: `WorksPage.svelte` — compact toolbar + merge KPI tiles into one row

**Files:**
- Modify: `packages/editor/src/lib/components/WorksPage.svelte`

**Interfaces:**
- Consumes: `FilterButton` (Task 2), `Button` `iconOnly` (Task 1), `common.filters` (Task 4). Stops using `StatTileRow` (its two `direction="column"` groups are merged into a single locally-styled `.stat-tiles` row so all 4 values wrap together instead of as two separate 2-tile groups).

- [ ] **Step 1: Add imports, remove unused import, add state**

Add to the imports (after `Card`/`StatTile` imports, around line 11-13):

```ts
  import Modal from "./ui/Modal.svelte";
  import FilterButton from "./ui/FilterButton.svelte";
```

Remove the now-unused import (around line 13):

```ts
  import StatTileRow from "./ui/StatTileRow.svelte";
```

After `let categoryFilter = $state("");` (around line 45), add:

```ts
  let filterModalOpen = $state(false);
  const filtersActive = $derived(statusFilter !== "" || categoryFilter !== "");
```

- [ ] **Step 2: Merge the two KPI stat groups into one row**

Replace (around lines 103-116):

```svelte
    <div class="chart-card-wrap">
      <Card style="flex:1; min-width:0;">
        <div class="chart-label">{$_('works.page.houseTimeline')}</div>
        <WorksTimeline works={store.works} onworkclick={handleTimelineClick} />
      </Card>
      <StatTileRow direction="column">
        <StatTile label={$_('works.status.planned')} value={plannedCount} />
        <StatTile label={$_('works.status.inProgress')} value={inProgressCount} />
      </StatTileRow>
      <StatTileRow direction="column">
        <StatTile label={$_('works.status.done')} value={doneCount} />
        <StatTile label={$_('works.page.totalCost')} value={`${fmt(allTimeCost)} €`} />
      </StatTileRow>
    </div>
```

with:

```svelte
    <div class="chart-card-wrap">
      <Card style="flex:1; min-width:0;">
        <div class="chart-label">{$_('works.page.houseTimeline')}</div>
        <WorksTimeline works={store.works} onworkclick={handleTimelineClick} />
      </Card>
      <div class="stat-tiles">
        <StatTile label={$_('works.status.planned')} value={plannedCount} />
        <StatTile label={$_('works.status.inProgress')} value={inProgressCount} />
        <StatTile label={$_('works.status.done')} value={doneCount} />
        <StatTile label={$_('works.page.totalCost')} value={`${fmt(allTimeCost)} €`} />
      </div>
    </div>
```

- [ ] **Step 3: Replace the toolbar and add the filter modal**

Replace (around lines 121-136):

```svelte
    <div class="toolbar">
      <Input placeholder={$_('chores.page.search')} bind:value={searchQuery} />
      <select class="native-input filter-sel" bind:value={statusFilter}>
        <option value="">{$_('works.page.allStatuses')}</option>
        <option value="planned">{$_('works.status.planned')}</option>
        <option value="in_progress">{$_('works.status.inProgress')}</option>
        <option value="done">{$_('works.status.done')}</option>
      </select>
      <select class="native-input filter-sel" bind:value={categoryFilter}>
        <option value="">{$_('costs.page.allCategories')}</option>
        {#each settingsStore.workCategories as cat}
          <option value={cat.id}>{cat.emoji} {cat.name}</option>
        {/each}
      </select>
      <Button onclick={() => { modalWork = "create"; }}>＋ {$_('works.page.addWork')}</Button>
    </div>
```

with:

```svelte
    <div class="toolbar">
      <Input placeholder={$_('chores.page.search')} bind:value={searchQuery} />
      <FilterButton active={filtersActive} title={$_('common.filters')} onclick={() => { filterModalOpen = true; }} />
      <Button iconOnly title={$_('works.page.addWork')} onclick={() => { modalWork = "create"; }}>＋</Button>
    </div>

    <Modal open={filterModalOpen} title={$_('common.filters')} onclose={() => { filterModalOpen = false; }} width="360px">
      <div class="filter-modal-body">
        <select class="native-input filter-sel" bind:value={statusFilter}>
          <option value="">{$_('works.page.allStatuses')}</option>
          <option value="planned">{$_('works.status.planned')}</option>
          <option value="in_progress">{$_('works.status.inProgress')}</option>
          <option value="done">{$_('works.status.done')}</option>
        </select>
        <select class="native-input filter-sel" bind:value={categoryFilter}>
          <option value="">{$_('costs.page.allCategories')}</option>
          {#each settingsStore.workCategories as cat}
            <option value={cat.id}>{cat.emoji} {cat.name}</option>
          {/each}
        </select>
      </div>
    </Modal>
```

- [ ] **Step 4: Update the CSS**

Replace (around lines 209-225):

```css
  .chart-card-wrap { display: flex; gap: var(--space-3); align-items: stretch; padding: var(--space-4); flex-shrink: 0; }
  .chart-card-wrap :global(.ui-stat-row.column) :global(.ui-card) { flex: 1; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }

  @media (max-width: 700px) {
    .chart-card-wrap { flex-direction: column; }
    .chart-card-wrap :global(.ui-stat-row.column) { width: auto; }
    .page { overflow-y: auto; }
    .table-card-wrap { flex: none; min-height: auto; }
    .table-card-wrap :global(.ui-card) { flex: none !important; width: 100%; overflow: visible !important; min-height: auto !important; }
    .table-wrapper { flex: none !important; overflow-y: visible !important; }
  }
```

with:

```css
  .chart-card-wrap { display: flex; gap: var(--space-3); align-items: stretch; padding: var(--space-4); flex-shrink: 0; }
  .stat-tiles { display: flex; flex-direction: column; gap: var(--space-3); flex-shrink: 0; width: 200px; }
  .stat-tiles :global(.ui-card) { flex: 1; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }

  .filter-modal-body { display: flex; flex-direction: column; gap: var(--space-3); }
  .filter-modal-body .native-input { width: 100%; }

  @media (max-width: 700px) {
    .chart-card-wrap { flex-direction: column; }
    .stat-tiles { flex-direction: row; flex-wrap: wrap; width: auto; }
    .stat-tiles :global(.ui-stat-tile) { flex: 1 1 90px; }
    .page { overflow-y: auto; }
    .table-card-wrap { flex: none; min-height: auto; }
    .table-card-wrap :global(.ui-card) { flex: none !important; width: 100%; overflow: visible !important; min-height: auto !important; }
    .table-wrapper { flex: none !important; overflow-y: visible !important; }
  }
```

- [ ] **Step 5: Run the full test file**

Run: `cd packages/editor && npx vitest run test/WorksPage.test.ts`
Expected: PASS with no test-file changes needed (the timeline-click test targets `.chart-card-wrap circle`, unaffected by the stat-tile restructure).

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/WorksPage.svelte
git commit -m "feat(works): compact toolbar behind filter modal, merge stat tiles into one row"
```

---

### Task 9: `CostsPage.svelte` — compact toolbar

**Files:**
- Modify: `packages/editor/src/lib/components/CostsPage.svelte`

**Interfaces:**
- Consumes: `FilterButton` (Task 2), `Button` `iconOnly` (Task 1), `common.filters` (Task 4). No KPI markup change — `.stats-under-bar` already lays its two tiles out side by side (`display: flex`), so it doesn't have the one-tile-per-line problem the other pages have.

- [ ] **Step 1: Add imports and state**

Add to the imports (after `Card`/`StatTile`/`DonutChart` imports, around line 12-14):

```ts
  import Modal from "./ui/Modal.svelte";
  import FilterButton from "./ui/FilterButton.svelte";
```

After `let yearFilter = $state("");` (around line 50), add:

```ts
  let filterModalOpen = $state(false);
  const filtersActive = $derived(categoryFilter !== "" || yearFilter !== "");
```

- [ ] **Step 2: Replace the toolbar and add the filter modal**

Replace (around lines 247-262):

```svelte
    <div class="toolbar">
      <Input bind:value={searchQuery} placeholder={$_('costs.page.searchEntries')} />
      <select class="native-input" bind:value={categoryFilter}>
        <option value="">{$_('costs.page.allCategories')}</option>
        {#each settingsStore.costCategories as cat}
          <option value={cat.id}>{cat.emoji} {cat.name}</option>
        {/each}
      </select>
      <select class="native-input" bind:value={yearFilter}>
        <option value="">{$_('costs.page.allYears')}</option>
        {#each allYears as y}
          <option value={String(y)}>{y}</option>
        {/each}
      </select>
      <Button onclick={() => { modalEntry = "create"; }}>＋ {$_('costs.page.addEntry')}</Button>
    </div>
```

with:

```svelte
    <div class="toolbar">
      <Input bind:value={searchQuery} placeholder={$_('costs.page.searchEntries')} />
      <FilterButton active={filtersActive} title={$_('common.filters')} onclick={() => { filterModalOpen = true; }} />
      <Button iconOnly title={$_('costs.page.addEntry')} onclick={() => { modalEntry = "create"; }}>＋</Button>
    </div>

    <Modal open={filterModalOpen} title={$_('common.filters')} onclose={() => { filterModalOpen = false; }} width="360px">
      <div class="filter-modal-body">
        <select class="native-input" bind:value={categoryFilter}>
          <option value="">{$_('costs.page.allCategories')}</option>
          {#each settingsStore.costCategories as cat}
            <option value={cat.id}>{cat.emoji} {cat.name}</option>
          {/each}
        </select>
        <select class="native-input" bind:value={yearFilter}>
          <option value="">{$_('costs.page.allYears')}</option>
          {#each allYears as y}
            <option value={String(y)}>{y}</option>
          {/each}
        </select>
      </div>
    </Modal>
```

- [ ] **Step 3: Update the CSS**

After the `.toolbar :global(.ui-input) { flex: 1; }` rule (around line 411), add:

```css
  .filter-modal-body { display: flex; flex-direction: column; gap: var(--space-3); }
  .filter-modal-body .native-input { width: 100%; }
```

- [ ] **Step 4: Run the full test file**

Run: `cd packages/editor && npx vitest run test/CostsPage.test.ts`
Expected: PASS with no test-file changes needed.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/CostsPage.svelte
git commit -m "feat(costs): compact toolbar behind filter modal"
```

---

### Task 10: `ContactsPage.svelte` — compact toolbar

**Files:**
- Modify: `packages/editor/src/lib/components/ContactsPage.svelte`

**Interfaces:**
- Consumes: `FilterButton` (Task 2), `Button` `iconOnly` (Task 1), `common.filters` (Task 4). No KPI change — already `StatTileRow direction="row"`, benefits from Task 3.

- [ ] **Step 1: Add imports and state**

Add to the imports (after `StatTile`/`StatTileRow` imports, around line 12-13):

```ts
  import Modal from "./ui/Modal.svelte";
  import FilterButton from "./ui/FilterButton.svelte";
```

After `let typeFilter = $state("");` (around line 26), add:

```ts
  let filterModalOpen = $state(false);
  const filtersActive = $derived(typeFilter !== "");
```

- [ ] **Step 2: Replace the toolbar and add the filter modal**

Replace (around lines 65-74):

```svelte
    <div class="toolbar">
      <Input placeholder={$_('chores.page.search')} bind:value={searchQuery} />
      <select class="native-input filter-sel" bind:value={typeFilter}>
        <option value="">{$_('contacts.page.allTypes')}</option>
        {#each settingsStore.contactTypes as t}
          <option value={t.id}>{t.name}</option>
        {/each}
      </select>
      <Button onclick={() => { modalContact = "create"; }}>＋ {$_('contacts.page.addContact')}</Button>
    </div>
```

with:

```svelte
    <div class="toolbar">
      <Input placeholder={$_('chores.page.search')} bind:value={searchQuery} />
      <FilterButton active={filtersActive} title={$_('common.filters')} onclick={() => { filterModalOpen = true; }} />
      <Button iconOnly title={$_('contacts.page.addContact')} onclick={() => { modalContact = "create"; }}>＋</Button>
    </div>

    <Modal open={filterModalOpen} title={$_('common.filters')} onclose={() => { filterModalOpen = false; }} width="360px">
      <div class="filter-modal-body">
        <select class="native-input filter-sel" bind:value={typeFilter}>
          <option value="">{$_('contacts.page.allTypes')}</option>
          {#each settingsStore.contactTypes as t}
            <option value={t.id}>{t.name}</option>
          {/each}
        </select>
      </div>
    </Modal>
```

- [ ] **Step 3: Update the CSS**

After the `.toolbar :global(.ui-input) { flex: 1; }` rule (around line 138), add:

```css
  .filter-modal-body { display: flex; flex-direction: column; gap: var(--space-3); }
  .filter-modal-body .native-input { width: 100%; }
```

- [ ] **Step 4: Run the full test file**

Run: `cd packages/editor && npx vitest run test/ContactsPage.test.ts`
Expected: PASS with no test-file changes needed.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ContactsPage.svelte
git commit -m "feat(contacts): compact toolbar behind filter modal"
```

---

### Task 11: `PropertiesPage.svelte` — compact toolbar

**Files:**
- Modify: `packages/editor/src/lib/components/PropertiesPage.svelte`
- Test: `packages/editor/test/PropertiesPage.test.ts`

**Interfaces:**
- Consumes: `FilterButton` (Task 2), `Button` `iconOnly` (Task 1), `common.filters` (Task 4). No KPI change — already `StatTileRow direction="row"`, benefits from Task 3.

- [ ] **Step 1: Add imports and state**

Add to the imports (after `StatTile`/`StatTileRow` imports, around line 11-12):

```ts
  import Modal from "./ui/Modal.svelte";
  import FilterButton from "./ui/FilterButton.svelte";
```

After `let typeFilter = $state("");` (around line 40), add:

```ts
  let filterModalOpen = $state(false);
  const filtersActive = $derived(statusFilter !== "" || typeFilter !== "");
```

- [ ] **Step 2: Replace the toolbar and add the filter modal**

Replace (around lines 118-135):

```svelte
    <div class="toolbar">
      <Input placeholder={$_('chores.page.search')} bind:value={searchQuery} />
      <select class="native-input filter-sel" bind:value={statusFilter}>
        <option value="">{$_('works.page.allStatuses')}</option>
        <option value="watching">{$_('properties.status.watching')}</option>
        <option value="visited">{$_('properties.status.visited')}</option>
        <option value="proposal_made">{$_('properties.status.proposalMade')}</option>
        <option value="purchased">{$_('properties.status.purchased')}</option>
        <option value="rejected">{$_('properties.status.rejected')}</option>
      </select>
      <select class="native-input filter-sel" bind:value={typeFilter}>
        <option value="">{$_('properties.page.allTypes')}</option>
        <option value="land">{$_('properties.type.land')}</option>
        <option value="house">{$_('properties.type.house')}</option>
        <option value="new_build">{$_('properties.type.newBuild')}</option>
      </select>
      <Button onclick={() => { modalProperty = "create"; }}>＋ {$_('properties.page.addProperty')}</Button>
    </div>
```

with:

```svelte
    <div class="toolbar">
      <Input placeholder={$_('chores.page.search')} bind:value={searchQuery} />
      <FilterButton active={filtersActive} title={$_('common.filters')} onclick={() => { filterModalOpen = true; }} />
      <Button iconOnly title={$_('properties.page.addProperty')} onclick={() => { modalProperty = "create"; }}>＋</Button>
    </div>

    <Modal open={filterModalOpen} title={$_('common.filters')} onclose={() => { filterModalOpen = false; }} width="360px">
      <div class="filter-modal-body">
        <select class="native-input filter-sel" bind:value={statusFilter}>
          <option value="">{$_('works.page.allStatuses')}</option>
          <option value="watching">{$_('properties.status.watching')}</option>
          <option value="visited">{$_('properties.status.visited')}</option>
          <option value="proposal_made">{$_('properties.status.proposalMade')}</option>
          <option value="purchased">{$_('properties.status.purchased')}</option>
          <option value="rejected">{$_('properties.status.rejected')}</option>
        </select>
        <select class="native-input filter-sel" bind:value={typeFilter}>
          <option value="">{$_('properties.page.allTypes')}</option>
          <option value="land">{$_('properties.type.land')}</option>
          <option value="house">{$_('properties.type.house')}</option>
          <option value="new_build">{$_('properties.type.newBuild')}</option>
        </select>
      </div>
    </Modal>
```

- [ ] **Step 3: Update the CSS**

After the `.toolbar :global(.ui-input) { flex: 1; }` rule (around line 224), add:

```css
  .filter-modal-body { display: flex; flex-direction: column; gap: var(--space-3); }
  .filter-modal-body .native-input { width: 100%; }
```

- [ ] **Step 4: Update the two affected tests**

In `packages/editor/test/PropertiesPage.test.ts`:

1. In the `"PropertiesPage — filters"` test (around line 59), after `flushSync();` and before `const statusSelect = ...`, insert:

```ts
    (target.querySelector('button[aria-label="Filters"]') as HTMLButtonElement).click();
    flushSync();
```

2. In the `"PropertiesPage — add property"` test, replace:

```ts
    const addBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Add property"))!;
    addBtn.click();
```

with:

```ts
    const addBtn = target.querySelector('button[title="Add property"]') as HTMLButtonElement;
    addBtn.click();
```

- [ ] **Step 5: Run the full test file**

Run: `cd packages/editor && npx vitest run test/PropertiesPage.test.ts`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/PropertiesPage.svelte packages/editor/test/PropertiesPage.test.ts
git commit -m "feat(properties): compact toolbar behind filter modal"
```

---

### Task 12: `InsurancePage.svelte` — compact toolbar

**Files:**
- Modify: `packages/editor/src/lib/components/InsurancePage.svelte`
- Test: `packages/editor/test/InsurancePage.test.ts`

**Interfaces:**
- Consumes: `FilterButton` (Task 2), `Button` `iconOnly` (Task 1), `common.filters` (Task 4), the mobile wrap fix from Task 3 (this page's KPI row uses `StatTileRow direction="column"`, so no KPI markup change is needed here).

- [ ] **Step 1: Add imports and state**

Add to the imports (after `StatTile`/`StatTileRow`/`DonutChart` imports, around line 13-15):

```ts
  import Modal from "./ui/Modal.svelte";
  import FilterButton from "./ui/FilterButton.svelte";
```

After `let categoryFilter = $state("");` (around line 32), add:

```ts
  let filterModalOpen = $state(false);
  const filtersActive = $derived(categoryFilter !== "");
```

- [ ] **Step 2: Replace the toolbar and add the filter modal**

Replace (around lines 128-137):

```svelte
    <div class="toolbar">
      <Input placeholder={$_('insurance.page.search')} bind:value={searchQuery} />
      <select class="native-input filter-sel" bind:value={categoryFilter}>
        <option value="">{$_('costs.page.allCategories')}</option>
        {#each settingsStore.insuranceCategories as cat}
          <option value={cat.id}>{cat.emoji} {cat.name}</option>
        {/each}
      </select>
      <Button onclick={() => { modalPolicy = "create"; }}>＋ {$_('insurance.page.addPolicy')}</Button>
    </div>
```

with:

```svelte
    <div class="toolbar">
      <Input placeholder={$_('insurance.page.search')} bind:value={searchQuery} />
      <FilterButton active={filtersActive} title={$_('common.filters')} onclick={() => { filterModalOpen = true; }} />
      <Button iconOnly title={$_('insurance.page.addPolicy')} onclick={() => { modalPolicy = "create"; }}>＋</Button>
    </div>

    <Modal open={filterModalOpen} title={$_('common.filters')} onclose={() => { filterModalOpen = false; }} width="360px">
      <div class="filter-modal-body">
        <select class="native-input filter-sel" bind:value={categoryFilter}>
          <option value="">{$_('costs.page.allCategories')}</option>
          {#each settingsStore.insuranceCategories as cat}
            <option value={cat.id}>{cat.emoji} {cat.name}</option>
          {/each}
        </select>
      </div>
    </Modal>
```

- [ ] **Step 3: Update the CSS**

After the `.toolbar :global(.ui-input) { flex: 1; }` rule (around line 226), add:

```css
  .filter-modal-body { display: flex; flex-direction: column; gap: var(--space-3); }
  .filter-modal-body .native-input { width: 100%; }
```

- [ ] **Step 4: Update the add-policy test**

In `packages/editor/test/InsurancePage.test.ts`, in the `"InsurancePage — add policy"` test, replace:

```ts
    const addButton = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Add policy"));
    addButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
```

with:

```ts
    const addButton = target.querySelector('button[title="Add policy"]');
    addButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
```

- [ ] **Step 5: Run the full test file**

Run: `cd packages/editor && npx vitest run test/InsurancePage.test.ts`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/InsurancePage.svelte packages/editor/test/InsurancePage.test.ts
git commit -m "feat(insurance): compact toolbar behind filter modal"
```

---

### Task 13: Full suite + manual verification

**Files:** none (verification only).

- [ ] **Step 1: Run the full frontend test suite**

Run: `cd packages/editor && npx vitest run`
Expected: PASS, no regressions (includes `BuildPage`, which needed no code change but should still render correctly with the tightened `StatTileRow` grid from Task 3).

- [ ] **Step 2: Manual browser check at a narrow viewport**

Use the `run` skill to start the dev server, open each of the 9 pages (Chores, Consumables, Inventory, Works, Costs, Contacts, Properties, Insurance, Build) in a browser at a 375px-wide viewport, and confirm:
- The toolbar (search, filter icon, quick toggle where present, add icon) fits on one line.
- Clicking the filter icon opens a modal with the page's dropdowns, and picking a value actually filters the table.
- The filter icon shows a badge dot after picking a non-default filter value, and the badge disappears when filters are cleared.
- The KPI row shows the chart (if any) on its own line, with the stat tiles wrapped into a row beneath it rather than one tile per line.
- Dark mode looks correct for the new `FilterButton` icon and badge.

- [ ] **Step 3: Fix any issues found, then final commit if needed**

If manual verification surfaces a bug, fix it in the relevant page/component, re-run that file's test, and commit as `fix(<module>): <description>`.
