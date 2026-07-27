# Module Overview Stat Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert every module page's overview/summary section from a single merged `Card` with `.stat-chip` divs into a row of individual `StatTile` cards (matching Build's existing per-stat-card layout), with any chart kept in its own separate card.

**Architecture:** Extend `StatTile.svelte` with two new optional props (`variant` for color, `valueContent` for rich content), add a new `StatTileRow.svelte` wrapper for the responsive grid, then convert each of 9 pages (Build, Contacts, Properties, Chores, Inventory, Consumables, Insurance, Works, Costs) to use them in place of their current `.stat-chip` markup.

**Tech Stack:** Svelte 5 (runes, snippets), vitest + `@testing-library`-free DOM assertions (existing convention in this repo), svelte-i18n (no new keys needed — every stat's label already has one).

## Global Constraints

- Every stat's existing i18n key, value formatting, and computed data source stays exactly as-is — this is a layout refactor, not a data change. Don't rename or recompute any `$derived`/store value.
- `StatTile`'s new props are additive and optional — `CostsCategoryModal.svelte`'s three existing `<StatTile value=... label=... />` call sites must keep working unmodified.
- Use the existing `--success`/`--danger`/`--warning` CSS custom properties from `theme.css` for colored stat variants, never hardcoded hex — the hardcoded hex this replaces (`#f44336`, `#4caf50`, `#ff9800`) was a real dark-mode bug (those colors don't adapt to theme).
- When a page's chart stays in its own `Card`, preserve its existing wrapper class (`.chart-card-wrap`) and any CSS selector in that page's own test file that depends on it (e.g. `.chart-card-wrap svg path`, `.chart-card-wrap circle`) — don't rename that class.
- New stat row markup goes in a `<div class="stat-row-wrap">` sibling block (own top-level padding), not nested inside the chart's `Card`.

---

### Task 1: Extend `StatTile.svelte` with `variant` and `valueContent`

**Files:**
- Modify: `packages/editor/src/lib/components/ui/StatTile.svelte`
- Test: `packages/editor/test/StatTile.test.ts`

**Interfaces:**
- Produces: `StatTile` props become `{ value: string | number; label: string; variant?: "success" | "danger" | "warning"; valueContent?: Snippet }`.

- [ ] **Step 1: Write the failing tests**

Append to `packages/editor/test/StatTile.test.ts` (add `createRawSnippet` to the existing `svelte` import):

```ts
import { describe, it, expect } from "vitest";
import { mount, unmount, createRawSnippet } from "svelte";
import StatTile from "../src/lib/components/ui/StatTile.svelte";
```

Then append these tests inside the existing `describe` block:

```ts
  it("applies a danger variant class to the value", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(StatTile, { target, props: { value: 3, label: "Overdue", variant: "danger" } });

    expect(target.querySelector(".ui-stat-value")!.classList.contains("danger")).toBe(true);

    unmount(comp);
    target.remove();
  });

  it("applies a success variant class to the value", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(StatTile, { target, props: { value: "33%", label: "On track", variant: "success" } });

    expect(target.querySelector(".ui-stat-value")!.classList.contains("success")).toBe(true);

    unmount(comp);
    target.remove();
  });

  it("applies a warning variant class to the value", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(StatTile, { target, props: { value: 2, label: "Low stock", variant: "warning" } });

    expect(target.querySelector(".ui-stat-value")!.classList.contains("warning")).toBe(true);

    unmount(comp);
    target.remove();
  });

  it("has no variant class by default", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(StatTile, { target, props: { value: 5, label: "Active" } });

    const el = target.querySelector(".ui-stat-value")!;
    expect(el.classList.contains("danger")).toBe(false);
    expect(el.classList.contains("success")).toBe(false);
    expect(el.classList.contains("warning")).toBe(false);

    unmount(comp);
    target.remove();
  });

  it("renders valueContent instead of the plain value when provided", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const valueContent = createRawSnippet(() => ({
      render: () => `<span class="custom-value">1,234 € <b class="up">▲2%</b></span>`,
    }));
    const comp = mount(StatTile, { target, props: { value: "1,234 €", label: "Last year", valueContent } });

    expect(target.querySelector(".custom-value")).not.toBeNull();
    expect(target.querySelector(".up")!.textContent).toBe("▲2%");

    unmount(comp);
    target.remove();
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -w @myhome/editor -- StatTile --run`
Expected: FAIL (variant/valueContent props don't exist yet, `.danger`/`.success`/`.warning`/`.custom-value` never appear)

- [ ] **Step 3: Implement the changes**

Replace the full contents of `packages/editor/src/lib/components/ui/StatTile.svelte`:

```svelte
<!-- packages/editor/src/lib/components/ui/StatTile.svelte -->
<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    value: string | number;
    label: string;
    variant?: "success" | "danger" | "warning";
    valueContent?: Snippet;
  }
  let { value, label, variant, valueContent }: Props = $props();
</script>

<div class="ui-card ui-stat-tile">
  <div
    class="ui-stat-value"
    class:success={variant === "success"}
    class:danger={variant === "danger"}
    class:warning={variant === "warning"}
  >
    {#if valueContent}{@render valueContent()}{:else}{value}{/if}
  </div>
  <div class="ui-stat-label">{label}</div>
</div>

<style>
  .ui-stat-tile {
    background: var(--surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    padding: var(--space-3);
  }
  .ui-stat-value {
    font-family: var(--font-sans);
    font-size: 22px; font-weight: 700; color: var(--text); line-height: 1.2;
  }
  .ui-stat-value.success { color: var(--success); }
  .ui-stat-value.danger { color: var(--danger); }
  .ui-stat-value.warning { color: var(--warning); }
  .ui-stat-label {
    font-family: var(--font-sans);
    font-size: 10px; color: var(--text-faint);
    text-transform: uppercase; letter-spacing: 0.05em;
    margin-top: 2px;
  }
</style>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test -w @myhome/editor -- StatTile --run`
Expected: PASS (6 tests)

- [ ] **Step 5: Run the CostsCategoryModal tests to confirm backward compatibility**

Run: `npm test -w @myhome/editor -- CostsCategoryModal --run`
Expected: PASS (unchanged — the three existing `<StatTile value=... label=... />` call sites don't pass `variant`/`valueContent`)

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/ui/StatTile.svelte packages/editor/test/StatTile.test.ts
git commit -m "feat(ui): add variant and valueContent props to StatTile"
```

---

### Task 2: Add `StatTileRow.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/ui/StatTileRow.svelte`
- Test: `packages/editor/test/StatTileRow.test.ts`

**Interfaces:**
- Produces: `StatTileRow` — `{ children: Snippet }`, renders children inside a responsive grid div (`.ui-stat-row`).

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/StatTileRow.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { mount, unmount } from "svelte";
import StatTileRow from "../src/lib/components/ui/StatTileRow.svelte";
import StatTile from "../src/lib/components/ui/StatTile.svelte";

describe("ui/StatTileRow", () => {
  it("renders its children inside the stat row grid", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(StatTileRow, {
      target,
      props: {
        children: () => {
          const c = mount(StatTile, { target: document.createElement("div"), props: { value: 1, label: "A" } });
          return c;
        },
      },
    });

    // children snippet composition is exercised end-to-end in each page's
    // own tests (Task 3+); here we just confirm the row wrapper itself renders.
    expect(target.querySelector(".ui-stat-row")).not.toBeNull();

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -w @myhome/editor -- StatTileRow --run`
Expected: FAIL (module doesn't exist)

- [ ] **Step 3: Implement `StatTileRow.svelte`**

Create `packages/editor/src/lib/components/ui/StatTileRow.svelte`:

```svelte
<!-- packages/editor/src/lib/components/ui/StatTileRow.svelte -->
<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    children: Snippet;
  }
  let { children }: Props = $props();
</script>

<div class="ui-stat-row">
  {@render children()}
</div>

<style>
  .ui-stat-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: var(--space-3);
  }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -w @myhome/editor -- StatTileRow --run`
Expected: PASS (1 test)

Note: the test above is deliberately minimal (mounting a real child snippet
composed from another component in isolation is awkward without a host
`.svelte` fixture) — full coverage of `StatTileRow` + `StatTile` composed
together comes from every page's own tests starting in Task 3.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/StatTileRow.svelte packages/editor/test/StatTileRow.test.ts
git commit -m "feat(ui): add StatTileRow grid wrapper component"
```

---

### Task 3: Convert Build's stat cards onto `StatTile`

**Files:**
- Modify: `packages/editor/src/lib/components/BuildPage.svelte`
- Modify: `packages/editor/test/BuildPage.test.ts`

**Interfaces:**
- Consumes: `StatTile`, `StatTileRow` (Task 1 & 2).

- [ ] **Step 1: Update the failing/changed tests**

In `packages/editor/test/BuildPage.test.ts`, change line 61's selector (inside the "shows the stat cards and the phases table together" test):

```ts
    const values = Array.from(target.querySelectorAll(".stat-value")).map((el) => el.textContent);
```
to:
```ts
    const values = Array.from(target.querySelectorAll(".ui-stat-value")).map((el) => el.textContent);
```

Then replace the "puts the card title above the value" test (currently lines 68-84) — StatTile renders value first, label below, so this test now asserts the opposite order and is renamed to describe that:

```ts
  it("puts the card title above the value in each stat card", async () => {
    const { store, target } = renderPage(seededDoc);
    await waitTick();
    const comp = mount(BuildPage, { target, props: { store, onopentask: vi.fn() } });
    await tick();
    flushSync();

    const firstCard = target.querySelector(".stat-row .ui-card") as HTMLElement;
    const children = Array.from(firstCard.children);
    const titleIndex = children.findIndex((c) => c.classList.contains("stat-title"));
    const valueIndex = children.findIndex((c) => c.classList.contains("stat-value"));
    expect(titleIndex).toBeGreaterThanOrEqual(0);
    expect(titleIndex).toBeLessThan(valueIndex);

    unmount(comp);
    target.remove();
```
to:
```ts
  it("puts the value above the label in each stat card", async () => {
    const { store, target } = renderPage(seededDoc);
    await waitTick();
    const comp = mount(BuildPage, { target, props: { store, onopentask: vi.fn() } });
    await tick();
    flushSync();

    const firstCard = target.querySelector(".ui-stat-row .ui-card") as HTMLElement;
    const children = Array.from(firstCard.children);
    const valueIndex = children.findIndex((c) => c.classList.contains("ui-stat-value"));
    const labelIndex = children.findIndex((c) => c.classList.contains("ui-stat-label"));
    expect(valueIndex).toBeGreaterThanOrEqual(0);
    expect(valueIndex).toBeLessThan(labelIndex);

    unmount(comp);
    target.remove();
```

(the closing `});` after that block stays as-is)

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -w @myhome/editor -- BuildPage --run`
Expected: FAIL (current markup still uses `.stat-value`/`.stat-title`, not `.ui-stat-value`/`.ui-stat-row`)

- [ ] **Step 3: Convert the markup**

In `packages/editor/src/lib/components/BuildPage.svelte`, add the imports:

```svelte
  import Card from "./ui/Card.svelte";
  import Button from "./ui/Button.svelte";
  import PhaseSection from "./PhaseSection.svelte";
```
to:
```svelte
  import Card from "./ui/Card.svelte";
  import Button from "./ui/Button.svelte";
  import PhaseSection from "./PhaseSection.svelte";
  import StatTile from "./ui/StatTile.svelte";
  import StatTileRow from "./ui/StatTileRow.svelte";
```

Replace:
```svelte
    <div class="stat-row-wrap">
      <div class="stat-row">
        <Card>
          <div class="stat-title">{$_('build.dashboard.status')}</div>
          <div class="stat-value">{$_(`build.projectStatus.${store.project.status === "in_progress" ? "inProgress" : store.project.status === "on_hold" ? "onHold" : store.project.status}`)}</div>
        </Card>
        <Card>
          <div class="stat-title">{$_('build.dashboard.currentPhase')}</div>
          <div class="stat-value">{currentPhase ? resolveLabel(currentPhase.nameKey, currentPhase.nameOverride) : "—"}</div>
        </Card>
        <Card>
          <div class="stat-title">{$_('build.dashboard.percentComplete')}</div>
          <div class="stat-value">{Math.round(store.projectProgress * 100)}%</div>
        </Card>
        <Card>
          <div class="stat-title">{$_('build.dashboard.plannedBudget')}</div>
          <div class="stat-value">{fmtMoney(store.projectBudget.planned)}</div>
        </Card>
        <Card>
          <div class="stat-title">{$_('build.dashboard.actualCost')}</div>
          <div class="stat-value">{fmtMoney(store.projectBudget.actual)}</div>
        </Card>
      </div>
    </div>
```
with:
```svelte
    <div class="stat-row-wrap">
      <StatTileRow>
        <StatTile
          label={$_('build.dashboard.status')}
          value={$_(`build.projectStatus.${store.project.status === "in_progress" ? "inProgress" : store.project.status === "on_hold" ? "onHold" : store.project.status}`)}
        />
        <StatTile
          label={$_('build.dashboard.currentPhase')}
          value={currentPhase ? resolveLabel(currentPhase.nameKey, currentPhase.nameOverride) : "—"}
        />
        <StatTile label={$_('build.dashboard.percentComplete')} value={`${Math.round(store.projectProgress * 100)}%`} />
        <StatTile label={$_('build.dashboard.plannedBudget')} value={fmtMoney(store.projectBudget.planned)} />
        <StatTile label={$_('build.dashboard.actualCost')} value={fmtMoney(store.projectBudget.actual)} />
      </StatTileRow>
    </div>
```

Then delete the now-dead CSS rules — change:
```css
  .stat-row-wrap { padding: var(--space-4); flex-shrink: 0; }
  .stat-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--space-3); }
  .stat-title { font-size: 10px; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
  .stat-value { font-size: 18px; font-weight: 700; color: var(--text); }

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }

  @media (max-width: 900px) {
    .stat-row { grid-template-columns: repeat(2, 1fr); }
  }
```
to:
```css
  .stat-row-wrap { padding: var(--space-4); flex-shrink: 0; }

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test -w @myhome/editor -- BuildPage --run`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/BuildPage.svelte packages/editor/test/BuildPage.test.ts
git commit -m "refactor(build): use shared StatTile/StatTileRow for dashboard stats"
```

---

### Task 4: Convert Contacts' type-count chips onto `StatTile`

**Files:**
- Modify: `packages/editor/src/lib/components/ContactsPage.svelte`

**Interfaces:**
- Consumes: `StatTile`, `StatTileRow` (Task 1 & 2).

- [ ] **Step 1: Convert the markup**

In `packages/editor/src/lib/components/ContactsPage.svelte`, add imports — change:
```svelte
  import SortableTable from "./ui/SortableTable.svelte";
  import type { Column } from "./ui/SortableTable.types";
  import Card from "./ui/Card.svelte";
```
to:
```svelte
  import SortableTable from "./ui/SortableTable.svelte";
  import type { Column } from "./ui/SortableTable.types";
  import Card from "./ui/Card.svelte";
  import StatTile from "./ui/StatTile.svelte";
  import StatTileRow from "./ui/StatTileRow.svelte";
```

Replace:
```svelte
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-label">{$_('contacts.page.countByType')}</div>
        <div class="stat-chips-row">
          {#each settingsStore.contactTypes as t}
            <div class="stat-chip">
              <div class="stat-title">{t.name}</div>
              <div class="stat-value">{typeCounts.get(t.id) ?? 0}</div>
            </div>
          {/each}
        </div>
      </Card>
    </div>
```
with:
```svelte
    <div class="stat-row-wrap">
      <div class="chart-label">{$_('contacts.page.countByType')}</div>
      <StatTileRow>
        {#each settingsStore.contactTypes as t}
          <StatTile label={t.name} value={typeCounts.get(t.id) ?? 0} />
        {/each}
      </StatTileRow>
    </div>
```

Then update the CSS — change:
```css
  .chart-card-wrap { padding: var(--space-4); flex-shrink: 0; }
  .chart-label { font-size: 10px; color: var(--text-faint); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px; }
  .stat-chips-row { display: flex; gap: 8px; flex-wrap: wrap; }
  .stat-chip { flex: 1; min-width: 100px; background: var(--surface-alt); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 6px 10px; }
  .stat-title { font-size: 8px; color: var(--text-faint); text-transform: uppercase; margin-bottom: 2px; }
  .stat-value { font-size: 13px; color: var(--text); font-weight: 600; }
```
to:
```css
  .stat-row-wrap { padding: var(--space-4); flex-shrink: 0; }
  .chart-label { font-size: 10px; color: var(--text-faint); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px; }
```

- [ ] **Step 2: Run the existing tests to verify nothing broke**

Run: `npm test -w @myhome/editor -- ContactsPage --run`
Expected: PASS (no test in this file coupled to `.stat-chip`/`.stat-value`/`.chart-card-wrap` per the design spec's survey — this step just confirms that stays true)

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/ContactsPage.svelte
git commit -m "refactor(contacts): use shared StatTile/StatTileRow for type-count stats"
```

---

### Task 5: Convert Properties' pipeline chips onto `StatTile`

**Files:**
- Modify: `packages/editor/src/lib/components/PropertiesPage.svelte`

**Interfaces:**
- Consumes: `StatTile`, `StatTileRow` (Task 1 & 2).

- [ ] **Step 1: Convert the markup**

Add imports (find the existing `Card` import line and add the two new ones after it, matching the pattern used in Task 4).

Replace:
```svelte
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-label">{$_('properties.page.searchPipeline')}</div>
        <div class="stat-chips-row">
          <div class="stat-chip">
            <div class="stat-title">{$_('properties.status.watching')}</div>
            <div class="stat-value">{countByStatus("watching")}</div>
          </div>
          <div class="stat-chip">
            <div class="stat-title">{$_('properties.status.visited')}</div>
            <div class="stat-value">{countByStatus("visited")}</div>
          </div>
          <div class="stat-chip">
            <div class="stat-title">{$_('properties.status.proposalMade')}</div>
            <div class="stat-value">{countByStatus("proposal_made")}</div>
          </div>
          <div class="stat-chip">
            <div class="stat-title">{$_('properties.status.purchased')}</div>
            <div class="stat-value">{countByStatus("purchased")}</div>
          </div>
          <div class="stat-chip">
            <div class="stat-title">{$_('properties.status.rejected')}</div>
            <div class="stat-value">{countByStatus("rejected")}</div>
          </div>
          <div class="stat-chip">
            <div class="stat-title">{$_('properties.page.total')}</div>
            <div class="stat-value">{store.properties.length}</div>
          </div>
        </div>
      </Card>
```
with:
```svelte
    <div class="stat-row-wrap">
      <div class="chart-label">{$_('properties.page.searchPipeline')}</div>
      <StatTileRow>
        <StatTile label={$_('properties.status.watching')} value={countByStatus("watching")} />
        <StatTile label={$_('properties.status.visited')} value={countByStatus("visited")} />
        <StatTile label={$_('properties.status.proposalMade')} value={countByStatus("proposal_made")} />
        <StatTile label={$_('properties.status.purchased')} value={countByStatus("purchased")} />
        <StatTile label={$_('properties.status.rejected')} value={countByStatus("rejected")} />
        <StatTile label={$_('properties.page.total')} value={store.properties.length} />
      </StatTileRow>
```

(the closing `</div>` after that block — the one that closed `.chart-card-wrap`'s outer wrapper — stays as-is, now closing `.stat-row-wrap`)

Update the CSS — change:
```css
  .chart-card-wrap { padding: var(--space-4); flex-shrink: 0; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }
  .stat-chips-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
  .stat-chip {
    flex: 1; min-width: 100px; background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 6px 10px;
  }
  .stat-title { font-size: 8px; color: var(--text-faint); text-transform: uppercase; margin-bottom: 2px; }
  .stat-value { font-size: 13px; color: var(--text); font-weight: 600; }
```
to:
```css
  .stat-row-wrap { padding: var(--space-4); flex-shrink: 0; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }
```

- [ ] **Step 2: Run the existing tests to verify nothing broke**

Run: `npm test -w @myhome/editor -- PropertiesPage --run`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/PropertiesPage.svelte
git commit -m "refactor(properties): use shared StatTile/StatTileRow for pipeline stats"
```

---

### Task 6: Convert Chores' schedule stats onto `StatTile`

**Files:**
- Modify: `packages/editor/src/lib/components/ChoresPage.svelte`
- Modify: `packages/editor/test/ChoresPage.test.ts`

**Interfaces:**
- Consumes: `StatTile`, `StatTileRow` (Task 1 & 2).

- [ ] **Step 1: Update the failing tests**

In `packages/editor/test/ChoresPage.test.ts`, change:
```ts
    expect(target.querySelector(".stat-value.overdue")?.textContent).toBe("1");
    expect(target.querySelector(".stat-value.ontrack")?.textContent).toBe("33%");
```
to:
```ts
    expect(target.querySelector(".ui-stat-value.danger")?.textContent).toBe("1");
    expect(target.querySelector(".ui-stat-value.success")?.textContent).toBe("33%");
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -w @myhome/editor -- ChoresPage --run`
Expected: FAIL (current markup still produces `.stat-value.overdue`/`.stat-value.ontrack`)

- [ ] **Step 3: Convert the markup**

Add imports — change:
```svelte
  import Card from "./ui/Card.svelte";
  import HorizontalBarChart from "./HorizontalBarChart.svelte";
```
to:
```svelte
  import Card from "./ui/Card.svelte";
  import HorizontalBarChart from "./HorizontalBarChart.svelte";
  import StatTile from "./ui/StatTile.svelte";
  import StatTileRow from "./ui/StatTileRow.svelte";
```

Replace:
```svelte
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-inner">
          <div class="bar-area">
            <div class="chart-label">{$_('chores.page.scheduleHealth')}</div>
            <HorizontalBarChart segments={healthBreakdown} />
          </div>

          <div class="chart-divider"></div>

          <div class="stats-area">
            <div class="chart-label">{$_('chores.page.atAGlance')}</div>
            <div class="stat-chips-col">
              <div class="stat-chip">
                <div class="stat-title">{$_('chores.page.active')}</div>
                <div class="stat-value">{totalAssignments}</div>
              </div>
              <div class="stat-chip">
                <div class="stat-title">{$_('chores.page.overdue')}</div>
                <div class="stat-value overdue">{overdueCount}</div>
              </div>
              <div class="stat-chip">
                <div class="stat-title">{$_('chores.page.onTrack')}</div>
                <div class="stat-value ontrack">{onTrackPct}%</div>
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
```
with:
```svelte
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-label">{$_('chores.page.scheduleHealth')}</div>
        <HorizontalBarChart segments={healthBreakdown} />
      </Card>
    </div>

    <div class="stat-row-wrap">
      <StatTileRow>
        <StatTile label={$_('chores.page.active')} value={totalAssignments} />
        <StatTile label={$_('chores.page.overdue')} value={overdueCount} variant="danger" />
        <StatTile label={$_('chores.page.onTrack')} value={`${onTrackPct}%`} variant="success" />
      </StatTileRow>
    </div>
```

Update the CSS — change:
```css
  .chart-card-wrap { padding: var(--space-4); flex-shrink: 0; }
  .chart-inner { display: flex; gap: 24px; align-items: center; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }
  .bar-area { flex: 1; min-width: 0; }
  .chart-divider { width: 1px; background: var(--border); align-self: stretch; flex-shrink: 0; margin: 0 8px; }

  .stats-area { flex: 1; min-width: 0; }
  .stat-chips-col { display: flex; flex-flow: row wrap; gap: 8px; }
  .stat-chip {
    background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 6px 10px;
  }
  .stat-title { font-size: 8px; color: var(--text-faint); text-transform: uppercase; margin-bottom: 2px; }
  .stat-value { font-size: 13px; color: var(--text); font-weight: 600; }
  .stat-value.overdue { color: #f44336; }
  .stat-value.ontrack { color: #4caf50; }
```
to:
```css
  .chart-card-wrap { padding: var(--space-4); flex-shrink: 0; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }

  .stat-row-wrap { padding: 0 var(--space-4) var(--space-4); flex-shrink: 0; }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test -w @myhome/editor -- ChoresPage --run`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ChoresPage.svelte packages/editor/test/ChoresPage.test.ts
git commit -m "refactor(chores): use shared StatTile/StatTileRow, fix dark-mode stat colors"
```

---

### Task 7: Convert Inventory's item stats onto `StatTile`

**Files:**
- Modify: `packages/editor/src/lib/components/InventoryPage.svelte`
- Modify: `packages/editor/test/InventoryPage.test.ts`

**Interfaces:**
- Consumes: `StatTile`, `StatTileRow` (Task 1 & 2).

- [ ] **Step 1: Update the failing test**

In `packages/editor/test/InventoryPage.test.ts`, change line 38:
```ts
    const values = Array.from(target.querySelectorAll(".stat-value")).map((el) => el.textContent);
```
to:
```ts
    const values = Array.from(target.querySelectorAll(".ui-stat-value")).map((el) => el.textContent);
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -w @myhome/editor -- InventoryPage --run`
Expected: FAIL

- [ ] **Step 3: Convert the markup**

Add imports next to the existing `Card`/`DonutChart` imports (same pattern as prior tasks: `import StatTile from "./ui/StatTile.svelte";` and `import StatTileRow from "./ui/StatTileRow.svelte";`).

Replace:
```svelte
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-inner">
          <div class="pie-area">
            <div class="chart-label">{$_('inventory.page.byCategory')}</div>
            <DonutChart
              segments={categoryBreakdown}
              centerLabel={$_('inventory.page.items')}
              centerValue={`${store.items.length}`}
              showLabels={true}
            />
          </div>

          <div class="chart-divider"></div>

          <div class="stats-area">
            <div class="chart-label">{$_('chores.page.atAGlance')}</div>
            <div class="stat-chips-col">
              <div class="stat-chip">
                <div class="stat-title">{$_('inventory.page.items')}</div>
                <div class="stat-value">{store.items.length}</div>
              </div>
              <div class="stat-chip">
                <div class="stat-title">{$_('inventory.page.totalValue')}</div>
                <div class="stat-value">{totalValue.toLocaleString()} €</div>
              </div>
            </div>
          </div>
        </div>
      </Card>
```
with:
```svelte
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-label">{$_('inventory.page.byCategory')}</div>
        <DonutChart
          segments={categoryBreakdown}
          centerLabel={$_('inventory.page.items')}
          centerValue={`${store.items.length}`}
          showLabels={true}
        />
      </Card>
    </div>

    <div class="stat-row-wrap">
      <StatTileRow>
        <StatTile label={$_('inventory.page.items')} value={store.items.length} />
        <StatTile label={$_('inventory.page.totalValue')} value={`${totalValue.toLocaleString()} €`} />
      </StatTileRow>
```

(the `</div>` closing the old `.chart-card-wrap` outer wrapper is now redundant — this replacement already closes with `</div>` after `</Card>`, and the subsequent existing `</div>` in the file that used to close `.chart-card-wrap`'s wrapper now closes `.stat-row-wrap` instead; verify by reading the surrounding `{/if}` context before saving)

Update the CSS — change:
```css
  .chart-card-wrap { padding: var(--space-4); flex-shrink: 0; }
  .chart-inner { display: flex; gap: 24px; align-items: center; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }
  .pie-area { flex-shrink: 0; }
  .chart-divider { width: 1px; background: var(--border); align-self: stretch; flex-shrink: 0; margin: 0 8px; }

  .stats-area { flex: 1; min-width: 0; }
  .stat-chips-col { display: flex; flex-direction: column; gap: 8px; max-width: 220px; }
  .stat-chip {
    background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 6px 10px;
  }
  .stat-title { font-size: 8px; color: var(--text-faint); text-transform: uppercase; margin-bottom: 2px; }
  .stat-value { font-size: 13px; color: var(--text); font-weight: 600; }
```
to:
```css
  .chart-card-wrap { padding: var(--space-4); flex-shrink: 0; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }

  .stat-row-wrap { padding: 0 var(--space-4) var(--space-4); flex-shrink: 0; }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test -w @myhome/editor -- InventoryPage --run`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/InventoryPage.svelte packages/editor/test/InventoryPage.test.ts
git commit -m "refactor(inventory): use shared StatTile/StatTileRow for item stats"
```

---

### Task 8: Convert Consumables' stock stats onto `StatTile`

**Files:**
- Modify: `packages/editor/src/lib/components/ConsumablesPage.svelte`
- Modify: `packages/editor/test/ConsumablesPage.test.ts`

**Interfaces:**
- Consumes: `StatTile`, `StatTileRow` (Task 1 & 2).

- [ ] **Step 1: Update the failing tests**

In `packages/editor/test/ConsumablesPage.test.ts`, change:
```ts
    expect(target.querySelector(".stat-value.low")?.textContent).toBe("1");
    expect(target.querySelector(".stat-value.empty")?.textContent).toBe("1");
```
to:
```ts
    expect(target.querySelector(".ui-stat-value.warning")?.textContent).toBe("1");
    expect(target.querySelector(".ui-stat-value.danger")?.textContent).toBe("1");
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -w @myhome/editor -- ConsumablesPage --run`
Expected: FAIL

- [ ] **Step 3: Convert the markup**

Add imports (same pattern as prior tasks).

Replace:
```svelte
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-inner">
          <div class="bar-area">
            <div class="chart-label">{$_('consumables.page.stockStatus', { values: { n: store.consumables.length } })}</div>
            <HorizontalBarChart segments={stockBreakdown} />
          </div>

          <div class="chart-divider"></div>

          <div class="stats-area">
            <div class="chart-label">{$_('chores.page.atAGlance')}</div>
            <div class="stat-chips-col">
              <div class="stat-chip">
                <div class="stat-title">{$_('consumables.page.low')}</div>
                <div class="stat-value low">{lowStockCount}</div>
              </div>
              <div class="stat-chip">
                <div class="stat-title">{$_('consumables.page.empty')}</div>
                <div class="stat-value empty">{emptyStockCount}</div>
              </div>
            </div>
          </div>
        </div>
      </Card>
```
with:
```svelte
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-label">{$_('consumables.page.stockStatus', { values: { n: store.consumables.length } })}</div>
        <HorizontalBarChart segments={stockBreakdown} />
      </Card>
    </div>

    <div class="stat-row-wrap">
      <StatTileRow>
        <StatTile label={$_('consumables.page.low')} value={lowStockCount} variant="warning" />
        <StatTile label={$_('consumables.page.empty')} value={emptyStockCount} variant="danger" />
      </StatTileRow>
```

Update the CSS — change:
```css
  .chart-card-wrap { padding: var(--space-4); flex-shrink: 0; }
  .chart-inner { display: flex; gap: 24px; align-items: center; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }
  .bar-area { flex: 1; min-width: 0; }
  .chart-divider { width: 1px; background: var(--border); align-self: stretch; flex-shrink: 0; margin: 0 8px; }

  .stats-area { flex: 1; min-width: 0; }
  .stat-chips-col { display: flex; flex-flow: row wrap; gap: 8px; }
  .stat-chip {
    background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 6px 10px;
  }
  .stat-title { font-size: 8px; color: var(--text-faint); text-transform: uppercase; margin-bottom: 2px; }
  .stat-value { font-size: 13px; color: var(--text); font-weight: 600; }
  .stat-value.low { color: #ff9800; }
  .stat-value.empty { color: #f44336; }
```
to:
```css
  .chart-card-wrap { padding: var(--space-4); flex-shrink: 0; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }

  .stat-row-wrap { padding: 0 var(--space-4) var(--space-4); flex-shrink: 0; }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test -w @myhome/editor -- ConsumablesPage --run`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ConsumablesPage.svelte packages/editor/test/ConsumablesPage.test.ts
git commit -m "refactor(consumables): use shared StatTile/StatTileRow, fix dark-mode stat colors"
```

---

### Task 9: Convert Insurance's policy stats onto `StatTile`

**Files:**
- Modify: `packages/editor/src/lib/components/InsurancePage.svelte`

**Interfaces:**
- Consumes: `StatTile`, `StatTileRow` (Task 1 & 2).

- [ ] **Step 1: Convert the markup**

Add imports (same pattern as prior tasks).

Replace:
```svelte
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-inner">
          <div class="pie-area">
            <div class="chart-label">{$_('insurance.page.byCategory')}</div>
            <DonutChart
              segments={categoryBreakdown}
              centerLabel={$_('insurance.page.annualCost')}
              centerValue={`${fmt(totalAnnualCost)} €`}
              showLabels={true}
            />
          </div>
          <div class="chart-divider"></div>
          <div class="stats-area">
            <div class="chart-label">{$_('chores.page.atAGlance')}</div>
            <div class="stat-chips-col">
              <div class="stat-chip">
                <div class="stat-title">{$_('insurance.page.policies')}</div>
                <div class="stat-value">{store.policies.length}</div>
              </div>
              <div class="stat-chip">
                <div class="stat-title">{$_('insurance.page.annualCost')}</div>
                <div class="stat-value">{fmt(totalAnnualCost)} €</div>
              </div>
            </div>
```
with:
```svelte
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-label">{$_('insurance.page.byCategory')}</div>
        <DonutChart
          segments={categoryBreakdown}
          centerLabel={$_('insurance.page.annualCost')}
          centerValue={`${fmt(totalAnnualCost)} €`}
          showLabels={true}
        />
      </Card>
    </div>

    <div class="stat-row-wrap">
      <StatTileRow>
        <StatTile label={$_('insurance.page.policies')} value={store.policies.length} />
        <StatTile label={$_('insurance.page.annualCost')} value={`${fmt(totalAnnualCost)} €`} />
      </StatTileRow>
```

Read the full surrounding block first (`InsurancePage.svelte` around lines 95-123) to confirm the exact closing tags that follow (`</div></div></Card></div>` in the original) so the replacement's brace/tag nesting matches what remains below it — apply the same `</div>` reconciliation approach used in Task 7.

Update the CSS the same way as Task 6/8 (delete `.chart-inner`, `.pie-area`, `.chart-divider`, `.stats-area`, `.stat-chips-col`, `.stat-chip`, `.stat-title`, `.stat-value`; keep `.chart-card-wrap` and `.chart-label`; add `.stat-row-wrap { padding: 0 var(--space-4) var(--space-4); flex-shrink: 0; }`).

- [ ] **Step 2: Run the existing tests to verify nothing broke**

Run: `npm test -w @myhome/editor -- InsurancePage --run`
Expected: PASS (no selector coupling to `.stat-chip`/`.stat-value` per the design spec's survey)

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/InsurancePage.svelte
git commit -m "refactor(insurance): use shared StatTile/StatTileRow for policy stats"
```

---

### Task 10: Convert Works' status stats onto `StatTile`

**Files:**
- Modify: `packages/editor/src/lib/components/WorksPage.svelte`

**Interfaces:**
- Consumes: `StatTile`, `StatTileRow` (Task 1 & 2).

- [ ] **Step 1: Convert the markup**

Add imports (same pattern as prior tasks).

Replace:
```svelte
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-label">{$_('works.page.houseTimeline')}</div>
        <div class="stat-chips-row">
          <div class="stat-chip">
            <div class="stat-title">{$_('works.status.planned')}</div>
            <div class="stat-value">{plannedCount}</div>
          </div>
          <div class="stat-chip">
            <div class="stat-title">{$_('works.status.inProgress')}</div>
            <div class="stat-value">{inProgressCount}</div>
          </div>
          <div class="stat-chip">
            <div class="stat-title">{$_('works.status.done')}</div>
            <div class="stat-value">{doneCount}</div>
          </div>
          <div class="stat-chip">
            <div class="stat-title">{$_('works.page.totalCost')}</div>
            <div class="stat-value">{fmt(allTimeCost)} €</div>
          </div>
        </div>
        <WorksTimeline works={store.works} onworkclick={handleTimelineClick} />
      </Card>
    </div>
```
with:
```svelte
    <div class="stat-row-wrap">
      <StatTileRow>
        <StatTile label={$_('works.status.planned')} value={plannedCount} />
        <StatTile label={$_('works.status.inProgress')} value={inProgressCount} />
        <StatTile label={$_('works.status.done')} value={doneCount} />
        <StatTile label={$_('works.page.totalCost')} value={`${fmt(allTimeCost)} €`} />
      </StatTileRow>
    </div>

    <div class="chart-card-wrap">
      <Card>
        <div class="chart-label">{$_('works.page.houseTimeline')}</div>
        <WorksTimeline works={store.works} onworkclick={handleTimelineClick} />
      </Card>
    </div>
```

Note this task reorders the two blocks relative to source order (stats now
come before the chart in the markup) to match every other converted page's
"stats row, then chart card" — visually equivalent to "chart row, then
stats" for the other modules since CSS doesn't enforce a specific visual
stacking order beyond source order here; confirm this reads correctly by
running the manual smoke check in Task 12 rather than assuming.

Update the CSS — change:
```css
  .chart-card-wrap { padding: var(--space-4); flex-shrink: 0; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }
  .stat-chips-row { display: flex; gap: 8px; margin-bottom: 10px; }
  .stat-chip {
    flex: 1; background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 6px 10px;
  }
  .stat-title { font-size: 8px; color: var(--text-faint); text-transform: uppercase; margin-bottom: 2px; }
  .stat-value { font-size: 13px; color: var(--text); font-weight: 600; }
```
to:
```css
  .chart-card-wrap { padding: var(--space-4); flex-shrink: 0; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }

  .stat-row-wrap { padding: var(--space-4) var(--space-4) 0; flex-shrink: 0; }
```

- [ ] **Step 2: Run the existing tests to verify nothing broke**

Run: `npm test -w @myhome/editor -- WorksPage --run`
Expected: PASS (line 65's `.chart-card-wrap circle` selector still resolves — `WorksTimeline` is still inside `.chart-card-wrap`)

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/WorksPage.svelte
git commit -m "refactor(works): use shared StatTile/StatTileRow for status stats"
```

---

### Task 11: Convert Costs' year stats onto `StatTile`, preserving the YoY indicator

**Files:**
- Modify: `packages/editor/src/lib/components/CostsPage.svelte`

**Interfaces:**
- Consumes: `StatTile`, `StatTileRow` (Task 1 & 2), `StatTile`'s `valueContent` prop (Task 1).

- [ ] **Step 1: Convert the markup**

Add imports (same pattern as prior tasks).

Replace:
```svelte
            <div class="stat-chips">
              <div class="stat-chip">
                <div class="stat-title">{$_('costs.page.tenYearAvg')}</div>
                <div class="stat-value">{$_('costs.page.perYear', { values: { amount: tenYearAvg.toLocaleString(undefined, { maximumFractionDigits: 0 }) } })}</div>
              </div>
              <div class="stat-chip">
                <div class="stat-title">{$_('costs.page.lastCompleteYr')}</div>
                <div class="stat-value">
                  {lastCompleteTotal.toLocaleString(undefined, { maximumFractionDigits: 0 })} €
                  {#if yoyPct !== null}
                    <span class="yoy" class:up={yoyPct > 0} class:down={yoyPct < 0}>
                      {yoyPct > 0 ? "▲" : "▼"}{Math.abs(yoyPct)}%
                    </span>
                  {/if}
                </div>
              </div>
            </div>
          </div>

        </div>
      </Card>
    </div>
```
with:
```svelte
          </div>
        </div>
      </Card>
    </div>

    {#snippet lastCompleteYearValue()}
      {lastCompleteTotal.toLocaleString(undefined, { maximumFractionDigits: 0 })} €
      {#if yoyPct !== null}
        <span class="yoy" class:up={yoyPct > 0} class:down={yoyPct < 0}>
          {yoyPct > 0 ? "▲" : "▼"}{Math.abs(yoyPct)}%
        </span>
      {/if}
    {/snippet}

    <div class="stat-row-wrap">
      <StatTileRow>
        <StatTile
          label={$_('costs.page.tenYearAvg')}
          value={$_('costs.page.perYear', { values: { amount: tenYearAvg.toLocaleString(undefined, { maximumFractionDigits: 0 }) } })}
        />
        <StatTile
          label={$_('costs.page.lastCompleteYr')}
          value={`${lastCompleteTotal.toLocaleString(undefined, { maximumFractionDigits: 0 })} €`}
          valueContent={lastCompleteYearValue}
        />
      </StatTileRow>
    </div>
```

Read the full surrounding block first (`CostsPage.svelte` around lines 164-243) to confirm exact tag nesting — the `.bar-chips`/`.stat-chips` div was nested inside `.bar-area`, itself inside `.chart-inner`, itself inside the one `Card`; this change removes only the `.stat-chips` block from inside that nesting and adds the new `<div class="stat-row-wrap">` block as a sibling after the whole chart `Card` closes, leaving the donut + 10-year bar chart together in the original card exactly as designed.

Update the CSS — change:
```css
  .stat-chips { display: flex; gap: 8px; margin-top: 8px; }
  .stat-chip {
    flex: 1; background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 6px 10px;
  }
  .stat-title { font-size: 8px; color: var(--text-faint); text-transform: uppercase; margin-bottom: 2px; }
  .stat-value { font-size: 13px; color: var(--text); font-weight: 600; }
  .yoy { font-size: 10px; margin-left: 4px; }
  .yoy.up { color: var(--danger); }
  .yoy.down { color: var(--success); }
```
to:
```css
  .stat-row-wrap { padding: 0 var(--space-4) var(--space-4); flex-shrink: 0; }
  .yoy { font-size: 10px; margin-left: 4px; }
  .yoy.up { color: var(--danger); }
  .yoy.down { color: var(--success); }
```

- [ ] **Step 2: Run the existing tests to verify nothing broke**

Run: `npm test -w @myhome/editor -- CostsPage --run`
Expected: PASS (no selector coupling to `.stat-chip`/`.stat-value`/`.yoy` per the design spec's survey)

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/CostsPage.svelte
git commit -m "refactor(costs): use shared StatTile/StatTileRow, preserve YoY indicator via valueContent"
```

---

### Task 12: Full verification

- [ ] **Step 1: Run the full frontend suite**

Run: `npm test -w @myhome/editor -- --run`
Expected: all tests pass, no regressions

- [ ] **Step 2: Manual smoke check**

Use the `run` skill (or start the dev server directly) and, in a browser with the demo home (or any home with data in each module), visit each of the 9 converted pages — Build, Contacts, Properties, Chores, Inventory, Consumables, Insurance, Works, Costs — and confirm for each: stats render as individually boxed cards, any chart renders in its own separate card, colored stats (Chores overdue/on-track, Consumables low/empty) show the right color in both light and dark theme, and Costs' YoY arrow/color still renders correctly next to the last-complete-year value.
