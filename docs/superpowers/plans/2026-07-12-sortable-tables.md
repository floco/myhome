# Sortable Tables Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every data table in the app click-to-sort column headers, via one new shared `SortableTable` component that owns table rendering, sort state, and comparison logic.

**Architecture:** A headless rune-based `createSortState` helper (tri-state asc/desc/unsorted, type-aware comparison, nulls-last) backs a new `ui/SortableTable.svelte` component that renders the full `<table>/<thead>/<tbody>`. Callers supply column definitions (with optional Svelte 5 snippets for custom cell content) and a data array; 8 existing page/settings components are migrated from hand-written `<table>` markup onto it.

**Tech Stack:** Svelte 5.56 (runes: `$state`, `$derived`, `$props`, snippets), TypeScript, Vite 8, Vitest + jsdom.

## Global Constraints

- Frontend package root: `packages/editor` (npm workspace `@myhome/editor`).
- Tests live in the flat `packages/editor/test/` directory (NOT colocated with source) — file naming convention `<ComponentName>.test.ts`.
- Svelte 5 component tests use `mount`/`unmount`/`flushSync` from `"svelte"` (no `@testing-library`), per `packages/editor/test/Button.test.ts`.
- jsdom event delegation gotcha: every test's `target` div must be `document.body.appendChild`-ed before `mount(...)` and removed after; any manually-dispatched `Event` needs `{ bubbles: true }`, or handlers silently never fire.
- No new npm dependencies — build entirely on existing Svelte 5 runes/snippets.
- Shared UI components live in `packages/editor/src/lib/components/ui/`; rune-based non-component helpers live in `packages/editor/src/lib/utils/` (new directory — doesn't exist yet).
- Run tests with `npm run test --workspace=packages/editor` (or `cd packages/editor && npx vitest run <file>` for a single file) from repo root `/projects/myhome`.
- Run `npm run typecheck --workspace=packages/editor` (`svelte-check`) after each migration task — Svelte generic components are easy to get subtly wrong on types.

---

## Task 1: `createSortState` headless helper

**Files:**
- Create: `packages/editor/src/lib/utils/sortState.svelte.ts`
- Test: `packages/editor/test/sortState.test.ts`

**Interfaces:**
- Produces: `SortDirection = "asc" | "desc"`, `SortState = { key: string; direction: SortDirection }`, `compareValues(a: unknown, b: unknown): number`, `createSortState(initial?: SortState | null)` returning `{ current: SortState | null (getter), toggle(key: string): void, directionFor(key: string): SortDirection | null, sortRows<T>(rows: T[], sortValue: (row: T) => unknown): T[] }`.

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/sortState.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { createSortState, compareValues } from "../src/lib/utils/sortState.svelte";

describe("compareValues", () => {
  it("compares numbers numerically", () => {
    expect(compareValues(2, 10)).toBeLessThan(0);
  });

  it("compares strings case-insensitively", () => {
    expect(compareValues("banana", "Apple")).toBeGreaterThan(0);
  });

  it("compares dates by timestamp", () => {
    const a = new Date("2026-01-01");
    const b = new Date("2026-06-01");
    expect(compareValues(a, b)).toBeLessThan(0);
  });

  it("sorts null and undefined to the end regardless of comparand", () => {
    expect(compareValues(null, 5)).toBeGreaterThan(0);
    expect(compareValues(5, undefined)).toBeLessThan(0);
    expect(compareValues(null, undefined)).toBe(0);
  });
});

describe("createSortState", () => {
  it("starts with no active sort", () => {
    const s = createSortState();
    expect(s.current).toBeNull();
    expect(s.directionFor("name")).toBeNull();
  });

  it("cycles a column asc -> desc -> unsorted", () => {
    const s = createSortState();
    s.toggle("name");
    expect(s.current).toEqual({ key: "name", direction: "asc" });
    s.toggle("name");
    expect(s.current).toEqual({ key: "name", direction: "desc" });
    s.toggle("name");
    expect(s.current).toBeNull();
  });

  it("switching to a different column resets to ascending", () => {
    const s = createSortState();
    s.toggle("name");
    s.toggle("name"); // now desc on "name"
    s.toggle("date");
    expect(s.current).toEqual({ key: "date", direction: "asc" });
  });

  it("accepts an initial sort state", () => {
    const s = createSortState({ key: "date", direction: "desc" });
    expect(s.current).toEqual({ key: "date", direction: "desc" });
    expect(s.directionFor("date")).toBe("desc");
  });

  it("sortRows returns the original array order when unsorted", () => {
    const s = createSortState();
    const rows = [{ n: 3 }, { n: 1 }, { n: 2 }];
    expect(s.sortRows(rows, (r) => r.n)).toEqual(rows);
  });

  it("sortRows sorts ascending then descending without mutating the input", () => {
    const s = createSortState();
    const rows = [{ n: 3 }, { n: 1 }, { n: 2 }];
    s.toggle("n");
    const asc = s.sortRows(rows, (r) => r.n);
    expect(asc.map((r) => r.n)).toEqual([1, 2, 3]);
    expect(rows.map((r) => r.n)).toEqual([3, 1, 2]); // original untouched

    s.toggle("n");
    const desc = s.sortRows(rows, (r) => r.n);
    expect(desc.map((r) => r.n)).toEqual([3, 2, 1]);
  });

  it("sortRows keeps null/undefined values last in both directions", () => {
    const s = createSortState();
    const rows = [{ n: 2 }, { n: null as number | null }, { n: 1 }];
    s.toggle("n");
    expect(s.sortRows(rows, (r) => r.n).map((r) => r.n)).toEqual([1, 2, null]);
    s.toggle("n");
    expect(s.sortRows(rows, (r) => r.n).map((r) => r.n)).toEqual([2, 1, null]);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/sortState.test.ts`
Expected: FAIL — `Failed to resolve import "../src/lib/utils/sortState.svelte"`.

- [ ] **Step 3: Implement `sortState.svelte.ts`**

Create `packages/editor/src/lib/utils/sortState.svelte.ts`:

```ts
export type SortDirection = "asc" | "desc";

export interface SortState {
  key: string;
  direction: SortDirection;
}

export function compareValues(a: unknown, b: unknown): number {
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  if (a instanceof Date && b instanceof Date) return a.getTime() - b.getTime();
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), undefined, { sensitivity: "base" });
}

export function createSortState(initial: SortState | null = null) {
  let state = $state<SortState | null>(initial);

  function toggle(key: string): void {
    if (!state || state.key !== key) {
      state = { key, direction: "asc" };
    } else if (state.direction === "asc") {
      state = { key, direction: "desc" };
    } else {
      state = null;
    }
  }

  function directionFor(key: string): SortDirection | null {
    return state && state.key === key ? state.direction : null;
  }

  function sortRows<T>(rows: T[], sortValue: (row: T) => unknown): T[] {
    if (!state) return rows;
    const dir = state.direction === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => dir * compareValues(sortValue(a), sortValue(b)));
  }

  return {
    get current() {
      return state;
    },
    toggle,
    directionFor,
    sortRows,
  };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/sortState.test.ts`
Expected: PASS, all 10 tests green.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/utils/sortState.svelte.ts packages/editor/test/sortState.test.ts
git commit -m "feat: add headless sort-state helper for tables"
```

---

## Task 2: `SortableTable.svelte` shared component

**Files:**
- Create: `packages/editor/src/lib/components/ui/SortableTable.svelte`
- Test: `packages/editor/test/SortableTable.test.ts`

**Interfaces:**
- Consumes: `createSortState`, `SortState`, `compareValues` from `../../utils/sortState.svelte` (Task 1).
- Produces: exported `Column<T>` type and the `SortableTable` component with props `{ columns, rows, rowKey, rowClick?, rowClass?, defaultSort?, emptyMessage?, class?, extraRow?, isRowExpanded?, expandedRow? }`. All 8 migration tasks depend on this exact prop shape.

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/SortableTable.test.ts`:

```ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, createRawSnippet } from "svelte";
import SortableTable from "../src/lib/components/ui/SortableTable.svelte";
import type { Column } from "../src/lib/components/ui/SortableTable.svelte";

interface Row {
  id: string;
  name: string;
  qty: number;
}

function textSnippet(text: (row: Row) => string) {
  return createRawSnippet((getRow: () => Row) => ({
    render: () => `<span>${text(getRow())}</span>`,
  }));
}

afterEach(() => {
  document.body.innerHTML = "";
});

function baseColumns(): Column<Row>[] {
  return [
    { key: "name", label: "Name", sortValue: (r) => r.name },
    { key: "qty", label: "Qty", sortValue: (r) => r.qty },
    { key: "actions", label: "", sortable: false },
  ];
}

function baseRows(): Row[] {
  return [
    { id: "b", name: "Banana", qty: 3 },
    { id: "a", name: "Apple", qty: 1 },
    { id: "c", name: "Cherry", qty: 2 },
  ];
}

describe("ui/SortableTable", () => {
  it("renders rows in original order when unsorted", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(SortableTable, {
      target,
      props: { columns: baseColumns(), rows: baseRows(), rowKey: (r: Row) => r.id },
    });
    flushSync();

    const names = [...target.querySelectorAll("tbody tr td:first-child")].map((td) => td.textContent);
    expect(names).toEqual(["Banana", "Apple", "Cherry"]);

    unmount(comp);
  });

  it("sorts ascending then descending then back to unsorted on repeated header clicks", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(SortableTable, {
      target,
      props: { columns: baseColumns(), rows: baseRows(), rowKey: (r: Row) => r.id },
    });
    flushSync();

    const nameHeaderBtn = target.querySelector("thead th:first-child button")!;
    (nameHeaderBtn as HTMLButtonElement).click();
    flushSync();
    let names = [...target.querySelectorAll("tbody tr td:first-child")].map((td) => td.textContent);
    expect(names).toEqual(["Apple", "Banana", "Cherry"]);

    (nameHeaderBtn as HTMLButtonElement).click();
    flushSync();
    names = [...target.querySelectorAll("tbody tr td:first-child")].map((td) => td.textContent);
    expect(names).toEqual(["Cherry", "Banana", "Apple"]);

    (nameHeaderBtn as HTMLButtonElement).click();
    flushSync();
    names = [...target.querySelectorAll("tbody tr td:first-child")].map((td) => td.textContent);
    expect(names).toEqual(["Banana", "Apple", "Cherry"]);

    unmount(comp);
  });

  it("sets aria-sort on the active column header", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(SortableTable, {
      target,
      props: { columns: baseColumns(), rows: baseRows(), rowKey: (r: Row) => r.id },
    });
    flushSync();

    const nameTh = target.querySelector("thead th:first-child")!;
    expect(nameTh.getAttribute("aria-sort")).toBe("none");
    (target.querySelector("thead th:first-child button") as HTMLButtonElement).click();
    flushSync();
    expect(nameTh.getAttribute("aria-sort")).toBe("ascending");

    unmount(comp);
  });

  it("does not render a sort button for non-sortable columns", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(SortableTable, {
      target,
      props: { columns: baseColumns(), rows: baseRows(), rowKey: (r: Row) => r.id },
    });
    flushSync();

    const actionsTh = target.querySelector("thead th:last-child")!;
    expect(actionsTh.querySelector("button")).toBeNull();
    expect(actionsTh.hasAttribute("aria-sort")).toBe(false);

    unmount(comp);
  });

  it("renders custom cell snippets", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const columns: Column<Row>[] = [
      { key: "name", label: "Name", sortValue: (r) => r.name, cell: textSnippet((r) => `★ ${r.name}`) },
    ];
    const comp = mount(SortableTable, {
      target,
      props: { columns, rows: baseRows(), rowKey: (r: Row) => r.id },
    });
    flushSync();

    expect(target.querySelector("tbody tr td span")?.textContent).toBe("★ Banana");

    unmount(comp);
  });

  it("fires rowClick when a row is clicked", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const rowClick = vi.fn();
    const comp = mount(SortableTable, {
      target,
      props: { columns: baseColumns(), rows: baseRows(), rowKey: (r: Row) => r.id, rowClick },
    });
    flushSync();

    (target.querySelector("tbody tr") as HTMLTableRowElement).click();
    expect(rowClick).toHaveBeenCalledOnce();
    expect(rowClick).toHaveBeenCalledWith(baseRows()[0]);

    unmount(comp);
  });

  it("renders emptyMessage when rows is empty", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(SortableTable, {
      target,
      props: { columns: baseColumns(), rows: [], rowKey: (r: Row) => r.id, emptyMessage: "Nothing here" },
    });
    flushSync();

    const emptyCell = target.querySelector("tbody tr td")!;
    expect(emptyCell.textContent).toBe("Nothing here");
    expect(emptyCell.getAttribute("colspan")).toBe("3");

    unmount(comp);
  });

  it("applies defaultSort on mount", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(SortableTable, {
      target,
      props: {
        columns: baseColumns(),
        rows: baseRows(),
        rowKey: (r: Row) => r.id,
        defaultSort: { key: "qty", direction: "asc" },
      },
    });
    flushSync();

    const names = [...target.querySelectorAll("tbody tr td:first-child")].map((td) => td.textContent);
    expect(names).toEqual(["Apple", "Cherry", "Banana"]); // qty 1, 2, 3

    unmount(comp);
  });

  it("renders extraRow as the last row in tbody when provided", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const extraRow = createRawSnippet(() => ({
      render: () => `<td colspan="3" class="new-row-marker">new row</td>`,
    }));
    const comp = mount(SortableTable, {
      target,
      props: { columns: baseColumns(), rows: baseRows(), rowKey: (r: Row) => r.id, extraRow },
    });
    flushSync();

    const allRows = [...target.querySelectorAll("tbody tr")];
    expect(allRows).toHaveLength(4); // 3 data rows + 1 extra row
    expect(allRows[3].querySelector(".new-row-marker")).not.toBeNull();

    unmount(comp);
  });

  it("renders an expanded detail row only for rows where isRowExpanded returns true", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const expandedRow = createRawSnippet((getRow: () => Row) => ({
      render: () => `<div class="detail">detail for ${getRow().id}</div>`,
    }));
    const comp = mount(SortableTable, {
      target,
      props: {
        columns: baseColumns(),
        rows: baseRows(),
        rowKey: (r: Row) => r.id,
        isRowExpanded: (r: Row) => r.id === "a",
        expandedRow,
      },
    });
    flushSync();

    const details = target.querySelectorAll(".detail");
    expect(details).toHaveLength(1);
    expect(details[0].textContent).toBe("detail for a");

    unmount(comp);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/SortableTable.test.ts`
Expected: FAIL — cannot resolve `../src/lib/components/ui/SortableTable.svelte`.

- [ ] **Step 3: Implement `SortableTable.svelte`**

Create `packages/editor/src/lib/components/ui/SortableTable.svelte`:

```svelte
<!-- packages/editor/src/lib/components/ui/SortableTable.svelte -->
<script lang="ts" generics="T">
  import type { Snippet } from "svelte";
  import { createSortState, type SortState } from "../../utils/sortState.svelte";

  export interface Column<T> {
    key: string;
    label: string;
    sortable?: boolean;
    sortValue?: (row: T) => string | number | Date | null | undefined;
    cell?: Snippet<[T]>;
    headerClass?: string;
    cellClass?: string | ((row: T) => string);
    stopRowClick?: boolean;
  }

  interface Props {
    columns: Column<T>[];
    rows: T[];
    rowKey: (row: T) => string | number;
    rowClick?: (row: T) => void;
    rowClass?: (row: T) => string;
    defaultSort?: SortState;
    emptyMessage?: string;
    class?: string;
    extraRow?: Snippet;
    isRowExpanded?: (row: T) => boolean;
    expandedRow?: Snippet<[T]>;
  }

  let {
    columns,
    rows,
    rowKey,
    rowClick,
    rowClass,
    defaultSort,
    emptyMessage,
    class: className,
    extraRow,
    isRowExpanded,
    expandedRow,
  }: Props = $props();

  const sortState = createSortState(defaultSort ?? null);

  const sortedRows = $derived.by(() => {
    const current = sortState.current;
    if (!current) return rows;
    const col = columns.find((c) => c.key === current.key);
    if (!col?.sortValue) return rows;
    return sortState.sortRows(rows, col.sortValue);
  });

  function ariaSortFor(key: string): "ascending" | "descending" | "none" {
    const dir = sortState.directionFor(key);
    if (dir === "asc") return "ascending";
    if (dir === "desc") return "descending";
    return "none";
  }

  function arrowFor(key: string): string {
    const dir = sortState.directionFor(key);
    if (dir === "asc") return "▲";
    if (dir === "desc") return "▼";
    return "";
  }

  function cellClassFor(column: Column<T>, row: T): string | undefined {
    return typeof column.cellClass === "function" ? column.cellClass(row) : column.cellClass;
  }
</script>

<table class="ui-sortable-table {className ?? ''}">
  <thead>
    <tr>
      {#each columns as column (column.key)}
        {#if column.sortable === false}
          <th class={column.headerClass}>{column.label}</th>
        {:else}
          <th class={column.headerClass} aria-sort={ariaSortFor(column.key)}>
            <button type="button" class="ui-sortable-table-sort-btn" onclick={() => sortState.toggle(column.key)}>
              {column.label}
              <span class="ui-sortable-table-arrow">{arrowFor(column.key)}</span>
            </button>
          </th>
        {/if}
      {/each}
    </tr>
  </thead>
  <tbody>
    {#each sortedRows as row (rowKey(row))}
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
      <tr onclick={rowClick ? () => rowClick(row) : undefined} class="{rowClass?.(row) ?? ''} {rowClick ? 'clickable' : ''}">
        {#each columns as column (column.key)}
          <td
            class={cellClassFor(column, row)}
            onclick={column.stopRowClick ? (e) => e.stopPropagation() : undefined}
          >
            {#if column.cell}
              {@render column.cell(row)}
            {:else}
              {column.sortValue?.(row) ?? "—"}
            {/if}
          </td>
        {/each}
      </tr>
      {#if expandedRow && isRowExpanded?.(row)}
        <tr class="ui-sortable-table-expand-row">
          <td colspan={columns.length}>{@render expandedRow(row)}</td>
        </tr>
      {/if}
    {/each}

    {#if extraRow}
      <tr>{@render extraRow()}</tr>
    {/if}

    {#if rows.length === 0 && emptyMessage}
      <tr>
        <td colspan={columns.length} class="ui-sortable-table-empty">{emptyMessage}</td>
      </tr>
    {/if}
  </tbody>
</table>

<style>
  .ui-sortable-table { width: 100%; border-collapse: collapse; font-size: 12px; color: var(--text-muted); }
  .ui-sortable-table thead { position: sticky; top: 0; background: var(--surface-alt); z-index: 1; }
  .ui-sortable-table th {
    padding: 6px 10px; color: var(--text-faint); font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.05em;
    text-align: left; border-bottom: 1px solid var(--border);
  }
  .ui-sortable-table-sort-btn {
    display: inline-flex; align-items: center; gap: 4px;
    background: none; border: none; padding: 0; margin: 0;
    color: inherit; font: inherit; text-transform: inherit; letter-spacing: inherit;
    cursor: pointer;
  }
  .ui-sortable-table-sort-btn:hover { color: var(--text); }
  .ui-sortable-table-arrow { font-size: 8px; min-width: 8px; display: inline-block; }
  .ui-sortable-table td { padding: 7px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  .ui-sortable-table tr:hover td { background: var(--surface-hover); }
  .ui-sortable-table tr.clickable:hover td { cursor: pointer; }
  .ui-sortable-table-expand-row td { background: var(--surface-alt); padding: 0; cursor: default; }
  .ui-sortable-table-empty { text-align: center; color: var(--text-faint); padding: 32px; }
</style>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/SortableTable.test.ts`
Expected: PASS, all 10 tests green.

- [ ] **Step 5: Typecheck**

Run: `cd packages/editor && npx svelte-check --tsconfig ./tsconfig.json`
Expected: no new errors from `SortableTable.svelte` or `sortState.svelte.ts`.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/ui/SortableTable.svelte packages/editor/test/SortableTable.test.ts
git commit -m "feat: add generic SortableTable component"
```

---

## Task 3: Migrate `InventoryPage.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/InventoryPage.svelte`

**Interfaces:**
- Consumes: `SortableTable`, `Column<T>` from `./ui/SortableTable.svelte` (Task 2).

- [ ] **Step 1: Add the import**

In `packages/editor/src/lib/components/InventoryPage.svelte`, after the `Input` import (line 6):

```svelte
  import SortableTable, { type Column } from "./ui/SortableTable.svelte";
```

- [ ] **Step 2: Replace the table markup**

Column definitions reference Svelte snippets, so they're declared inline in the markup (snippets are template-level constructs, not values usable from a plain `<script>` array literal). Replace lines 117–157 (the `<div class="table-wrapper">...</div>` block) with:

```svelte
  <div class="table-wrapper">
    {#snippet emojiCell(item: InventoryItem)}
      {item.emoji}
    {/snippet}
    {#snippet nameCell(item: InventoryItem)}
      {item.name}
    {/snippet}
    {#snippet categoryCell(item: InventoryItem)}
      {item.category || "—"}
    {/snippet}
    {#snippet roomCell(item: InventoryItem)}
      {roomName(item.placement?.roomId)}
    {/snippet}
    {#snippet purchasedCell(item: InventoryItem)}
      {formatDate(item.purchaseDate)}
    {/snippet}
    {#snippet costCell(item: InventoryItem)}
      {formatPrice(item.purchasePrice)}
    {/snippet}
    {#snippet warrantyCell(item: InventoryItem)}
      {@const chip = warrantyChip(item)}
      <span class="chip" style="color:{chip.color}">{chip.label}</span>
    {/snippet}

    <SortableTable
      columns={[
        { key: "emoji", label: "", sortable: false, cellClass: "emoji-cell", cell: emojiCell },
        { key: "name", label: "Name", sortValue: (i) => i.name, cellClass: "name-cell", cell: nameCell },
        { key: "category", label: "Category", sortValue: (i) => i.category || null, cell: categoryCell },
        { key: "room", label: "Room", sortValue: (i) => roomName(i.placement?.roomId), cell: roomCell },
        { key: "purchased", label: "Purchased", sortValue: (i) => (i.purchaseDate ? new Date(i.purchaseDate) : null), cell: purchasedCell },
        { key: "cost", label: "Cost", sortValue: (i) => i.purchasePrice, cell: costCell },
        { key: "warranty", label: "Warranty", sortable: false, cell: warrantyCell },
      ] as Column<InventoryItem>[]}
      rows={filtered}
      rowKey={(item) => item.id}
      rowClick={(item) => { modalItem = item; }}
      emptyMessage={store.items.length === 0
        ? "No items yet — click ＋ Add item to get started."
        : "No items match your filters."}
    />
  </div>
```

- [ ] **Step 3: Trim the page's own table CSS**

In the `<style>` block, remove the now-redundant base table rules (they live in `SortableTable.svelte` now): delete these lines (198–206 in the original file):

```css
  table { width: 100%; border-collapse: collapse; font-size: 12px; color: var(--text-muted); }
  thead { position: sticky; top: 0; background: var(--surface-alt); z-index: 1; }
  th {
    padding: 6px 10px; color: var(--text-faint); font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.05em;
    text-align: left; border-bottom: 1px solid var(--border);
  }
  td { padding: 7px 10px; border-bottom: 1px solid var(--border); }
  tr:hover td { background: var(--surface-hover); cursor: pointer; }
```

Keep `.table-wrapper`, `.empty` (now unused — also safe to delete, `SortableTable` supplies `.ui-sortable-table-empty`), `.chip`, and `.footer`. Change `.emoji-cell` and `.name-cell` to global selectors since those classes are now applied to elements rendered inside `SortableTable`'s scope:

```css
  :global(.emoji-cell) { font-size: 16px; width: 32px; text-align: center; }
  :global(.name-cell) { color: var(--text); }
```

Delete the standalone `.empty { ... }` rule (now dead code, `SortableTable` owns its own empty-state style).

- [ ] **Step 4: Run the existing test suite for regressions**

Run: `cd packages/editor && npx vitest run test/InventoryModal.test.ts test/InventoryOverlay.test.ts test/inventoryStore.test.ts test/HomeInventoryWidget.test.ts`
Expected: PASS (there is no dedicated `InventoryPage.test.ts`, so this confirms nothing InventoryPage touches broke).

- [ ] **Step 5: Typecheck**

Run: `cd packages/editor && npx svelte-check --tsconfig ./tsconfig.json`
Expected: no errors in `InventoryPage.svelte`.

- [ ] **Step 6: Manual sanity via full test run**

Run: `cd packages/editor && npx vitest run`
Expected: full suite passes (no regressions elsewhere from the `InventoryItem` type import change).

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/components/InventoryPage.svelte
git commit -m "refactor: migrate InventoryPage to SortableTable"
```

---

## Task 4: Migrate `WorksPage.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/WorksPage.svelte`

**Interfaces:**
- Consumes: `SortableTable`, `Column<T>` from `./ui/SortableTable.svelte` (Task 2).

- [ ] **Step 1: Add the import**

After the `Input` import (line 6):

```svelte
  import SortableTable, { type Column } from "./ui/SortableTable.svelte";
```

- [ ] **Step 2: Replace the table markup**

Replace lines 92–138 (the `<div class="table-wrapper">...</div>` block) with:

```svelte
  <div class="table-wrapper">
    {#snippet emojiCell(work: Work)}
      {categoryMap.get(work.categoryId ?? "")?.emoji ?? "🔧"}
    {/snippet}
    {#snippet titleCell(work: Work)}
      {work.title}
      {#if work.description}<span class="desc">{work.description}</span>{/if}
    {/snippet}
    {#snippet categoryCell(work: Work)}
      {categoryMap.get(work.categoryId ?? "")?.name ?? "—"}
    {/snippet}
    {#snippet dateCell(work: Work)}
      {work.date}
    {/snippet}
    {#snippet supplierCell(work: Work)}
      {supplierMap.get(work.supplierId ?? "")?.name ?? "—"}
    {/snippet}
    {#snippet costCell(work: Work)}
      {work.totalCost != null ? fmt(work.totalCost) + " €" : "—"}
    {/snippet}
    {#snippet statusCell(work: Work)}
      <span
        class="status-chip"
        style="background:{statusColor(work.status)}22;color:{statusColor(work.status)};border:1px solid {statusColor(work.status)}44"
      >{statusLabel(work.status)}</span>
      {#if work.placement}<span class="pin-indicator" title="Pinned">📍</span>{/if}
    {/snippet}

    <SortableTable
      columns={[
        { key: "emoji", label: "", sortable: false, cellClass: "emoji-cell", cell: emojiCell },
        { key: "title", label: "Title", sortValue: (w) => w.title, cellClass: "name-cell", cell: titleCell },
        { key: "category", label: "Category", sortValue: (w) => categoryMap.get(w.categoryId ?? "")?.name ?? null, cell: categoryCell },
        { key: "date", label: "Date", sortValue: (w) => (w.date ? new Date(w.date) : null), cell: dateCell },
        { key: "supplier", label: "Supplier", sortValue: (w) => supplierMap.get(w.supplierId ?? "")?.name ?? null, cell: supplierCell },
        { key: "cost", label: "Cost", sortValue: (w) => w.totalCost, cell: costCell },
        { key: "status", label: "Status", sortValue: (w) => w.status, cell: statusCell },
      ] as Column<Work>[]}
      rows={filteredWorks}
      rowKey={(work) => work.id}
      rowClick={(work) => { modalWork = work; }}
      emptyMessage={store.works.length === 0 ? "No works yet — click ＋ Add work to get started." : "No works match your filters."}
    />
  </div>
```

- [ ] **Step 3: Trim the page's own table CSS**

Delete these lines from the `<style>` block (170–178 in the original):

```css
  table { width: 100%; border-collapse: collapse; font-size: 12px; color: var(--text-muted); }
  thead { position: sticky; top: 0; background: var(--surface-alt); z-index: 1; }
  th {
    padding: 6px 10px; color: var(--text-faint); font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.05em;
    text-align: left; border-bottom: 1px solid var(--border);
  }
  td { padding: 7px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:hover td { background: var(--surface-hover); cursor: pointer; }
```

Change `.emoji-cell` and `.name-cell` to global, and delete the dead `.empty { ... }` rule:

```css
  :global(.emoji-cell) { font-size: 16px; width: 32px; text-align: center; }
  :global(.name-cell) { color: var(--text); font-weight: 600; }
```

`.desc`, `.status-chip`, `.pin-indicator` stay as-is but must also become `:global()` since they're rendered inside snippets defined in this file — wait, they are NOT global-needed: snippets defined in this component's markup keep this component's CSS scope even when rendered by `SortableTable`, so `.desc`, `.status-chip`, `.pin-indicator` styles apply unchanged, no `:global()` needed. Only `.emoji-cell` and `.name-cell` need `:global()` because those classes are applied via `cellClass` to the `<td>` element, which is rendered by `SortableTable.svelte` itself (a different component's scope), not by a snippet from this file.

- [ ] **Step 4: Run the existing test suite for regressions**

Run: `cd packages/editor && npx vitest run test/WorksPage.test.ts test/worksStore.test.ts test/WorkModal.test.ts test/HomeWorksWidget.test.ts`
Expected: PASS.

- [ ] **Step 5: Typecheck**

Run: `cd packages/editor && npx svelte-check --tsconfig ./tsconfig.json`
Expected: no errors in `WorksPage.svelte`.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/WorksPage.svelte
git commit -m "refactor: migrate WorksPage to SortableTable"
```

---

## Task 5: Migrate `CostsPage.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/CostsPage.svelte`

**Interfaces:**
- Consumes: `SortableTable`, `Column<T>` from `./ui/SortableTable.svelte` (Task 2).

- [ ] **Step 1: Add the import**

After the `DonutChart` import (line 11):

```svelte
  import SortableTable, { type Column } from "./ui/SortableTable.svelte";
```

- [ ] **Step 2: Replace the table markup**

Replace lines 257–296 (the `<div class="table-wrapper">...</div>` block) with:

```svelte
  <div class="table-wrapper">
    {#snippet emojiCell(entry: CostEntry)}
      {categoryEmoji(entry.categoryId)}
    {/snippet}
    {#snippet categoryCell(entry: CostEntry)}
      {categoryName(entry.categoryId)}
    {/snippet}
    {#snippet dateCell(entry: CostEntry)}
      {entry.date}
    {/snippet}
    {#snippet supplierCell(entry: CostEntry)}
      {entry.supplierId ? (supplierMap.get(entry.supplierId)?.name ?? "—") : "—"}
    {/snippet}
    {#snippet qtyCell(entry: CostEntry)}
      {formatQty(entry)}
    {/snippet}
    {#snippet unitPriceCell(entry: CostEntry)}
      {formatUnitPrice(entry)}
    {/snippet}
    {#snippet totalCell(entry: CostEntry)}
      {entry.totalAmount.toLocaleString()} €
    {/snippet}
    {#snippet roomCell(entry: CostEntry)}
      {roomName(entry.roomId)}
    {/snippet}

    <SortableTable
      columns={[
        { key: "emoji", label: "", sortable: false, cellClass: "emoji-cell", cell: emojiCell },
        { key: "category", label: "Category", sortValue: (e) => categoryName(e.categoryId), cellClass: "name-cell", cell: categoryCell },
        { key: "date", label: "Date", sortValue: (e) => new Date(e.date), cell: dateCell },
        { key: "supplier", label: "Supplier", sortValue: (e) => (e.supplierId ? supplierMap.get(e.supplierId)?.name ?? null : null), cell: supplierCell },
        { key: "qty", label: "Qty", headerClass: "num-col", cellClass: "num-col", sortValue: (e) => e.quantity, cell: qtyCell },
        { key: "unitPrice", label: "Unit price", headerClass: "num-col", cellClass: "num-col", sortValue: (e) => e.unitPrice, cell: unitPriceCell },
        { key: "total", label: "Total", headerClass: "num-col", cellClass: "num-col amount-cell", sortValue: (e) => e.totalAmount, cell: totalCell },
        { key: "room", label: "Room", sortValue: (e) => roomName(e.roomId), cell: roomCell },
      ] as Column<CostEntry>[]}
      rows={filtered}
      rowKey={(entry) => entry.id}
      rowClick={(entry) => { modalEntry = entry; }}
      emptyMessage={costsStore.entries.length === 0
        ? "No entries yet — click ＋ Add entry to get started."
        : "No entries match your filters."}
    />
  </div>
```

- [ ] **Step 3: Trim the page's own table CSS**

Delete these lines from the `<style>` block (390–400 in the original):

```css
  table { width: 100%; border-collapse: collapse; font-size: 12px; color: var(--text-muted); }
  thead { position: sticky; top: 0; background: var(--surface-alt); z-index: 1; }
  th {
    padding: 6px 10px; color: var(--text-faint); font-size: 10px;
    text-transform: uppercase; letter-spacing: .05em;
    text-align: left; border-bottom: 1px solid var(--border);
  }
  th.num-col { text-align: right; }
  td { padding: 7px 10px; border-bottom: 1px solid var(--border); }
  td.num-col { text-align: right; }
  tr:hover td { background: var(--surface-hover); cursor: pointer; }
```

Add `.num-col` back as a global rule (it's now applied via `headerClass`/`cellClass` to elements owned by `SortableTable`), and globalize `.emoji-cell`/`.name-cell`; delete the dead `.empty { ... }` rule:

```css
  :global(.num-col) { text-align: right; }
  :global(.emoji-cell) { font-size: 15px; width: 28px; text-align: center; }
  :global(.name-cell) { color: var(--text); }
```

`.amount-cell` stays as a page-scoped rule only if it's applied via a snippet — but here it's passed via `cellClass: "num-col amount-cell"` to the `<td>`, so it also needs globalizing:

```css
  :global(.amount-cell) { color: var(--text); }
```

- [ ] **Step 4: Run the existing test suite for regressions**

Run: `cd packages/editor && npx vitest run test/CostsPage.test.ts test/costsStore.test.ts test/CostsEntryModal.test.ts test/CostsCategoryModal.test.ts`
Expected: PASS.

- [ ] **Step 5: Typecheck**

Run: `cd packages/editor && npx svelte-check --tsconfig ./tsconfig.json`
Expected: no errors in `CostsPage.svelte`.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/CostsPage.svelte
git commit -m "refactor: migrate CostsPage to SortableTable"
```

---

## Task 6: Migrate `ConsumablesPage.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/ConsumablesPage.svelte`

**Interfaces:**
- Consumes: `SortableTable`, `Column<T>` from `./ui/SortableTable.svelte` (Task 2).

**Note:** This page's existing test (`ConsumablesPage.test.ts`) asserts on `tbody tr` element count directly — verify row count assertions still pass after migration since `SortableTable` still renders one `<tr>` per row.

- [ ] **Step 1: Add the import**

After the `Input` import (line 6):

```svelte
  import SortableTable, { type Column } from "./ui/SortableTable.svelte";
```

- [ ] **Step 2: Replace the table markup**

Replace lines 90–149 (the `<div class="table-wrapper">...</div>` block) with:

```svelte
  <div class="table-wrapper">
    {#snippet emojiCell(c: Consumable)}
      {c.emoji}
    {/snippet}
    {#snippet nameCell(c: Consumable)}
      {c.name}
    {/snippet}
    {#snippet categoryCell(c: Consumable)}
      {categoryName(c.categoryId)}
    {/snippet}
    {#snippet quantityCell(c: Consumable)}
      {c.quantity} {c.unit}
    {/snippet}
    {#snippet minCell(c: Consumable)}
      {c.minQuantity} {c.unit}
    {/snippet}
    {#snippet stockCell(c: Consumable)}
      {@const st = stockStatus(c)}
      {@const fill = barFill(c)}
      <div class="bar-track">
        <div class="bar-fill" style="width:{fill * 100}%;background:{STATUS_COLOR[st]}"></div>
        <div class="bar-min"></div>
      </div>
    {/snippet}
    {#snippet statusCell(c: Consumable)}
      {@const st = stockStatus(c)}
      <span class="status-badge" style="color:{STATUS_COLOR[st]};background:{STATUS_COLOR[st]}22">
        {STATUS_LABEL[st]}
      </span>
    {/snippet}
    {#snippet actionsCell(c: Consumable)}
      {#if onplaceonmap && !c.placement}
        <button class="icon-btn" title="Place on map" onclick={() => onplaceonmap?.(c.id)}>📌</button>
      {/if}
    {/snippet}

    <SortableTable
      columns={[
        { key: "emoji", label: "", sortable: false, cellClass: "emoji-cell", cell: emojiCell },
        { key: "name", label: "Name", sortValue: (c) => c.name, cellClass: "name-cell", cell: nameCell },
        { key: "category", label: "Category", sortValue: (c) => categoryName(c.categoryId), cell: categoryCell },
        { key: "quantity", label: "Quantity", sortValue: (c) => c.quantity, cell: quantityCell },
        { key: "min", label: "Min", cellClass: "faint", sortValue: (c) => c.minQuantity, cell: minCell },
        { key: "stock", label: "Stock", sortable: false, cellClass: "bar-cell", cell: stockCell },
        { key: "status", label: "Status", sortValue: (c) => stockStatus(c), cell: statusCell },
        { key: "actions", label: "", sortable: false, cellClass: "actions-cell", stopRowClick: true, cell: actionsCell },
      ] as Column<Consumable>[]}
      rows={filtered}
      rowKey={(c) => c.id}
      rowClick={(c) => { editConsumable = c; }}
      rowClass={(c) => {
        const st = stockStatus(c);
        return st === "low" ? "row-low" : st === "empty" ? "row-empty" : "";
      }}
      emptyMessage={store.consumables.length === 0
        ? "No consumables yet — click ＋ Add consumable to get started."
        : "No consumables match your filters."}
    />
  </div>
```

- [ ] **Step 3: Trim the page's own table CSS**

Delete these lines from the `<style>` block (185–189 in the original):

```css
  table { width: 100%; border-collapse: collapse; font-size: 12px; color: var(--text-muted); }
  thead { position: sticky; top: 0; background: var(--surface-alt); z-index: 1; }
  th { padding: 6px 10px; color: var(--text-faint); font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; text-align: left; border-bottom: 1px solid var(--border); }
  td { padding: 7px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:hover td { background: var(--surface-hover); cursor: pointer; }
```

Globalize the classes now applied to `SortableTable`-owned elements (`<td>`/`<tr>`), delete the dead `.empty { ... }` rule:

```css
  :global(.emoji-cell) { font-size: 16px; width: 32px; text-align: center; }
  :global(.name-cell) { color: var(--text); font-weight: 600; }
  :global(.faint) { color: var(--text-faint); }
  :global(.actions-cell) { white-space: nowrap; text-align: right; }
  :global(.row-low) td { background: color-mix(in srgb, #ff9800 6%, transparent); }
  :global(.row-empty) td { background: color-mix(in srgb, var(--danger) 8%, transparent); }
  :global(.bar-cell) { width: 80px; }
```

`.bar-track`, `.bar-fill`, `.bar-min`, `.status-badge`, `.icon-btn` stay scoped (unchanged) — they're rendered inside this component's own snippets (`stockCell`, `statusCell`, `actionsCell`), so they keep this component's CSS scope automatically.

- [ ] **Step 4: Run the existing test suite for regressions**

Run: `cd packages/editor && npx vitest run test/ConsumablesPage.test.ts test/consumableStore.test.ts test/ConsumableModal.test.ts`
Expected: PASS, including the `tbody tr` count assertions at lines 79 and 106.

- [ ] **Step 5: Typecheck**

Run: `cd packages/editor && npx svelte-check --tsconfig ./tsconfig.json`
Expected: no errors in `ConsumablesPage.svelte`.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/ConsumablesPage.svelte
git commit -m "refactor: migrate ConsumablesPage to SortableTable"
```

---

## Task 7: Migrate `ChoresPage.svelte` (expand/collapse rows)

**Files:**
- Modify: `packages/editor/src/lib/components/ChoresPage.svelte`

**Interfaces:**
- Consumes: `SortableTable`, `Column<T>` from `./ui/SortableTable.svelte` (Task 2), using the `isRowExpanded`/`expandedRow` props for the per-chore assignment detail row.

This is the most involved migration: each chore row can expand into an assignments detail row. `SortableTable`'s `isRowExpanded`/`expandedRow` props (Task 2) exist specifically for this case.

- [ ] **Step 1: Add the import**

After the `ChoreEditModal` import (line 7):

```svelte
  import SortableTable, { type Column } from "./ui/SortableTable.svelte";
```

- [ ] **Step 2: Replace the table markup**

Replace lines 179–276 (the `<div class="table-wrapper">...</div>` block) with:

```svelte
  <div class="table-wrapper">
    {#snippet expandCell(chore: Chore)}
      <button
        class="expand-btn"
        onclick={(e) => { e.stopPropagation(); expandedHistory = expandedHistory === chore.id ? null : chore.id; }}
      >{expandedHistory === chore.id ? "▼" : "▶"}</button>
    {/snippet}
    {#snippet emojiCell(chore: Chore)}
      {chore.emoji}
    {/snippet}
    {#snippet nameCell(chore: Chore)}
      {displayName(chore)}{#if chore.scheduleFromDue}&nbsp;<span class="sfd-badge" title="Schedules from due date">📅</span>{/if}
    {/snippet}
    {#snippet scheduleCell(chore: Chore)}
      {scheduleLabel(chore)}
    {/snippet}
    {#snippet roomsCell(chore: Chore)}
      {roomsSummary(assignmentsForChore(chore.id))}
    {/snippet}
    {#snippet nextDueCell(chore: Chore)}
      {@const nextDue = earliestDue(assignmentsForChore(chore.id))}
      {nextDue ? formatDate(nextDue) : "—"}
    {/snippet}
    {#snippet actionsCell(chore: Chore)}
      {@const completingChore = completing?.kind === "chore" && completing.id === chore.id ? completing : null}
      {#if completingChore}
        <input
          class="note-input"
          bind:value={completingChore.notes}
          placeholder="Note (optional)"
          onkeydown={(e) => { if (e.key === "Enter") confirmComplete(); if (e.key === "Escape") completing = null; }}
        />
        <button class="icon-btn confirm-btn" onclick={confirmComplete}>✓</button>
        <button class="icon-btn" onclick={() => { completing = null; }}>✕</button>
      {:else}
        <button class="icon-btn" title="Mark all done" onclick={() => { completing = { kind: "chore", id: chore.id, notes: "" }; }}>✓</button>
      {/if}
      <button class="icon-btn" title="Delay all assignments by 1 week" onclick={() => store.delayChore(chore.id, 7)}>⏭</button>
    {/snippet}
    {#snippet assignmentsExpanded(chore: Chore)}
      {@const assignments = assignmentsForChore(chore.id)}
      <div class="expand-body">
        {#if assignments.length > 0}
          {#each assignments as a (a.id)}
            {@const completingAssign = completing?.kind === "assignment" && completing.id === a.id ? completing : null}
            <div class="assign-row">
              <span class="assign-where">{a.roomId ? getRoomName(a.roomId) : "🏠 Whole house"}</span>
              <span class="assign-due">Due: {formatDate(a.nextDueDate)}</span>
              {#if completingAssign}
                <input
                  class="note-input"
                  bind:value={completingAssign.notes}
                  placeholder="Note (optional)"
                  onkeydown={(e) => { if (e.key === "Enter") confirmComplete(); if (e.key === "Escape") completing = null; }}
                />
                <button class="icon-btn confirm-btn" onclick={confirmComplete}>✓</button>
                <button class="icon-btn" onclick={() => { completing = null; }}>✕</button>
              {:else}
                <button class="icon-btn" onclick={() => { completing = { kind: "assignment", id: a.id, notes: "" }; }}>✓</button>
              {/if}
              <button class="icon-btn danger" onclick={() => store.deleteAssignment(a.id)}>✕</button>
              <button class="icon-btn" title="Delay by 1 week" onclick={() => store.delayAssignment(a.id, 7)}>⏭</button>
            </div>
          {/each}
        {:else}
          <div class="no-assign">Not assigned to any room</div>
        {/if}
      </div>
    {/snippet}

    <SortableTable
      columns={[
        { key: "expand", label: "", sortable: false, cellClass: "expand-cell", cell: expandCell },
        { key: "emoji", label: "", sortable: false, cellClass: "emoji-cell", cell: emojiCell },
        { key: "name", label: "Name", sortValue: (c) => displayName(c), cellClass: "name-cell", cell: nameCell },
        { key: "schedule", label: "Schedule", sortValue: (c) => scheduleLabel(c), cell: scheduleCell },
        { key: "rooms", label: "Rooms", sortValue: (c) => roomsSummary(assignmentsForChore(c.id)), cell: roomsCell },
        { key: "nextDue", label: "Next due", sortValue: (c) => { const d = earliestDue(assignmentsForChore(c.id)); return d ? new Date(d) : null; }, cell: nextDueCell },
        { key: "actions", label: "", sortable: false, cellClass: "actions-cell", stopRowClick: true, cell: actionsCell },
      ] as Column<Chore>[]}
      rows={filteredChores}
      rowKey={(chore) => chore.id}
      rowClick={(chore) => { editChore = chore; }}
      isRowExpanded={(chore) => expandedHistory === chore.id}
      expandedRow={assignmentsExpanded}
      emptyMessage={store.chores.length === 0
        ? "No chores yet — click ＋ Add chore to get started."
        : dueFilter === "attention"
          ? "No chores need attention right now."
          : "No chores match your filters."}
    />
  </div>
```

- [ ] **Step 3: Trim the page's own table CSS**

Delete these lines from the `<style>` block (308–316 in the original):

```css
  table { width: 100%; border-collapse: collapse; font-size: 12px; color: var(--text-muted); }
  thead { position: sticky; top: 0; background: var(--surface-alt); z-index: 1; }
  th {
    padding: 6px 10px; color: var(--text-faint); font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.05em;
    text-align: left; border-bottom: 1px solid var(--border);
  }
  td { padding: 7px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:not(.expand-row):hover td { background: var(--surface-hover); cursor: pointer; }
```

Globalize the classes now applied to `SortableTable`-owned `<td>` elements, and delete the standalone `.empty { ... }` and `.expand-row td { ... }` rules (the latter is now `SortableTable`'s own `.ui-sortable-table-expand-row`, styled identically in Task 2):

```css
  :global(.emoji-cell) { font-size: 16px; width: 32px; text-align: center; }
  :global(.name-cell) { color: var(--text); font-weight: 600; }
  :global(.actions-cell) { white-space: nowrap; text-align: right; }
  :global(.expand-cell) { width: 20px; padding: 0 4px; text-align: center; }
```

`.sfd-badge`, `.icon-btn`, `.expand-btn`, `.note-input`, `.expand-body`, `.assign-row`, `.assign-where`, `.assign-due`, `.no-assign`, `.confirm-btn` all stay scoped as-is (unchanged) — they render inside this component's own snippets.

- [ ] **Step 4: Run the existing test suite for regressions**

Run: `cd packages/editor && npx vitest run test/ChoresPage.test.ts test/choreStore.test.ts test/choreFormat.test.ts test/ChoreEditModal.test.ts test/ChoreRow.test.ts`
Expected: PASS.

- [ ] **Step 5: Typecheck**

Run: `cd packages/editor && npx svelte-check --tsconfig ./tsconfig.json`
Expected: no errors in `ChoresPage.svelte`.

- [ ] **Step 6: Add a regression test for expand/collapse via SortableTable**

Add to `packages/editor/test/ChoresPage.test.ts` (new `describe` block):

```ts
describe("ChoresPage — expand/collapse assignments", () => {
  it("expands and collapses the assignment detail row on toggle click", () => {
    const chore = makeChore();
    const store = makeStore([chore]);
    store.assignments = [{ id: "a1", choreId: "c1", roomId: null, nextDueDate: "2026-08-01T12:00:00.000Z" }];
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    expect(target.querySelector(".assign-row")).toBeNull();

    const toggleBtn = target.querySelector(".expand-btn") as HTMLButtonElement;
    toggleBtn.click();
    flushSync();
    expect(target.querySelector(".assign-row")).not.toBeNull();
    expect(target.querySelector(".assign-where")?.textContent).toBe("🏠 Whole house");

    toggleBtn.click();
    flushSync();
    expect(target.querySelector(".assign-row")).toBeNull();

    unmount(comp);
  });
});
```

Note: `makeStore` in this test file doesn't type `assignments` strictly enough to assign directly — if TypeScript complains, cast with `store.assignments = [...] as typeof store.assignments;` when writing this step.

- [ ] **Step 7: Run the new test**

Run: `cd packages/editor && npx vitest run test/ChoresPage.test.ts`
Expected: PASS, 3 tests (2 existing + 1 new).

- [ ] **Step 8: Commit**

```bash
git add packages/editor/src/lib/components/ChoresPage.svelte packages/editor/test/ChoresPage.test.ts
git commit -m "refactor: migrate ChoresPage to SortableTable with expand rows"
```

---

## Task 8: Migrate `SettingsSecurity.svelte` (API Tokens, Users)

**Files:**
- Modify: `packages/editor/src/lib/components/settings/SettingsSecurity.svelte`

**Interfaces:**
- Consumes: `SortableTable`, `Column<T>` from `../ui/SortableTable.svelte` (Task 2).

- [ ] **Step 1: Add the import**

After the `Modal` import (line 7):

```svelte
  import SortableTable, { type Column } from "../ui/SortableTable.svelte";
```

- [ ] **Step 2: Replace the API Tokens table**

Replace lines 231–253 (the `<table class="token-table">...</table>` for tokens) with:

```svelte
      {#snippet tokenNameCell(t: TokenInfo)}{t.name}{/snippet}
      {#snippet tokenScopeCell(t: TokenInfo)}<span class="role-badge">{t.role}</span>{/snippet}
      {#snippet tokenCreatedCell(t: TokenInfo)}{t.created_at?.slice(0, 10) ?? "—"}{/snippet}
      {#snippet tokenLastUsedCell(t: TokenInfo)}{t.last_used_at ? t.last_used_at.slice(0, 10) : "—"}{/snippet}
      {#snippet tokenActionsCell(t: TokenInfo)}
        {#if confirmRevokeTokenId === t.id}
          <Button variant="danger" onclick={() => revokeToken(t.id)}>Confirm revoke</Button>
          <Button variant="secondary" onclick={() => { confirmRevokeTokenId = null; }}>Cancel</Button>
        {:else}
          <Button variant="secondary" onclick={() => { confirmRevokeTokenId = t.id; }}>Revoke</Button>
        {/if}
      {/snippet}
      <SortableTable
        class="token-table"
        columns={[
          { key: "name", label: "Name", sortValue: (t) => t.name, cell: tokenNameCell },
          { key: "scope", label: "Scope", sortValue: (t) => t.role, cell: tokenScopeCell },
          { key: "created", label: "Created", sortValue: (t) => (t.created_at ? new Date(t.created_at) : null), cell: tokenCreatedCell },
          { key: "lastUsed", label: "Last used", sortValue: (t) => (t.last_used_at ? new Date(t.last_used_at) : null), cell: tokenLastUsedCell },
          { key: "actions", label: "", sortable: false, cell: tokenActionsCell },
        ] as Column<TokenInfo>[]}
        rows={apiTokens}
        rowKey={(t) => t.id}
      />
```

- [ ] **Step 3: Replace the Users table**

Replace lines 265–315 (the `<table class="token-table">...</table>` for users) with:

```svelte
      {#snippet userNameCell(u: UserInfo)}{u.username}{/snippet}
      {#snippet userRoleCell(u: UserInfo)}
        {#if editingUserId === u.id}
          <select bind:value={editUserRole} class="modal-select">
            {#each ["ro", "normal", "admin"] as r}
              <option value={r}>{r}</option>
            {/each}
          </select>
          <Button onclick={() => updateUserRole(u.id, editUserRole)}>Save</Button>
          <Button variant="secondary" onclick={() => { editingUserId = null; }}>Cancel</Button>
        {:else}
          <span class="role-badge">{u.role}</span>
        {/if}
      {/snippet}
      {#snippet userCreatedCell(u: UserInfo)}{u.created_at?.slice(0, 10) ?? "—"}{/snippet}
      {#snippet userActionsCell(u: UserInfo)}
        <div style="display:flex;gap:4px;flex-wrap:wrap">
          {#if editingUserId !== u.id}
            <Button variant="secondary" onclick={() => { editingUserId = u.id; editUserRole = u.role; }}>Edit role</Button>
          {/if}
          {#if resetPasswordUserId === u.id}
            <input
              type="password"
              bind:value={resetPasswordValue}
              placeholder="New password (min 8)"
              class="inline-pw-input"
            />
            <Button onclick={() => resetUserPassword(u.id)}>Set</Button>
            <Button variant="secondary" onclick={() => { resetPasswordUserId = null; resetPasswordValue = ""; }}>Cancel</Button>
          {:else}
            <Button variant="secondary" onclick={() => { resetPasswordUserId = u.id; }}>Reset pw</Button>
          {/if}
          {#if u.id !== authStore.user?.id}
            {#if confirmDeleteUserId === u.id}
              <Button variant="danger" onclick={() => deleteUser(u.id)}>Confirm delete</Button>
              <Button variant="secondary" onclick={() => { confirmDeleteUserId = null; }}>Cancel</Button>
            {:else}
              <Button variant="secondary" onclick={() => { confirmDeleteUserId = u.id; }}>Delete</Button>
            {/if}
          {/if}
        </div>
      {/snippet}
      <SortableTable
        class="token-table"
        columns={[
          { key: "username", label: "Username", sortValue: (u) => u.username, cell: userNameCell },
          { key: "role", label: "Role", sortValue: (u) => u.role, cell: userRoleCell },
          { key: "created", label: "Created", sortValue: (u) => (u.created_at ? new Date(u.created_at) : null), cell: userCreatedCell },
          { key: "actions", label: "Actions", sortable: false, cell: userActionsCell },
        ] as Column<UserInfo>[]}
        rows={users}
        rowKey={(u) => u.id}
      />
```

- [ ] **Step 4: Trim the page's own table CSS**

In the `<style>` block, delete the base rules now owned by `SortableTable` (lines 444–446 in the original):

```css
  .token-table { width: 100%; border-collapse: collapse; margin-top: var(--space-2); font-size: 0.875rem; }
  .token-table th { text-align: left; padding: 6px 8px; color: var(--text-muted); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; border-bottom: 1px solid var(--border); }
  .token-table td { padding: 8px 8px; border-bottom: 1px solid var(--border); color: var(--text); }
```

Replace with a global override targeting `SortableTable`'s own class combined with the `class="token-table"` prop, to preserve the slightly different sizing this page used (`margin-top`, `0.875rem` font, `color: var(--text)` on cells):

```css
  :global(table.token-table) { margin-top: var(--space-2); font-size: 0.875rem; }
  :global(table.token-table td) { color: var(--text); }
```

`.role-badge`, `.modal-select` (used inside `userRoleCell`), `.inline-pw-input` stay scoped as-is (rendered inside this component's own snippets).

- [ ] **Step 5: Run the existing test suite for regressions**

Run: `cd packages/editor && npx vitest run test/SettingsSecurity.test.ts`
Expected: PASS.

- [ ] **Step 6: Typecheck**

Run: `cd packages/editor && npx svelte-check --tsconfig ./tsconfig.json`
Expected: no errors in `SettingsSecurity.svelte`.

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/components/settings/SettingsSecurity.svelte
git commit -m "refactor: migrate SettingsSecurity tables to SortableTable"
```

---

## Task 9: Migrate `SettingsBackup.svelte` (Scheduled Backups)

**Files:**
- Modify: `packages/editor/src/lib/components/settings/SettingsBackup.svelte`

**Interfaces:**
- Consumes: `SortableTable`, `Column<T>` from `../ui/SortableTable.svelte` (Task 2).

- [ ] **Step 1: Add the import**

After the `Modal` import (line 6):

```svelte
  import SortableTable, { type Column } from "../ui/SortableTable.svelte";
```

- [ ] **Step 2: Replace the table markup**

Replace lines 282–306 (the `<div class="table-wrapper">...</div>` block) with:

```svelte
    <div class="table-wrapper" style="margin-top: var(--space-3)">
      {#snippet createdCell(backup: ScheduledBackupEntry)}
        {new Date(backup.createdAt).toLocaleString()}
      {/snippet}
      {#snippet sizeCell(backup: ScheduledBackupEntry)}
        {formatBackupSize(backup.sizeBytes)}
      {/snippet}
      {#snippet actionsCell(backup: ScheduledBackupEntry)}
        {#if confirmDeleteBackupFilename === backup.filename}
          <span class="confirm-text">Delete?</span>
          <button class="icon-action danger" onclick={() => deleteScheduledBackup(backup.filename)}>✓</button>
          <button class="icon-action" onclick={() => { confirmDeleteBackupFilename = null; }}>✕</button>
        {:else}
          <button class="icon-action" onclick={() => downloadScheduledBackup(backup.filename)} title="Download">⬇</button>
          <button class="icon-action danger" onclick={() => { confirmDeleteBackupFilename = backup.filename; }} title="Delete">🗑</button>
        {/if}
      {/snippet}
      <SortableTable
        columns={[
          { key: "created", label: "Created", sortValue: (b) => new Date(b.createdAt), cell: createdCell },
          { key: "size", label: "Size", sortValue: (b) => b.sizeBytes, cell: sizeCell },
          { key: "actions", label: "", sortable: false, cellClass: "actions", cell: actionsCell },
        ] as Column<ScheduledBackupEntry>[]}
        rows={scheduledBackups}
        rowKey={(b) => b.filename}
        rowClass={() => "backup-row"}
      />
    </div>
```

- [ ] **Step 3: Trim the page's own table CSS**

Delete these lines from the `<style>` block (341–345 in the original):

```css
  table { width: 100%; border-collapse: collapse; font-size: 12px; color: var(--text-muted); }
  thead { background: var(--surface-alt); }
  th { padding: 5px 10px; color: var(--text-faint); font-size: 10px; text-transform: uppercase; letter-spacing: .05em; text-align: left; border-bottom: 1px solid var(--border); }
  td { padding: 6px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:hover td { background: var(--surface-hover); }
```

Globalize `.actions` (now applied via `cellClass` to a `SortableTable`-owned `<td>`):

```css
  :global(.actions) { display: flex; align-items: center; gap: 4px; white-space: nowrap; }
```

`.icon-action`, `.confirm-text` stay scoped as-is (rendered inside this component's own `actionsCell` snippet). Note `.backup-row` had no CSS rules to begin with in the original file (dead class already) — leave as-is, it's harmless.

- [ ] **Step 4: Run the existing test suite for regressions**

Run: `cd packages/editor && npx vitest run test/SettingsBackup.test.ts`
Expected: PASS.

- [ ] **Step 5: Typecheck**

Run: `cd packages/editor && npx svelte-check --tsconfig ./tsconfig.json`
Expected: no errors in `SettingsBackup.svelte`.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/settings/SettingsBackup.svelte
git commit -m "refactor: migrate SettingsBackup scheduled-backups table to SortableTable"
```

---

## Task 10: Migrate `SettingsCategories.svelte` (5 tables)

**Files:**
- Modify: `packages/editor/src/lib/components/settings/SettingsCategories.svelte`

**Interfaces:**
- Consumes: `SortableTable`, `Column<T>` from `../ui/SortableTable.svelte` (Task 2), using `extraRow` for each table's inline "add new" form row.

This file has 5 near-identical tables (Cost categories, Inventory categories, Work categories, Suppliers, Consumable categories), each with inline edit-in-place rows and an inline "add new" row. Each row's `cell` snippet inspects the page's local `editingXId` state to decide between display and edit-input content — this works because snippets close over the component's reactive state. The "add new" row isn't tied to any data row, so it uses `SortableTable`'s `extraRow` prop.

- [ ] **Step 1: Add the import**

After the `Tabs` import (line 8):

```svelte
  import SortableTable, { type Column } from "../ui/SortableTable.svelte";
```

- [ ] **Step 2: Replace the Cost categories table**

Replace lines 277–335 (the `<div class="table-wrapper">...</div>` for cost categories) with:

```svelte
    <div class="table-wrapper">
      {#snippet costColorCell(cat: CostCategory)}
        {#if editingCostId === cat.id}
          <input type="color" bind:value={costDraft.color} class="color-input" />
        {:else}
          <span class="color-swatch" style="background:{cat.color}"></span>
        {/if}
      {/snippet}
      {#snippet costEmojiCell(cat: CostCategory)}
        {#if editingCostId === cat.id}
          <EmojiPicker bind:value={costDraft.emoji} />
        {:else}
          {cat.emoji}
        {/if}
      {/snippet}
      {#snippet costNameCell(cat: CostCategory)}
        {#if editingCostId === cat.id}
          <Input bind:value={costDraft.name} placeholder="Name" />
        {:else}
          {cat.name}
        {/if}
      {/snippet}
      {#snippet costUnitCell(cat: CostCategory)}
        {#if editingCostId === cat.id}
          <Input bind:value={costDraftUnit} placeholder="L, kWh…" />
        {:else}
          {cat.unit ?? "—"}
        {/if}
      {/snippet}
      {#snippet costActionsCell(cat: CostCategory)}
        {#if editingCostId === cat.id}
          <button class="icon-action ok" onclick={saveEditCost} title="Save">✓</button>
          <button class="icon-action" onclick={cancelEditCost} title="Cancel">✕</button>
        {:else if confirmDeleteCostId === cat.id}
          <span class="confirm-text">Delete?</span>
          <button class="icon-action danger" onclick={() => deleteCostCategory(cat.id)}>✓</button>
          <button class="icon-action" onclick={() => { confirmDeleteCostId = null; }}>✕</button>
        {:else}
          <button class="icon-action" onclick={() => startEditCost(cat)} title="Edit">✏</button>
          <button class="icon-action danger" onclick={() => { confirmDeleteCostId = cat.id; }} title="Delete">🗑</button>
        {/if}
      {/snippet}
      {#snippet costNewRow()}
        <td><input type="color" bind:value={newCostDraft.color} class="color-input" /></td>
        <td><EmojiPicker bind:value={newCostDraft.emoji} /></td>
        <td class="name-cell-input"><Input bind:value={newCostDraft.name} placeholder="Name *" /></td>
        <td class="unit-cell-input"><Input bind:value={newCostDraft.unit} placeholder="L, kWh… (optional)" /></td>
        <td class="actions">
          <button class="icon-action ok" onclick={addCostCategory} title="Add">✓</button>
          <button class="icon-action" onclick={() => { showNewCostForm = false; costError = null; }} title="Cancel">✕</button>
        </td>
      {/snippet}
      <SortableTable
        columns={[
          { key: "color", label: "Color", sortable: false, cell: costColorCell },
          { key: "emoji", label: "Emoji", sortable: false, cellClass: "emoji-cell", cell: costEmojiCell },
          { key: "name", label: "Name", sortValue: (c) => c.name, cellClass: (c) => editingCostId === c.id ? "name-cell-input" : "", cell: costNameCell },
          { key: "unit", label: "Unit", sortValue: (c) => c.unit, cellClass: (c) => editingCostId === c.id ? "unit-cell-input" : "unit-cell", cell: costUnitCell },
          { key: "actions", label: "", sortable: false, cellClass: "actions", cell: costActionsCell },
        ] as Column<CostCategory>[]}
        rows={store.costCategories}
        rowKey={(c) => c.id}
        rowClass={(c) => editingCostId === c.id ? "editing-row" : ""}
        extraRow={showNewCostForm ? costNewRow : undefined}
      />
    </div>
    {#if costError}<div class="error">{costError}</div>{/if}
  </Card>
{/if}
```

Note: keep the existing `{#if activeTab === "cost"}` opening (line 270) and the `<Card>`/section-header block (lines 271–276) unchanged — only the `<div class="table-wrapper">...</div>` through the closing `{/if}` at line 338 is replaced by the block above (the final `{/if}` in the snippet above corresponds to the original line 338 closing the `{#if activeTab === "cost"}` block, so no extra `{/if}` should be added).

- [ ] **Step 3: Replace the Inventory categories table**

Replace lines 347–390 (the `<div class="table-wrapper">...</div>` for inventory categories) with:

```svelte
    <div class="table-wrapper">
      {#snippet invNameCell(cat: InventoryCategory)}
        {#if editingInvId === cat.id}
          <Input bind:value={invDraft.name} placeholder="Name" />
        {:else}
          {cat.name}
        {/if}
      {/snippet}
      {#snippet invActionsCell(cat: InventoryCategory)}
        {#if editingInvId === cat.id}
          <button class="icon-action ok" onclick={saveEditInv} title="Save">✓</button>
          <button class="icon-action" onclick={cancelEditInv} title="Cancel">✕</button>
        {:else if confirmDeleteInvId === cat.id}
          <span class="confirm-text">Delete?</span>
          <button class="icon-action danger" onclick={() => deleteInventoryCategory(cat.id)}>✓</button>
          <button class="icon-action" onclick={() => { confirmDeleteInvId = null; }}>✕</button>
        {:else}
          <button class="icon-action" onclick={() => startEditInv(cat)} title="Edit">✏</button>
          <button class="icon-action danger" onclick={() => { confirmDeleteInvId = cat.id; }} title="Delete">🗑</button>
        {/if}
      {/snippet}
      {#snippet invNewRow()}
        <td class="name-cell-input wide"><Input bind:value={newInvDraft.name} placeholder="Name *" /></td>
        <td class="actions">
          <button class="icon-action ok" onclick={addInventoryCategory} title="Add">✓</button>
          <button class="icon-action" onclick={() => { showNewInvForm = false; invError = null; }} title="Cancel">✕</button>
        </td>
      {/snippet}
      <SortableTable
        columns={[
          { key: "name", label: "Name", sortValue: (c) => c.name, cellClass: (c) => editingInvId === c.id ? "name-cell-input wide" : "", cell: invNameCell },
          { key: "actions", label: "", sortable: false, cellClass: "actions", cell: invActionsCell },
        ] as Column<InventoryCategory>[]}
        rows={store.inventoryCategories}
        rowKey={(c) => c.id}
        rowClass={(c) => editingInvId === c.id ? "editing-row" : ""}
        extraRow={showNewInvForm ? invNewRow : undefined}
      />
    </div>
    {#if invError}<div class="error">{invError}</div>{/if}
  </Card>
{/if}
```

Same note as Step 2 — this replaces through the original closing `{/if}` for the inventory tab (line 393).

- [ ] **Step 4: Replace the Work categories table**

Replace lines 401–446 (the `<div class="table-wrapper">...</div>` for work categories) with:

```svelte
    <div class="table-wrapper">
      {#snippet workEmojiCell(cat: WorkCategory)}
        {#if editingWorkId === cat.id}
          <EmojiPicker bind:value={workDraft.emoji} />
        {:else}
          {cat.emoji}
        {/if}
      {/snippet}
      {#snippet workNameCell(cat: WorkCategory)}
        {#if editingWorkId === cat.id}
          <Input bind:value={workDraft.name} placeholder="Name" />
        {:else}
          {cat.name}
        {/if}
      {/snippet}
      {#snippet workActionsCell(cat: WorkCategory)}
        {#if editingWorkId === cat.id}
          <button class="icon-action ok" onclick={saveEditWork} title="Save">✓</button>
          <button class="icon-action" onclick={cancelEditWork} title="Cancel">✕</button>
        {:else if confirmDeleteWorkId === cat.id}
          <span class="confirm-text">Delete?</span>
          <button class="icon-action danger" onclick={() => deleteWorkCategory(cat.id)}>✓</button>
          <button class="icon-action" onclick={() => { confirmDeleteWorkId = null; }}>✕</button>
        {:else}
          <button class="icon-action" onclick={() => startEditWork(cat)} title="Edit">✏</button>
          <button class="icon-action danger" onclick={() => { confirmDeleteWorkId = cat.id; }} title="Delete">🗑</button>
        {/if}
      {/snippet}
      {#snippet workNewRow()}
        <td><EmojiPicker bind:value={newWorkDraft.emoji} /></td>
        <td class="name-cell-input"><Input bind:value={newWorkDraft.name} placeholder="Name *" /></td>
        <td class="actions">
          <button class="icon-action ok" onclick={addWorkCategory} title="Add">✓</button>
          <button class="icon-action" onclick={() => { showNewWorkForm = false; workError = null; }} title="Cancel">✕</button>
        </td>
      {/snippet}
      <SortableTable
        columns={[
          { key: "emoji", label: "Emoji", sortable: false, cellClass: "emoji-cell", cell: workEmojiCell },
          { key: "name", label: "Name", sortValue: (c) => c.name, cellClass: (c) => editingWorkId === c.id ? "name-cell-input" : "", cell: workNameCell },
          { key: "actions", label: "", sortable: false, cellClass: "actions", cell: workActionsCell },
        ] as Column<WorkCategory>[]}
        rows={store.workCategories}
        rowKey={(c) => c.id}
        rowClass={(c) => editingWorkId === c.id ? "editing-row" : ""}
        extraRow={showNewWorkForm ? workNewRow : undefined}
      />
    </div>
    {#if workError}<div class="error">{workError}</div>{/if}
  </Card>
{/if}
```

Replaces through the original closing `{/if}` for the work tab (line 449).

- [ ] **Step 5: Replace the Suppliers table**

Replace lines 457–500 (the `<div class="table-wrapper">...</div>` for suppliers) with:

```svelte
    <div class="table-wrapper">
      {#snippet supplierNameCell(s: Supplier)}
        {#if editingSupplierId === s.id}
          <Input bind:value={supplierDraft.name} placeholder="Name" />
        {:else}
          {s.name}
        {/if}
      {/snippet}
      {#snippet supplierActionsCell(s: Supplier)}
        {#if editingSupplierId === s.id}
          <button class="icon-action ok" onclick={saveEditSupplier} title="Save">✓</button>
          <button class="icon-action" onclick={cancelEditSupplier} title="Cancel">✕</button>
        {:else if confirmDeleteSupplierId === s.id}
          <span class="confirm-text">Delete?</span>
          <button class="icon-action danger" onclick={() => deleteSupplier(s.id)}>✓</button>
          <button class="icon-action" onclick={() => { confirmDeleteSupplierId = null; }}>✕</button>
        {:else}
          <button class="icon-action" onclick={() => startEditSupplier(s)} title="Edit">✏</button>
          <button class="icon-action danger" onclick={() => { confirmDeleteSupplierId = s.id; }} title="Delete">🗑</button>
        {/if}
      {/snippet}
      {#snippet supplierNewRow()}
        <td class="name-cell-input wide"><Input bind:value={newSupplierDraft.name} placeholder="Name *" /></td>
        <td class="actions">
          <button class="icon-action ok" onclick={addSupplier} title="Add">✓</button>
          <button class="icon-action" onclick={() => { showNewSupplierForm = false; supplierError = null; }} title="Cancel">✕</button>
        </td>
      {/snippet}
      <SortableTable
        columns={[
          { key: "name", label: "Name", sortValue: (s) => s.name, cellClass: (s) => editingSupplierId === s.id ? "name-cell-input wide" : "", cell: supplierNameCell },
          { key: "actions", label: "", sortable: false, cellClass: "actions", cell: supplierActionsCell },
        ] as Column<Supplier>[]}
        rows={store.suppliers}
        rowKey={(s) => s.id}
        rowClass={(s) => editingSupplierId === s.id ? "editing-row" : ""}
        extraRow={showNewSupplierForm ? supplierNewRow : undefined}
      />
    </div>
    {#if supplierError}<div class="error">{supplierError}</div>{/if}
  </Card>
{/if}
```

Replaces through the original closing `{/if}` for the suppliers tab (line 502).

- [ ] **Step 6: Replace the Consumable categories table**

Replace lines 527–572 (the `<div class="table-wrapper">...</div>` for consumable categories, inside the "consumables" tab) with:

```svelte
    <div class="table-wrapper">
      {#snippet consCatEmojiCell(cat: ConsumableCategory)}
        {#if editingConsumableCatId === cat.id}
          <EmojiPicker bind:value={consumableCatDraft.emoji} />
        {:else}
          {cat.emoji}
        {/if}
      {/snippet}
      {#snippet consCatNameCell(cat: ConsumableCategory)}
        {#if editingConsumableCatId === cat.id}
          <Input bind:value={consumableCatDraft.name} placeholder="Name" />
        {:else}
          {cat.name}
        {/if}
      {/snippet}
      {#snippet consCatActionsCell(cat: ConsumableCategory)}
        {#if editingConsumableCatId === cat.id}
          <button class="icon-action ok" onclick={saveEditConsumableCat} title="Save">✓</button>
          <button class="icon-action" onclick={cancelEditConsumableCat} title="Cancel">✕</button>
        {:else if confirmDeleteConsumableCatId === cat.id}
          <span class="confirm-text">Delete?</span>
          <button class="icon-action danger" onclick={() => deleteConsumableCategory(cat.id)}>✓</button>
          <button class="icon-action" onclick={() => { confirmDeleteConsumableCatId = null; }}>✕</button>
        {:else}
          <button class="icon-action" onclick={() => startEditConsumableCat(cat)} title="Edit">✏</button>
          <button class="icon-action danger" onclick={() => { confirmDeleteConsumableCatId = cat.id; }} title="Delete">🗑</button>
        {/if}
      {/snippet}
      {#snippet consCatNewRow()}
        <td><EmojiPicker bind:value={newConsumableCatDraft.emoji} /></td>
        <td class="name-cell-input"><Input bind:value={newConsumableCatDraft.name} placeholder="Name *" /></td>
        <td class="actions">
          <button class="icon-action ok" onclick={addConsumableCategory} title="Add">✓</button>
          <button class="icon-action" onclick={() => { showNewConsumableCatForm = false; consumableCatError = null; }} title="Cancel">✕</button>
        </td>
      {/snippet}
      <SortableTable
        columns={[
          { key: "emoji", label: "Emoji", sortable: false, cellClass: "emoji-cell", cell: consCatEmojiCell },
          { key: "name", label: "Name", sortValue: (c) => c.name, cellClass: (c) => editingConsumableCatId === c.id ? "name-cell-input" : "", cell: consCatNameCell },
          { key: "actions", label: "", sortable: false, cellClass: "actions", cell: consCatActionsCell },
        ] as Column<ConsumableCategory>[]}
        rows={store.consumableCategories}
        rowKey={(c) => c.id}
        rowClass={(c) => editingConsumableCatId === c.id ? "editing-row" : ""}
        extraRow={showNewConsumableCatForm ? consCatNewRow : undefined}
      />
    </div>
```

This block sits between the `<h3 class="subsection-title">Categories</h3>` (line 526) and the `<div class="add-row">` (line 573) — unchanged surrounding markup, only the table div is replaced.

- [ ] **Step 7: Trim the page's own table CSS**

Delete these lines from the `<style>` block (585–589 in the original):

```css
  table { width: 100%; border-collapse: collapse; font-size: 12px; color: var(--text-muted); }
  thead { background: var(--surface-alt); }
  th { padding: 5px 10px; color: var(--text-faint); font-size: 10px; text-transform: uppercase; letter-spacing: .05em; text-align: left; border-bottom: 1px solid var(--border); }
  td { padding: 6px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:hover td { background: var(--surface-hover); }
```

Globalize the classes now applied via `cellClass`/`rowClass` to `SortableTable`-owned elements:

```css
  :global(.editing-row) td { background: var(--surface-alt); }
  :global(.emoji-cell) { font-size: 15px; }
  :global(.unit-cell) { color: var(--text-faint); }
  :global(.name-cell-input) :global(.ui-input) { width: 160px; }
  :global(.name-cell-input.wide) :global(.ui-input) { width: 260px; }
  :global(.unit-cell-input) :global(.ui-input) { width: 100px; }
  :global(.actions) { display: flex; align-items: center; gap: 4px; white-space: nowrap; }
```

`.color-swatch`, `.color-input`, `.icon-action`, `.confirm-text` stay scoped as-is (rendered inside this component's own snippets). Note the nested `:global(.name-cell-input) :global(.ui-input)` selector — this preserves the original `.name-cell-input :global(.ui-input)` pattern (a page-scoped class combined with a global child selector), now doubly-global since `.name-cell-input` itself is applied to a `SortableTable`-owned `<td>`.

- [ ] **Step 8: Run the existing test suite for regressions**

Run: `cd packages/editor && npx vitest run test/SettingsCategories.test.ts`
Expected: PASS.

- [ ] **Step 9: Typecheck**

Run: `cd packages/editor && npx svelte-check --tsconfig ./tsconfig.json`
Expected: no errors in `SettingsCategories.svelte`.

- [ ] **Step 10: Full suite regression check**

Run: `cd packages/editor && npx vitest run`
Expected: entire suite passes — this is the last and largest migration, a full run catches any cross-file breakage.

- [ ] **Step 11: Commit**

```bash
git add packages/editor/src/lib/components/settings/SettingsCategories.svelte
git commit -m "refactor: migrate all 5 SettingsCategories tables to SortableTable"
```

---

## Task 11: Browser smoke check

**Files:** none (verification only)

- [ ] **Step 1: Start the dev server**

Use the project's `run` skill or: `cd packages/editor && npm run dev` (check for the known stray main-repo vite-on-5173 gotcha noted in project memory — confirm which port this workspace's dev server actually binds before testing).

- [ ] **Step 2: Verify Inventory table sorting**

Using the `webapp-testing` skill (Playwright), navigate to the Inventory page. Click the "Name" column header — confirm rows reorder alphabetically and an ascending arrow appears. Click again — confirm descending order and arrow flips. Click a third time — confirm it returns to original order with no arrow. Click "Cost" — confirm numeric sort (not lexicographic). Confirm clicking a row still opens the edit modal, and the emoji/warranty columns (non-sortable) show no button/arrow on hover.

- [ ] **Step 3: Verify a Settings table**

Navigate to Settings → Categories (Cost categories tab). Click "Name" header — confirm sort works. Click "Edit" (pencil icon) on a row — confirm the inline edit form still appears correctly and Save/Cancel work. Click "＋ Add" — confirm the new-row form appears at the bottom of the table and Add/Cancel work.

- [ ] **Step 4: Verify Chores expand/collapse still works alongside sorting**

Navigate to Chores. Click the expand arrow on a chore row — confirm the assignment detail row appears. Click "Next due" header to sort — confirm expand state and sort coexist without visual glitches (e.g., expanded row staying attached to the correct chore after a re-sort).

- [ ] **Step 5: Report results**

Summarize pass/fail for each check above. If anything fails, use `superpowers:systematic-debugging` before making fixes — do not guess.

---
