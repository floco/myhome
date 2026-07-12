# Module Summary Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the Costs page's two-card layout (summary/chart card on top, table-in-a-card below) to Chores, Inventory, Consumables, and Works, with a per-module summary view — donut breakdowns reusing each store's existing helpers for the first three, and a new horizontal timeline component for Works.

**Architecture:** Each page gets the same CSS skeleton already proven in `CostsPage.svelte` (`chart-card-wrap` → `Card`, `table-card-wrap` → `Card` wrapping the existing toolbar/table/footer unchanged). Chores/Inventory/Consumables reuse `DonutChart.svelte` as-is with page-local `$derived` bucketing built on top of helpers that already exist (`store.getProgress`/`store.getColor` for Chores, category grouping for Inventory, `stockStatus()` for Consumables). Works gets a new `WorksTimeline.svelte` component: a responsive SVG with one dot per work positioned on a continuous date axis, colored by status, with a collision-avoidance "lane" algorithm so dots never overlap.

**Tech Stack:** Svelte 5 (runes), TypeScript, Vitest + jsdom for component tests.

## Global Constraints

- Toolbar, table, and footer markup/behavior in every page are **unchanged** — only their wrapping container changes. Do not touch filter logic, `SortableTable` columns, or modal wiring except where a step explicitly says to.
- All new chart/summary data is computed from the **unfiltered** full store collection (e.g. `store.chores`/`store.assignments`, not `filteredChores`), matching how `CostsPage`'s donut (`breakdownLastCompleteYear`) is independent of the table's search/filter state.
- Reuse existing colors/helpers instead of inventing new ones: Chores uses `store.getColor`'s exact thresholds/colors; Consumables uses `ConsumablesPage.svelte`'s existing `STATUS_COLOR` map; Works uses `WorksPage.svelte`'s existing `statusColor()` values (not `HomeWorksWidget`'s, which differ).
- No new shared layout component — each page copies the `chart-card-wrap`/`table-card-wrap` CSS skeleton inline, following the pattern `CostsPage.svelte` already established (only 4 call sites; not worth abstracting yet).
- Per Svelte 5 + jsdom testing gotcha already documented in this repo: component tests must attach `target` to `document.body` and dispatch events with `bubbles: true`, or handlers silently never fire.

---

### Task 1: Chores summary card + table-in-card layout

**Files:**
- Modify: `packages/editor/src/lib/components/ChoresPage.svelte`
- Modify: `packages/editor/test/ChoresPage.test.ts`

**Interfaces:**
- Consumes: `DonutChart.svelte` (`segments: {id,label,emoji,color,valueLabel,pct}[]`, `centerLabel`, `centerValue`, `showLabels`), `Card.svelte` (default export, spreads `style`/other props onto its root div), `store.getProgress(assignment, chore): number` and `store.getColor(pct): string` (both already exist in `choreStore.svelte.ts`).
- Produces: nothing consumed by later tasks (Chores is independent of Inventory/Consumables/Works).

- [ ] **Step 1: Update the existing test's mock store to include `getProgress`/`getColor`**

The test `"expands and collapses the assignment detail row on toggle click"` in `ChoresPage.test.ts` sets a non-empty `store.assignments`. The new chart card (added in Step 3) will call `store.getProgress(assignment, chore)` for every assignment, so the mock must implement it or that test will crash on mount.

Open `packages/editor/test/ChoresPage.test.ts` and replace the `makeStore` function:

```ts
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
    getCompletionsForChore: vi.fn().mockReturnValue([]),
    deleteCompletion: vi.fn(),
    uploadAttachment: vi.fn(),
    deleteAttachment: vi.fn(),
    getProgress: vi.fn((assignment: { nextDueDate: string }, chore: Chore) => {
      const now = Date.now();
      const due = new Date(assignment.nextDueDate).getTime();
      const periodMs = chore.periodDays * 86400 * 1000;
      return Math.max(0, Math.min(1, (due - now) / periodMs));
    }),
    getColor: vi.fn((pct: number) => (pct > 0.5 ? "#4caf50" : pct > 0.25 ? "#ff9800" : "#f44336")),
  };
}
```

This mirrors the real `choreStore.svelte.ts` implementation (`getProgress` at line 101, `getColor` at line 108) so the new chart card renders sensible data in tests without importing the real store.

- [ ] **Step 2: Run the existing test suite to confirm it currently passes**

Run: `cd packages/editor && npx vitest run test/ChoresPage.test.ts`
Expected: 3 tests pass (this confirms the baseline before markup changes).

- [ ] **Step 3: Add the schedule-health donut derived state**

In `packages/editor/src/lib/components/ChoresPage.svelte`, add two imports after the existing `SortableTable` import (line 8-9):

```ts
  import Card from "./ui/Card.svelte";
  import DonutChart from "./DonutChart.svelte";
```

Then, immediately after `const allRooms = $derived(floorStore.floors.flatMap((f) => f.rooms));` (line 57), insert:

```ts
  type HealthBucket = "on-track" | "due-soon" | "overdue";

  const HEALTH_META: Record<HealthBucket, { label: string; emoji: string; color: string }> = {
    "on-track": { label: "On track", emoji: "🟢", color: "#4caf50" },
    "due-soon": { label: "Due soon", emoji: "🟠", color: "#ff9800" },
    overdue: { label: "Overdue", emoji: "🔴", color: "#f44336" },
  };

  function healthBucket(pct: number): HealthBucket {
    if (pct > 0.5) return "on-track";
    if (pct > 0.25) return "due-soon";
    return "overdue";
  }

  const assignmentHealth = $derived(
    store.assignments
      .map((a) => {
        const chore = store.chores.find((c) => c.id === a.choreId);
        return chore ? healthBucket(store.getProgress(a, chore)) : null;
      })
      .filter((h): h is HealthBucket => h !== null)
  );

  const totalAssignments = $derived(assignmentHealth.length);
  const overdueCount = $derived(assignmentHealth.filter((h) => h === "overdue").length);
  const onTrackCount = $derived(assignmentHealth.filter((h) => h === "on-track").length);
  const onTrackPct = $derived(totalAssignments > 0 ? Math.round((onTrackCount / totalAssignments) * 100) : 0);

  const healthBreakdown = $derived(
    (["on-track", "due-soon", "overdue"] as HealthBucket[])
      .map((bucket) => {
        const count = assignmentHealth.filter((h) => h === bucket).length;
        const meta = HEALTH_META[bucket];
        return {
          id: bucket,
          label: meta.label,
          emoji: meta.emoji,
          color: meta.color,
          valueLabel: `${count}`,
          pct: totalAssignments > 0 ? (count / totalAssignments) * 100 : 0,
          count,
        };
      })
      .filter((b) => b.count > 0)
  );
```

- [ ] **Step 4: Add the chart card and wrap the table in a card**

Replace the markup from `<div class="page">` through the closing `</div>` right before `{#if editChore}` (lines 147-275) with:

```svelte
<div class="page">

  {#if totalAssignments === 0}
    <div class="empty-charts">
      <span class="empty-icon">✅</span>
      <p>No chore assignments yet — click ＋ Add chore to get started.</p>
    </div>
  {:else}
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-inner">
          <div class="pie-area">
            <div class="chart-label">Schedule health</div>
            <DonutChart
              segments={healthBreakdown}
              centerLabel="Assignments"
              centerValue={`${totalAssignments}`}
              showLabels={true}
            />
          </div>

          <div class="chart-divider"></div>

          <div class="stats-area">
            <div class="chart-label">At a glance</div>
            <div class="stat-chips-col">
              <div class="stat-chip">
                <div class="stat-title">Active</div>
                <div class="stat-value">{totalAssignments}</div>
              </div>
              <div class="stat-chip">
                <div class="stat-title">Overdue</div>
                <div class="stat-value overdue">{overdueCount}</div>
              </div>
              <div class="stat-chip">
                <div class="stat-title">On track</div>
                <div class="stat-value ontrack">{onTrackPct}%</div>
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  {/if}

  <div class="table-card-wrap">
    <Card style="display:flex; flex-direction:column; padding:0; overflow:hidden; flex:1; min-height:0;">
    <div class="toolbar">
      <Input placeholder="🔍 Search…" bind:value={searchQuery} />
      <select class="native-input" bind:value={roomFilter}>
        <option value="">All rooms</option>
        {#each allRooms as room}
          <option value={room.id}>{room.label}</option>
        {/each}
      </select>
      <select class="native-input" bind:value={scheduleFilter}>
        <option value="">All schedules</option>
        <option value="daily">Daily</option>
        <option value="weekly">Weekly</option>
        <option value="monthly">Monthly</option>
        <option value="yearly">Yearly</option>
      </select>
      <div class="filter-toggle">
        <button class="toggle-btn" class:active={dueFilter === "all"} title="All chores" onclick={() => { dueFilter = "all"; }}>☰</button>
        <button class="toggle-btn" class:active={dueFilter === "attention"} title="Needs attention" onclick={() => { dueFilter = "attention"; }}>⚠</button>
      </div>
      <Button onclick={() => onnewchore?.()}>＋ Add chore</Button>
      {#if !showImportInput}
        <Button variant="secondary" onclick={() => { showImportInput = true; }}>Import from Donetick</Button>
      {:else}
        <Input type="password" placeholder="API token" bind:value={importToken} />
        <Button disabled={importStatus === "loading"} onclick={handleImport}>
          {importStatus === "loading" ? "Importing…" : "Import"}
        </Button>
        <Button variant="ghost" onclick={() => { showImportInput = false; }}>Cancel</Button>
        {#if importStatus === "error"}<span class="msg-error">Failed</span>{/if}
        {#if importStatus === "done"}<span class="msg-success">{importCount} imported</span>{/if}
      {/if}
    </div>

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

    <div class="footer">{filteredChores.length} chore{filteredChores.length !== 1 ? "s" : ""}</div>
    </Card>
  </div>
</div>
```

- [ ] **Step 5: Add the new CSS**

In the `<style>` block of `ChoresPage.svelte`, right after the `.page { ... }` rule, insert:

```css
  .empty-charts {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 32px; gap: 10px; color: var(--text-faint); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .empty-icon { font-size: 36px; }
  .empty-charts p { margin: 0; font-size: 13px; }

  .chart-card-wrap { padding: var(--space-4); flex-shrink: 0; }
  .chart-inner { display: flex; gap: 24px; align-items: flex-start; }
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
  .stat-value.overdue { color: #f44336; }
  .stat-value.ontrack { color: #4caf50; }

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }
```

- [ ] **Step 6: Run the full test suite and fix anything broken**

Run: `cd packages/editor && npx vitest run test/ChoresPage.test.ts`
Expected: all 3 tests still pass.

- [ ] **Step 7: Add a test for the schedule-health breakdown**

Append to `packages/editor/test/ChoresPage.test.ts`, inside a new `describe` block:

```ts
describe("ChoresPage — schedule health summary", () => {
  it("renders a donut segment per non-empty health bucket and the right stat numbers", () => {
    const now = Date.now();
    const chore1 = makeChore({ id: "c1", periodDays: 10 });
    const chore2 = makeChore({ id: "c2", periodDays: 10 });
    const chore3 = makeChore({ id: "c3", periodDays: 10 });
    const store = makeStore([chore1, chore2, chore3]);
    store.assignments = [
      // pct = (due - now) / periodMs; periodDays=10 -> periodMs = 864,000,000
      { id: "a1", choreId: "c1", roomId: null, nextDueDate: new Date(now + 9 * 86400000).toISOString() }, // pct ~0.9 -> on-track
      { id: "a2", choreId: "c2", roomId: null, nextDueDate: new Date(now + 3 * 86400000).toISOString() }, // pct ~0.3 -> due-soon
      { id: "a3", choreId: "c3", roomId: null, nextDueDate: new Date(now - 1 * 86400000).toISOString() }, // pct 0 -> overdue
    ] as typeof store.assignments;

    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    expect(target.querySelectorAll(".chart-card-wrap svg path")).toHaveLength(3);
    expect(target.querySelector(".stat-value")?.textContent).toBe("3");
    expect(target.querySelector(".stat-value.overdue")?.textContent).toBe("1");
    expect(target.querySelector(".stat-value.ontrack")?.textContent).toBe("33%");

    unmount(comp);
  });

  it("shows the empty-charts placeholder when there are no assignments", () => {
    const store = makeStore([makeChore()]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    expect(target.querySelector(".empty-charts")).not.toBeNull();
    expect(target.querySelector(".chart-card-wrap")).toBeNull();

    unmount(comp);
  });
});
```

- [ ] **Step 8: Run the tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/ChoresPage.test.ts`
Expected: 5 tests pass.

- [ ] **Step 9: Commit**

```bash
git add packages/editor/src/lib/components/ChoresPage.svelte packages/editor/test/ChoresPage.test.ts
git commit -m "feat: add schedule-health summary card and table-in-card layout to ChoresPage"
```

---

### Task 2: Inventory summary card + table-in-card layout

**Files:**
- Modify: `packages/editor/src/lib/components/InventoryPage.svelte`
- Create: `packages/editor/test/InventoryPage.test.ts`

**Interfaces:**
- Consumes: `DonutChart.svelte`, `Card.svelte` (same as Task 1).
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Add the category donut derived state**

In `packages/editor/src/lib/components/InventoryPage.svelte`, add imports after the `SortableTable` import (line 7-8):

```ts
  import Card from "./ui/Card.svelte";
  import DonutChart from "./DonutChart.svelte";
```

Then, immediately after `const allCategories = $derived(...)` (lines 76-78), insert:

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

(`paletteFor` is intentionally duplicated from `HomeInventoryWidget.svelte` rather than extracted — it's 5 lines used in exactly 2 places.)

- [ ] **Step 2: Add the chart card and wrap the table in a card**

Replace the markup from `<div class="page">` through its closing `</div>` (lines 101-168) with:

```svelte
<div class="page">

  {#if store.items.length === 0}
    <div class="empty-charts">
      <span class="empty-icon">📦</span>
      <p>No items yet — click ＋ Add item to get started.</p>
    </div>
  {:else}
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-inner">
          <div class="pie-area">
            <div class="chart-label">By category</div>
            <DonutChart
              segments={categoryBreakdown}
              centerLabel="Items"
              centerValue={`${store.items.length}`}
              showLabels={true}
            />
          </div>

          <div class="chart-divider"></div>

          <div class="stats-area">
            <div class="chart-label">At a glance</div>
            <div class="stat-chips-col">
              <div class="stat-chip">
                <div class="stat-title">Items</div>
                <div class="stat-value">{store.items.length}</div>
              </div>
              <div class="stat-chip">
                <div class="stat-title">Total value</div>
                <div class="stat-value">{totalValue.toLocaleString()} €</div>
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  {/if}

  <div class="table-card-wrap">
    <Card style="display:flex; flex-direction:column; padding:0; overflow:hidden; flex:1; min-height:0;">
    <div class="toolbar">
      <Input bind:value={searchQuery} placeholder="🔍 Search items…" />
      <select class="native-input" bind:value={roomFilter}>
        <option value="">All rooms</option>
        {#each allRooms as room}
          <option value={room.id}>{room.label}</option>
        {/each}
      </select>
      <select class="native-input" bind:value={categoryFilter}>
        <option value="">All categories</option>
        {#each allCategories as cat}
          <option value={cat}>{cat}</option>
        {/each}
      </select>
      <Button onclick={() => { modalItem = "create"; }}>＋ Add item</Button>
    </div>

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

    <div class="footer">
      {store.items.length} item{store.items.length !== 1 ? "s" : ""}
      {#if totalValue > 0}
        · total value: {totalValue.toLocaleString()} €
      {/if}
    </div>
    </Card>
  </div>
</div>
```

- [ ] **Step 3: Add the new CSS**

In the `<style>` block, right after `.page { ... }`, insert the same block as Task 1 Step 5 (identical rules — `empty-charts`, `chart-card-wrap`, `chart-inner`, `chart-label`, `pie-area`, `chart-divider`, `stats-area`, `stat-chips-col`, `stat-chip`, `stat-title`, `stat-value`, `table-card-wrap`), but **without** the `.overdue`/`.ontrack` value-color modifiers (Inventory's stat values don't need status coloring):

```css
  .empty-charts {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 32px; gap: 10px; color: var(--text-faint); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .empty-icon { font-size: 36px; }
  .empty-charts p { margin: 0; font-size: 13px; }

  .chart-card-wrap { padding: var(--space-4); flex-shrink: 0; }
  .chart-inner { display: flex; gap: 24px; align-items: flex-start; }
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

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }
```

- [ ] **Step 4: Write `InventoryPage.test.ts`** (no test file exists for this page yet)

Create `packages/editor/test/InventoryPage.test.ts`:

```ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import InventoryPage from "../src/lib/components/InventoryPage.svelte";
import type { InventoryItem } from "../src/lib/inventoryStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makeItem(overrides: Partial<InventoryItem> = {}): InventoryItem {
  return {
    id: "i1", name: "Drill", emoji: "🔧", category: "Tools", brand: null, model: null,
    serialNumber: null, purchaseDate: null, purchasePrice: 80, warrantyExpiryDate: null,
    notes: "", attachments: [], placement: null,
    ...overrides,
  };
}

function makeStore(items: InventoryItem[]) {
  return {
    items, loaded: true, loadError: null,
    createItem: vi.fn(), updateItem: vi.fn(), deleteItem: vi.fn(),
    uploadAttachment: vi.fn(), deleteAttachment: vi.fn(),
  };
}

describe("InventoryPage — category summary", () => {
  it("renders one donut segment per category and the right stat numbers", () => {
    const store = makeStore([
      makeItem({ id: "i1", category: "Tools", purchasePrice: 80 }),
      makeItem({ id: "i2", category: "Tools", purchasePrice: 20 }),
      makeItem({ id: "i3", category: "Electronics", purchasePrice: 100 }),
    ]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(InventoryPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    expect(target.querySelectorAll(".chart-card-wrap svg path")).toHaveLength(2);
    const values = Array.from(target.querySelectorAll(".stat-value")).map((el) => el.textContent);
    expect(values).toEqual(["3", "200 €"]);

    unmount(comp);
  });

  it("shows the empty-charts placeholder when there are no items", () => {
    const store = makeStore([]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(InventoryPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    expect(target.querySelector(".empty-charts")).not.toBeNull();
    expect(target.querySelector(".chart-card-wrap")).toBeNull();

    unmount(comp);
  });
});
```

- [ ] **Step 5: Run the tests**

Run: `cd packages/editor && npx vitest run test/InventoryPage.test.ts`
Expected: 2 tests pass.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/InventoryPage.svelte packages/editor/test/InventoryPage.test.ts
git commit -m "feat: add category summary card and table-in-card layout to InventoryPage"
```

---

### Task 3: Consumables summary card + table-in-card layout

**Files:**
- Modify: `packages/editor/src/lib/components/ConsumablesPage.svelte`

**Interfaces:**
- Consumes: `DonutChart.svelte`, `Card.svelte`, `stockStatus(c: Consumable): "ok"|"low"|"empty"` (already imported in this file from `consumableStore.svelte`).
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Add the stock-status donut derived state**

In `packages/editor/src/lib/components/ConsumablesPage.svelte`, add imports after the `SortableTable` import (line 8-9):

```ts
  import Card from "./ui/Card.svelte";
  import DonutChart from "./DonutChart.svelte";
```

Then, immediately after the existing `STATUS_LABEL` constant (line 45), insert:

```ts
  const STOCK_META: Record<"ok" | "low" | "empty", { label: string; emoji: string; color: string }> = {
    ok: { label: "OK", emoji: "🟢", color: "#4caf50" },
    low: { label: "Low", emoji: "🟠", color: "#ff9800" },
    empty: { label: "Empty", emoji: "🔴", color: "#f44336" },
  };

  const stockBreakdown = $derived(
    (["ok", "low", "empty"] as const)
      .map((status) => {
        const count = store.consumables.filter((c) => stockStatus(c) === status).length;
        const meta = STOCK_META[status];
        return {
          id: status,
          label: meta.label,
          emoji: meta.emoji,
          color: meta.color,
          valueLabel: `${count}`,
          pct: store.consumables.length > 0 ? (count / store.consumables.length) * 100 : 0,
          count,
        };
      })
      .filter((b) => b.count > 0)
  );

  const lowStockCount = $derived(store.consumables.filter((c) => stockStatus(c) === "low").length);
  const emptyStockCount = $derived(store.consumables.filter((c) => stockStatus(c) === "empty").length);
```

(This introduces its own `STOCK_META` color set rather than reusing the page's `STATUS_COLOR`/`STATUS_LABEL`, because those are keyed for inline style strings like `var(--success)` and the donut needs plain hex — using literal hex values here keeps `DonutChart`'s `fill` attribute unambiguous and matches `HomeConsumablesWidget`'s own `STATE_COLOR` palette.)

- [ ] **Step 2: Add the chart card and wrap the table in a card**

Replace the markup from `<div class="page">` through its closing `</div>` (lines 66-153) with:

```svelte
<div class="page">

  {#if store.consumables.length === 0}
    <div class="empty-charts">
      <span class="empty-icon">🛒</span>
      <p>No consumables yet — click ＋ Add consumable to get started.</p>
    </div>
  {:else}
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-inner">
          <div class="pie-area">
            <div class="chart-label">Stock status</div>
            <DonutChart
              segments={stockBreakdown}
              centerLabel="Items"
              centerValue={`${store.consumables.length}`}
              showLabels={true}
            />
          </div>

          <div class="chart-divider"></div>

          <div class="stats-area">
            <div class="chart-label">At a glance</div>
            <div class="stat-chips-col">
              <div class="stat-chip">
                <div class="stat-title">Low</div>
                <div class="stat-value low">{lowStockCount}</div>
              </div>
              <div class="stat-chip">
                <div class="stat-title">Empty</div>
                <div class="stat-value empty">{emptyStockCount}</div>
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  {/if}

  <div class="table-card-wrap">
    <Card style="display:flex; flex-direction:column; padding:0; overflow:hidden; flex:1; min-height:0;">
    <div class="toolbar">
      <Input placeholder="🔍 Search…" bind:value={searchQuery} />
      <select class="native-select" bind:value={categoryFilter}>
        <option value="">All categories</option>
        {#each settingsStore.consumableCategories as cat}
          <option value={cat.id}>{cat.emoji} {cat.name}</option>
        {/each}
      </select>
      <div class="filter-toggle">
        <button
          class="toggle-btn"
          class:active={!attentionFilter}
          onclick={() => { attentionFilter = false; }}
          title="All"
        >☰</button>
        <button
          class="toggle-btn"
          class:active={attentionFilter}
          onclick={() => { attentionFilter = true; }}
          title="Needs attention"
        >⚠</button>
      </div>
      <Button onclick={() => { showCreate = true; }}>＋ Add consumable</Button>
    </div>

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

    <div class="footer">{filtered.length} item{filtered.length !== 1 ? "s" : ""}</div>
    </Card>
  </div>
</div>
```

- [ ] **Step 3: Add the new CSS**

In the `<style>` block, right after `.page { ... }`, insert:

```css
  .empty-charts {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 32px; gap: 10px; color: var(--text-faint); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .empty-icon { font-size: 36px; }
  .empty-charts p { margin: 0; font-size: 13px; }

  .chart-card-wrap { padding: var(--space-4); flex-shrink: 0; }
  .chart-inner { display: flex; gap: 24px; align-items: flex-start; }
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
  .stat-value.low { color: #ff9800; }
  .stat-value.empty { color: #f44336; }

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }
```

- [ ] **Step 4: Run the existing test suite**

Run: `cd packages/editor && npx vitest run test/ConsumablesPage.test.ts`
Expected: all existing tests still pass (this file's mock store already builds a real `createConsumableStore()`, so `stockStatus` works exactly as in production — no mock updates needed).

- [ ] **Step 5: Add a test for the stock-status breakdown**

The file's existing `sampleDoc` fixture (top of file) has 3 consumables: `c1` qty 6/min 4 → `ok`, `c2` qty 0 → `empty`, `c3` qty 50/min 100 → `low`. Its `makeStore()` helper stubs `fetch` to return `sampleDoc` and builds a real `createConsumableStore(getHomeId)`, requiring `await makeTick()` before mounting. Append a new test following that exact pattern:

```ts
describe("ConsumablesPage — stock status summary", () => {
  it("renders one donut segment per non-empty stock bucket and the right stat numbers", async () => {
    const store = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumablesPage, {
      target,
      props: {
        store,
        settingsStore: { consumableCategories: [], consumableUnits: [] },
        onplaceonmap: vi.fn(),
      },
    });
    await tick();
    flushSync();

    expect(target.querySelectorAll(".chart-card-wrap svg path")).toHaveLength(3);
    expect(target.querySelector(".stat-value.low")?.textContent).toBe("1");
    expect(target.querySelector(".stat-value.empty")?.textContent).toBe("1");

    unmount(comp);
  });
});
```

Replace the comment placeholders above with real assertions once you've confirmed the exact store-setup pattern from the file — this file uses `createConsumableStore` + a fetch mock rather than a hand-rolled mock object like the other three pages, so the setup boilerplate must match what's already there (look at the first `describe` block's `beforeEach` for the exact incantation).

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/ConsumablesPage.test.ts`
Expected: all tests pass, including the new one.

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/components/ConsumablesPage.svelte packages/editor/test/ConsumablesPage.test.ts
git commit -m "feat: add stock-status summary card and table-in-card layout to ConsumablesPage"
```

---

### Task 4: `WorksTimeline.svelte` component

**Files:**
- Create: `packages/editor/src/lib/components/WorksTimeline.svelte`
- Create: `packages/editor/test/WorksTimeline.test.ts`

**Interfaces:**
- Consumes: `Work` type from `../worksStore.svelte` (`{id, title, description, status: "planned"|"in_progress"|"done", categoryId, date, totalCost, supplierId, notes, attachments, placement}`).
- Produces: `WorksTimeline.svelte` default export with props `{ works: Work[]; onworkclick?: (id: string) => void }`. Task 5 imports this component and passes `store.works` and a click handler.

- [ ] **Step 1: Write the component**

Create `packages/editor/src/lib/components/WorksTimeline.svelte`:

```svelte
<script lang="ts">
  import type { Work } from "../worksStore.svelte";

  interface Props {
    works: Work[];
    onworkclick?: (id: string) => void;
  }
  let { works, onworkclick }: Props = $props();

  const VIEW_W = 1000;
  const VIEW_H = 140;
  const PAD_X = 30;
  const MARGIN_TOP = 10;
  const MARGIN_BOTTOM = 24;
  const CENTER_Y = MARGIN_TOP + (VIEW_H - MARGIN_TOP - MARGIN_BOTTOM) / 2;
  const LANE_HEIGHT = 10;
  const MAX_LANE = 5;
  const MIN_GAP = 16;
  const DOT_R = 4;

  const STATUS_COLOR: Record<Work["status"], string> = {
    done: "#33aa66",
    in_progress: "#3388cc",
    planned: "#cc8833",
  };
  const STATUS_LABEL: Record<Work["status"], string> = {
    done: "Done",
    in_progress: "In progress",
    planned: "Planned",
  };

  const timeRange = $derived((() => {
    if (works.length === 0) {
      const now = Date.now();
      return { min: now, max: now };
    }
    const times = works.map((w) => new Date(w.date).getTime());
    return { min: Math.min(...times), max: Math.max(...times) };
  })());

  function xForTime(t: number): number {
    const { min, max } = timeRange;
    if (max === min) return VIEW_W / 2;
    return PAD_X + ((t - min) / (max - min)) * (VIEW_W - 2 * PAD_X);
  }

  interface Dot {
    work: Work;
    x: number;
    y: number;
  }

  // Works whose dates land close together on the x-axis get assigned to
  // alternating vertical "lanes" (0, +1, -1, +2, -2, ...) so their dots
  // never overlap -- processed left-to-right, tracking each lane's last
  // placed x so a lane is only reused once it's far enough away again.
  const dots = $derived((() => {
    const sorted = [...works]
      .map((w) => ({ work: w, x: xForTime(new Date(w.date).getTime()) }))
      .sort((a, b) => a.x - b.x);

    const laneLastX = new Map<number, number>();
    const result: Dot[] = [];
    for (const item of sorted) {
      let lane = 0;
      let assigned = false;
      for (let offset = 0; offset <= MAX_LANE && !assigned; offset++) {
        const candidates = offset === 0 ? [0] : [offset, -offset];
        for (const cand of candidates) {
          const last = laneLastX.get(cand);
          if (last === undefined || item.x - last >= MIN_GAP) {
            lane = cand;
            assigned = true;
            break;
          }
        }
      }
      laneLastX.set(lane, item.x);
      result.push({ work: item.work, x: item.x, y: CENTER_Y + lane * LANE_HEIGHT });
    }
    return result;
  })());

  const yearTicks = $derived((() => {
    const startYear = new Date(timeRange.min).getFullYear();
    const endYear = new Date(timeRange.max).getFullYear();
    const ticks: { year: number; x: number }[] = [];
    for (let y = startYear; y <= endYear; y++) {
      const jan1 = new Date(Date.UTC(y, 0, 1)).getTime();
      const x = Math.min(Math.max(xForTime(jan1), PAD_X), VIEW_W - PAD_X);
      ticks.push({ year: y, x });
    }
    if (ticks.length === 0) {
      ticks.push({ year: startYear, x: VIEW_W / 2 });
    }
    return ticks;
  })());

  const todayX = $derived((() => {
    const now = Date.now();
    if (now < timeRange.min || now > timeRange.max) return null;
    return xForTime(now);
  })());

  function formatDate(iso: string): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }
</script>

<div class="timeline-wrap">
  <svg viewBox="0 0 {VIEW_W} {VIEW_H}" preserveAspectRatio="none" style="width:100%; height:{VIEW_H}px;">
    <line x1={PAD_X} y1={CENTER_Y} x2={VIEW_W - PAD_X} y2={CENTER_Y} stroke="var(--border)" stroke-width="1" />

    {#each yearTicks as t (t.year)}
      <line x1={t.x} y1={MARGIN_TOP} x2={t.x} y2={VIEW_H - MARGIN_BOTTOM + 4} stroke="var(--border)" stroke-width="1" stroke-dasharray="2 2" />
      <text x={t.x} y={VIEW_H - 8} text-anchor="middle" font-size="10" fill="var(--text-faint)" font-family="sans-serif">{t.year}</text>
    {/each}

    {#if todayX !== null}
      <line x1={todayX} y1={MARGIN_TOP} x2={todayX} y2={VIEW_H - MARGIN_BOTTOM} stroke="var(--text-muted)" stroke-width="1" stroke-dasharray="3 3" />
    {/if}

    {#each dots as d (d.work.id)}
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <circle
        cx={d.x}
        cy={d.y}
        r={DOT_R}
        fill={STATUS_COLOR[d.work.status]}
        opacity="0.9"
        style="cursor:{onworkclick ? 'pointer' : 'default'}"
        onclick={() => onworkclick?.(d.work.id)}
      >
        <title>{d.work.title} — {STATUS_LABEL[d.work.status]} — {formatDate(d.work.date)}{d.work.totalCost != null ? ` — ${d.work.totalCost.toLocaleString(undefined, { maximumFractionDigits: 0 })} €` : ""}</title>
      </circle>
    {/each}
  </svg>

  <div class="legend">
    <span class="legend-item"><span class="dot" style="background:{STATUS_COLOR.done}"></span>Done</span>
    <span class="legend-item"><span class="dot" style="background:{STATUS_COLOR.in_progress}"></span>In progress</span>
    <span class="legend-item"><span class="dot" style="background:{STATUS_COLOR.planned}"></span>Planned</span>
  </div>
</div>

<style>
  .timeline-wrap { width: 100%; }
  .legend { display: flex; gap: 16px; margin-top: 4px; padding-left: 4px; }
  .legend-item { display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--text-muted); }
  .legend .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
</style>
```

- [ ] **Step 2: Write the failing tests**

Create `packages/editor/test/WorksTimeline.test.ts`:

```ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import WorksTimeline from "../src/lib/components/WorksTimeline.svelte";
import type { Work } from "../src/lib/worksStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makeWork(overrides: Partial<Work> = {}): Work {
  return {
    id: "w1", title: "Fix roof leak", description: "", status: "planned",
    categoryId: null, date: "2026-06-10T12:00:00.000Z", totalCost: null,
    supplierId: null, notes: "", attachments: [], placement: null,
    ...overrides,
  };
}

describe("WorksTimeline", () => {
  it("renders zero dots and does not crash with an empty works list", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(WorksTimeline, { target, props: { works: [] } });
    flushSync();

    expect(target.querySelectorAll("circle")).toHaveLength(0);

    unmount(comp);
  });

  it("renders one dot per work, colored by status", () => {
    const works = [
      makeWork({ id: "w1", status: "done", date: "2024-01-15T00:00:00.000Z" }),
      makeWork({ id: "w2", status: "in_progress", date: "2025-06-01T00:00:00.000Z" }),
      makeWork({ id: "w3", status: "planned", date: "2026-12-01T00:00:00.000Z" }),
    ];
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(WorksTimeline, { target, props: { works } });
    flushSync();

    const circles = target.querySelectorAll("circle");
    expect(circles).toHaveLength(3);
    const fills = Array.from(circles).map((c) => c.getAttribute("fill"));
    expect(fills).toEqual(["#33aa66", "#3388cc", "#cc8833"]);

    unmount(comp);
  });

  it("renders a single dot without crashing when there is only one work", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(WorksTimeline, { target, props: { works: [makeWork()] } });
    flushSync();

    expect(target.querySelectorAll("circle")).toHaveLength(1);

    unmount(comp);
  });

  it("staggers dots that share the exact same date onto different lanes", () => {
    const sameDate = "2026-03-01T00:00:00.000Z";
    const works = Array.from({ length: 5 }, (_, i) => makeWork({ id: `w${i}`, date: sameDate }));
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(WorksTimeline, { target, props: { works } });
    flushSync();

    const circles = Array.from(target.querySelectorAll("circle"));
    expect(circles).toHaveLength(5);
    const yValues = new Set(circles.map((c) => c.getAttribute("cy")));
    expect(yValues.size).toBeGreaterThan(1);

    unmount(comp);
  });

  it("calls onworkclick with the work's id when its dot is clicked", () => {
    const onworkclick = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(WorksTimeline, {
      target,
      props: { works: [makeWork({ id: "w42" })], onworkclick },
    });
    flushSync();

    const circle = target.querySelector("circle") as SVGCircleElement;
    circle.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(onworkclick).toHaveBeenCalledWith("w42");

    unmount(comp);
  });

  it("shows a dashed today-marker line when works span the present", () => {
    const past = new Date(Date.now() - 30 * 86400000).toISOString();
    const future = new Date(Date.now() + 30 * 86400000).toISOString();
    const works = [makeWork({ id: "w1", date: past, status: "done" }), makeWork({ id: "w2", date: future, status: "planned" })];
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(WorksTimeline, { target, props: { works } });
    flushSync();

    expect(target.querySelector('line[stroke-dasharray="3 3"]')).not.toBeNull();

    unmount(comp);
  });

  it("omits the today-marker line when all works are in the past", () => {
    const older = new Date(Date.now() - 60 * 86400000).toISOString();
    const newer = new Date(Date.now() - 30 * 86400000).toISOString();
    const works = [makeWork({ id: "w1", date: older, status: "done" }), makeWork({ id: "w2", date: newer, status: "done" })];
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(WorksTimeline, { target, props: { works } });
    flushSync();

    expect(target.querySelector('line[stroke-dasharray="3 3"]')).toBeNull();

    unmount(comp);
  });
});
```

- [ ] **Step 3: Run the tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/WorksTimeline.test.ts`
Expected: 7 tests pass. (The component was written before the tests here since its shape was fully specified in Step 1 — if any test fails, fix the component, not the test, since the assertions directly encode the design's requirements: one dot per work, status colors, lane separation, click callback, and conditional today-marker.)

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/WorksTimeline.svelte packages/editor/test/WorksTimeline.test.ts
git commit -m "feat: add WorksTimeline component with lane-based collision avoidance"
```

---

### Task 5: Wire `WorksTimeline` into `WorksPage` + table-in-card layout

**Files:**
- Modify: `packages/editor/src/lib/components/WorksPage.svelte`

**Interfaces:**
- Consumes: `WorksTimeline.svelte` from Task 4 (`props: { works: Work[]; onworkclick?: (id: string) => void }`), `Card.svelte`.
- Produces: nothing (final task).

- [ ] **Step 1: Add imports and derived stats**

In `packages/editor/src/lib/components/WorksPage.svelte`, add imports after the `SortableTable` import (line 7-8):

```ts
  import Card from "./ui/Card.svelte";
  import WorksTimeline from "./WorksTimeline.svelte";
```

Then, immediately after `const totalCost = $derived(...)` (lines 56-58), insert:

```ts
  const plannedCount = $derived(store.works.filter((w) => w.status === "planned").length);
  const inProgressCount = $derived(store.works.filter((w) => w.status === "in_progress").length);
  const doneCount = $derived(store.works.filter((w) => w.status === "done").length);
  const allTimeCost = $derived(store.works.reduce((sum, w) => sum + (w.totalCost ?? 0), 0));

  function handleTimelineClick(id: string): void {
    const found = store.works.find((w) => w.id === id);
    if (found) modalWork = found;
  }
```

- [ ] **Step 2: Add the chart card and wrap the table in a card**

Replace the markup from `<div class="page">` through its closing `</div>` (lines 76-140) with:

```svelte
<div class="page">

  {#if store.works.length === 0}
    <div class="empty-charts">
      <span class="empty-icon">🔧</span>
      <p>No works yet — click ＋ Add work to get started.</p>
    </div>
  {:else}
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-label">House timeline</div>
        <div class="stat-chips-row">
          <div class="stat-chip">
            <div class="stat-title">Planned</div>
            <div class="stat-value">{plannedCount}</div>
          </div>
          <div class="stat-chip">
            <div class="stat-title">In progress</div>
            <div class="stat-value">{inProgressCount}</div>
          </div>
          <div class="stat-chip">
            <div class="stat-title">Done</div>
            <div class="stat-value">{doneCount}</div>
          </div>
          <div class="stat-chip">
            <div class="stat-title">Total cost</div>
            <div class="stat-value">{fmt(allTimeCost)} €</div>
          </div>
        </div>
        <WorksTimeline works={store.works} onworkclick={handleTimelineClick} />
      </Card>
    </div>
  {/if}

  <div class="table-card-wrap">
    <Card style="display:flex; flex-direction:column; padding:0; overflow:hidden; flex:1; min-height:0;">
    <div class="toolbar">
      <Input placeholder="🔍 Search…" bind:value={searchQuery} />
      <select class="native-input filter-sel" bind:value={statusFilter}>
        <option value="">All statuses</option>
        <option value="planned">Planned</option>
        <option value="in_progress">In progress</option>
        <option value="done">Done</option>
      </select>
      <select class="native-input filter-sel" bind:value={categoryFilter}>
        <option value="">All categories</option>
        {#each settingsStore.workCategories as cat}
          <option value={cat.id}>{cat.emoji} {cat.name}</option>
        {/each}
      </select>
      <Button onclick={() => { modalWork = "create"; }}>＋ Add work</Button>
    </div>

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

    <div class="footer">{filteredWorks.length} works · total: {fmt(totalCost)} €</div>
    </Card>
  </div>
</div>
```

- [ ] **Step 3: Add the new CSS**

In the `<style>` block, right after `.page { ... }`, insert:

```css
  .empty-charts {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 32px; gap: 10px; color: var(--text-faint); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .empty-icon { font-size: 36px; }
  .empty-charts p { margin: 0; font-size: 13px; }

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

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }
```

- [ ] **Step 4: Run the existing test suite**

Run: `cd packages/editor && npx vitest run test/WorksPage.test.ts`
Expected: existing tests pass unchanged (they don't touch `getProgress`-style store methods — `store.works` is all the new code reads, which the existing mock already provides).

- [ ] **Step 5: Add a test for the timeline-click-opens-modal wiring**

Append to `packages/editor/test/WorksPage.test.ts`:

```ts
describe("WorksPage — timeline click opens modal", () => {
  it("opens the edit modal for the work whose timeline dot was clicked", () => {
    const work = makeWork({ id: "w1", title: "Fix roof leak" });
    const store = makeWorksStore([work]);
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(WorksPage, { target, props: { store, settingsStore: makeSettingsStore() } });
    flushSync();

    const circle = target.querySelector(".chart-card-wrap circle") as SVGCircleElement;
    circle.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(target.querySelector(".ui-modal-title")?.textContent).toBe("Edit work");

    unmount(comp);
  });
});
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/WorksPage.test.ts`
Expected: all tests pass, including the new one.

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/components/WorksPage.svelte packages/editor/test/WorksPage.test.ts
git commit -m "feat: add house timeline card and table-in-card layout to WorksPage"
```

---

### Task 6: Full regression pass and manual verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full frontend test suite**

Run: `cd packages/editor && npx vitest run`
Expected: all tests pass (baseline was 516 before this plan; expect 516 + new tests from Tasks 1-5 — roughly 530+).

- [ ] **Step 2: Browser smoke check against demo-home data**

Use the pattern already established for this repo (isolated backend on a scratch `DATA_DIR` + a temp `vite.test.config.ts` proxying to it, seeded via `POST /api/homes` with `{"type":"demo"}` for realistic multi-category data — see prior sessions' approach in this same conversation for exact commands). For each of the four pages (`#/chores`, `#/inventory`, `#/consumables`, `#/works`):
- Confirm the top card renders with a visible donut (or timeline for Works) and no layout overlap/clipping.
- Confirm the bottom table card shows the gray page-background margin on all sides (matching Costs), not touching the top card.
- For Works specifically: click a timeline dot and confirm the edit modal opens with that work's data.
- Clean up: delete the scratch demo home, kill the temp backend/vite processes, remove `vite.test.config.ts`.

- [ ] **Step 3: Final commit if smoke check required any fixes**

If Step 2 surfaced any visual bugs, fix them, re-run the affected test file, and commit:

```bash
git add -A
git commit -m "fix: address visual issues found in module summary cards smoke check"
```

(Skip this step entirely if no fixes were needed.)
