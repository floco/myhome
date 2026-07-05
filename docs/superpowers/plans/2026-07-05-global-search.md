# Global Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `Ctrl/Cmd+K` command palette (plus a topbar search icon) that searches across Chores, Inventory, Consumables, Works, Costs, and Knowledge Base for the current home, and opens the matching item's existing detail view when a result is selected.

**Architecture:** A pure `searchIndex.ts` module projects the six already-loaded module stores into a flat, filterable list. A new `CommandPalette.svelte` overlay component owns the query input, keyboard navigation, and result list, fed by that index. `App.svelte` wires the palette's open state, builds the index from its existing stores, and on selection sets the target module's `selectedItemId`-style prop — a pattern that already exists on `InventoryPage.svelte` and is extended here to the other five pages so each can be told "open item X" externally.

**Tech Stack:** Svelte 5 (runes), TypeScript, Vitest (`mount`/`unmount`/`flushSync`/`tick` component testing, no Testing Library).

**Spec:** `docs/superpowers/specs/2026-07-05-global-search-design.md`

---

### Task 1: `searchIndex.ts` — build and filter the search index

**Files:**
- Create: `packages/editor/src/lib/searchIndex.ts`
- Test: `packages/editor/test/searchIndex.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// packages/editor/test/searchIndex.test.ts
import { describe, it, expect } from "vitest";
import { buildSearchIndex, filterResults, MODULE_ORDER } from "../src/lib/searchIndex";

function makeStores(overrides: Partial<Parameters<typeof buildSearchIndex>[0]> = {}) {
  return {
    choreStore: { chores: [] },
    inventoryStore: { items: [] },
    consumableStore: { consumables: [] },
    worksStore: { works: [] },
    costsStore: { entries: [] },
    kbStore: { entries: [] },
    settingsStore: { costCategories: [], workCategories: [], suppliers: [] },
    ...overrides,
  };
}

describe("buildSearchIndex", () => {
  it("maps a chore into a SearchResult using its own emoji and next due date", () => {
    const stores = makeStores({
      choreStore: {
        chores: [
          { id: "c1", name: "Sweep kitchen", emoji: "🧹", description: "Daily sweep", nextDueDate: "2026-08-01T00:00:00.000Z" } as any,
        ],
      },
    });
    const index = buildSearchIndex(stores);
    expect(index).toEqual([
      {
        module: "chores",
        id: "c1",
        icon: "🧹",
        title: "Sweep kitchen",
        subtitle: "Aug 1, 2026",
        searchText: "sweep kitchen daily sweep",
        titleText: "sweep kitchen",
      },
    ]);
  });

  it("maps an inventory item using its category as subtitle", () => {
    const stores = makeStores({
      inventoryStore: {
        items: [
          { id: "i1", name: "Samsung TV", emoji: "📺", category: "Electronics", brand: "Samsung", model: "QE65", serialNumber: "XYZ", notes: "Living room" } as any,
        ],
      },
    });
    const index = buildSearchIndex(stores);
    expect(index[0]).toEqual({
      module: "inventory",
      id: "i1",
      icon: "📺",
      title: "Samsung TV",
      subtitle: "Electronics",
      searchText: "samsung tv samsung qe65 xyz living room",
      titleText: "samsung tv",
    });
  });

  it("falls back to a default subtitle when an inventory item has no category", () => {
    const stores = makeStores({
      inventoryStore: { items: [{ id: "i1", name: "Ladder", emoji: "🪜", category: "", brand: null, model: null, serialNumber: null, notes: "" } as any] },
    });
    const index = buildSearchIndex(stores);
    expect(index[0].subtitle).toBe("Inventory");
  });

  it("maps a consumable using quantity and unit as subtitle", () => {
    const stores = makeStores({
      consumableStore: { consumables: [{ id: "co1", name: "Dish Soap", emoji: "🧴", unit: "mL", quantity: 250, description: "Under the sink" } as any] },
    });
    const index = buildSearchIndex(stores);
    expect(index[0]).toEqual({
      module: "consumables",
      id: "co1",
      icon: "🧴",
      title: "Dish Soap",
      subtitle: "250 mL",
      searchText: "dish soap under the sink",
      titleText: "dish soap",
    });
  });

  it("maps a work using a humanized status and date as subtitle, with its category emoji", () => {
    const stores = makeStores({
      worksStore: { works: [{ id: "w1", title: "Fix roof leak", description: "Patch near chimney", notes: "", status: "in_progress", categoryId: "wcat-roofing", date: "2026-06-10T00:00:00.000Z" } as any] },
      settingsStore: { costCategories: [], suppliers: [], workCategories: [{ id: "wcat-roofing", name: "Roofing", emoji: "🏠" }] },
    });
    const index = buildSearchIndex(stores);
    expect(index[0]).toEqual({
      module: "works",
      id: "w1",
      icon: "🏠",
      title: "Fix roof leak",
      subtitle: "In progress · Jun 10, 2026",
      searchText: "fix roof leak patch near chimney",
      titleText: "fix roof leak",
    });
  });

  it("falls back to a default icon when a work has no matching category", () => {
    const stores = makeStores({
      worksStore: { works: [{ id: "w1", title: "Fix roof leak", description: "", notes: "", status: "planned", categoryId: null, date: "2026-06-10T00:00:00.000Z" } as any] },
    });
    const index = buildSearchIndex(stores);
    expect(index[0].icon).toBe("🔧");
  });

  it("maps a cost entry resolving category and supplier names, with the category emoji", () => {
    const stores = makeStores({
      costsStore: { entries: [{ id: "ce1", categoryId: "cat-electricity", supplierId: "sup1", notes: "Winter bill", totalAmount: 120.5 } as any] },
      settingsStore: {
        costCategories: [{ id: "cat-electricity", name: "Electricity", emoji: "💡", unit: "kWh", color: "#4466cc" }],
        workCategories: [],
        suppliers: [{ id: "sup1", name: "PowerCo" }],
      },
    });
    const index = buildSearchIndex(stores);
    expect(index[0]).toEqual({
      module: "costs",
      id: "ce1",
      icon: "💡",
      title: "Electricity",
      subtitle: "120.5 €",
      searchText: "electricity powerco winter bill",
      titleText: "electricity",
    });
  });

  it("maps a KB entry using the fixed Knowledge Base icon and subtitle", () => {
    const stores = makeStores({
      kbStore: { entries: [{ id: "kb1", title: "Boiler manual", content: "Reset procedure is..." } as any] },
    });
    const index = buildSearchIndex(stores);
    expect(index[0]).toEqual({
      module: "kb",
      id: "kb1",
      icon: "📄",
      title: "Boiler manual",
      subtitle: "Knowledge Base",
      searchText: "boiler manual reset procedure is...",
      titleText: "boiler manual",
    });
  });
});

describe("filterResults", () => {
  const index = [
    { module: "chores" as const, id: "c1", icon: "🧹", title: "Sweep kitchen", subtitle: "", searchText: "sweep kitchen daily sweep", titleText: "sweep kitchen" },
    { module: "chores" as const, id: "c2", icon: "🪟", title: "Clean windows", subtitle: "", searchText: "clean windows sweep up glass dust", titleText: "clean windows" },
    { module: "inventory" as const, id: "i1", icon: "📺", title: "Samsung TV", subtitle: "", searchText: "samsung tv", titleText: "samsung tv" },
  ];

  it("returns nothing for queries shorter than 2 characters", () => {
    expect(filterResults(index, "s")).toEqual([]);
    expect(filterResults(index, "")).toEqual([]);
  });

  it("matches case-insensitively against searchText", () => {
    const results = filterResults(index, "SAMSUNG");
    expect(results.map((r) => r.id)).toEqual(["i1"]);
  });

  it("ranks title matches above body-only matches within the same module", () => {
    // "sweep" matches c1's title and c2's body text only
    const results = filterResults(index, "sweep");
    expect(results.map((r) => r.id)).toEqual(["c1", "c2"]);
  });

  it("groups results by module in the fixed MODULE_ORDER", () => {
    const results = filterResults(index, "s");
    // not reachable due to min-length guard; use a 2+ char query matching all three
    const results2 = filterResults(index, "sa");
    expect(results2.map((r) => r.module)).toEqual(["inventory"]);
    expect(MODULE_ORDER).toEqual(["chores", "inventory", "consumables", "works", "costs", "kb"]);
  });

  it("caps results at the given limit", () => {
    const big = Array.from({ length: 25 }, (_, i) => ({
      module: "chores" as const, id: `c${i}`, icon: "🧹", title: `Sweep ${i}`, subtitle: "", searchText: `sweep ${i}`, titleText: `sweep ${i}`,
    }));
    expect(filterResults(big, "sweep", 20).length).toBe(20);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run searchIndex.test.ts` (from `packages/editor/`)
Expected: FAIL — `Cannot find module '../src/lib/searchIndex'`

- [ ] **Step 3: Write the implementation**

```ts
// packages/editor/src/lib/searchIndex.ts
import type { Chore } from "./choreStore.svelte";
import type { InventoryItem } from "./inventoryStore.svelte";
import type { Consumable } from "./consumableStore.svelte";
import type { Work } from "./worksStore.svelte";
import type { CostEntry } from "./costsStore.svelte";
import type { KBEntry } from "./kbStore.svelte";
import type { CostCategory, WorkCategory, Supplier } from "./settingsStore.svelte";

export type SearchModule = "chores" | "inventory" | "consumables" | "works" | "costs" | "kb";

export const MODULE_ORDER: SearchModule[] = ["chores", "inventory", "consumables", "works", "costs", "kb"];

export const MODULE_LABELS: Record<SearchModule, string> = {
  chores: "Chores",
  inventory: "Inventory",
  consumables: "Consumables",
  works: "Works",
  costs: "Costs",
  kb: "Knowledge Base",
};

export interface SearchResult {
  module: SearchModule;
  id: string;
  icon: string;
  title: string;
  subtitle: string;
  searchText: string;
  titleText: string;
}

export interface SearchStores {
  choreStore: { chores: Chore[] };
  inventoryStore: { items: InventoryItem[] };
  consumableStore: { consumables: Consumable[] };
  worksStore: { works: Work[] };
  costsStore: { entries: CostEntry[] };
  kbStore: { entries: KBEntry[] };
  settingsStore: { costCategories: CostCategory[]; workCategories: WorkCategory[]; suppliers: Supplier[] };
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function statusLabel(status: Work["status"]): string {
  if (status === "in_progress") return "In progress";
  if (status === "done") return "Done";
  return "Planned";
}

function norm(...parts: (string | null | undefined)[]): string {
  return parts.filter((p): p is string => !!p).join(" ").toLowerCase();
}

export function buildSearchIndex(stores: SearchStores): SearchResult[] {
  const results: SearchResult[] = [];

  for (const chore of stores.choreStore.chores) {
    results.push({
      module: "chores",
      id: chore.id,
      icon: chore.emoji,
      title: chore.name,
      subtitle: fmtDate(chore.nextDueDate),
      searchText: norm(chore.name, chore.description),
      titleText: chore.name.toLowerCase(),
    });
  }

  for (const item of stores.inventoryStore.items) {
    results.push({
      module: "inventory",
      id: item.id,
      icon: item.emoji,
      title: item.name,
      subtitle: item.category || "Inventory",
      searchText: norm(item.name, item.brand, item.model, item.serialNumber, item.notes),
      titleText: item.name.toLowerCase(),
    });
  }

  for (const c of stores.consumableStore.consumables) {
    results.push({
      module: "consumables",
      id: c.id,
      icon: c.emoji,
      title: c.name,
      subtitle: `${c.quantity} ${c.unit}`,
      searchText: norm(c.name, c.description),
      titleText: c.name.toLowerCase(),
    });
  }

  const workCategoryMap = new Map(stores.settingsStore.workCategories.map((c) => [c.id, c]));
  for (const work of stores.worksStore.works) {
    const category = work.categoryId ? workCategoryMap.get(work.categoryId) : undefined;
    results.push({
      module: "works",
      id: work.id,
      icon: category?.emoji ?? "🔧",
      title: work.title,
      subtitle: `${statusLabel(work.status)} · ${fmtDate(work.date)}`,
      searchText: norm(work.title, work.description, work.notes),
      titleText: work.title.toLowerCase(),
    });
  }

  const costCategoryMap = new Map(stores.settingsStore.costCategories.map((c) => [c.id, c]));
  const supplierMap = new Map(stores.settingsStore.suppliers.map((s) => [s.id, s]));
  for (const entry of stores.costsStore.entries) {
    const category = costCategoryMap.get(entry.categoryId);
    const supplier = entry.supplierId ? supplierMap.get(entry.supplierId) : undefined;
    const title = category?.name ?? "Cost entry";
    results.push({
      module: "costs",
      id: entry.id,
      icon: category?.emoji ?? "💶",
      title,
      subtitle: `${entry.totalAmount} €`,
      searchText: norm(title, supplier?.name, entry.notes),
      titleText: title.toLowerCase(),
    });
  }

  for (const entry of stores.kbStore.entries) {
    results.push({
      module: "kb",
      id: entry.id,
      icon: "📄",
      title: entry.title,
      subtitle: "Knowledge Base",
      searchText: norm(entry.title, entry.content),
      titleText: entry.title.toLowerCase(),
    });
  }

  return results;
}

export function filterResults(index: SearchResult[], query: string, limit = 20): SearchResult[] {
  const q = query.trim().toLowerCase();
  if (q.length < 2) return [];

  const matches = index.filter((r) => r.searchText.includes(q));
  matches.sort((a, b) => {
    const moduleDelta = MODULE_ORDER.indexOf(a.module) - MODULE_ORDER.indexOf(b.module);
    if (moduleDelta !== 0) return moduleDelta;
    const aTitle = a.titleText.includes(q) ? 0 : 1;
    const bTitle = b.titleText.includes(q) ? 0 : 1;
    return aTitle - bTitle;
  });
  return matches.slice(0, limit);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run searchIndex.test.ts` (from `packages/editor/`)
Expected: PASS (all cases in both `describe` blocks)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/searchIndex.ts packages/editor/test/searchIndex.test.ts
git commit -m "feat: add searchIndex module for global search"
```

---

### Task 2: `CommandPalette.svelte` — overlay UI

**Files:**
- Create: `packages/editor/src/lib/components/CommandPalette.svelte`
- Test: `packages/editor/test/CommandPalette.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// packages/editor/test/CommandPalette.test.ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import CommandPalette from "../src/lib/components/CommandPalette.svelte";
import type { SearchResult } from "../src/lib/searchIndex";

afterEach(() => { document.body.innerHTML = ""; });

const INDEX: SearchResult[] = [
  { module: "chores", id: "c1", icon: "🧹", title: "Sweep kitchen", subtitle: "Aug 1, 2026", searchText: "sweep kitchen home", titleText: "sweep kitchen" },
  { module: "inventory", id: "i1", icon: "📺", title: "Samsung TV", subtitle: "Electronics", searchText: "samsung tv home", titleText: "samsung tv" },
];

function mountPalette(props: { open: boolean; index: SearchResult[]; onclose: () => void; onselect: (r: SearchResult) => void }) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const comp = mount(CommandPalette, { target, props });
  flushSync();
  return { target, comp };
}

describe("CommandPalette", () => {
  it("renders nothing when closed", () => {
    const { target, comp } = mountPalette({ open: false, index: INDEX, onclose: vi.fn(), onselect: vi.fn() });
    expect(target.querySelector(".cmdk")).toBeNull();
    unmount(comp);
  });

  it("shows no results below the minimum query length", async () => {
    const { target, comp } = mountPalette({ open: true, index: INDEX, onclose: vi.fn(), onselect: vi.fn() });
    const input = target.querySelector("input") as HTMLInputElement;
    input.value = "s";
    input.dispatchEvent(new Event("input"));
    flushSync();
    expect(target.querySelectorAll(".cmdk-result").length).toBe(0);
    unmount(comp);
  });

  it("filters results as the query changes and groups them by module", async () => {
    const { target, comp } = mountPalette({ open: true, index: INDEX, onclose: vi.fn(), onselect: vi.fn() });
    const input = target.querySelector("input") as HTMLInputElement;
    input.value = "samsung";
    input.dispatchEvent(new Event("input"));
    flushSync();
    const results = target.querySelectorAll(".cmdk-result");
    expect(results.length).toBe(1);
    expect(results[0].textContent).toContain("Samsung TV");
    expect(target.querySelector(".cmdk-group-label")?.textContent).toBe("Inventory");
    unmount(comp);
  });

  it("calls onselect with the highlighted result on Enter", async () => {
    const onselect = vi.fn();
    const { target, comp } = mountPalette({ open: true, index: INDEX, onclose: vi.fn(), onselect });
    const input = target.querySelector("input") as HTMLInputElement;
    input.value = "sweep";
    input.dispatchEvent(new Event("input"));
    flushSync();
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    flushSync();
    expect(onselect).toHaveBeenCalledWith(INDEX[0]);
    unmount(comp);
  });

  it("moves the highlight with ArrowDown and selects the second result", async () => {
    // Both fixture entries share the word "home" in their searchText,
    // so this query surfaces both, in fixed module order (chores before inventory).
    const onselect = vi.fn();
    const { target, comp } = mountPalette({ open: true, index: INDEX, onclose: vi.fn(), onselect });
    const input = target.querySelector("input") as HTMLInputElement;
    input.value = "home";
    input.dispatchEvent(new Event("input"));
    flushSync();
    expect(target.querySelectorAll(".cmdk-result").length).toBe(2);

    input.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
    flushSync();
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    flushSync();

    expect(onselect).toHaveBeenCalledWith(INDEX[1]);
    unmount(comp);
  });

  it("closes on Escape without selecting anything", () => {
    const onclose = vi.fn();
    const onselect = vi.fn();
    const { target, comp } = mountPalette({ open: true, index: INDEX, onclose, onselect });
    const input = target.querySelector("input") as HTMLInputElement;
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    flushSync();
    expect(onclose).toHaveBeenCalledOnce();
    expect(onselect).not.toHaveBeenCalled();
    unmount(comp);
  });

});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run CommandPalette.test.ts` (from `packages/editor/`)
Expected: FAIL — `Cannot find module '../src/lib/components/CommandPalette.svelte'`

- [ ] **Step 3: Write the implementation**

```svelte
<!-- packages/editor/src/lib/components/CommandPalette.svelte -->
<script lang="ts">
  import { filterResults, MODULE_LABELS, MODULE_ORDER, type SearchResult } from "../searchIndex";

  interface Props {
    open: boolean;
    index: SearchResult[];
    onclose: () => void;
    onselect: (result: SearchResult) => void;
  }
  let { open, index, onclose, onselect }: Props = $props();

  let query = $state("");
  let highlighted = $state(0);
  let inputEl: HTMLInputElement | undefined = $state();

  const results = $derived(filterResults(index, query));

  const groups = $derived.by(() => {
    const byModule = new Map<string, SearchResult[]>();
    for (const r of results) {
      if (!byModule.has(r.module)) byModule.set(r.module, []);
      byModule.get(r.module)!.push(r);
    }
    return MODULE_ORDER
      .filter((m) => byModule.has(m))
      .map((m) => ({ module: m, label: MODULE_LABELS[m], items: byModule.get(m)! }));
  });

  $effect(() => {
    if (open) {
      query = "";
      highlighted = 0;
      inputEl?.focus();
    }
  });

  $effect(() => {
    results;
    highlighted = 0;
  });

  function handleKeydown(e: KeyboardEvent): void {
    if (e.key === "Escape") { onclose(); return; }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (results.length > 0) highlighted = (highlighted + 1) % results.length;
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (results.length > 0) highlighted = (highlighted - 1 + results.length) % results.length;
      return;
    }
    if (e.key === "Enter") {
      const target = results[highlighted];
      if (target) onselect(target);
    }
  }

  function flatIndexOf(result: SearchResult): number {
    return results.indexOf(result);
  }
</script>

{#if open}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div class="cmdk-backdrop" role="presentation" onclick={onclose}></div>
  <div class="cmdk" role="dialog" aria-modal="true" aria-label="Global search">
    <input
      bind:this={inputEl}
      class="cmdk-input"
      type="text"
      placeholder="Search chores, inventory, works, costs…"
      bind:value={query}
      onkeydown={handleKeydown}
    />
    <div class="cmdk-results">
      {#if query.trim().length >= 2 && results.length === 0}
        <div class="cmdk-empty">No results for '{query}'</div>
      {/if}
      {#each groups as group (group.module)}
        <div class="cmdk-group-label">{group.label}</div>
        {#each group.items as result (result.id)}
          <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
          <div
            class="cmdk-result"
            class:highlighted={flatIndexOf(result) === highlighted}
            onclick={() => onselect(result)}
          >
            <span class="cmdk-result-icon">{result.icon}</span>
            <div class="cmdk-result-text">
              <div class="cmdk-result-title">{result.title}</div>
              <div class="cmdk-result-subtitle">{result.subtitle}</div>
            </div>
          </div>
        {/each}
      {/each}
    </div>
  </div>
{/if}

<style>
  .cmdk-backdrop {
    position: fixed; inset: 0; z-index: 199;
    background: rgba(0, 0, 0, 0.45);
  }
  .cmdk {
    position: fixed; top: 12vh; left: 50%; transform: translateX(-50%);
    z-index: 200;
    width: min(90vw, 560px);
    background: var(--surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-lg);
    display: flex; flex-direction: column;
    max-height: 70vh; overflow: hidden;
  }
  .cmdk-input {
    font-family: var(--font-sans);
    font-size: 14px;
    background: var(--surface-alt);
    color: var(--text);
    border: none;
    border-bottom: 1px solid var(--border);
    padding: 14px 16px;
    box-sizing: border-box;
  }
  .cmdk-input:focus { outline: none; }
  .cmdk-results { overflow-y: auto; padding: var(--space-2); }
  .cmdk-empty { padding: 16px; font-size: 12px; color: var(--text-faint); text-align: center; }
  .cmdk-group-label {
    font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
    color: var(--text-faint); padding: 8px 10px 4px;
  }
  .cmdk-result {
    display: flex; align-items: center; gap: var(--space-2);
    padding: 8px 10px; border-radius: var(--radius-md); cursor: pointer;
  }
  .cmdk-result:hover, .cmdk-result.highlighted { background: var(--surface-hover); }
  .cmdk-result-icon { font-size: 16px; flex-shrink: 0; }
  .cmdk-result-title { font-size: 13px; color: var(--text); font-weight: 500; }
  .cmdk-result-subtitle { font-size: 11px; color: var(--text-faint); margin-top: 1px; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run CommandPalette.test.ts` (from `packages/editor/`)
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/CommandPalette.svelte packages/editor/test/CommandPalette.test.ts
git commit -m "feat: add CommandPalette overlay component"
```

---

### Task 3: Extend `ChoresPage.svelte` with external selection

**Files:**
- Modify: `packages/editor/src/lib/components/ChoresPage.svelte`
- Test: `packages/editor/test/ChoresPage.test.ts` (new)

- [ ] **Step 1: Write the failing test**

```ts
// packages/editor/test/ChoresPage.test.ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import ChoresPage from "../src/lib/components/ChoresPage.svelte";
import type { Chore } from "../src/lib/choreStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makeChore(overrides: Partial<Chore> = {}): Chore {
  return {
    id: "c1", donetickId: null, name: "Sweep kitchen", emoji: "🧹",
    periodDays: 7, frequencyType: "interval", frequency: 7, frequencyMetadata: {},
    scheduleFromDue: false, nextDueDate: "2026-08-01T00:00:00.000Z", description: "", attachments: [],
    ...overrides,
  };
}

function makeStore(chores: Chore[]) {
  return {
    chores,
    assignments: [],
    completions: [],
    loaded: true,
    loadError: null,
    createChore: vi.fn(),
    updateChore: vi.fn(),
    deleteChore: vi.fn(),
    completeChore: vi.fn(),
    createAssignment: vi.fn(),
    updateAssignmentPosition: vi.fn(),
    removeAssignment: vi.fn(),
    completeAssignment: vi.fn(),
  };
}

describe("ChoresPage — external selection", () => {
  it("opens the edit modal for the chore matching selectedItemId and clears selection", () => {
    const chore = makeChore();
    const store = makeStore([chore]);
    const onclearselection = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(ChoresPage, {
      target,
      props: { store, floorStore: { floors: [] }, selectedItemId: "c1", onclearselection },
    });
    flushSync();

    expect(target.querySelector(".ui-modal-title")?.textContent).toBe("🧹 Sweep kitchen");
    expect(onclearselection).toHaveBeenCalledOnce();

    unmount(comp);
  });

  it("does nothing when selectedItemId doesn't match any chore", () => {
    const store = makeStore([makeChore()]);
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(ChoresPage, {
      target,
      props: { store, floorStore: { floors: [] }, selectedItemId: "missing" },
    });
    flushSync();

    expect(target.querySelector(".ui-modal-title")).toBeNull();

    unmount(comp);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run ChoresPage.test.ts` (from `packages/editor/`)
Expected: FAIL — `selectedItemId`/`onclearselection` aren't accepted, modal never opens

- [ ] **Step 3: Modify `ChoresPage.svelte`**

In `packages/editor/src/lib/components/ChoresPage.svelte`, extend the `Props` interface and destructuring (near the top of the `<script>` block, alongside `store`, `floorStore`, `onnewchore`, `onplaceonmap`):

```ts
interface Props {
  store: ChoreStore;
  floorStore: { floors: Array<{ id: string; name: string; rooms: Array<{ id: string; label: string }> }> };
  onnewchore?: () => void;
  onplaceonmap?: (choreId: string) => void;
  selectedItemId?: string | null;
  onclearselection?: () => void;
}

let { store, floorStore, onnewchore, onplaceonmap, selectedItemId = null, onclearselection }: Props = $props();
```

Add this effect right after the existing `let editChore = $state<Chore | null>(null);` line:

```ts
$effect(() => {
  if (selectedItemId) {
    const found = store.chores.find((c) => c.id === selectedItemId);
    if (found) {
      editChore = found;
      onclearselection?.();
    }
  }
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run ChoresPage.test.ts` (from `packages/editor/`)
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ChoresPage.svelte packages/editor/test/ChoresPage.test.ts
git commit -m "feat: let ChoresPage open a chore via external selection"
```

---

### Task 4: Extend `ConsumablesPage.svelte` with external selection

**Files:**
- Modify: `packages/editor/src/lib/components/ConsumablesPage.svelte`
- Modify: `packages/editor/test/ConsumablesPage.test.ts`

- [ ] **Step 1: Write the failing test**

Add to the existing `describe("ConsumablesPage", ...)` block in `packages/editor/test/ConsumablesPage.test.ts` (reuse the file's existing `makeStore`/`sampleDoc` helpers):

```ts
  it("opens the edit modal for the consumable matching selectedItemId and clears selection", async () => {
    const store = makeStore();
    await makeTick();
    const onclearselection = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumablesPage, {
      target,
      props: { store, settingsStore: { consumableCategories: [], consumableUnits: [] }, selectedItemId: "c2", onclearselection },
    });
    flushSync();

    expect(target.querySelector(".ui-modal-title")?.textContent).toBe("Dish Soap");
    expect(onclearselection).toHaveBeenCalledOnce();

    unmount(comp);
  });
```

(Check the existing test file's `props:` shape in its other `it()` blocks first — reuse whatever `settingsStore` stub they already pass rather than inventing a new one, to stay consistent.)

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run ConsumablesPage.test.ts` (from `packages/editor/`)
Expected: FAIL — modal doesn't open, `selectedItemId` prop not recognized

- [ ] **Step 3: Modify `ConsumablesPage.svelte`**

Extend `Props` and destructuring:

```ts
interface Props {
  store: ConsumableStore;
  settingsStore: SettingsStore;
  onplaceonmap?: (id: string) => void;
  selectedItemId?: string | null;
  onclearselection?: () => void;
}

let { store, settingsStore, onplaceonmap, selectedItemId = null, onclearselection }: Props = $props();
```

Add this effect right after `let editConsumable = $state<Consumable | null>(null);`:

```ts
$effect(() => {
  if (selectedItemId) {
    const found = store.consumables.find((c) => c.id === selectedItemId);
    if (found) {
      editConsumable = found;
      onclearselection?.();
    }
  }
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run ConsumablesPage.test.ts` (from `packages/editor/`)
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ConsumablesPage.svelte packages/editor/test/ConsumablesPage.test.ts
git commit -m "feat: let ConsumablesPage open a consumable via external selection"
```

---

### Task 5: Extend `WorksPage.svelte` with external selection

**Files:**
- Modify: `packages/editor/src/lib/components/WorksPage.svelte`
- Test: `packages/editor/test/WorksPage.test.ts` (new)

- [ ] **Step 1: Write the failing test**

```ts
// packages/editor/test/WorksPage.test.ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import WorksPage from "../src/lib/components/WorksPage.svelte";
import type { Work } from "../src/lib/worksStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makeWork(overrides: Partial<Work> = {}): Work {
  return {
    id: "w1", title: "Fix roof leak", description: "", status: "planned",
    categoryId: null, date: "2026-06-10T00:00:00.000Z", totalCost: null,
    supplierId: null, notes: "", attachments: [], placement: null,
    ...overrides,
  };
}

function makeWorksStore(works: Work[]) {
  return {
    works, loaded: true, loadError: null,
    createWork: vi.fn(), updateWork: vi.fn(), deleteWork: vi.fn(),
    uploadAttachment: vi.fn(), deleteAttachment: vi.fn(), setPlacement: vi.fn(),
  };
}

function makeSettingsStore() {
  return { workCategories: [], suppliers: [] };
}

describe("WorksPage — external selection", () => {
  it("opens the edit modal for the work matching selectedItemId and clears selection", () => {
    const store = makeWorksStore([makeWork()]);
    const onclearselection = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(WorksPage, {
      target,
      props: { store, settingsStore: makeSettingsStore(), selectedItemId: "w1", onclearselection },
    });
    flushSync();

    expect(target.querySelector(".ui-modal-title")?.textContent).toBe("Edit work");
    const titleInput = target.querySelector(".ui-modal input") as HTMLInputElement;
    expect(titleInput.value).toBe("Fix roof leak");
    expect(onclearselection).toHaveBeenCalledOnce();

    unmount(comp);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run WorksPage.test.ts` (from `packages/editor/`)
Expected: FAIL — modal never opens

- [ ] **Step 3: Modify `WorksPage.svelte`**

Extend `Props` and destructuring:

```ts
interface Props {
  store: WorksStore;
  settingsStore: SettingsStore;
  onplaceonmap?: (workId: string) => void;
  selectedItemId?: string | null;
  onclearselection?: () => void;
}

let { store, settingsStore, onplaceonmap, selectedItemId = null, onclearselection }: Props = $props();
```

Add this effect right after `let modalWork = $state<Work | "create" | null>(null);`:

```ts
$effect(() => {
  if (selectedItemId) {
    const found = store.works.find((w) => w.id === selectedItemId);
    if (found) {
      modalWork = found;
      onclearselection?.();
    }
  }
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run WorksPage.test.ts` (from `packages/editor/`)
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/WorksPage.svelte packages/editor/test/WorksPage.test.ts
git commit -m "feat: let WorksPage open a work via external selection"
```

---

### Task 6: Extend `CostsPage.svelte` with external selection

**Files:**
- Modify: `packages/editor/src/lib/components/CostsPage.svelte`
- Test: `packages/editor/test/CostsPage.test.ts` (new)

- [ ] **Step 1: Write the failing test**

```ts
// packages/editor/test/CostsPage.test.ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import CostsPage from "../src/lib/components/CostsPage.svelte";
import type { CostEntry } from "../src/lib/costsStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makeEntry(overrides: Partial<CostEntry> = {}): CostEntry {
  return {
    id: "ce1", categoryId: "cat-electricity", date: "2026-01-15",
    totalAmount: 120.5, quantity: null, unitPrice: null,
    supplierId: null, notes: "", roomId: null, attachments: [],
    ...overrides,
  };
}

function makeCostsStore(entries: CostEntry[]) {
  return {
    entries, loaded: true, loadError: null,
    createEntry: vi.fn(), updateEntry: vi.fn(), deleteEntry: vi.fn(),
    uploadAttachment: vi.fn(), deleteAttachment: vi.fn(),
    totalByYear: vi.fn().mockReturnValue(new Map()),
    breakdownLastCompleteYear: vi.fn().mockReturnValue([]),
    entriesByYear: vi.fn().mockReturnValue(new Map()),
    lastCompleteYear: vi.fn().mockReturnValue(2025),
  };
}

function makeSettingsStore() {
  return {
    costCategories: [{ id: "cat-electricity", name: "Electricity", emoji: "💡", color: "#ff0", unit: null }],
    suppliers: [],
    workCategories: [],
  };
}

describe("CostsPage — external selection", () => {
  it("opens the edit modal for the entry matching selectedItemId and clears selection", () => {
    const entry = makeEntry();
    const target = document.createElement("div");
    document.body.appendChild(target);

    const onclearselection = vi.fn();
    const comp = mount(CostsPage, {
      target,
      props: {
        costsStore: makeCostsStore([entry]),
        settingsStore: makeSettingsStore(),
        floorStore: { floors: [] },
        selectedItemId: "ce1",
        onclearselection,
      },
    });
    flushSync();

    expect(target.querySelector(".ui-modal-title")?.textContent).toBe("Edit entry");
    expect(onclearselection).toHaveBeenCalledOnce();

    unmount(comp);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run CostsPage.test.ts` (from `packages/editor/`)
Expected: FAIL — modal never opens

- [ ] **Step 3: Modify `CostsPage.svelte`**

Extend `Props` and destructuring:

```ts
interface Props {
  costsStore: CostsStore;
  settingsStore: SettingsStore;
  floorStore: HouseStore;
  onplaceonmap?: (catId: string) => void;
  selectedItemId?: string | null;
  onclearselection?: () => void;
}

let { costsStore, settingsStore, floorStore, onplaceonmap, selectedItemId = null, onclearselection }: Props = $props();
```

Add this effect right after `let modalEntry = $state<CostEntry | "create" | null>(null);`:

```ts
$effect(() => {
  if (selectedItemId) {
    const found = costsStore.entries.find((e) => e.id === selectedItemId);
    if (found) {
      modalEntry = found;
      onclearselection?.();
    }
  }
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run CostsPage.test.ts` (from `packages/editor/`)
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/CostsPage.svelte packages/editor/test/CostsPage.test.ts
git commit -m "feat: let CostsPage open an entry via external selection"
```

---

### Task 7: Extend `KBPage.svelte` with external selection

**Files:**
- Modify: `packages/editor/src/lib/components/KBPage.svelte`
- Modify: `packages/editor/test/KBPage.test.ts`

- [ ] **Step 1: Write the failing test**

Add a new `describe` block to `packages/editor/test/KBPage.test.ts`, reusing its existing `makeEntry`/`makeStore` helpers (default `makeEntry()` has `id: "e1"`, `title: "How to paint"`):

```ts
describe("KBPage — external selection", () => {
  it("selects the entry matching selectedItemId and clears selection", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const onclearselection = vi.fn();
    const app = mount(KBPage, {
      target,
      props: { store, selectedItemId: "e1", onclearselection },
    });
    flushSync();

    expect(target.querySelector(".content-title")?.textContent?.trim()).toBe("How to paint");
    expect(onclearselection).toHaveBeenCalledOnce();

    unmount(app);
    target.remove();
  });

  it("does nothing when selectedItemId doesn't match any entry", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const app = mount(KBPage, {
      target,
      props: { store, selectedItemId: "missing" },
    });
    flushSync();

    expect(target.querySelector(".content-empty")).not.toBeNull();

    unmount(app);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run KBPage.test.ts` (from `packages/editor/`)
Expected: FAIL — entry isn't selected, `.content-title` shows the empty state

- [ ] **Step 3: Modify `KBPage.svelte`**

Extend `Props`:

```ts
interface Props {
  store: KBStore;
  selectedItemId?: string | null;
  onclearselection?: () => void;
}
let { store, selectedItemId = null, onclearselection }: Props = $props();
```

Add this effect right after the existing `selectEntry` function definition:

```ts
$effect(() => {
  if (selectedItemId) {
    const found = store.entries.find((e) => e.id === selectedItemId);
    if (found) {
      selectEntry(found);
      onclearselection?.();
    }
  }
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run KBPage.test.ts` (from `packages/editor/`)
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/KBPage.svelte packages/editor/test/KBPage.test.ts
git commit -m "feat: let KBPage select an entry via external selection"
```

---

### Task 8: Wire the palette into `App.svelte`

**Files:**
- Modify: `packages/editor/src/App.svelte`

- [ ] **Step 1: Write the failing test**

Add a new test file `packages/editor/test/CommandPalette.integration.test.ts`:

```ts
// packages/editor/test/CommandPalette.integration.test.ts
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import App from "../src/App.svelte";

const HOME = { id: "home-1", name: "Main House", type: "existing", enabledModules: [], createdAt: "2026-01-01T00:00:00.000Z" };

const CHORES_DOC = {
  version: 1,
  chores: [{ id: "c1", donetickId: null, name: "Sweep kitchen", emoji: "🧹", periodDays: 7, frequencyType: "interval", frequency: 7, frequencyMetadata: {}, scheduleFromDue: false, nextDueDate: "2026-08-01T00:00:00.000Z", description: "", attachments: [] }],
  assignments: [],
  completions: [],
};

const SETTINGS_DOC = {
  version: 1,
  costCategories: [], inventoryCategories: [], workCategories: [], suppliers: [], consumableCategories: [], consumableUnits: [],
};

function stubFetch() {
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
    const handlers: Record<string, unknown> = {
      "/api/auth/me": { id: "u1", username: "admin", role: "admin" },
      "/api/homes": [HOME],
      [`/api/homes/${HOME.id}/chores`]: CHORES_DOC,
      [`/api/homes/${HOME.id}/settings`]: SETTINGS_DOC,
      [`/api/homes/${HOME.id}/inventory`]: { version: 1, items: [] },
      [`/api/homes/${HOME.id}/consumables`]: { version: 1, consumables: [], transactions: [] },
      [`/api/homes/${HOME.id}/works`]: { version: 1, works: [] },
      [`/api/homes/${HOME.id}/costs`]: { version: 1, entries: [] },
      [`/api/homes/${HOME.id}/kb`]: { version: 1, entries: [] },
    };
    if (url in handlers) {
      return Promise.resolve({ ok: true, status: 200, json: async () => handlers[url] });
    }
    return Promise.resolve({ ok: false, status: 404, json: async () => undefined });
  }));
}

async function mountApp(target: HTMLElement): Promise<ReturnType<typeof mount>> {
  window.location.hash = "#/";
  const app = mount(App, { target });
  // This chain is longer than existing App tests exercise: authStore resolves,
  // then homesStore.loadHomes() fetches and sets activeHomeId, then the
  // $effect watching activeHomeId fires .reload() on every module store, each
  // doing its own fetch. No prior test in this suite stubs "/api/homes" with
  // real data, so treat this tick count as a starting guess — if the chore
  // isn't found yet when assertions run, add more `await tick()` / a
  // `setTimeout(0)` flush here rather than in the assertions below.
  for (let i = 0; i < 6; i++) await tick();
  flushSync();
  return app;
}

describe("Global search integration", () => {
  let target: HTMLElement;
  let app: ReturnType<typeof mount> | undefined;

  beforeEach(() => { stubFetch(); });
  afterEach(() => { if (app) { unmount(app); app = undefined; } target?.remove(); });

  it("opens the palette with Ctrl+K, selects a chore, and navigates to Chores with its edit modal open", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);
    app = await mountApp(target);

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true }));
    flushSync();
    expect(target.querySelector(".cmdk")).not.toBeNull();

    const input = target.querySelector(".cmdk-input") as HTMLInputElement;
    input.value = "sweep";
    input.dispatchEvent(new Event("input"));
    flushSync();

    const result = target.querySelector(".cmdk-result") as HTMLElement;
    expect(result.textContent).toContain("Sweep kitchen");
    result.click();
    flushSync();
    // jsdom dispatches "hashchange" as a queued task, not synchronously —
    // give it a turn before asserting the route changed.
    await new Promise((r) => setTimeout(r, 0));
    await tick();
    flushSync();

    expect(target.querySelector(".cmdk")).toBeNull();
    expect(window.location.hash).toBe("#/chores");
    expect(target.querySelector(".ui-modal-title")?.textContent).toBe("🧹 Sweep kitchen");
  });

  it("opens the palette from the topbar search button", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);
    app = await mountApp(target);

    const btn = target.querySelector(".topbar .search-btn") as HTMLButtonElement;
    btn.click();
    flushSync();

    expect(target.querySelector(".cmdk")).not.toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run CommandPalette.integration.test.ts` (from `packages/editor/`)
Expected: FAIL — no `.cmdk` ever appears, no `.search-btn` in the topbar

- [ ] **Step 3: Modify `App.svelte`**

Add the import near the other component imports:

```ts
import CommandPalette from "./lib/components/CommandPalette.svelte";
import { buildSearchIndex, type SearchResult } from "./lib/searchIndex";
```

Add state near the other top-level `$state` declarations (alongside `selectedInventoryItemId` if present, or near `navExpanded`):

```ts
let commandPaletteOpen = $state(false);
let selectedChoreId = $state<string | null>(null);
let selectedConsumableId = $state<string | null>(null);
let selectedWorkId = $state<string | null>(null);
let selectedCostEntryId = $state<string | null>(null);
let selectedKBEntryId = $state<string | null>(null);
```

(`selectedInventoryItemId` should already exist — reuse it rather than adding a duplicate.)

Add a derived index, near other `$derived` declarations:

```ts
const globalSearchIndex = $derived(buildSearchIndex({
  choreStore, inventoryStore, consumableStore, worksStore, costsStore, kbStore, settingsStore,
}));
```

Add the selection handler as a plain function alongside the other `handle*` functions:

```ts
function handleSearchSelect(result: SearchResult): void {
  commandPaletteOpen = false;
  if (result.module === "chores") { selectedChoreId = result.id; window.location.hash = "#/chores"; }
  else if (result.module === "inventory") { selectedInventoryItemId = result.id; window.location.hash = "#/inventory"; }
  else if (result.module === "consumables") { selectedConsumableId = result.id; window.location.hash = "#/consumables"; }
  else if (result.module === "works") { selectedWorkId = result.id; window.location.hash = "#/works"; }
  else if (result.module === "costs") { selectedCostEntryId = result.id; window.location.hash = "#/costs"; }
  else if (result.module === "kb") { selectedKBEntryId = result.id; window.location.hash = "#/kb"; }
}
```

In `handleKeydown`, add the shortcut as the very first check (same placement as the existing `Ctrl+S` check, so it fires regardless of current focus):

```ts
function handleKeydown(event: KeyboardEvent): void {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    commandPaletteOpen = true;
    return;
  }
  if (event.ctrlKey && event.key === "s") { event.preventDefault(); if (isFloorPlan) handleSave(); return; }
  // ...rest unchanged
```

Add the search button to the topbar, right before the `<HomesSwitcher topbar={true} />` line inside `<header class="topbar">`:

```svelte
<button class="icon-btn search-btn" title="Search (Ctrl+K)" onclick={() => { commandPaletteOpen = true; }}>🔍</button>
```

Add the palette itself right after the `<svelte:window .../>` block (top-level, so it overlays regardless of route):

```svelte
<CommandPalette
  open={commandPaletteOpen}
  index={globalSearchIndex}
  onclose={() => { commandPaletteOpen = false; }}
  onselect={handleSearchSelect}
/>
```

Pass the new props to each page in the `{:else if}` chain:

```svelte
{:else if currentRoute === "#/chores" || currentRoute === "#/chores/manage"}
  <ChoresPage store={choreStore} {floorStore} selectedItemId={selectedChoreId} onclearselection={() => { selectedChoreId = null; }} onnewchore={() => { showNewChoreModal = true; }} onplaceonmap={(choreId) => { ... }} />

{:else if currentRoute === "#/consumables"}
  <ConsumablesPage store={consumableStore} {settingsStore} selectedItemId={selectedConsumableId} onclearselection={() => { selectedConsumableId = null; }} onplaceonmap={(id) => { ... }} />

{:else if currentRoute === "#/works"}
  <WorksPage store={worksStore} {settingsStore} selectedItemId={selectedWorkId} onclearselection={() => { selectedWorkId = null; }} onplaceonmap={(workId) => { ... }} />

{:else if currentRoute === "#/kb"}
  <KBPage store={kbStore} selectedItemId={selectedKBEntryId} onclearselection={() => { selectedKBEntryId = null; }} />

{:else if currentRoute === "#/costs"}
  <CostsPage {costsStore} {settingsStore} {floorStore} selectedItemId={selectedCostEntryId} onclearselection={() => { selectedCostEntryId = null; }} onplaceonmap={(catId) => { ... }} />
```

(Keep each block's existing `onplaceonmap` body exactly as-is — only the two new props are being added.)

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run CommandPalette.integration.test.ts` (from `packages/editor/`)
Expected: PASS

Then run the full frontend suite to confirm nothing else broke:

Run: `npx vitest run` (from `packages/editor/`)
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/test/CommandPalette.integration.test.ts
git commit -m "feat: wire global search command palette into App"
```

---

## Post-implementation check

Re-read the "Dependencies / Coordination" note in the spec: `feat/ui-refactor-topbar-toolbar-badges` (in `.worktrees/feat-ui-refactor`, not yet merged) also touches `<header class="topbar">`. Before merging this work, check whether that branch has landed on `main` — if not, flag the topbar diff for a manual rebase rather than merging blind.
