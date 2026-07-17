# Summary Card Chart Types Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change the Costs summary chart to a treemap, the Consumables and Chores summary charts to horizontal bar charts, and fix Inventory's category-color assignment so colors never collide, all in `packages/editor` (Svelte 5 + Vitest, no charting library — hand-rolled SVG/CSS following the existing `DonutChart.svelte` precedent).

**Architecture:** Two new pure-logic utils (`colorAssignment.ts`, `treemapLayout.ts` + `colorContrast.ts`) each covered by isolated unit tests, and two new presentational components (`TreemapChart.svelte`, `HorizontalBarChart.svelte`) that consume the same `DonutSegment` shape the existing `DonutChart.svelte` already uses — so call sites swap components with minimal prop changes. A new validated 8-color categorical token ramp is added to `theme.css`.

**Tech Stack:** Svelte 5 (runes), TypeScript strict mode, Vitest 4 + jsdom, no new dependencies.

## Global Constraints

- No new npm dependencies — hand-rolled SVG/CSS only, matching `DonutChart.svelte`.
- `tsconfig.json` has `strict: true`, `noUnusedLocals: true`, `noUnusedParameters: true` — every import must be used; delete dead code rather than leaving it unreferenced.
- Tests live flat under `packages/editor/test/*.test.ts` (no co-located `*.test.ts`, no `__tests__` dirs) and use `mount`/`unmount`/`flushSync`/`tick` from `"svelte"` directly — no `@testing-library/svelte`.
- Run a single test file with: `cd /projects/myhome/packages/editor && npx vitest run test/<File>.test.ts`
- Run the full suite with: `cd /projects/myhome/packages/editor && npm test`
- Typecheck with: `cd /projects/myhome/packages/editor && npm run typecheck`
- Design doc: `docs/superpowers/specs/2026-07-17-summary-chart-types-design.md` — consult it for the "why" behind each decision below.

---

### Task 1: Categorical chart-series color tokens

**Files:**
- Modify: `packages/editor/src/lib/theme.css`

**Interfaces:**
- Produces: CSS custom properties `--chart-series-1` through `--chart-series-8`, defined on `:root` (light) and `[data-theme="dark"]`. Later tasks reference these by name (never by hex) so light/dark swap automatically.

- [ ] **Step 1: Add the light-mode ramp**

In `packages/editor/src/lib/theme.css`, inside the `:root { ... }` block, right after the `/* Semantic */` group (after `--warning: #d99a1b;`, before the `/* Scales (theme-independent) */` comment), insert:

```css
  /* Categorical chart series — validated colorblind-safe order, do not reorder */
  --chart-series-1: #2a78d6; /* blue */
  --chart-series-2: #1baf7a; /* aqua */
  --chart-series-3: #eda100; /* yellow */
  --chart-series-4: #008300; /* green */
  --chart-series-5: #4a3aa7; /* violet */
  --chart-series-6: #e34948; /* red */
  --chart-series-7: #e87ba4; /* magenta */
  --chart-series-8: #eb6834; /* orange */
```

- [ ] **Step 2: Add the dark-mode ramp**

In the same file, inside `[data-theme="dark"] { ... }`, right after `--warning: #fbbf24;` (before the `--shadow-sm` group), insert:

```css
  /* Categorical chart series — same 8 hues, stepped for the dark surface */
  --chart-series-1: #3987e5;
  --chart-series-2: #199e70;
  --chart-series-3: #c98500;
  --chart-series-4: #008300;
  --chart-series-5: #9085e9;
  --chart-series-6: #e66767;
  --chart-series-7: #d55181;
  --chart-series-8: #d95926;
```

- [ ] **Step 3: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/theme.css
git commit -m "feat: add validated categorical chart-series color tokens"
```

---

### Task 2: `colorAssignment.ts` — collision-free category colors

**Files:**
- Create: `packages/editor/src/lib/colorAssignment.ts`
- Test: `packages/editor/test/colorAssignment.test.ts`

**Interfaces:**
- Produces: `assignCategoryColors(categories: string[]): Map<string, string>` — every distinct input string gets a distinct output color string (either `"var(--chart-series-N)"` for N in 1..8, or a generated `"hsl(...)"` string for categories beyond the base 8). Deterministic for a given category set regardless of input order (sorts internally).

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/colorAssignment.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { assignCategoryColors } from "../src/lib/colorAssignment";

describe("assignCategoryColors", () => {
  it("gives every category within the base palette a distinct color", () => {
    const categories = ["Tools", "Furniture", "Electronics", "Books", "Kitchen"];
    const colors = assignCategoryColors(categories);
    const values = [...colors.values()];
    expect(new Set(values).size).toBe(categories.length);
  });

  it("gives every category a distinct color even beyond the 8-slot base palette", () => {
    const categories = Array.from({ length: 15 }, (_, i) => `Category ${i}`);
    const colors = assignCategoryColors(categories);
    const values = [...colors.values()];
    expect(new Set(values).size).toBe(15);
  });

  it("is deterministic for the same category set regardless of input order", () => {
    const a = assignCategoryColors(["Tools", "Furniture", "Electronics"]);
    const b = assignCategoryColors(["Electronics", "Tools", "Furniture"]);
    expect(a).toEqual(b);
  });

  it("returns an empty map for no categories", () => {
    expect(assignCategoryColors([]).size).toBe(0);
  });

  it("deduplicates repeated category names", () => {
    const colors = assignCategoryColors(["Tools", "Tools", "Furniture"]);
    expect(colors.size).toBe(2);
  });

  it("uses the base palette tokens for the first 8 categories", () => {
    const categories = ["A", "B", "C", "D", "E", "F", "G", "H"];
    const colors = assignCategoryColors(categories);
    for (const color of colors.values()) {
      expect(color).toMatch(/^var\(--chart-series-[1-8]\)$/);
    }
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/colorAssignment.test.ts`
Expected: FAIL — cannot find module `../src/lib/colorAssignment`

- [ ] **Step 3: Write the implementation**

Create `packages/editor/src/lib/colorAssignment.ts`:

```ts
// packages/editor/src/lib/colorAssignment.ts

function hashString(str: string): number {
  let h = 0;
  for (const ch of str) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return h;
}

function generatedColor(indexBeyondPalette: number, totalBeyondPalette: number): string {
  const hue = (indexBeyondPalette * 360) / totalBeyondPalette;
  return `hsl(${hue.toFixed(2)}, 60%, 55%)`;
}

const BASE_PALETTE_SIZE = 8;

/**
 * Assigns each category a color guaranteed distinct from every other category
 * currently in the set. Uses open addressing (hash + linear probe) into a
 * slot array sized to the category count, so every category is guaranteed a
 * free slot — no collisions possible. The first 8 slots map to the validated
 * `--chart-series-N` tokens; slots beyond that get an evenly-spaced generated
 * hue (there are exactly as many extra hues as extra slots, so those stay
 * distinct too).
 */
export function assignCategoryColors(categories: string[]): Map<string, string> {
  const sorted = [...new Set(categories)].sort();
  const n = sorted.length;
  if (n === 0) return new Map();

  const usedSlots = new Set<number>();
  const result = new Map<string, string>();
  const extraCount = Math.max(0, n - BASE_PALETTE_SIZE);

  for (const category of sorted) {
    let slot = hashString(category) % n;
    while (usedSlots.has(slot)) {
      slot = (slot + 1) % n;
    }
    usedSlots.add(slot);

    const color =
      slot < BASE_PALETTE_SIZE
        ? `var(--chart-series-${slot + 1})`
        : generatedColor(slot - BASE_PALETTE_SIZE, extraCount);
    result.set(category, color);
  }

  return result;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/colorAssignment.test.ts`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/colorAssignment.ts packages/editor/test/colorAssignment.test.ts
git commit -m "feat: add collision-free category color assignment util"
```

---

### Task 3: Wire Inventory page onto `colorAssignment`

**Files:**
- Modify: `packages/editor/src/lib/components/InventoryPage.svelte:10, 82-115`
- Modify: `packages/editor/test/InventoryPage.test.ts`

**Interfaces:**
- Consumes: `assignCategoryColors(categories: string[]): Map<string, string>` from Task 2.

- [ ] **Step 1: Write the failing test**

Append to `packages/editor/test/InventoryPage.test.ts` (inside the existing `describe("InventoryPage — category summary", ...)` block, after the last `it`):

```ts
  it("gives every category a distinct color, even with more than 8 categories", () => {
    const items = Array.from({ length: 12 }, (_, i) =>
      makeItem({ id: `i${i}`, category: `Category ${i}`, purchasePrice: 10 }),
    );
    const store = makeStore(items);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(InventoryPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    const fills = Array.from(target.querySelectorAll(".chart-card-wrap svg path")).map((p) =>
      p.getAttribute("fill"),
    );
    expect(fills).toHaveLength(12);
    expect(new Set(fills).size).toBe(12);

    unmount(comp);
  });
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/InventoryPage.test.ts`
Expected: FAIL — with 12 categories, `hash % 8` collisions produce fewer than 12 distinct fills (the current buggy behavior).

- [ ] **Step 3: Wire up `assignCategoryColors`**

In `packages/editor/src/lib/components/InventoryPage.svelte`, add the import after the existing `DonutChart` import (line 10):

```ts
  import DonutChart from "./DonutChart.svelte";
  import { assignCategoryColors } from "../colorAssignment";
```

Then replace lines 82–115 (the `PALETTE` constant through the end of `categoryBreakdown`):

```ts
  const PALETTE = ["#5b8def", "#f2994a", "#27ae60", "#eb5757", "#9b51e0", "#17a2b8", "#f2c94c", "#bdbdbd"];

  function paletteFor(str: string): string {
    let h = 0;
    for (const ch of str) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    return PALETTE[h % PALETTE.length];
  }

  interface CategoryCount {
    category: string;
    count: number;
  }

  const categoryCounts = $derived((() => {
    const counts = new Map<string, number>();
    for (const item of store.items) {
      const key = item.category || "Uncategorized";
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return [...counts.entries()]
      .map(([category, count]): CategoryCount => ({ category, count }))
      .sort((a, b) => b.count - a.count);
  })());

  const categoryBreakdown = $derived(
    categoryCounts.map((c) => ({
      id: c.category,
      label: c.category,
      emoji: "📦",
      color: paletteFor(c.category),
      valueLabel: `${c.count}`,
      pct: store.items.length > 0 ? (c.count / store.items.length) * 100 : 0,
    }))
  );
```

with:

```ts
  interface CategoryCount {
    category: string;
    count: number;
  }

  const categoryCounts = $derived((() => {
    const counts = new Map<string, number>();
    for (const item of store.items) {
      const key = item.category || "Uncategorized";
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return [...counts.entries()]
      .map(([category, count]): CategoryCount => ({ category, count }))
      .sort((a, b) => b.count - a.count);
  })());

  const categoryColors = $derived(assignCategoryColors(categoryCounts.map((c) => c.category)));

  const categoryBreakdown = $derived(
    categoryCounts.map((c) => ({
      id: c.category,
      label: c.category,
      emoji: "📦",
      color: categoryColors.get(c.category) ?? "var(--chart-series-1)",
      valueLabel: `${c.count}`,
      pct: store.items.length > 0 ? (c.count / store.items.length) * 100 : 0,
    }))
  );
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/InventoryPage.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/components/InventoryPage.svelte packages/editor/test/InventoryPage.test.ts
git commit -m "fix(inventory): guarantee distinct category colors on the summary chart"
```

---

### Task 4: Wire `HomeInventoryWidget` onto `colorAssignment`

**Files:**
- Modify: `packages/editor/src/lib/components/HomeInventoryWidget.svelte`
- Modify: `packages/editor/test/HomeInventoryWidget.test.ts`

**Interfaces:**
- Consumes: `assignCategoryColors` from Task 2 (same as Task 3 — this file has its own duplicated copy of the old palette logic to remove).

- [ ] **Step 1: Write the failing test**

Append to `packages/editor/test/HomeInventoryWidget.test.ts`, inside the `describe("HomeInventoryWidget", ...)` block, after the last `it`:

```ts
  it("gives every category a distinct color, even with more than 8 categories", async () => {
    const manyDoc = {
      items: Array.from({ length: 10 }, (_, i) => ({
        id: `i${i}`, name: `Item ${i}`, emoji: "📦", category: `Category ${i}`,
        brand: null, model: null, serialNumber: null, purchaseDate: null,
        purchasePrice: null, warrantyExpiryDate: null, notes: "", attachments: [], placement: null,
      })),
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => manyDoc }));
    const inventoryStore = createInventoryStore(getHomeId);
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeInventoryWidget, { target, props: { inventoryStore, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    const fills = Array.from(target.querySelectorAll("svg path")).map((p) => p.getAttribute("fill"));
    expect(fills).toHaveLength(10);
    expect(new Set(fills).size).toBe(10);

    unmount(comp);
    target.remove();
  });
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/HomeInventoryWidget.test.ts`
Expected: FAIL — 10 categories hashed mod 8 produce fewer than 10 distinct fills.

- [ ] **Step 3: Wire up `assignCategoryColors`**

In `packages/editor/src/lib/components/HomeInventoryWidget.svelte`, add the import after the existing `DonutChart` import:

```ts
  import DonutChart from "./DonutChart.svelte";
  import { assignCategoryColors } from "../colorAssignment";
```

Then replace the block from `const PALETTE = ...` through the end of the `segments` derived (currently lines 14–46):

```ts
  const PALETTE = ["#5b8def", "#f2994a", "#27ae60", "#eb5757", "#9b51e0", "#17a2b8", "#f2c94c", "#bdbdbd"];

  function paletteFor(str: string): string {
    let h = 0;
    for (const ch of str) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    return PALETTE[h % PALETTE.length];
  }

  interface CategoryCount {
    category: string;
    count: number;
  }

  const categoryCounts = $derived((() => {
    const counts = new Map<string, number>();
    for (const item of inventoryStore.items) {
      const key = item.category || "Uncategorized";
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return [...counts.entries()]
      .map(([category, count]): CategoryCount => ({ category, count }))
      .sort((a, b) => b.count - a.count);
  })());

  const total = $derived(categoryCounts.reduce((a, c) => a + c.count, 0));

  const segments = $derived(
    categoryCounts.map((c) => ({
      id: c.category,
      label: c.category,
      emoji: "📦",
      color: paletteFor(c.category),
      valueLabel: `${c.count}`,
      pct: total > 0 ? (c.count / total) * 100 : 0,
    }))
  );
```

with:

```ts
  interface CategoryCount {
    category: string;
    count: number;
  }

  const categoryCounts = $derived((() => {
    const counts = new Map<string, number>();
    for (const item of inventoryStore.items) {
      const key = item.category || "Uncategorized";
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return [...counts.entries()]
      .map(([category, count]): CategoryCount => ({ category, count }))
      .sort((a, b) => b.count - a.count);
  })());

  const total = $derived(categoryCounts.reduce((a, c) => a + c.count, 0));

  const categoryColors = $derived(assignCategoryColors(categoryCounts.map((c) => c.category)));

  const segments = $derived(
    categoryCounts.map((c) => ({
      id: c.category,
      label: c.category,
      emoji: "📦",
      color: categoryColors.get(c.category) ?? "var(--chart-series-1)",
      valueLabel: `${c.count}`,
      pct: total > 0 ? (c.count / total) * 100 : 0,
    }))
  );
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/HomeInventoryWidget.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/components/HomeInventoryWidget.svelte packages/editor/test/HomeInventoryWidget.test.ts
git commit -m "fix(inventory): guarantee distinct category colors on the dashboard widget"
```

---

### Task 5: `HorizontalBarChart.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/HorizontalBarChart.svelte`
- Test: `packages/editor/test/HorizontalBarChart.test.ts`

**Interfaces:**
- Consumes: `DonutSegment` type from `./DonutChart.svelte` (`{ id, label, emoji, color, valueLabel, pct }`) — reused as-is, no new type.
- Produces: `HorizontalBarChart` component, props `{ segments: DonutSegment[] }`. Renders one `.hbar-row` per segment **in input order** (callers control ordering — this component does not sort). Bar width is `segments[i].pct` scaled relative to the largest `pct` in the array (not relative to 100%), rendered as inline `style="width:N%"` on `.hbar-fill`.

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/HorizontalBarChart.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import HorizontalBarChart from "../src/lib/components/HorizontalBarChart.svelte";

const segments = [
  { id: "ok", label: "OK", emoji: "🟢", color: "#4caf50", valueLabel: "8", pct: 80 },
  { id: "low", label: "Low", emoji: "🟠", color: "#ff9800", valueLabel: "2", pct: 20 },
];

describe("HorizontalBarChart", () => {
  it("renders one row per segment", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HorizontalBarChart, { target, props: { segments } });
    flushSync();
    expect(target.querySelectorAll(".hbar-row")).toHaveLength(2);
    unmount(comp);
    target.remove();
  });

  it("scales bar width relative to the largest segment", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HorizontalBarChart, { target, props: { segments } });
    flushSync();
    const fills = Array.from(target.querySelectorAll(".hbar-fill")) as HTMLElement[];
    expect(fills[0].style.width).toBe("100%");
    expect(fills[1].style.width).toBe("25%");
    unmount(comp);
    target.remove();
  });

  it("preserves input order rather than sorting by value", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HorizontalBarChart, { target, props: { segments: [segments[1], segments[0]] } });
    flushSync();
    const labels = Array.from(target.querySelectorAll(".hbar-label")).map((el) => el.textContent);
    expect(labels).toEqual(["🟠 Low", "🟢 OK"]);
    unmount(comp);
    target.remove();
  });

  it("renders no rows for an empty segment list", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HorizontalBarChart, { target, props: { segments: [] } });
    flushSync();
    expect(target.querySelectorAll(".hbar-row")).toHaveLength(0);
    unmount(comp);
    target.remove();
  });

  it("includes the value and percent in the row's title tooltip", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HorizontalBarChart, { target, props: { segments } });
    flushSync();
    const row = target.querySelector(".hbar-row") as HTMLElement;
    expect(row.title).toBe("OK: 8 (80%)");
    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/HorizontalBarChart.test.ts`
Expected: FAIL — cannot find module `../src/lib/components/HorizontalBarChart.svelte`

- [ ] **Step 3: Write the implementation**

Create `packages/editor/src/lib/components/HorizontalBarChart.svelte`:

```svelte
<script lang="ts">
  import type { DonutSegment } from "./DonutChart.svelte";

  interface Props {
    segments: DonutSegment[];
  }
  let { segments }: Props = $props();

  const maxPct = $derived(Math.max(...segments.map((s) => s.pct), 0.0001));

  function barWidth(seg: DonutSegment): number {
    return Math.round((seg.pct / maxPct) * 100);
  }
</script>

<div class="hbar-chart">
  {#each segments as seg (seg.id)}
    <div class="hbar-row" title="{seg.label}: {seg.valueLabel} ({seg.pct.toFixed(0)}%)">
      <div class="hbar-label">{seg.emoji} {seg.label}</div>
      <div class="hbar-track">
        <div class="hbar-fill" style="width:{barWidth(seg)}%; background:{seg.color}"></div>
      </div>
      <div class="hbar-value">{seg.valueLabel}</div>
    </div>
  {/each}
</div>

<style>
  .hbar-chart { display: flex; flex-direction: column; gap: 2px; width: 100%; }
  .hbar-row { display: flex; align-items: center; gap: 8px; min-height: 22px; }
  .hbar-label {
    flex: 0 0 110px; font-size: 11px; color: var(--text); white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis;
  }
  .hbar-track {
    flex: 1; height: 14px; background: var(--surface-alt); border-radius: var(--radius-sm);
    overflow: hidden;
  }
  .hbar-fill { height: 100%; border-radius: 0 var(--radius-sm) var(--radius-sm) 0; min-width: 3px; transition: width .2s; }
  .hbar-value { flex: 0 0 auto; font-size: 11px; color: var(--text-muted); font-weight: 600; min-width: 28px; text-align: right; }
</style>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/HorizontalBarChart.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/components/HorizontalBarChart.svelte packages/editor/test/HorizontalBarChart.test.ts
git commit -m "feat: add HorizontalBarChart component"
```

---

### Task 6: Wire Consumables summary card onto `HorizontalBarChart`

**Files:**
- Modify: `packages/editor/src/lib/components/ConsumablesPage.svelte:11, 106-114` (script/markup), `:254` (style)
- Modify: `packages/editor/test/ConsumablesPage.test.ts`

**Interfaces:**
- Consumes: `HorizontalBarChart` from Task 5, fed with the existing `stockBreakdown` derived (already the right shape — `id, label, emoji, color, valueLabel, pct`).

- [ ] **Step 1: Write the failing test**

In `packages/editor/test/ConsumablesPage.test.ts`, replace the existing `"renders one donut segment per non-empty stock bucket and the right stat numbers"` test body:

```ts
    expect(target.querySelectorAll(".chart-card-wrap svg path")).toHaveLength(3);
    expect(target.querySelector(".stat-value.low")?.textContent).toBe("1");
    expect(target.querySelector(".stat-value.empty")?.textContent).toBe("1");
```

with:

```ts
    expect(target.querySelectorAll(".chart-card-wrap .hbar-row")).toHaveLength(3);
    expect(target.querySelector(".stat-value.low")?.textContent).toBe("1");
    expect(target.querySelector(".stat-value.empty")?.textContent).toBe("1");
```

Also rename the test's `it` description from `"renders one donut segment per non-empty stock bucket and the right stat numbers"` to `"renders one bar per non-empty stock bucket and the right stat numbers"`.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/ConsumablesPage.test.ts`
Expected: FAIL — `.hbar-row` doesn't exist yet (still a donut).

- [ ] **Step 3: Swap the component**

In `packages/editor/src/lib/components/ConsumablesPage.svelte`, replace line 11:

```ts
  import DonutChart from "./DonutChart.svelte";
```

with:

```ts
  import HorizontalBarChart from "./HorizontalBarChart.svelte";
```

Replace the `pie-area` block (lines 106–114):

```svelte
          <div class="pie-area">
            <div class="chart-label">Stock status</div>
            <DonutChart
              segments={stockBreakdown}
              centerLabel="Items"
              centerValue={`${store.consumables.length}`}
              showLabels={true}
            />
          </div>
```

with:

```svelte
          <div class="bar-area">
            <div class="chart-label">Stock status — {store.consumables.length} items</div>
            <HorizontalBarChart segments={stockBreakdown} />
          </div>
```

- [ ] **Step 4: Update the CSS**

In the same file's `<style>` block (around line 254), replace:

```css
  .pie-area { flex-shrink: 0; }
```

with:

```css
  .bar-area { flex: 1; min-width: 0; }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/ConsumablesPage.test.ts`
Expected: PASS (all tests in the file)

- [ ] **Step 6: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/components/ConsumablesPage.svelte packages/editor/test/ConsumablesPage.test.ts
git commit -m "feat(consumables): switch stock-status summary chart to a horizontal bar chart"
```

---

### Task 7: Wire Chores summary card onto `HorizontalBarChart`

**Files:**
- Modify: `packages/editor/src/lib/components/ChoresPage.svelte:11, 193-201` (script/markup), `:369` (style)
- Modify: `packages/editor/test/ChoresPage.test.ts`

**Interfaces:**
- Consumes: `HorizontalBarChart` from Task 5, fed with the existing `healthBreakdown` derived.

- [ ] **Step 1: Write the failing test**

In `packages/editor/test/ChoresPage.test.ts`, in the `"renders a donut segment per non-empty health bucket and the right stat numbers"` test, replace:

```ts
    expect(target.querySelectorAll(".chart-card-wrap svg path")).toHaveLength(3);
```

with:

```ts
    expect(target.querySelectorAll(".chart-card-wrap .hbar-row")).toHaveLength(3);
```

Also rename the test's `it` description to `"renders a bar per non-empty health bucket and the right stat numbers"`.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/ChoresPage.test.ts`
Expected: FAIL — `.hbar-row` doesn't exist yet.

- [ ] **Step 3: Swap the component**

In `packages/editor/src/lib/components/ChoresPage.svelte`, replace line 11:

```ts
  import DonutChart from "./DonutChart.svelte";
```

with:

```ts
  import HorizontalBarChart from "./HorizontalBarChart.svelte";
```

Replace the `pie-area` block (lines 193–201):

```svelte
          <div class="pie-area">
            <div class="chart-label">Schedule health</div>
            <DonutChart
              segments={healthBreakdown}
              centerLabel="Assignments"
              centerValue={`${totalAssignments}`}
              showLabels={true}
            />
          </div>
```

with:

```svelte
          <div class="bar-area">
            <div class="chart-label">Schedule health</div>
            <HorizontalBarChart segments={healthBreakdown} />
          </div>
```

- [ ] **Step 4: Update the CSS**

In the same file's `<style>` block (around line 369), replace:

```css
  .pie-area { flex-shrink: 0; }
```

with:

```css
  .bar-area { flex: 1; min-width: 0; }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/ChoresPage.test.ts`
Expected: PASS (all tests in the file)

- [ ] **Step 6: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/components/ChoresPage.svelte packages/editor/test/ChoresPage.test.ts
git commit -m "feat(chores): switch schedule-health summary chart to a horizontal bar chart"
```

---

### Task 8: `colorContrast.ts` — text color for an arbitrary fill

**Files:**
- Create: `packages/editor/src/lib/colorContrast.ts`
- Test: `packages/editor/test/colorContrast.test.ts`

**Interfaces:**
- Produces: `textColorForFill(hex: string): "#ffffff" | "#111111"` — picks readable text ink for a colored background. Falls back to `"#111111"` for unparseable input.

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/colorContrast.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { textColorForFill } from "../src/lib/colorContrast";

describe("textColorForFill", () => {
  it("picks dark text on a white fill", () => {
    expect(textColorForFill("#ffffff")).toBe("#111111");
  });

  it("picks light text on a black fill", () => {
    expect(textColorForFill("#000000")).toBe("#ffffff");
  });

  it("picks light text on a mid-dark blue fill", () => {
    expect(textColorForFill("#2a78d6")).toBe("#ffffff");
  });

  it("picks dark text on a light yellow fill", () => {
    expect(textColorForFill("#eda100")).toBe("#111111");
  });

  it("falls back to dark text for an unparseable value", () => {
    expect(textColorForFill("not-a-color")).toBe("#111111");
    expect(textColorForFill("var(--chart-series-1)")).toBe("#111111");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/colorContrast.test.ts`
Expected: FAIL — cannot find module `../src/lib/colorContrast`

- [ ] **Step 3: Write the implementation**

Create `packages/editor/src/lib/colorContrast.ts`:

```ts
// packages/editor/src/lib/colorContrast.ts

function parseHex(hex: string): [number, number, number] | null {
  const m = /^#([0-9a-f]{6})$/i.exec(hex.trim());
  if (!m) return null;
  const int = parseInt(m[1], 16);
  return [(int >> 16) & 255, (int >> 8) & 255, int & 255];
}

/** Perceived brightness on a 0-255 scale (ITU-R BT.601 weights). */
function brightness(r: number, g: number, b: number): number {
  return (r * 299 + g * 587 + b * 114) / 1000;
}

/**
 * Picks readable ink for text placed directly on an arbitrary fill color
 * (e.g. a treemap cell). Falls back to dark text when the input isn't a
 * parseable `#rrggbb` hex string (e.g. a CSS variable reference).
 */
export function textColorForFill(hex: string): "#ffffff" | "#111111" {
  const rgb = parseHex(hex);
  if (!rgb) return "#111111";
  const [r, g, b] = rgb;
  return brightness(r, g, b) > 140 ? "#111111" : "#ffffff";
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/colorContrast.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/colorContrast.ts packages/editor/test/colorContrast.test.ts
git commit -m "feat: add fill-color-aware text ink util"
```

---

### Task 9: `treemapLayout.ts` — squarified layout + content-tier decision

**Files:**
- Create: `packages/editor/src/lib/treemapLayout.ts`
- Test: `packages/editor/test/treemapLayout.test.ts`

**Interfaces:**
- Produces:
  - `interface Rect { x: number; y: number; w: number; h: number; }`
  - `computeTreemap(values: number[], width: number, height: number): Rect[]` — one `Rect` per input value, same order as input, areas proportional to input values, tiling `width x height` exactly with no gaps or overlaps.
  - `cellContentTier(w: number, h: number): "label" | "icon" | "none"` — pure sizing decision, used by `TreemapChart.svelte` (Task 10) to decide what to render inside a cell.

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/treemapLayout.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { computeTreemap, cellContentTier } from "../src/lib/treemapLayout";

describe("computeTreemap", () => {
  it("tiles the full rectangle with no gaps or overlaps", () => {
    const rects = computeTreemap([50, 30, 20], 300, 200);
    const totalArea = rects.reduce((a, r) => a + r.w * r.h, 0);
    expect(totalArea).toBeCloseTo(300 * 200, 0);
  });

  it("gives each rect area proportional to its input value", () => {
    const rects = computeTreemap([60, 40], 300, 200);
    const area0 = rects[0].w * rects[0].h;
    const area1 = rects[1].w * rects[1].h;
    expect(area0 / area1).toBeCloseTo(60 / 40, 1);
  });

  it("returns one rect per input value", () => {
    const rects = computeTreemap([10, 20, 30], 100, 100);
    expect(rects).toHaveLength(3);
  });

  it("returns an empty array for empty input", () => {
    expect(computeTreemap([], 100, 100)).toEqual([]);
  });

  it("fills the whole rect for a single value", () => {
    const rects = computeTreemap([42], 300, 200);
    expect(rects).toEqual([{ x: 0, y: 0, w: 300, h: 200 }]);
  });
});

describe("cellContentTier", () => {
  it("shows a full label for a roomy cell", () => {
    expect(cellContentTier(100, 50)).toBe("label");
  });

  it("shows only an icon for a small-but-square cell", () => {
    expect(cellContentTier(30, 30)).toBe("icon");
  });

  it("shows nothing for a thin sliver", () => {
    expect(cellContentTier(300, 8)).toBe("none");
  });

  it("shows nothing for a tiny cell", () => {
    expect(cellContentTier(10, 10)).toBe("none");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/treemapLayout.test.ts`
Expected: FAIL — cannot find module `../src/lib/treemapLayout`

- [ ] **Step 3: Write the implementation**

Create `packages/editor/src/lib/treemapLayout.ts`:

```ts
// packages/editor/src/lib/treemapLayout.ts

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

function worstRatio(row: number[], shortSide: number): number {
  const sum = row.reduce((a, b) => a + b, 0);
  const rowMax = Math.max(...row);
  const rowMin = Math.min(...row);
  return Math.max(
    (shortSide * shortSide * rowMax) / (sum * sum),
    (sum * sum) / (shortSide * shortSide * rowMin),
  );
}

function layoutRow(row: number[], rect: Rect, horizontal: boolean): Rect[] {
  const sum = row.reduce((a, b) => a + b, 0);
  const rects: Rect[] = [];
  if (horizontal) {
    const rowHeight = sum / rect.w;
    let x = rect.x;
    for (const v of row) {
      const w = v / rowHeight;
      rects.push({ x, y: rect.y, w, h: rowHeight });
      x += w;
    }
  } else {
    const rowWidth = sum / rect.h;
    let y = rect.y;
    for (const v of row) {
      const h = v / rowWidth;
      rects.push({ x: rect.x, y, w: rowWidth, h });
      y += h;
    }
  }
  return rects;
}

/** Squarified treemap (Bruls, Huizing, van Wijk) — packs cells to stay near-square. */
function squarify(values: number[], rect: Rect): Rect[] {
  if (values.length === 0 || rect.w <= 0 || rect.h <= 0) return values.map(() => ({ x: rect.x, y: rect.y, w: 0, h: 0 }));

  const horizontal = rect.w >= rect.h;
  const shortSide = horizontal ? rect.h : rect.w;

  let row: number[] = [];
  let i = 0;
  while (i < values.length) {
    const candidate = [...row, values[i]];
    if (row.length === 0 || worstRatio(candidate, shortSide) <= worstRatio(row, shortSide)) {
      row = candidate;
      i++;
    } else {
      break;
    }
  }

  const rowRects = layoutRow(row, rect, horizontal);
  const rowSum = row.reduce((a, b) => a + b, 0);

  const remainingRect: Rect = horizontal
    ? { x: rect.x, y: rect.y + rowSum / rect.w, w: rect.w, h: rect.h - rowSum / rect.w }
    : { x: rect.x + rowSum / rect.h, y: rect.y, w: rect.w - rowSum / rect.h, h: rect.h };

  return [...rowRects, ...squarify(values.slice(row.length), remainingRect)];
}

/**
 * Lays out `values` as a squarified treemap filling `width x height`,
 * returning one Rect per value in the same order as the input.
 */
export function computeTreemap(values: number[], width: number, height: number): Rect[] {
  if (values.length === 0) return [];
  const total = values.reduce((a, b) => a + b, 0);
  if (total <= 0) return values.map(() => ({ x: 0, y: 0, w: 0, h: 0 }));
  const area = width * height;
  const scaled = values.map((v) => (v / total) * area);
  return squarify(scaled, { x: 0, y: 0, w: width, h: height });
}

/** Decides how much content a treemap cell of size w x h can hold. */
export function cellContentTier(w: number, h: number): "label" | "icon" | "none" {
  if (w >= 64 && h >= 36) return "label";
  if (w >= 22 && h >= 22) return "icon";
  return "none";
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/treemapLayout.test.ts`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/treemapLayout.ts packages/editor/test/treemapLayout.test.ts
git commit -m "feat: add squarified treemap layout util"
```

---

### Task 10: `TreemapChart.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/TreemapChart.svelte`
- Test: `packages/editor/test/TreemapChart.test.ts`

**Interfaces:**
- Consumes: `DonutSegment` type from `./DonutChart.svelte`; `computeTreemap`, `Rect`, `cellContentTier` from `../treemapLayout` (Task 9); `textColorForFill` from `../colorContrast` (Task 8).
- Produces: `TreemapChart` component, props `{ segments: DonutSegment[]; onsliceclick?: (id: string) => void }`. Renders an SVG with one `<rect>` per segment with `pct > 0`, sized/positioned by `computeTreemap`. Cells sized `label` tier show emoji+label+value text; `icon` tier shows only the emoji; `none` tier shows a bare colored cell (value still available via a native `<title>` tooltip on every cell).

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/TreemapChart.test.ts`:

```ts
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import TreemapChart from "../src/lib/components/TreemapChart.svelte";

const segments = [
  { id: "a", label: "Mortgage", emoji: "🏠", color: "#2a78d6", valueLabel: "10,000 €", pct: 70 },
  { id: "b", label: "Utilities", emoji: "💡", color: "#eda100", valueLabel: "3,000 €", pct: 21 },
  { id: "c", label: "Tax", emoji: "🏛️", color: "#e34948", valueLabel: "1,300 €", pct: 9 },
];

describe("TreemapChart", () => {
  it("renders one rect per segment", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(TreemapChart, { target, props: { segments } });
    flushSync();
    expect(target.querySelectorAll("svg rect")).toHaveLength(3);
    unmount(comp);
    target.remove();
  });

  it("sizes the largest segment's rect area larger than the smallest", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(TreemapChart, { target, props: { segments } });
    flushSync();
    const areaOf = (r: Element) => Number(r.getAttribute("width")) * Number(r.getAttribute("height"));
    const areas = Array.from(target.querySelectorAll("svg rect")).map(areaOf);
    expect(Math.max(...areas)).toBeGreaterThan(Math.min(...areas));
    unmount(comp);
    target.remove();
  });

  it("shows emoji, label, and value text for a single full-size segment", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const single = [{ id: "a", label: "Mortgage", emoji: "🏠", color: "#2a78d6", valueLabel: "10,000 €", pct: 100 }];
    const comp = mount(TreemapChart, { target, props: { segments: single } });
    flushSync();
    const text = target.querySelector("svg")!.textContent ?? "";
    expect(text).toContain("Mortgage");
    expect(text).toContain("10,000 €");
    unmount(comp);
    target.remove();
  });

  it("calls onsliceclick with the segment id when a cell is clicked", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onsliceclick = vi.fn();
    const comp = mount(TreemapChart, { target, props: { segments, onsliceclick } });
    flushSync();
    (target.querySelector("svg g") as SVGGElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();
    expect(onsliceclick).toHaveBeenCalledOnce();
    unmount(comp);
    target.remove();
  });

  it("filters out zero-pct segments", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const withZero = [...segments, { id: "z", label: "Zero", emoji: "0", color: "#000000", valueLabel: "0 €", pct: 0 }];
    const comp = mount(TreemapChart, { target, props: { segments: withZero } });
    flushSync();
    expect(target.querySelectorAll("svg rect")).toHaveLength(3);
    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/TreemapChart.test.ts`
Expected: FAIL — cannot find module `../src/lib/components/TreemapChart.svelte`

- [ ] **Step 3: Write the implementation**

Create `packages/editor/src/lib/components/TreemapChart.svelte`:

```svelte
<script lang="ts">
  import type { DonutSegment } from "./DonutChart.svelte";
  import { computeTreemap, cellContentTier } from "../treemapLayout";
  import { textColorForFill } from "../colorContrast";

  interface Props {
    segments: DonutSegment[];
    onsliceclick?: (id: string) => void;
  }
  let { segments, onsliceclick }: Props = $props();

  const WIDTH = 300;
  const HEIGHT = 200;

  interface Cell {
    seg: DonutSegment;
    x: number;
    y: number;
    w: number;
    h: number;
    textColor: string;
    tier: "label" | "icon" | "none";
  }

  const cells = $derived((() => {
    const sorted = [...segments].filter((s) => s.pct > 0).sort((a, b) => b.pct - a.pct);
    const rects = computeTreemap(sorted.map((s) => s.pct), WIDTH, HEIGHT);
    return sorted.map((seg, i): Cell => {
      const r = rects[i];
      return {
        seg,
        x: r.x,
        y: r.y,
        w: r.w,
        h: r.h,
        textColor: textColorForFill(seg.color),
        tier: cellContentTier(r.w, r.h),
      };
    });
  })());
</script>

<svg viewBox="0 0 {WIDTH} {HEIGHT}" width={WIDTH} height={HEIGHT}>
  {#each cells as cell (cell.seg.id)}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <g style="cursor:{onsliceclick ? 'pointer' : 'default'}" onclick={() => onsliceclick?.(cell.seg.id)}>
      <title>{cell.seg.label}: {cell.seg.valueLabel} ({cell.seg.pct.toFixed(0)}%)</title>
      <rect
        x={cell.x + 1}
        y={cell.y + 1}
        width={Math.max(cell.w - 2, 0)}
        height={Math.max(cell.h - 2, 0)}
        fill={cell.seg.color}
        rx="3"
      />
      {#if cell.tier === "label"}
        <text x={cell.x + 6} y={cell.y + 15} fill={cell.textColor} font-size="10" font-family="sans-serif" font-weight="600">{cell.seg.emoji} {cell.seg.label}</text>
        <text x={cell.x + 6} y={cell.y + 28} fill={cell.textColor} font-size="9" font-family="sans-serif" opacity="0.85">{cell.seg.valueLabel} · {cell.seg.pct.toFixed(0)}%</text>
      {:else if cell.tier === "icon"}
        <text x={cell.x + cell.w / 2} y={cell.y + cell.h / 2 + 4} text-anchor="middle" fill={cell.textColor} font-size="13">{cell.seg.emoji}</text>
      {/if}
    </g>
  {/each}
</svg>

<style>
  svg { overflow: visible; }
</style>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/TreemapChart.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/components/TreemapChart.svelte packages/editor/test/TreemapChart.test.ts
git commit -m "feat: add TreemapChart component"
```

---

### Task 11: Wire Costs summary card onto `TreemapChart`

**Files:**
- Modify: `packages/editor/src/lib/components/CostsPage.svelte:11, 164-183`
- Modify: `packages/editor/test/CostsPage.test.ts`

**Interfaces:**
- Consumes: `TreemapChart` from Task 10, fed with the existing `breakdown` derived mapped the same way the donut was, minus `centerLabel`/`centerValue` (no center in a treemap). Keeps the existing `onsliceclick={(id) => { chartModalCategoryId = id; }}` wiring unchanged.

- [ ] **Step 1: Write the failing test**

Add a new `describe` block to `packages/editor/test/CostsPage.test.ts`, after the existing one:

```ts
describe("CostsPage — category breakdown treemap", () => {
  it("renders one treemap cell per category", () => {
    const store = makeCostsStore([makeEntry()]);
    store.breakdownLastCompleteYear = vi.fn().mockReturnValue([
      { categoryId: "cat-electricity", name: "Electricity", emoji: "💡", color: "#2a78d6", totalAmount: 1200, pct: 100 },
    ]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(CostsPage, {
      target,
      props: { costsStore: store, settingsStore: makeSettingsStore(), floorStore: { floors: [] } },
    });
    flushSync();

    expect(target.querySelectorAll(".chart-card-wrap svg rect")).toHaveLength(1);

    unmount(comp);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/CostsPage.test.ts`
Expected: FAIL — no `svg rect` yet (still a donut, which renders `svg path`).

- [ ] **Step 3: Swap the component**

In `packages/editor/src/lib/components/CostsPage.svelte`, replace line 11:

```ts
  import DonutChart from "./DonutChart.svelte";
```

with:

```ts
  import TreemapChart from "./TreemapChart.svelte";
```

Replace the `pie-area` block (lines 164–183):

```svelte
          <!-- Pie chart with connector labels -->
          <div class="pie-area">
            <div class="chart-label">
              {lastCompleteYearNum} — breakdown by category
            </div>
            <DonutChart
              segments={breakdown.map((b) => ({
                id: b.categoryId,
                label: b.name,
                emoji: b.emoji,
                color: b.color,
                valueLabel: `${b.totalAmount.toLocaleString(undefined, { maximumFractionDigits: 0 })} €`,
                pct: b.pct,
              }))}
              centerLabel="Total"
              centerValue={`${breakdown.reduce((a, b) => a + b.totalAmount, 0).toLocaleString(undefined, { maximumFractionDigits: 0 })} €`}
              showLabels={true}
              onsliceclick={(id) => { chartModalCategoryId = id; }}
            />
          </div>
```

with:

```svelte
          <!-- Treemap breakdown by category -->
          <div class="pie-area">
            <div class="chart-label">
              {lastCompleteYearNum} — breakdown by category
            </div>
            <TreemapChart
              segments={breakdown.map((b) => ({
                id: b.categoryId,
                label: b.name,
                emoji: b.emoji,
                color: b.color,
                valueLabel: `${b.totalAmount.toLocaleString(undefined, { maximumFractionDigits: 0 })} €`,
                pct: b.pct,
              }))}
              onsliceclick={(id) => { chartModalCategoryId = id; }}
            />
          </div>
```

(`.pie-area` CSS is unchanged — `TreemapChart` is a fixed-size SVG just like `DonutChart` was, so `flex-shrink: 0` still applies correctly.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/CostsPage.test.ts`
Expected: PASS (both describe blocks)

- [ ] **Step 5: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/components/CostsPage.svelte packages/editor/test/CostsPage.test.ts
git commit -m "feat(costs): switch category-breakdown summary chart to a treemap"
```

---

### Task 12: Full suite + typecheck

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `cd /projects/myhome/packages/editor && npm test`
Expected: all tests pass, including every file touched in Tasks 1–11.

- [ ] **Step 2: Run typecheck**

Run: `cd /projects/myhome/packages/editor && npm run typecheck`
Expected: no errors — in particular, confirm no unused-import errors from the removed `PALETTE`/`paletteFor`/`DonutChart` references in Tasks 3, 4, 6, 7, 11.

- [ ] **Step 3: Fix any failures**

If either command fails, fix the issue in the relevant file from Tasks 1–11 and re-run both commands until clean. Do not proceed to Task 13 until both pass.

---

### Task 13: Manual browser verification

**Files:** none (manual verification only)

- [ ] **Step 1: Start the dev server**

Run (from repo root): `cd /projects/myhome/packages/editor && npm run dev` (background), then use the `webapp-testing` skill (Playwright) to drive a browser against it.

- [ ] **Step 2: Verify each changed chart in light mode**

Navigate to each module page and confirm:
- **Costs** — the category breakdown renders as a treemap (rectangles sized by spend, not a donut); clicking a cell opens that category's filtered entry modal (same behavior the donut used to have).
- **Consumables** — "Stock status" renders as horizontal bars (one row per ok/low/empty bucket present), with the total item count visible in the section label.
- **Chores** — "Schedule health" renders as horizontal bars (one row per on-track/due-soon/overdue bucket present).
- **Inventory** — category donut still renders (unchanged chart type); if the seeded/demo data has more than 8 categories, confirm no two categories share a visibly identical color.

- [ ] **Step 3: Verify dark mode**

Toggle dark mode (via the app's theme switcher) and repeat the same checks — confirm the treemap/bar chart colors and text remain legible (no white-on-white or black-on-black), since `--chart-series-*` and category-persisted colors both have dark-mode variants.

- [ ] **Step 4: Check for layout regressions**

Confirm no label/cell overlap, no horizontal scrollbars introduced on the chart cards, and that the `stats-area`/`stat-chip` side panels on Consumables and Chores still render correctly next to the new bar charts.

- [ ] **Step 5: Fix and re-verify**

If any visual issue is found (e.g. treemap text overflow, bar chart column too narrow), fix it in the relevant component from Tasks 5–11, re-run that task's unit tests, and repeat Steps 2–4.
