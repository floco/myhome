# Mobile Responsiveness Phase 1: Tables Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every module's data table usable on a narrow viewport without horizontal scrolling to reach action buttons, by hiding lower-priority columns at two breakpoints while keeping the primary identifier and any actions column always visible.

**Architecture:** Add an optional `hideBelow?: "tablet" | "mobile"` field to the shared `SortableTable`'s `Column<T>` type; `SortableTable.svelte` applies a matching CSS class (`col-hide-tablet`/`col-hide-mobile`) to both the `<th>` and `<td>` for that column, hidden via `@media` at 700px/480px. Each of the 9 module pages then sets `hideBelow` on its own lower-priority columns. This is spec Phase 1 of `docs/superpowers/specs/2026-08-05-mobile-responsive-audit-design.md`.

**Tech Stack:** Svelte 5 (runes, snippets), vitest (jsdom environment, no `@testing-library` — this repo's convention is direct `mount`/`unmount`/`flushSync` + DOM queries), Playwright via the `webapp-testing` skill for real-viewport verification (jsdom does not execute `@media` queries, so column-hiding itself can only be verified in a real browser).

## Global Constraints

- `hideBelow` is optional and additive — every existing `Column<T>` object across the codebase that doesn't set it must render exactly as before (no `hideBelow` → no hide class → always visible, matching current behavior).
- The actions column (`stopRowClick: true`, present in `ChoresPage.svelte` and `ConsumablesPage.svelte`) never gets `hideBelow` — action buttons must always be reachable, which is the problem this plan fixes.
- For modules with no actions column (the other 7), the row itself is clickable (`rowClick` opens the edit modal) — `hideBelow` must never hide the column that gives the row visible/tappable content, so at least one always-visible column exists in every table.
- Use `700px`/`480px` as the literal breakpoint values in every new `@media` block added by this plan, matching the `--bp-tablet`/`--bp-mobile` tokens added in Task 1 (CSS custom properties can't drive `@media` conditions, so this is a documented-convention match, not a `var()` substitution).
- Don't change any column's `label`, `sortValue`, `cell`, or existing `cellClass`/`headerClass` — this plan only adds `hideBelow` to existing column objects.

---

### Task 1: Add breakpoint tokens to `theme.css`

**Files:**
- Modify: `packages/editor/src/lib/theme.css`

**Interfaces:**
- Produces: `--bp-tablet` (700px) and `--bp-mobile` (480px) documented as the project's two breakpoint values. Not consumed via `var()` in `@media` (not possible in CSS) — later tasks match these numbers literally in their `@media` blocks.

- [ ] **Step 1: Add the tokens**

In `packages/editor/src/lib/theme.css`, inside the `:root { ... }` block, after the `--space-6: 32px;` line (line 48) and before the `--font-sans` line, add:

```css

  /* Breakpoints (documented convention — @media conditions can't use
     var(), so every @media added elsewhere in the codebase must match
     these two numbers literally: 700px and 480px). */
  --bp-tablet: 700px;
  --bp-mobile: 480px;
```

- [ ] **Step 2: Verify**

Run: `grep -n "bp-tablet\|bp-mobile" packages/editor/src/lib/theme.css`
Expected: two lines showing `--bp-tablet: 700px;` and `--bp-mobile: 480px;`

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/theme.css
git commit -m "chore: add --bp-tablet/--bp-mobile breakpoint tokens"
```

---

### Task 2: Add `hideBelow` support to `SortableTable`

**Files:**
- Modify: `packages/editor/src/lib/components/ui/SortableTable.types.ts`
- Modify: `packages/editor/src/lib/components/ui/SortableTable.svelte`
- Test: `packages/editor/test/SortableTable.test.ts`

**Interfaces:**
- Consumes: nothing new.
- Produces: `Column<T>.hideBelow?: "tablet" | "mobile"`. When set, `SortableTable` adds CSS class `col-hide-tablet` or `col-hide-mobile` to that column's `<th>` and every `<td>` in that column. `.col-hide-tablet` is `display: none` at `max-width: 700px`; `.col-hide-mobile` is `display: none` at `max-width: 480px`. Later tasks (3-11) set this field on module pages' column arrays.

- [ ] **Step 1: Write the failing test**

Append to `packages/editor/test/SortableTable.test.ts`, inside the `describe("ui/SortableTable", ...)` block (after the last existing `it(...)`, before the closing `});` on line 229):

```ts
  it("applies col-hide-tablet/col-hide-mobile classes to columns marked hideBelow", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const columns: Column<Row>[] = [
      { key: "name", label: "Name", sortValue: (r) => r.name },
      { key: "qty", label: "Qty", sortValue: (r) => r.qty, hideBelow: "tablet" },
      { key: "actions", label: "", sortable: false, hideBelow: "mobile" },
    ];
    const comp = mount(SortableTable, {
      target,
      props: { columns, rows: baseRows(), rowKey: (r: Row) => r.id },
    });
    flushSync();

    const headers = target.querySelectorAll("thead th");
    expect(headers[0].classList.contains("col-hide-tablet")).toBe(false);
    expect(headers[0].classList.contains("col-hide-mobile")).toBe(false);
    expect(headers[1].classList.contains("col-hide-tablet")).toBe(true);
    expect(headers[2].classList.contains("col-hide-mobile")).toBe(true);

    const firstRowCells = target.querySelectorAll("tbody tr:first-child td");
    expect(firstRowCells[1].classList.contains("col-hide-tablet")).toBe(true);
    expect(firstRowCells[2].classList.contains("col-hide-mobile")).toBe(true);

    unmount(comp);
  });
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -w @myhome/editor -- SortableTable --run`
Expected: FAIL — `col-hide-tablet`/`col-hide-mobile` classes don't exist yet, all four `toBe(true)` assertions fail.

- [ ] **Step 3: Add `hideBelow` to the `Column<T>` type**

In `packages/editor/src/lib/components/ui/SortableTable.types.ts`, add the field after `stopRowClick?: boolean;` (line 11):

```ts
export interface Column<T> {
  key: string;
  label: string;
  sortable?: boolean;
  sortValue?: (row: T) => string | number | Date | null | undefined;
  cell?: Snippet<[T]>;
  headerClass?: string;
  cellClass?: string | ((row: T) => string);
  stopRowClick?: boolean;
  hideBelow?: "tablet" | "mobile";
}
```

- [ ] **Step 4: Implement the class helper and wire it into the template**

In `packages/editor/src/lib/components/ui/SortableTable.svelte`, add a helper function after `cellClassFor` (after line 61, before the closing `</script>` on line 62):

```ts
  function hideClassFor(column: Column<T>): string {
    if (column.hideBelow === "tablet") return "col-hide-tablet";
    if (column.hideBelow === "mobile") return "col-hide-mobile";
    return "";
  }
```

Replace the header row (lines 66-79):

```svelte
    <tr>
      {#each columns as column (column.key)}
        {#if column.sortable === false}
          <th class="{column.headerClass ?? ''} {hideClassFor(column)}">{column.label}</th>
        {:else}
          <th class="{column.headerClass ?? ''} {hideClassFor(column)}" aria-sort={ariaSortFor(column.key)}>
            <button type="button" class="ui-sortable-table-sort-btn" onclick={() => sortState.toggle(column.key)}>
              {column.label}
              <span class="ui-sortable-table-arrow">{arrowFor(column.key)}</span>
            </button>
          </th>
        {/if}
      {/each}
    </tr>
```

Replace the body cell (lines 85-96):

```svelte
        {#each columns as column (column.key)}
          <td
            class="{cellClassFor(column, row) ?? ''} {hideClassFor(column)}"
            onclick={column.stopRowClick ? (e) => e.stopPropagation() : undefined}
          >
            {#if column.cell}
              {@render column.cell(row)}
            {:else}
              {column.sortValue?.(row) ?? "—"}
            {/if}
          </td>
        {/each}
```

- [ ] **Step 5: Add the `@media` rules**

In the `<style>` block, after the `.ui-sortable-table-empty { ... }` rule (line 137), add:

```css
  @media (max-width: 700px) { /* --bp-tablet */
    .ui-sortable-table .col-hide-tablet { display: none; }
  }
  @media (max-width: 480px) { /* --bp-mobile */
    .ui-sortable-table .col-hide-mobile { display: none; }
  }
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `npm test -w @myhome/editor -- SortableTable --run`
Expected: PASS (all tests in the file, including the new one and the 9 pre-existing ones — the pre-existing ones use `baseColumns()` with no `hideBelow` set, so `hideClassFor` returns `""` for them and their `:first-child`/`:last-child` assertions are unaffected).

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/components/ui/SortableTable.types.ts packages/editor/src/lib/components/ui/SortableTable.svelte packages/editor/test/SortableTable.test.ts
git commit -m "feat: add hideBelow column visibility to SortableTable"
```

---

### Task 3: Chores table — hide `rooms` at tablet, `schedule` at mobile

**Files:**
- Modify: `packages/editor/src/lib/components/ChoresPage.svelte:317-325`
- Test: `packages/editor/test/ChoresPage.test.ts`

**Interfaces:**
- Consumes: `Column<T>.hideBelow` (Task 2).

Always visible: `expand`, `emoji`, `name`, `actions` (already `stopRowClick: true`). Hidden below 700px: `rooms`. Hidden below 480px (in addition): `schedule`. `nextDue` stays always visible (most actionable field — tells the user when the chore is due).

- [ ] **Step 1: Write the failing test**

Append to `packages/editor/test/ChoresPage.test.ts` (add a `describe` block using the existing `makeChore`/`makeStore` helpers already defined in this file):

```ts
describe("ChoresPage — responsive columns", () => {
  it("marks rooms hideBelow tablet and schedule hideBelow mobile, keeps actions always visible", () => {
    const store = makeStore([makeChore()]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    const headers = target.querySelectorAll("thead th");
    // expand, emoji, name, schedule, rooms, nextDue, actions
    expect(headers[4].classList.contains("col-hide-tablet")).toBe(true); // rooms
    expect(headers[3].classList.contains("col-hide-mobile")).toBe(true); // schedule
    expect(headers[6].classList.contains("col-hide-tablet")).toBe(false); // actions
    expect(headers[6].classList.contains("col-hide-mobile")).toBe(false); // actions

    unmount(comp);
  });
});
```

Note: check `ChoresPage.svelte`'s existing prop list for the exact prop names the component expects (it's mounted elsewhere in this same test file) — reuse the same prop shape already used by other tests in `ChoresPage.test.ts` if it differs from `{ store, floorStore }`.

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -w @myhome/editor -- ChoresPage --run`
Expected: FAIL — `col-hide-tablet`/`col-hide-mobile` not present yet on `rooms`/`schedule` headers.

- [ ] **Step 3: Add `hideBelow` to the columns**

In `packages/editor/src/lib/components/ChoresPage.svelte`, modify the `schedule` and `rooms` column entries (lines 321-322):

```svelte
          { key: "schedule", label: $_('chores.page.schedule'), sortValue: (c) => scheduleLabel(c), cell: scheduleCell, hideBelow: "mobile" },
          { key: "rooms", label: $_('chores.page.rooms'), sortValue: (c) => roomsSummary(assignmentsForChore(c.id)), cell: roomsCell, hideBelow: "tablet" },
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npm test -w @myhome/editor -- ChoresPage --run`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ChoresPage.svelte packages/editor/test/ChoresPage.test.ts
git commit -m "feat(chores): hide rooms/schedule columns on narrow viewports"
```

---

### Task 4: Inventory table — hide 4 columns at tablet, 3 more at mobile

**Files:**
- Modify: `packages/editor/src/lib/components/InventoryPage.svelte:264-274`
- Test: `packages/editor/test/InventoryPage.test.ts`

**Interfaces:**
- Consumes: `Column<T>.hideBelow` (Task 2).

Always visible: `emoji`, `name` (no actions column in this table — the whole row opens the edit modal via `rowClick`). Hidden below 700px: `category`, `owner`, `store`, `room`. Hidden below 480px (in addition): `purchased`, `cost`, `warranty`. This is the exact 9-column table cited as the original motivating example (currently overflows with no way to reach anything beyond `name` on a narrow screen).

- [ ] **Step 1: Write the failing test**

Append to `packages/editor/test/InventoryPage.test.ts` (reuse `makeStore`/`makeItem`/`BASE_PROPS` already defined in this file):

```ts
describe("InventoryPage — responsive columns", () => {
  it("hides category/owner/store/room at tablet and purchased/cost/warranty at mobile", () => {
    const store = makeStore([makeItem()]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(InventoryPage, { target, props: { store, floorStore: { floors: [] }, ...BASE_PROPS } });
    flushSync();

    const headers = target.querySelectorAll("thead th");
    // emoji, name, category, owner, store, room, purchased, cost, warranty
    for (const i of [2, 3, 4, 5]) {
      expect(headers[i].classList.contains("col-hide-tablet")).toBe(true);
    }
    for (const i of [6, 7, 8]) {
      expect(headers[i].classList.contains("col-hide-mobile")).toBe(true);
    }
    expect(headers[1].classList.contains("col-hide-tablet")).toBe(false); // name always visible
    expect(headers[1].classList.contains("col-hide-mobile")).toBe(false);

    unmount(comp);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -w @myhome/editor -- InventoryPage --run`
Expected: FAIL

- [ ] **Step 3: Add `hideBelow` to the columns**

In `packages/editor/src/lib/components/InventoryPage.svelte`, modify lines 267-273:

```svelte
          { key: "category", label: $_('costs.page.category'), sortValue: (i) => categoryName(i.categoryId) || null, cell: categoryCell, hideBelow: "tablet" },
          { key: "owner", label: $_('inventory.modal.owner'), sortValue: (i) => ownerName(i.ownerId) || null, cell: ownerCell, hideBelow: "tablet" },
          { key: "store", label: $_('inventory.modal.store'), sortValue: (i) => storeName(i.storeId) || null, cell: storeCell, hideBelow: "tablet" },
          { key: "room", label: $_('costs.page.room'), sortValue: (i) => roomName(i.placement?.roomId), cell: roomCell, hideBelow: "tablet" },
          { key: "purchased", label: $_('inventory.page.purchased'), sortValue: (i) => (i.purchaseDate ? new Date(i.purchaseDate) : null), cell: purchasedCell, hideBelow: "mobile" },
          { key: "cost", label: $_('inventory.page.cost'), sortValue: (i) => i.purchasePrice, cell: costCell, hideBelow: "mobile" },
          { key: "warranty", label: $_('inventory.pinPopup.warranty'), sortable: false, cell: warrantyCell, hideBelow: "mobile" },
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npm test -w @myhome/editor -- InventoryPage --run`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/InventoryPage.svelte packages/editor/test/InventoryPage.test.ts
git commit -m "feat(inventory): hide secondary columns on narrow viewports"
```

---

### Task 5: Consumables table — hide `category`/`min` at tablet, `quantity`/`status` at mobile

**Files:**
- Modify: `packages/editor/src/lib/components/ConsumablesPage.svelte:189-199`
- Test: `packages/editor/test/ConsumablesPage.test.ts`

**Interfaces:**
- Consumes: `Column<T>.hideBelow` (Task 2).

Always visible: `emoji`, `name`, `stock` (the bar-cell visual level indicator), `actions` (`stopRowClick: true`). Hidden below 700px: `category`, `min`. Hidden below 480px (in addition): `quantity`, `status`.

- [ ] **Step 1: Write the failing test**

Append to `packages/editor/test/ConsumablesPage.test.ts` (this file uses `createConsumableStore`/`sampleDoc` already defined — check how existing tests in the file mount `ConsumablesPage` and reuse that exact setup, e.g. constructing the store via `createConsumableStore` with a stubbed `fetch` returning `sampleDoc`, matching the pattern already used later in this file):

```ts
describe("ConsumablesPage — responsive columns", () => {
  it("hides category/min at tablet and quantity/status at mobile", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => sampleDoc }));
    const store = createConsumableStore(() => "home-1");
    await tick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumablesPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    const headers = target.querySelectorAll("thead th");
    // emoji, name, category, quantity, min, stock, status, actions
    expect(headers[2].classList.contains("col-hide-tablet")).toBe(true); // category
    expect(headers[4].classList.contains("col-hide-tablet")).toBe(true); // min
    expect(headers[3].classList.contains("col-hide-mobile")).toBe(true); // quantity
    expect(headers[6].classList.contains("col-hide-mobile")).toBe(true); // status
    expect(headers[7].classList.contains("col-hide-tablet")).toBe(false); // actions
    expect(headers[7].classList.contains("col-hide-mobile")).toBe(false); // actions

    unmount(comp);
    vi.unstubAllGlobals();
  });
});
```

If `ConsumablesPage.svelte` requires additional props beyond `{ store, floorStore }` in this file's existing tests, match whatever the existing mount calls in this file already pass.

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -w @myhome/editor -- ConsumablesPage --run`
Expected: FAIL

- [ ] **Step 3: Add `hideBelow` to the columns**

In `packages/editor/src/lib/components/ConsumablesPage.svelte`, modify lines 193, 195, 194, 197 (category, min get `hideBelow: "tablet"`; quantity, status get `hideBelow: "mobile"`):

```svelte
          { key: "category", label: $_('costs.page.category'), sortValue: (c) => categoryName(c.categoryId), cell: categoryCell, hideBelow: "tablet" },
          { key: "quantity", label: $_('consumables.page.quantity'), sortValue: (c) => c.quantity, cell: quantityCell, hideBelow: "mobile" },
          { key: "min", label: $_('consumables.page.min'), cellClass: "faint", sortValue: (c) => c.minQuantity, cell: minCell, hideBelow: "tablet" },
          { key: "stock", label: $_('consumables.page.stock'), sortable: false, cellClass: "bar-cell", cell: stockCell },
          { key: "status", label: $_('works.page.status'), sortValue: (c) => stockStatus(c), cell: statusCell, hideBelow: "mobile" },
```

(Order and the untouched `name`/`emoji`/`actions` lines stay exactly as they are — only these four lines change.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `npm test -w @myhome/editor -- ConsumablesPage --run`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ConsumablesPage.svelte packages/editor/test/ConsumablesPage.test.ts
git commit -m "feat(consumables): hide secondary columns on narrow viewports"
```

---

### Task 6: Works table — hide `date`/`supplier` at tablet, `category`/`cost` at mobile

**Files:**
- Modify: `packages/editor/src/lib/components/WorksPage.svelte:166-175`
- Test: `packages/editor/test/WorksPage.test.ts`

**Interfaces:**
- Consumes: `Column<T>.hideBelow` (Task 2).

Always visible: `emoji`, `title`, `status` (no actions column — row click opens the edit modal). Hidden below 700px: `date`, `supplier`. Hidden below 480px (in addition): `category`, `cost`.

- [ ] **Step 1: Write the failing test**

Append to `packages/editor/test/WorksPage.test.ts` (reuse `makeWork`/`makeWorksStore`/`makeSettingsStore`/`makeContactsStore` already defined in this file):

```ts
describe("WorksPage — responsive columns", () => {
  it("hides date/supplier at tablet and category/cost at mobile", () => {
    const store = makeWorksStore([makeWork()]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(WorksPage, {
      target,
      props: { store, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore() },
    });
    flushSync();

    const headers = target.querySelectorAll("thead th");
    // emoji, title, category, date, supplier, cost, status
    expect(headers[3].classList.contains("col-hide-tablet")).toBe(true); // date
    expect(headers[4].classList.contains("col-hide-tablet")).toBe(true); // supplier
    expect(headers[2].classList.contains("col-hide-mobile")).toBe(true); // category
    expect(headers[5].classList.contains("col-hide-mobile")).toBe(true); // cost
    expect(headers[1].classList.contains("col-hide-tablet")).toBe(false); // title always visible

    unmount(comp);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -w @myhome/editor -- WorksPage --run`
Expected: FAIL

- [ ] **Step 3: Add `hideBelow` to the columns**

In `packages/editor/src/lib/components/WorksPage.svelte`, modify lines 170-173:

```svelte
          { key: "category", label: $_('costs.page.category'), sortValue: (w) => categoryMap.get(w.categoryId ?? "")?.name ?? null, cell: categoryCell, hideBelow: "mobile" },
          { key: "date", label: $_('costs.page.date'), sortValue: (w) => (w.date ? new Date(w.date) : null), cell: dateCell, hideBelow: "tablet" },
          { key: "supplier", label: $_('costs.page.supplier'), sortValue: (w) => supplierMap.get(w.contactId ?? "")?.name ?? null, cell: supplierCell, hideBelow: "tablet" },
          { key: "cost", label: $_('inventory.page.cost'), sortValue: (w) => w.totalCost, cell: costCell, hideBelow: "mobile" },
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npm test -w @myhome/editor -- WorksPage --run`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/WorksPage.svelte packages/editor/test/WorksPage.test.ts
git commit -m "feat(works): hide secondary columns on narrow viewports"
```

---

### Task 7: Costs table — hide `qty`/`unitPrice`/`supplier`/`room` at tablet, `date` at mobile

**Files:**
- Modify: `packages/editor/src/lib/components/CostsPage.svelte:290-300`
- Test: `packages/editor/test/CostsPage.test.ts`

**Interfaces:**
- Consumes: `Column<T>.hideBelow` (Task 2).

Always visible: `emoji`, `category` (the entry's description), `total` (the amount — most important glanceable figure). Hidden below 700px: `date`... wait, keep `date` visible until mobile since it's needed for context; hidden below 700px: `qty`, `unitPrice`, `supplier`, `room`. Hidden below 480px (in addition): `date`.

- [ ] **Step 1: Write the failing test**

Append to `packages/editor/test/CostsPage.test.ts` (reuse `makeEntry`/`makeCostsStore`/`makeSettingsStore`/`makeContactsStore` already defined in this file):

```ts
describe("CostsPage — responsive columns", () => {
  it("hides qty/unitPrice/supplier/room at tablet and date at mobile", () => {
    const store = makeCostsStore([makeEntry()]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(CostsPage, {
      target,
      props: { store, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore() },
    });
    flushSync();

    const headers = target.querySelectorAll("thead th");
    // emoji, category, date, supplier, qty, unitPrice, total, room
    expect(headers[4].classList.contains("col-hide-tablet")).toBe(true); // qty
    expect(headers[5].classList.contains("col-hide-tablet")).toBe(true); // unitPrice
    expect(headers[3].classList.contains("col-hide-tablet")).toBe(true); // supplier
    expect(headers[7].classList.contains("col-hide-tablet")).toBe(true); // room
    expect(headers[2].classList.contains("col-hide-mobile")).toBe(true); // date
    expect(headers[6].classList.contains("col-hide-tablet")).toBe(false); // total always visible

    unmount(comp);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -w @myhome/editor -- CostsPage --run`
Expected: FAIL

- [ ] **Step 3: Add `hideBelow` to the columns**

In `packages/editor/src/lib/components/CostsPage.svelte`, modify lines 294, 295, 296, 297, 299:

```svelte
        { key: "date", label: $_('costs.page.date'), sortValue: (e) => new Date(e.date), cell: dateCell, hideBelow: "mobile" },
        { key: "supplier", label: $_('costs.page.supplier'), sortValue: (e) => (e.contactId ? supplierMap.get(e.contactId)?.name ?? null : null), cell: supplierCell, hideBelow: "tablet" },
        { key: "qty", label: $_('costs.page.qty'), headerClass: "num-col", cellClass: "num-col", sortValue: (e) => e.quantity, cell: qtyCell, hideBelow: "tablet" },
        { key: "unitPrice", label: $_('costs.page.unitPrice'), headerClass: "num-col", cellClass: "num-col", sortValue: (e) => e.unitPrice, cell: unitPriceCell, hideBelow: "tablet" },
        { key: "total", label: $_('costs.page.total'), headerClass: "num-col", cellClass: "num-col amount-cell", sortValue: (e) => e.totalAmount, cell: totalCell },
        { key: "room", label: $_('costs.page.room'), sortValue: (e) => roomName(e.roomId), cell: roomCell, hideBelow: "tablet" },
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npm test -w @myhome/editor -- CostsPage --run`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/CostsPage.svelte packages/editor/test/CostsPage.test.ts
git commit -m "feat(costs): hide secondary columns on narrow viewports"
```

---

### Task 8: Contacts table — hide `email` at tablet, `phone` at mobile

**Files:**
- Modify: `packages/editor/src/lib/components/ContactsPage.svelte:91-97`
- Test: `packages/editor/test/ContactsPage.test.ts`

**Interfaces:**
- Consumes: `Column<T>.hideBelow` (Task 2).

Only 4 columns total, no icon column. Always visible: `name`, `type`. Hidden below 700px: `email`. Hidden below 480px (in addition): `phone`.

- [ ] **Step 1: Write the failing test**

Append to `packages/editor/test/ContactsPage.test.ts` (reuse `makeContact`/`makeContactsStore`/`makeSettingsStore` already defined in this file):

```ts
describe("ContactsPage — responsive columns", () => {
  it("hides email at tablet and phone at mobile", () => {
    const store = makeContactsStore([makeContact()]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ContactsPage, { target, props: { store, settingsStore: makeSettingsStore() } });
    flushSync();

    const headers = target.querySelectorAll("thead th");
    // name, type, phone, email
    expect(headers[3].classList.contains("col-hide-tablet")).toBe(true); // email
    expect(headers[2].classList.contains("col-hide-mobile")).toBe(true); // phone
    expect(headers[0].classList.contains("col-hide-tablet")).toBe(false); // name
    expect(headers[1].classList.contains("col-hide-tablet")).toBe(false); // type

    unmount(comp);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -w @myhome/editor -- ContactsPage --run`
Expected: FAIL

- [ ] **Step 3: Add `hideBelow` to the columns**

In `packages/editor/src/lib/components/ContactsPage.svelte`, modify lines 95-96:

```svelte
          { key: "phone", label: $_('contacts.page.phone'), sortValue: (c) => c.phone, cell: phoneCell, hideBelow: "mobile" },
          { key: "email", label: $_('contacts.page.email'), sortValue: (c) => c.email, cell: emailCell, hideBelow: "tablet" },
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npm test -w @myhome/editor -- ContactsPage --run`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ContactsPage.svelte packages/editor/test/ContactsPage.test.ts
git commit -m "feat(contacts): hide email/phone columns on narrow viewports"
```

---

### Task 9: Properties table — hide `type`/`size` at tablet, `location`/`price` at mobile

**Files:**
- Modify: `packages/editor/src/lib/components/PropertiesPage.svelte:164-173`
- Test: `packages/editor/test/PropertiesPage.test.ts`

**Interfaces:**
- Consumes: `Column<T>.hideBelow` (Task 2).

Always visible: `emoji`, `name`, `status` (no actions column — row click opens the edit modal). Hidden below 700px: `type`, `size`. Hidden below 480px (in addition): `location`, `price`.

- [ ] **Step 1: Write the failing test**

Append to `packages/editor/test/PropertiesPage.test.ts` (reuse `makeProperty`/`makeStore`/`makeLocationsStore` already defined in this file):

```ts
describe("PropertiesPage — responsive columns", () => {
  it("hides type/size at tablet and location/price at mobile", () => {
    const store = makeStore([makeProperty()]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(PropertiesPage, { target, props: { store, locationsStore: makeLocationsStore() } });
    flushSync();

    const headers = target.querySelectorAll("thead th");
    // emoji, name, type, location, price, size, status
    expect(headers[2].classList.contains("col-hide-tablet")).toBe(true); // type
    expect(headers[5].classList.contains("col-hide-tablet")).toBe(true); // size
    expect(headers[3].classList.contains("col-hide-mobile")).toBe(true); // location
    expect(headers[4].classList.contains("col-hide-mobile")).toBe(true); // price
    expect(headers[1].classList.contains("col-hide-tablet")).toBe(false); // name

    unmount(comp);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -w @myhome/editor -- PropertiesPage --run`
Expected: FAIL

- [ ] **Step 3: Add `hideBelow` to the columns**

In `packages/editor/src/lib/components/PropertiesPage.svelte`, modify lines 168-171:

```svelte
          { key: "type", label: $_('properties.page.type'), sortValue: (p) => typeLabel(p.type), cell: typeCell, hideBelow: "tablet" },
          { key: "location", label: $_('properties.page.location'), sortValue: (p) => (p.locationId ? locationMap.get(p.locationId)?.name ?? null : null), cell: locationCell, hideBelow: "mobile" },
          { key: "price", label: $_('properties.page.price'), sortValue: (p) => p.price, cell: priceCell, hideBelow: "mobile" },
          { key: "size", label: $_('properties.page.size'), sortValue: (p) => p.builtSize ?? p.landSize, cell: sizeCell, hideBelow: "tablet" },
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npm test -w @myhome/editor -- PropertiesPage --run`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/PropertiesPage.svelte packages/editor/test/PropertiesPage.test.ts
git commit -m "feat(properties): hide secondary columns on narrow viewports"
```

---

### Task 10: Insurance table — hide `category`/`provider` at tablet, `endDate` at mobile

**Files:**
- Modify: `packages/editor/src/lib/components/InsurancePage.svelte:163-171`
- Test: `packages/editor/test/InsurancePage.test.ts`

**Interfaces:**
- Consumes: `Column<T>.hideBelow` (Task 2).

Always visible: `emoji`, `name`, `premium` (no actions column — row click opens the edit modal; premium is the key cost figure). Hidden below 700px: `category`, `provider`. Hidden below 480px (in addition): `endDate`.

- [ ] **Step 1: Write the failing test**

Append to `packages/editor/test/InsurancePage.test.ts` (reuse `makePolicy`/`makeInsuranceStore`/`makeSettingsStore`/`makeContactsStore` already defined in this file):

```ts
describe("InsurancePage — responsive columns", () => {
  it("hides category/provider at tablet and endDate at mobile", () => {
    const store = makeInsuranceStore([makePolicy()]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(InsurancePage, {
      target,
      props: { store, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore() },
    });
    flushSync();

    const headers = target.querySelectorAll("thead th");
    // emoji, name, category, provider, premium, endDate
    expect(headers[2].classList.contains("col-hide-tablet")).toBe(true); // category
    expect(headers[3].classList.contains("col-hide-tablet")).toBe(true); // provider
    expect(headers[5].classList.contains("col-hide-mobile")).toBe(true); // endDate
    expect(headers[4].classList.contains("col-hide-tablet")).toBe(false); // premium always visible

    unmount(comp);
  });
});
```

Check `InsurancePage.test.ts`'s existing mount calls for this component's exact prop shape (this file's `makeContactsStore` continues past line 45 — match whatever props the file's existing tests already pass).

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -w @myhome/editor -- InsurancePage --run`
Expected: FAIL

- [ ] **Step 3: Add `hideBelow` to the columns**

In `packages/editor/src/lib/components/InsurancePage.svelte`, modify lines 167-170:

```svelte
          { key: "category", label: $_('costs.page.category'), sortValue: (p) => categoryMap.get(p.categoryId)?.name ?? null, cell: categoryCell, hideBelow: "tablet" },
          { key: "provider", label: $_('costs.entryModal.supplier'), sortValue: (p) => contactMap.get(p.contactId ?? "")?.name ?? null, cell: providerCell, hideBelow: "tablet" },
          { key: "premium", label: $_('insurance.page.premium'), sortValue: (p) => annualized(p), cell: premiumCell },
          { key: "endDate", label: $_('insurance.page.endDate'), sortValue: (p) => (p.endDate ? new Date(p.endDate) : null), cell: endDateCell, hideBelow: "mobile" },
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npm test -w @myhome/editor -- InsurancePage --run`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/InsurancePage.svelte packages/editor/test/InsurancePage.test.ts
git commit -m "feat(insurance): hide category/provider/endDate columns on narrow viewports"
```

---

### Task 11: Build phases table — hide `progress` at tablet, `count` at mobile

**Files:**
- Modify: `packages/editor/src/lib/components/PhaseSection.svelte:91-98`
- Test: `packages/editor/test/PhaseSection.test.ts`

**Interfaces:**
- Consumes: `Column<T>.hideBelow` (Task 2).

Always visible: `expand`, `name`, `status` (row click toggles expand/collapse, not an edit modal — see survey notes; no actions column). Hidden below 700px: `progress`. Hidden below 480px (in addition): `count`.

- [ ] **Step 1: Write the failing test**

Append to `packages/editor/test/PhaseSection.test.ts` (reuse the existing `doc`/`getHomeId`/`waitTick` fixtures already defined in this file, matching the mount pattern of the existing `"renders one table row per phase"` test):

```ts
  it("marks progress hideBelow tablet and count hideBelow mobile", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }));
    const store = createBuildStore(getHomeId);
    await waitTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(PhaseSection, { target, props: { store, onopentask: vi.fn() } });
    await tick();
    flushSync();

    const headers = target.querySelectorAll("thead th");
    // expand, name, status, count, progress
    expect(headers[4].classList.contains("col-hide-tablet")).toBe(true); // progress
    expect(headers[3].classList.contains("col-hide-mobile")).toBe(true); // count
    expect(headers[1].classList.contains("col-hide-tablet")).toBe(false); // name always visible

    unmount(comp);
    target.remove();
  });
```

Add this `it` inside the existing `describe("PhaseSection", ...)` block, after the existing `"renders one table row per phase"` test.

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -w @myhome/editor -- PhaseSection --run`
Expected: FAIL

- [ ] **Step 3: Add `hideBelow` to the columns**

In `packages/editor/src/lib/components/PhaseSection.svelte`, modify lines 96-97:

```svelte
      { key: "count", label: "", sortable: false, cellClass: "count-cell", cell: countCell, hideBelow: "mobile" },
      { key: "progress", label: "", sortable: false, cellClass: "progress-cell", cell: progressCell, hideBelow: "tablet" },
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npm test -w @myhome/editor -- PhaseSection --run`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/PhaseSection.svelte packages/editor/test/PhaseSection.test.ts
git commit -m "feat(build): hide progress/count columns on narrow viewports"
```

---

### Task 12: Delete dead code — `ChoreListPage.svelte`

**Files:**
- Delete: `packages/editor/src/lib/components/ChoreListPage.svelte`

**Interfaces:**
- None — this component is confirmed unused (superseded by `ChoresPage.svelte` + `SortableTable`, converted in Task 3).

- [ ] **Step 1: Confirm it's unused**

Run: `grep -rn "ChoreListPage" packages/editor/src`
Expected: no output (zero matches — already confirmed during planning research; re-verify before deleting since this repo's code may have changed since).

- [ ] **Step 2: Delete the file**

```bash
git rm packages/editor/src/lib/components/ChoreListPage.svelte
```

- [ ] **Step 3: Verify the build and full test suite still pass**

Run: `npm test -w @myhome/editor -- --run`
Expected: PASS (no test references this file — confirmed during planning, no `ChoreListPage.test.ts` exists)

Run: `npm run build -w @myhome/editor`
Expected: build succeeds (no import references this file, confirmed via the grep above)

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: remove unused ChoreListPage.svelte (superseded by ChoresPage)"
```

---

### Task 13: Real-viewport verification across all 9 modules

**Files:**
- None modified — this is a verification-only task using the `webapp-testing` skill (Playwright), since jsdom (used by the vitest tests in Tasks 2-11) does not execute `@media` queries or compute layout, so the actual hide-at-breakpoint behavior has not yet been checked in a real browser.

**Interfaces:**
- Consumes: all `hideBelow` columns set in Tasks 3-11.

- [ ] **Step 1: Start the app**

Use the `run` skill to start the editor app locally (it already knows how to work around this project's known dev-server quirks — a stray main-repo Vite instance sometimes left on port 5173, and a `PYTHONPATH` gotcha for the backend — documented in prior session memory). Confirm the app is reachable and loads real seeded data (use or create a demo home if the running instance has no data, so tables have enough rows/columns to check).

- [ ] **Step 2: Invoke the `webapp-testing` skill**

For each of these 9 routes — `#/chores`, `#/inventory`, `#/consumables`, `#/works`, `#/costs`, `#/contacts`, `#/properties`, `#/insurance`, `#/build` — drive Playwright to:

1. Set viewport to 768×1024 (tablet) with `hasTouch: true`, navigate to the route.
2. Assert no horizontal overflow: `document.documentElement.scrollWidth <= document.documentElement.clientWidth` evaluates true.
3. Assert the table's primary identifier column (name/title — whichever this module always shows per Tasks 3-11) is visible within the viewport bounds.
4. For Chores and Consumables specifically, assert the actions column (edit/delete buttons) is visible within the viewport bounds without scrolling.
5. Repeat steps 1-4 at 375×667 (mobile) viewport.
6. Take a screenshot at each size for visual confirmation.

- [ ] **Step 3: Fix any real issues found**

If a module still overflows or an action button is unreachable at either size, that means either this plan's `hideBelow` assignment for that module was insufficient (go back and mark an additional column `hideBelow: "tablet"` in that module's task, following the same Step 3/4 pattern as Tasks 3-11) or there's a container-level CSS issue outside `SortableTable` (e.g. a fixed-width ancestor) — diagnose with the systematic-debugging skill if the cause isn't immediately obvious from the DOM/CSS inspection.

- [ ] **Step 4: Commit any follow-up fixes**

If Step 3 required changes, commit them individually per the same pattern as Tasks 3-11 (failing test where practical, or a direct fix + Playwright re-check + commit for CSS-only issues vitest can't exercise).
