# Visual Redesign Phase 4 (Pages) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the 7 top-level page-body components (`InventoryPage`, `ChoresPage`, `ChoreListPage`, `CostsPage`, `WorksPage`, `SettingsPage`, `ConsumablesPage`) from their original hardcoded-dark-theme styling onto the shared design-token system and Phase 1 UI components (`Card`, `Button`, `Input`, theme tokens from `theme.css`), per Phase 4 of the approved Spec 6 design doc (`docs/superpowers/specs/2026-06-22-visual-redesign-design.md`, line 130-131).

**Architecture:**
This is a pure visual/markup migration — no data models, stores, props, or business logic change. Each task fully replaces one `.svelte` file's `<script>` (unchanged), markup (selectively swapped onto shared components), and `<style>` block (hardcoded hex values replaced with `var(--token)` references). Three rules apply consistently across all 7 tasks:

1. **Chrome vs. data/status color.** Per the design doc's stated principle ("color reserved for data/status rather than chrome"), per-item semantic indicators — `InventoryPage`'s `warrantyChip()`, `WorksPage`'s `statusColor()`, `CostsPage`'s `cat.color` (user-configurable category swatch/pie-slice fill), `ChoreListPage`'s `store.getColor(pct)` — are **left exactly as they are today**. Only chrome (page backgrounds, borders, table/list styling, buttons, inputs, neutral text) migrates to tokens. The one exception: `CostsPage`'s 10-year bar chart's *emphasis* colors (`.bar.highlight`, `.bar-label.current-label`) are chrome (not user data), so those become `var(--accent)`; the YoY up/down indicator cleanly maps onto the existing `--danger`/`--success` semantic tokens, so that one also converts.
2. **Component fit, not forced adoption.** A native element converts to a shared UI component only when the component's narrow API (see `Button`/`Input`/`Card` props below) actually covers the need. Search boxes and plain single-line text fields become `<Input>`. Primary text-labeled action buttons (`+Add X`, `Save`, `Cancel`, `Import`) become `<Button>` with the appropriate variant. Static list/card items with no per-item dynamic styling or click handlers (e.g. `ChoresPage`'s per-chore card, `SettingsPage`'s 4 sections) become `<Card>`. Dense rows of small icon-only affordances (table-row edit/delete icons, per-instance ✓/✕ controls, multi-button chore-card action rows) and inputs needing attributes `<Input>` doesn't expose (`maxlength`, `type="color"`, `type="number"`, `type="checkbox"`) stay native HTML, restyled with tokens — this mirrors the precedent already established in Phase 3's modals.
3. **`+Add X` buttons are always `<Button>` (default `primary` variant).** Delete/destructive single-row icon buttons keep their existing native icon-button treatment (no Button component — they're too small/dense for Button's pill padding) but use `var(--danger)` for their hover/active state instead of a hardcoded hex.

**Tech Stack:** Svelte 5 (runes), TypeScript, Vitest, existing `packages/editor/src/lib/components/ui/{Button,Input,Card}.svelte` from Phase 1, theme tokens from `packages/editor/src/lib/theme.css`.

---

## Shared component APIs used in this plan (for reference, no changes needed)

```ts
// Button.svelte — variant defaults to "primary"
interface Props {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  onclick?: () => void;
  disabled?: boolean;
  title?: string;
  children?: Snippet;
}

// Input.svelte — single-line input only, bindable value
interface Props {
  value?: string;       // $bindable("")
  placeholder?: string;
  type?: string;
}

// Card.svelte — plain surface wrapper, no extra props
interface Props {
  children?: Snippet;
}
```

### Task 1: ConsumablesPage (stub)

**Files:**
- Modify: `packages/editor/src/lib/components/ConsumablesPage.svelte`

This is a placeholder "Coming soon" stub with no script logic — the simplest task, good for validating the workflow before tackling the larger pages. The only bug today is that `.stub` has no explicit background, so it visually blends into whatever the app shell behind it is (this is why the user described it as already looking "light" — it was never actually migrated, it just had no hardcoded background to begin with). This task makes that implicit behavior explicit and replaces the remaining 4 hardcoded colors with tokens.

- [ ] **Step 1: Replace the entire file content**

```svelte
<div class="stub">
  <span class="stub-icon">🛒</span>
  <h2>Consumables</h2>
  <p>Monitor stock levels for everyday supplies — cleaning products, food staples, and household essentials.</p>
  <p class="coming-soon">Coming soon</p>
</div>

<style>
  .stub {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    height: 100%; gap: 12px; color: var(--text-muted); font-family: var(--font-sans);
  }
  .stub-icon { font-size: 56px; line-height: 1; }
  h2 { margin: 0; font-size: 22px; color: var(--text); font-weight: 600; }
  p { margin: 0; font-size: 14px; max-width: 320px; text-align: center; line-height: 1.6; color: var(--text-muted); }
  .coming-soon {
    margin-top: 8px; padding: 4px 14px; border-radius: var(--radius-pill);
    background: var(--surface-alt); color: var(--text-faint); font-size: 11px; text-transform: uppercase;
    letter-spacing: 0.1em;
  }
</style>
```

- [ ] **Step 2: Run the full test suite**

Run: `cd packages/editor && npm test -- --run`
Expected: 162/162 passing (no test imports this component directly; this guards against regressions elsewhere).

- [ ] **Step 3: Manually sanity-check in the browser**

Run `npm run dev` in `packages/editor`, open the route for this page, and toggle the theme switcher between light and dark. Confirm: no leftover hardcoded-dark rectangles, search/select/buttons are legible and themed in both modes, and clicking through to any modal still opens correctly.

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/ConsumablesPage.svelte
git commit -m "feat(editor): migrate ConsumablesPage.svelte onto Card/Button/Input/tokens"
```

---

### Task 2: WorksPage

**Files:**
- Modify: `packages/editor/src/lib/components/WorksPage.svelte`

Per Architecture rule 1, `statusColor()` is data/status (one of 3 fixed semantic states with no clean 1:1 mapping onto the existing `--success`/`--danger`/`--warning` tokens, since "in progress" has no semantic token) — it is **not modified**, and neither is the `.status-chip" inline style attribute that consumes it. Only `.page`, `.toolbar`, `.card` chrome, and text colors change.

- [ ] **Step 1: Replace the entire file content**

```svelte
<script lang="ts">
  import type { createWorksStore, Work } from "../worksStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import WorkModal from "./WorkModal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";

  type WorksStore = ReturnType<typeof createWorksStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    store: WorksStore;
    settingsStore: SettingsStore;
    onplaceonmap?: (workId: string) => void;
  }

  let { store, settingsStore, onplaceonmap }: Props = $props();

  let modalWork = $state<Work | "create" | null>(null);
  let searchQuery = $state("");
  let statusFilter = $state("");
  let categoryFilter = $state("");

  const categoryMap = $derived(
    new Map(settingsStore.workCategories.map(c => [c.id, c]))
  );
  const supplierMap = $derived(
    new Map(settingsStore.suppliers.map(s => [s.id, s]))
  );

  const filteredWorks = $derived(store.works.filter(w => {
    if (statusFilter && w.status !== statusFilter) return false;
    if (categoryFilter && w.categoryId !== categoryFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (!w.title.toLowerCase().includes(q) && !w.description.toLowerCase().includes(q)) return false;
    }
    return true;
  }));

  const totalCost = $derived(
    filteredWorks.reduce((sum, w) => sum + (w.totalCost ?? 0), 0)
  );

  function statusLabel(status: Work["status"]): string {
    if (status === "in_progress") return "In progress";
    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  function statusColor(status: Work["status"]): string {
    if (status === "done") return "#33aa66";
    if (status === "in_progress") return "#3388cc";
    return "#cc8833";
  }

  function fmt(n: number): string {
    return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
</script>

<div class="page">
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

  <div class="list">
    {#if filteredWorks.length === 0}
      <div class="empty">No works yet — click ＋ Add work to get started.</div>
    {:else}
      {#each filteredWorks as work (work.id)}
        {@const cat = work.categoryId ? categoryMap.get(work.categoryId) : null}
        {@const supplier = work.supplierId ? supplierMap.get(work.supplierId) : null}
        <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
        <div
          class="card"
          style="border-left-color:{statusColor(work.status)}"
          onclick={() => { modalWork = work; }}
        >
          <div class="card-top">
            <span class="cat-emoji">{cat?.emoji ?? "🔧"}</span>
            <span class="card-title">{work.title}</span>
            <span
              class="status-chip"
              style="background:{statusColor(work.status)}22;color:{statusColor(work.status)};border:1px solid {statusColor(work.status)}44"
            >{statusLabel(work.status)}</span>
          </div>
          <div class="card-meta">
            <span>{work.date}</span>
            {#if supplier}<span>{supplier.name}</span>{/if}
            {#if work.totalCost != null}<span>{fmt(work.totalCost)} €</span>{/if}
            {#if work.placement}<span class="pin-indicator" title="Pinned on floor plan">📍</span>{/if}
          </div>
          {#if work.description}
            <div class="card-desc">{work.description}</div>
          {/if}
        </div>
      {/each}
    {/if}
  </div>

  <div class="footer">{filteredWorks.length} works · total: {fmt(totalCost)} €</div>
</div>

{#if modalWork !== null}
  <WorkModal
    work={modalWork === "create" ? null : modalWork}
    {store}
    {settingsStore}
    onclose={() => { modalWork = null; }}
    {onplaceonmap}
  />
{/if}

<style>
  .page { display: flex; flex-direction: column; height: 100%; background: var(--bg); font-family: var(--font-sans); }

  .toolbar {
    display: flex; gap: var(--space-2); padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--border); flex-shrink: 0; align-items: center;
  }
  .toolbar :global(.ui-input) { flex: 1; }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px;
    font-family: var(--font-sans); box-sizing: border-box;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  .filter-sel { cursor: pointer; }

  .list { flex: 1; overflow-y: auto; padding: var(--space-3) var(--space-4); display: flex; flex-direction: column; gap: var(--space-2); }
  .empty { color: var(--text-faint); font-size: 13px; text-align: center; padding: 40px 0; }

  .card {
    background: var(--surface); border: 1px solid var(--border); border-left-width: 3px;
    border-radius: var(--radius-md); padding: 10px 14px; cursor: pointer;
  }
  .card:hover { background: var(--surface-hover); }
  .card-top { display: flex; align-items: center; gap: var(--space-2); margin-bottom: 4px; }
  .cat-emoji { font-size: 16px; flex-shrink: 0; }
  .card-title { font-size: 13px; color: var(--text); font-weight: 600; flex: 1; }
  .status-chip { padding: 2px 7px; border-radius: var(--radius-sm); font-size: 10px; font-weight: 500; flex-shrink: 0; }
  .card-meta { display: flex; gap: 12px; font-size: 11px; color: var(--text-faint); flex-wrap: wrap; }
  .pin-indicator { font-size: 11px; }
  .card-desc { font-size: 11px; color: var(--text-faint); margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  .footer { padding: var(--space-2) var(--space-4); border-top: 1px solid var(--border); font-size: 11px; color: var(--text-faint); flex-shrink: 0; }
</style>
```

- [ ] **Step 2: Run the full test suite**

Run: `cd packages/editor && npm test -- --run`
Expected: 162/162 passing (no test imports this component directly; this guards against regressions elsewhere).

- [ ] **Step 3: Manually sanity-check in the browser**

Run `npm run dev` in `packages/editor`, open the route for this page, and toggle the theme switcher between light and dark. Confirm: no leftover hardcoded-dark rectangles, search/select/buttons are legible and themed in both modes, and clicking through to any modal still opens correctly.

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/WorksPage.svelte
git commit -m "feat(editor): migrate WorksPage.svelte onto Card/Button/Input/tokens"
```

---

### Task 3: ChoreListPage

**Files:**
- Modify: `packages/editor/src/lib/components/ChoreListPage.svelte`

Per Architecture rule 1, `store.getColor(pct)` (consumed via the inline `style="color:{color}"` on `.due`) is data/status and is **not modified**. The inline "mark done" note-input and confirm/cancel icon buttons stay native (dense per-row controls, rule 2) but are restyled with tokens.

- [ ] **Step 1: Replace the entire file content**

```svelte
<script lang="ts">
  import type { createChoreStore, Chore, Assignment } from "../choreStore.svelte";

  type ChoreStore = ReturnType<typeof createChoreStore>;

  interface Props {
    store: ChoreStore;
    floorStore: { floors: Array<{ id: string; name: string; rooms: Array<{ id: string; label: string }> }> };
  }

  let { store, floorStore }: Props = $props();

  function getRoomName(roomId: string | null): string {
    if (!roomId) return "🏠 Whole house";
    for (const floor of floorStore.floors) {
      const room = floor.rooms.find((r) => r.id === roomId);
      if (room) return room.label || `Room (${floor.name})`;
    }
    return "Unknown room";
  }

  function displayName(chore: Chore): string {
    let name = chore.name.trim();
    if (chore.emoji && name.startsWith(chore.emoji)) name = name.slice(chore.emoji.length).trim();
    return name;
  }

  function formatDue(iso: string): string {
    if (!iso) return "—";
    const d = new Date(iso);
    const now = new Date();
    const diffDays = Math.round((d.getTime() - now.getTime()) / 86400000);
    if (diffDays < -1) return `${Math.abs(diffDays)}d overdue`;
    if (diffDays === -1) return "Yesterday";
    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Tomorrow";
    if (diffDays <= 7) return `In ${diffDays}d`;
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }

  type Row = { assignment: Assignment; chore: Chore; pct: number };

  const rows = $derived(
    store.assignments
      .map((a) => {
        const chore = store.chores.find((c) => c.id === a.choreId);
        if (!chore) return null;
        return { assignment: a, chore, pct: store.getProgress(a, chore) };
      })
      .filter((r): r is Row => r !== null)
      .sort((a, b) => a.pct - b.pct)
  );

  const overdue = $derived(rows.filter((r) => r.pct <= 0.25));
  const ok = $derived(rows.filter((r) => r.pct > 0.25));

  type CompletingState = { id: string; notes: string };
  let completing = $state<CompletingState | null>(null);

  async function confirmComplete(): Promise<void> {
    if (!completing) return;
    const { id, notes } = completing;
    completing = null;
    await store.completeAssignment(id, notes);
  }
</script>

<div class="page">
  <header class="page-header">
    <h2>Chore List</h2>
    <span class="count">{rows.length} assignments</span>
  </header>

  <div class="list">
    {#if overdue.length > 0}
      <div class="group-header urgent">Needs attention ({overdue.length})</div>
      {#each overdue as { assignment, chore, pct } (assignment.id)}
        {@const color = store.getColor(pct)}
        <div class="row">
          <span class="emoji">{chore.emoji}</span>
          <span class="name">{displayName(chore)}</span>
          <span class="location">{getRoomName(assignment.roomId)}</span>
          <span class="due" style="color:{color}">{formatDue(assignment.nextDueDate)}</span>
          {#if completing?.id === assignment.id}
            <input
              class="note-input"
              bind:value={completing.notes}
              placeholder="Note (optional)"
              onkeydown={(e) => { if (e.key === "Enter") confirmComplete(); if (e.key === "Escape") completing = null; }}
            />
            <button class="done-btn confirm" onclick={confirmComplete}>✓</button>
            <button class="cancel-btn" onclick={() => { completing = null; }}>✕</button>
          {:else}
            <button
              class="done-btn"
              onclick={() => { completing = { id: assignment.id, notes: "" }; }}
              title="Mark done"
            >✓</button>
          {/if}
        </div>
      {/each}
    {/if}

    {#if ok.length > 0}
      {#if overdue.length > 0}<div class="group-divider"></div>{/if}
      <div class="group-header">On track ({ok.length})</div>
      {#each ok as { assignment, chore, pct } (assignment.id)}
        {@const color = store.getColor(pct)}
        <div class="row">
          <span class="emoji">{chore.emoji}</span>
          <span class="name">{displayName(chore)}</span>
          <span class="location">{getRoomName(assignment.roomId)}</span>
          <span class="due" style="color:{color}">{formatDue(assignment.nextDueDate)}</span>
          {#if completing?.id === assignment.id}
            <input
              class="note-input"
              bind:value={completing.notes}
              placeholder="Note (optional)"
              onkeydown={(e) => { if (e.key === "Enter") confirmComplete(); if (e.key === "Escape") completing = null; }}
            />
            <button class="done-btn confirm" onclick={confirmComplete}>✓</button>
            <button class="cancel-btn" onclick={() => { completing = null; }}>✕</button>
          {:else}
            <button
              class="done-btn"
              onclick={() => { completing = { id: assignment.id, notes: "" }; }}
              title="Mark done"
            >✓</button>
          {/if}
        </div>
      {/each}
    {/if}

    {#if rows.length === 0}
      <div class="empty">No chore assignments yet. Go to Management to create chores and assign them to rooms.</div>
    {/if}
  </div>
</div>

<style>
  .page { display: flex; flex-direction: column; height: 100%; background: var(--bg); color: var(--text); font-family: var(--font-sans); }
  .page-header {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 16px; background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .page-header h2 { margin: 0; font-size: 15px; font-weight: 600; color: var(--text); }
  .count { font-size: 11px; color: var(--text-faint); }

  .list { flex: 1; overflow-y: auto; }

  .group-header {
    padding: 8px 16px 4px;
    font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--text-faint); background: var(--bg); position: sticky; top: 0;
  }
  .group-header.urgent { color: var(--danger); }
  .group-divider { height: 8px; background: var(--bg); }

  .row {
    display: flex; align-items: center; gap: 10px;
    padding: 9px 16px; border-bottom: 1px solid var(--border);
    font-size: 13px;
  }
  .row:hover { background: var(--surface-hover); }

  .emoji { font-size: 16px; flex-shrink: 0; width: 22px; text-align: center; }
  .name { flex: 2; min-width: 80px; font-weight: 500; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .location { flex: 2; min-width: 80px; color: var(--text-muted); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .due { flex: 1; min-width: 70px; font-size: 12px; text-align: right; white-space: nowrap; }

  .note-input {
    flex: 1; min-width: 80px; max-width: 160px;
    padding: 3px 8px; background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); color: var(--text); font-size: 11px;
  }
  .note-input:focus { outline: none; border-color: var(--accent); }
  .done-btn {
    padding: 4px 10px; border: none; border-radius: var(--radius-sm);
    background: var(--success); color: var(--accent-contrast); cursor: pointer; font-size: 12px;
    min-height: 30px; flex-shrink: 0; touch-action: manipulation;
  }
  .done-btn:hover { opacity: 0.85; }
  .done-btn:disabled { opacity: 0.5; cursor: default; }
  .cancel-btn {
    padding: 4px 8px; border: none; border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text-muted); cursor: pointer; font-size: 12px;
    min-height: 30px; flex-shrink: 0;
  }
  .cancel-btn:hover { background: var(--surface-hover); }

  .empty { padding: 40px 20px; text-align: center; color: var(--text-faint); font-size: 13px; line-height: 1.6; }

  @media (max-width: 500px) {
    .row { flex-wrap: wrap; gap: 6px; }
    .location { flex-basis: 100%; order: 3; }
    .due { text-align: left; }
  }
</style>
```

- [ ] **Step 2: Run the full test suite**

Run: `cd packages/editor && npm test -- --run`
Expected: 162/162 passing (no test imports this component directly; this guards against regressions elsewhere).

- [ ] **Step 3: Manually sanity-check in the browser**

Run `npm run dev` in `packages/editor`, open the route for this page, and toggle the theme switcher between light and dark. Confirm: no leftover hardcoded-dark rectangles, search/select/buttons are legible and themed in both modes, and clicking through to any modal still opens correctly.

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/ChoreListPage.svelte
git commit -m "feat(editor): migrate ChoreListPage.svelte onto Card/Button/Input/tokens"
```

---

### Task 4: InventoryPage

**Files:**
- Modify: `packages/editor/src/lib/components/InventoryPage.svelte`

Per Architecture rule 1, `warrantyChip()`'s returned hex colors (red/orange/green/neutral) are data/status and are **not modified** — only the `<span class="chip">` wrapper's structural CSS (font-size/weight) stays, no color rule to change since it was already fully inline-styled. Search box becomes `<Input>`; room/category `<select>`s stay native (no Input support for `<select>`); "+ Add item" becomes `<Button>`.

- [ ] **Step 1: Replace the entire file content**

```svelte
<script lang="ts">
  import type { createInventoryStore, InventoryItem } from "../inventoryStore.svelte";
  import type { createHouseStore } from "../houseStore.svelte";
  import InventoryModal from "./InventoryModal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";

  type InvStore = ReturnType<typeof createInventoryStore>;
  type HouseStore = ReturnType<typeof createHouseStore>;

  interface Props {
    store: InvStore;
    floorStore: HouseStore;
    inventoryCategories?: string[];
    selectedItemId?: string | null;
    onclearselection?: () => void;
    onplaceonmap?: (itemId: string) => void;
  }

  let {
    store,
    floorStore,
    inventoryCategories = [],
    selectedItemId = null,
    onclearselection,
    onplaceonmap,
  }: Props = $props();

  let modalItem = $state<InventoryItem | "create" | null>(null);
  let searchQuery = $state("");
  let roomFilter = $state("");
  let categoryFilter = $state("");

  $effect(() => {
    if (selectedItemId) {
      const found = store.items.find((i) => i.id === selectedItemId);
      if (found) {
        modalItem = found;
        onclearselection?.();
      }
    }
  });

  function roomName(roomId: string | null | undefined): string {
    if (!roomId) return "—";
    for (const floor of floorStore.floors) {
      const room = floor.rooms.find((r: { id: string; label: string }) => r.id === roomId);
      if (room) return room.label || roomId;
    }
    return "—";
  }

  function warrantyChip(item: InventoryItem): { label: string; color: string } {
    if (!item.warrantyExpiryDate) return { label: "—", color: "#445" };
    const expiry = new Date(item.warrantyExpiryDate).getTime();
    const now = Date.now();
    const days = Math.round((expiry - now) / 86400000);
    if (days < 0) return { label: "✕ expired", color: "#f44336" };
    if (days <= 30) return { label: `⚠ ${days}d`, color: "#ff9800" };
    return { label: "✓", color: "#4caf50" };
  }

  function formatDate(d: string | null): string {
    if (!d) return "—";
    return d.slice(0, 10);
  }

  function formatPrice(p: number | null): string {
    if (p == null) return "—";
    return p.toLocaleString() + " €";
  }

  const allRooms = $derived(floorStore.floors.flatMap((f: { rooms: { id: string; label: string }[] }) => f.rooms));
  const allCategories = $derived(
    [...new Set(store.items.map((i) => i.category).filter(Boolean))]
  );

  const filtered = $derived(
    store.items.filter((i) => {
      if (
        searchQuery &&
        !i.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
        return false;
      if (roomFilter) {
        if (!i.placement?.roomId) return false;
        if (i.placement.roomId !== roomFilter) return false;
      }
      if (categoryFilter && i.category !== categoryFilter) return false;
      return true;
    })
  );

  const totalValue = $derived(
    store.items.reduce((sum, i) => sum + (i.purchasePrice ?? 0), 0)
  );
</script>

<div class="page">
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
    <table>
      <thead>
        <tr>
          <th></th>
          <th>Name</th>
          <th>Category</th>
          <th>Room</th>
          <th>Purchased</th>
          <th>Cost</th>
          <th>Warranty</th>
        </tr>
      </thead>
      <tbody>
        {#each filtered as item (item.id)}
          {@const chip = warrantyChip(item)}
          <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
          <tr onclick={() => { modalItem = item; }}>
            <td class="emoji-cell">{item.emoji}</td>
            <td class="name-cell">{item.name}</td>
            <td>{item.category || "—"}</td>
            <td>{roomName(item.placement?.roomId)}</td>
            <td>{formatDate(item.purchaseDate)}</td>
            <td>{formatPrice(item.purchasePrice)}</td>
            <td>
              <span class="chip" style="color:{chip.color}">{chip.label}</span>
            </td>
          </tr>
        {/each}
        {#if filtered.length === 0}
          <tr>
            <td colspan="7" class="empty">
              {store.items.length === 0
                ? "No items yet — click ＋ Add item to get started."
                : "No items match your filters."}
            </td>
          </tr>
        {/if}
      </tbody>
    </table>
  </div>

  <div class="footer">
    {store.items.length} item{store.items.length !== 1 ? "s" : ""}
    {#if totalValue > 0}
      · total value: {totalValue.toLocaleString()} €
    {/if}
  </div>
</div>

{#if modalItem}
  <InventoryModal
    item={modalItem === "create" ? null : modalItem}
    {store}
    {inventoryCategories}
    onclose={() => { modalItem = null; }}
    onplaceonmap={onplaceonmap
      ? (id) => { modalItem = null; onplaceonmap!(id); }
      : undefined}
  />
{/if}

<style>
  .page {
    display: flex; flex-direction: column; height: 100%;
    background: var(--bg); font-family: var(--font-sans);
  }

  .toolbar {
    display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3);
    background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .toolbar :global(.ui-input) { flex: 1; }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px;
    font-family: var(--font-sans); box-sizing: border-box; cursor: pointer;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }

  .table-wrapper { flex: 1; overflow-y: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; color: var(--text-muted); }
  thead { position: sticky; top: 0; background: var(--surface-alt); z-index: 1; }
  th {
    padding: 6px 10px; color: var(--text-faint); font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.05em;
    text-align: left; border-bottom: 1px solid var(--border);
  }
  td { padding: 7px 10px; border-bottom: 1px solid var(--border); }
  tr:hover td { background: var(--surface-hover); cursor: pointer; }
  .emoji-cell { font-size: 16px; width: 32px; text-align: center; }
  .name-cell { color: var(--text); }
  .chip { font-size: 10px; font-weight: 500; }
  .empty { text-align: center; color: var(--text-faint); padding: 32px; }

  .footer {
    padding: 6px 12px; font-size: 11px; color: var(--text-faint);
    border-top: 1px solid var(--border); flex-shrink: 0;
  }
</style>
```

- [ ] **Step 2: Run the full test suite**

Run: `cd packages/editor && npm test -- --run`
Expected: 162/162 passing (no test imports this component directly; this guards against regressions elsewhere).

- [ ] **Step 3: Manually sanity-check in the browser**

Run `npm run dev` in `packages/editor`, open the route for this page, and toggle the theme switcher between light and dark. Confirm: no leftover hardcoded-dark rectangles, search/select/buttons are legible and themed in both modes, and clicking through to any modal still opens correctly.

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/InventoryPage.svelte
git commit -m "feat(editor): migrate InventoryPage.svelte onto Card/Button/Input/tokens"
```

---

### Task 5: ChoresPage

**Files:**
- Modify: `packages/editor/src/lib/components/ChoresPage.svelte`

This page has no data/status color functions, so it gets the fullest token migration of the three chore-related pages. Each chore's outer card has no per-item dynamic styling or whole-card click handler (only its inner buttons are interactive), so per Architecture rule 2 it converts cleanly to `<Card>`. The header's "+ New chore"/"Import from Donetick"/"Import"/"Cancel" become `<Button>` (primary/secondary/primary/ghost respectively); the Donetick API token field becomes `<Input type="password">`. The Name field in the edit form becomes `<Input>`; Emoji (needs `maxlength`), Period days (needs `type="number"`), and the schedule-from-due checkbox stay native per rule 2. Per-chore action rows (✓ All done / note-input+confirm/cancel / ✏️ / 🕐 / 🗑️) and per-instance rows stay native (dense icon-button density, rule 2), restyled with tokens; the 🗑️ delete buttons get a `var(--danger)` hover color.

- [ ] **Step 1: Replace the entire file content**

```svelte
<script lang="ts">
  import type { createChoreStore } from "../choreStore.svelte";
  import type { Chore } from "../choreStore.svelte";
  import { scheduleLabel } from "../choreStore.svelte";
  import DatePicker from "./DatePicker.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import Card from "./ui/Card.svelte";

  type ChoreStore = ReturnType<typeof createChoreStore>;

  interface Props {
    store: ChoreStore;
    floorStore: { floors: Array<{ id: string; name: string; rooms: Array<{ id: string; label: string }> }> };
    onnewchore?: () => void;
  }

  let { store, floorStore, onnewchore }: Props = $props();

  function getRoomName(roomId: string): string {
    for (const floor of floorStore.floors) {
      const room = floor.rooms.find((r) => r.id === roomId);
      if (room) return room.label || `Room (${floor.name})`;
    }
    return "Unknown room";
  }

  let editingId = $state<string | null>(null);
  let editName = $state("");
  let editEmoji = $state("");
  let editPeriodDays = $state(30);
  let editNextDue = $state("");
  let editScheduleFromDue = $state(false);

  function startEdit(chore: Chore): void {
    editingId = chore.id;
    editName = chore.name;
    editEmoji = chore.emoji;
    editPeriodDays = chore.periodDays;
    editNextDue = chore.nextDueDate.slice(0, 10);
    editScheduleFromDue = chore.scheduleFromDue;
  }

  async function handleUpdate(): Promise<void> {
    if (!editingId) return;
    await store.updateChore(editingId, {
      name: editName.trim(),
      emoji: editEmoji.trim() || "📋",
      periodDays: editPeriodDays,
      nextDueDate: new Date(editNextDue).toISOString(),
      scheduleFromDue: editScheduleFromDue,
    });
    editingId = null;
  }

  function assignmentsForChore(choreId: string) {
    return store.assignments.filter((a) => a.choreId === choreId);
  }

  function displayName(chore: Chore): string {
    let name = chore.name.trim();
    if (chore.emoji && name.startsWith(chore.emoji)) name = name.slice(chore.emoji.length).trim();
    return name;
  }

  function formatDate(iso: string): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

  function formatDateTime(iso: string): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  }

  let showImportInput = $state(false);
  let importToken = $state("");
  let importStatus = $state<"idle" | "loading" | "done" | "error">("idle");
  let importCount = $state(0);

  async function handleImport(): Promise<void> {
    importStatus = "loading";
    try {
      importCount = await store.importFromDonetick(importToken.trim());
      importStatus = "done"; importToken = ""; showImportInput = false;
    } catch { importStatus = "error"; }
  }

  // Inline completion with notes
  type CompletingState = { kind: "chore"; id: string; notes: string } | { kind: "assignment"; id: string; notes: string };
  let completing = $state<CompletingState | null>(null);

  async function confirmComplete(): Promise<void> {
    if (!completing) return;
    const c = completing;
    completing = null;
    if (c.kind === "chore") await store.completeChore(c.id, c.notes);
    else await store.completeAssignment(c.id, c.notes);
  }

  // Per-chore history expansion
  let expandedHistory = $state<string | null>(null);
</script>

<div class="page">
  <header class="page-header">
    <h1>Chore Management</h1>
    <Button onclick={() => onnewchore?.()}>＋ New chore</Button>
    {#if !showImportInput}
      <Button variant="secondary" onclick={() => { showImportInput = true; }}>Import from Donetick</Button>
    {:else}
      <Input type="password" placeholder="API token" bind:value={importToken} />
      <Button disabled={importStatus === "loading"} onclick={handleImport}>
        {importStatus === "loading" ? "Importing…" : "Import"}
      </Button>
      <Button variant="ghost" onclick={() => { showImportInput = false; }}>Cancel</Button>
      {#if importStatus === "error"}<span class="error-msg">Failed</span>{/if}
      {#if importStatus === "done"}<span class="success-msg">{importCount} imported</span>{/if}
    {/if}
  </header>

  <div class="chore-list">
    {#each store.chores as chore (chore.id)}
      <Card>
        {#if editingId === chore.id}
          <div class="edit-form">
            <Input bind:value={editName} placeholder="Name" />
            <input class="native-input emoji-field" bind:value={editEmoji} placeholder="Emoji" maxlength="4" />
            <label>Period (days) <input class="native-input" type="number" bind:value={editPeriodDays} min="1"/></label>
            <label>Default due <DatePicker bind:value={editNextDue} /></label>
            <div class="sfd-row">
              <input type="checkbox" id="sfd-{chore.id}" bind:checked={editScheduleFromDue}/>
              <label for="sfd-{chore.id}" title="Next due = planned date + period">Schedule from due date</label>
            </div>
            <div class="row-btns">
              <Button onclick={handleUpdate}>Save</Button>
              <Button variant="ghost" onclick={() => { editingId = null; }}>Cancel</Button>
            </div>
          </div>
        {:else}
          <div class="chore-header">
            <span class="chore-emoji">{chore.emoji}</span>
            <div class="chore-info">
              <span class="chore-name">{displayName(chore)}</span>
              <span class="chore-meta">
                {scheduleLabel(chore)}
                {#if chore.scheduleFromDue}<span class="sfd-badge" title="Schedules from due date">📅</span>{/if}
              </span>
            </div>

            {#if completing?.kind === "chore" && completing.id === chore.id}
              <input
                class="native-input note-input"
                bind:value={completing.notes}
                placeholder="Note (optional)"
                onkeydown={(e) => { if (e.key === "Enter") confirmComplete(); if (e.key === "Escape") completing = null; }}
              />
              <button class="icon-btn confirm-btn" onclick={confirmComplete}>✓</button>
              <button class="icon-btn" onclick={() => { completing = null; }}>✕</button>
            {:else}
              <button class="icon-btn" title="Mark all done" onclick={() => { completing = { kind: "chore", id: chore.id, notes: "" }; }}>✓ All done</button>
            {/if}

            <button class="icon-btn" onclick={() => startEdit(chore)}>✏️</button>
            <button
              class="icon-btn"
              title={expandedHistory === chore.id ? "Hide history" : "Show history"}
              class:active-hist={expandedHistory === chore.id}
              onclick={() => { expandedHistory = expandedHistory === chore.id ? null : chore.id; }}
            >🕐</button>
            <button class="icon-btn danger" onclick={() => store.deleteChore(chore.id)}>🗑️</button>
          </div>

          {@const instances = assignmentsForChore(chore.id)}
          {#if instances.length > 0}
            <div class="instances">
              {#each instances as a (a.id)}
                <div class="instance-row">
                  <span class="instance-where">
                    {a.roomId ? getRoomName(a.roomId) : "🏠 Whole house"}
                  </span>
                  <span class="instance-due">Due: {formatDate(a.nextDueDate)}</span>
                  {#if completing?.kind === "assignment" && completing.id === a.id}
                    <input
                      class="native-input note-input-sm"
                      bind:value={completing.notes}
                      placeholder="Note (optional)"
                      onkeydown={(e) => { if (e.key === "Enter") confirmComplete(); if (e.key === "Escape") completing = null; }}
                    />
                    <button class="icon-btn confirm-btn" onclick={confirmComplete}>✓</button>
                    <button class="icon-btn" onclick={() => { completing = null; }}>✕</button>
                  {:else}
                    <button class="icon-btn" onclick={() => { completing = { kind: "assignment", id: a.id, notes: "" }; }}>✓</button>
                  {/if}
                  <button class="icon-btn danger" onclick={() => store.deleteAssignment(a.id)}>✕</button>
                </div>
              {/each}
            </div>
          {:else}
            <div class="no-instances">Not assigned to any room</div>
          {/if}

          {#if expandedHistory === chore.id}
            {@const history = store.getCompletionsForChore(chore.id).slice().reverse()}
            <div class="history-section">
              <div class="history-title">Completion history</div>
              {#if history.length === 0}
                <div class="no-history">No completions yet</div>
              {:else}
                {#each history as rec (rec.id)}
                  <div class="history-row">
                    <span class="hist-date">{formatDateTime(rec.completedAt)}</span>
                    {#if rec.scheduledDue}<span class="hist-due">was due {formatDate(rec.scheduledDue)}</span>{/if}
                    {#if rec.notes}<span class="hist-notes">{rec.notes}</span>{/if}
                  </div>
                {/each}
              {/if}
            </div>
          {/if}
        {/if}
      </Card>
    {/each}

    {#if store.chores.length === 0}
      <div class="empty-state">
        No chores yet. Click <strong>＋ New chore</strong> to get started.
      </div>
    {/if}
  </div>
</div>

<style>
  .page { display: flex; flex-direction: column; height: 100%; background: var(--bg); color: var(--text); font-family: var(--font-sans); }

  .page-header {
    display: flex; align-items: center; gap: 8px 12px; flex-wrap: wrap;
    padding: var(--space-2) var(--space-4); background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .page-header h1 { font-size: 16px; margin: 0; flex: 1; min-width: 120px; color: var(--text); }
  .page-header :global(.ui-input) { flex: 0 1 220px; }

  .chore-list { flex: 1; overflow-y: auto; padding: var(--space-3); display: flex; flex-direction: column; gap: var(--space-3); }

  .chore-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
  .chore-emoji { font-size: 18px; flex-shrink: 0; }
  .chore-info { flex: 1; min-width: 80px; display: flex; flex-direction: column; gap: 2px; }
  .chore-name { font-weight: 600; color: var(--text); word-break: break-word; }
  .chore-meta { font-size: 11px; color: var(--text-faint); display: flex; align-items: center; gap: 4px; }
  .sfd-badge { font-size: 11px; cursor: help; }

  .native-input {
    padding: 6px 8px; border: 1px solid var(--border); border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text); font-size: 12px;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  .note-input { flex: 1; min-width: 100px; }
  .note-input-sm { width: 110px; font-size: 11px; }
  .emoji-field { width: 60px; }

  .icon-btn {
    padding: 6px 10px; border: none; border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text-muted); cursor: pointer; font-size: 12px;
    min-height: 34px; touch-action: manipulation;
  }
  .icon-btn:hover { background: var(--surface-hover); color: var(--text); }
  .icon-btn.danger:hover { color: var(--danger); }
  .confirm-btn { background: var(--success) !important; color: var(--accent-contrast) !important; }
  .confirm-btn:hover { opacity: 0.85; }
  .active-hist { background: var(--surface-hover) !important; color: var(--accent) !important; }

  .instances { display: flex; flex-direction: column; gap: 6px; padding-left: 12px; border-left: 2px solid var(--border); margin-top: 4px; }
  .instance-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 12px; }
  .instance-where { flex: 1; min-width: 80px; color: var(--text-muted); }
  .instance-due { color: var(--text-faint); font-size: 11px; white-space: nowrap; }
  .no-instances { font-size: 11px; color: var(--text-faint); padding-left: 12px; font-style: italic; margin-top: 4px; }

  .history-section {
    margin-top: 8px; padding: var(--space-2) var(--space-3);
    background: var(--surface-alt); border-radius: var(--radius-sm); border: 1px solid var(--border);
  }
  .history-title { font-size: 10px; text-transform: uppercase; color: var(--text-faint); letter-spacing: 0.06em; margin-bottom: 6px; }
  .no-history { font-size: 11px; color: var(--text-faint); font-style: italic; }
  .history-row { display: flex; align-items: baseline; gap: 10px; padding: 3px 0; font-size: 11px; flex-wrap: wrap; }
  .hist-date { color: var(--text-muted); white-space: nowrap; flex-shrink: 0; }
  .hist-due { color: var(--text-faint); white-space: nowrap; }
  .hist-notes { color: var(--text-muted); font-style: italic; }

  .sfd-row { display: flex; align-items: center; gap: 6px; font-size: 12px; }
  .sfd-row input[type="checkbox"] { width: auto; }
  .sfd-row label { color: var(--text-muted); cursor: pointer; }

  .edit-form { display: flex; flex-direction: column; gap: 6px; }
  .edit-form input[type="number"] { width: 100px; }
  label { display: flex; flex-direction: column; gap: 2px; font-size: 11px; color: var(--text-faint); }
  .row-btns { display: flex; gap: 8px; margin-top: 4px; flex-wrap: wrap; }

  .error-msg { color: var(--danger); font-size: 11px; }
  .success-msg { color: var(--success); font-size: 11px; }

  .empty-state { padding: 40px 20px; text-align: center; color: var(--text-faint); font-size: 13px; line-height: 1.6; }

  @media (max-width: 500px) {
    .page-header { padding: 8px 10px; }
    .chore-list { padding: 8px; gap: 8px; }
    .chore-header { gap: 6px; }
    .edit-form input[type="number"] { width: 100%; }
    .row-btns { flex-direction: column; }
    .row-btns :global(.ui-button) { width: 100%; }
    .instance-row { gap: 6px; }
  }
</style>
```

- [ ] **Step 2: Run the full test suite**

Run: `cd packages/editor && npm test -- --run`
Expected: 162/162 passing (no test imports this component directly; this guards against regressions elsewhere).

- [ ] **Step 3: Manually sanity-check in the browser**

Run `npm run dev` in `packages/editor`, open the route for this page, and toggle the theme switcher between light and dark. Confirm: no leftover hardcoded-dark rectangles, search/select/buttons are legible and themed in both modes, and clicking through to any modal still opens correctly.

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/ChoresPage.svelte
git commit -m "feat(editor): migrate ChoresPage.svelte onto Card/Button/Input/tokens"
```

---

### Task 6: SettingsPage

**Files:**
- Modify: `packages/editor/src/lib/components/SettingsPage.svelte`

The 4 CRUD sections (Cost categories, Inventory categories, Work categories, Suppliers) each become a `<Card>` (no per-section dynamic styling, rule 2). Each section's "+ Add" button becomes `<Button>`. Inline-edit Name/Unit text fields become `<Input>` (wrapped in a `<td>` with a CSS rule sizing the rendered `.ui-input` to the original fixed width, since `<Input>` always renders `width:100%` of its container). Emoji input (`maxlength`) and color swatch input (`type="color"`) stay native per rule 2 — `<Input>`'s API has no `maxlength`/`type="color"` support. The dense icon-only row actions (✏️ edit / 🗑️ delete / ✓ save / ✕ cancel) stay native, restyled with tokens.

- [ ] **Step 1: Replace the entire file content**

```svelte
<!-- packages/editor/src/lib/components/SettingsPage.svelte -->
<script lang="ts">
  import type { createSettingsStore, CostCategory, InventoryCategory, WorkCategory, Supplier } from "../settingsStore.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import Card from "./ui/Card.svelte";

  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    store: SettingsStore;
  }
  let { store }: Props = $props();

  // --- Cost categories ---
  let editingCostId = $state<string | null>(null);
  let costDraft = $state<CostCategory>({ id: "", name: "", emoji: "", unit: null, color: "#4466cc" });
  let costDraftUnit = $state("");
  let showNewCostForm = $state(false);
  let newCostDraft = $state({ name: "", emoji: "", unit: "", color: "#4466cc" });
  let confirmDeleteCostId = $state<string | null>(null);
  let costError = $state<string | null>(null);

  function startEditCost(cat: CostCategory): void {
    editingCostId = cat.id;
    costDraft = { ...cat };
    costDraftUnit = cat.unit ?? "";
  }

  function cancelEditCost(): void {
    editingCostId = null;
    costError = null;
  }

  async function saveEditCost(): Promise<void> {
    if (!costDraft.name.trim()) { costError = "Name required"; return; }
    const updated = store.costCategories.map(c =>
      c.id === editingCostId ? { ...costDraft, name: costDraft.name.trim(), unit: costDraftUnit.trim() || null } : c
    );
    await store.updateCostCategories(updated);
    editingCostId = null;
    costError = null;
  }

  async function deleteCostCategory(id: string): Promise<void> {
    const updated = store.costCategories.filter(c => c.id !== id);
    await store.updateCostCategories(updated);
    confirmDeleteCostId = null;
  }

  async function addCostCategory(): Promise<void> {
    if (!newCostDraft.name.trim()) { costError = "Name required"; return; }
    const newCat: CostCategory = {
      id: crypto.randomUUID(),
      name: newCostDraft.name.trim(),
      emoji: newCostDraft.emoji || "💰",
      unit: newCostDraft.unit.trim() || null,
      color: newCostDraft.color,
    };
    await store.updateCostCategories([...store.costCategories, newCat]);
    newCostDraft = { name: "", emoji: "", unit: "", color: "#4466cc" };
    showNewCostForm = false;
    costError = null;
  }

  // --- Inventory categories ---
  let editingInvId = $state<string | null>(null);
  let invDraft = $state<InventoryCategory>({ id: "", name: "" });
  let showNewInvForm = $state(false);
  let newInvDraft = $state({ name: "" });
  let confirmDeleteInvId = $state<string | null>(null);
  let invError = $state<string | null>(null);

  function startEditInv(cat: InventoryCategory): void {
    editingInvId = cat.id;
    invDraft = { ...cat };
    invError = null;
  }

  function cancelEditInv(): void { editingInvId = null; invError = null; }

  async function saveEditInv(): Promise<void> {
    if (!invDraft.name.trim()) { invError = "Name required"; return; }
    const updated = store.inventoryCategories.map(c =>
      c.id === editingInvId ? { ...invDraft, name: invDraft.name.trim() } : c
    );
    await store.updateInventoryCategories(updated);
    editingInvId = null; invError = null;
  }

  async function deleteInventoryCategory(id: string): Promise<void> {
    await store.updateInventoryCategories(store.inventoryCategories.filter(c => c.id !== id));
    confirmDeleteInvId = null;
  }

  async function addInventoryCategory(): Promise<void> {
    if (!newInvDraft.name.trim()) { invError = "Name required"; return; }
    const newCat: InventoryCategory = {
      id: crypto.randomUUID(),
      name: newInvDraft.name.trim(),
    };
    await store.updateInventoryCategories([...store.inventoryCategories, newCat]);
    newInvDraft = { name: "" };
    showNewInvForm = false;
    invError = null;
  }

  // --- Work categories ---
  let editingWorkId = $state<string | null>(null);
  let workDraft = $state<WorkCategory>({ id: "", name: "", emoji: "" });
  let showNewWorkForm = $state(false);
  let newWorkDraft = $state({ name: "", emoji: "" });
  let confirmDeleteWorkId = $state<string | null>(null);
  let workError = $state<string | null>(null);

  function startEditWork(cat: WorkCategory): void {
    editingWorkId = cat.id;
    workDraft = { ...cat };
    workError = null;
  }

  function cancelEditWork(): void { editingWorkId = null; workError = null; }

  async function saveEditWork(): Promise<void> {
    if (!workDraft.name.trim()) { workError = "Name required"; return; }
    const updated = store.workCategories.map(c =>
      c.id === editingWorkId ? { ...workDraft, name: workDraft.name.trim() } : c
    );
    await store.updateWorkCategories(updated);
    editingWorkId = null; workError = null;
  }

  async function deleteWorkCategory(id: string): Promise<void> {
    await store.updateWorkCategories(store.workCategories.filter(c => c.id !== id));
    confirmDeleteWorkId = null;
  }

  async function addWorkCategory(): Promise<void> {
    if (!newWorkDraft.name.trim()) { workError = "Name required"; return; }
    const newCat: WorkCategory = {
      id: crypto.randomUUID(),
      name: newWorkDraft.name.trim(),
      emoji: newWorkDraft.emoji || "🔧",
    };
    await store.updateWorkCategories([...store.workCategories, newCat]);
    newWorkDraft = { name: "", emoji: "" };
    showNewWorkForm = false; workError = null;
  }

  // --- Suppliers ---
  let editingSupplierId = $state<string | null>(null);
  let supplierDraft = $state<Supplier>({ id: "", name: "" });
  let showNewSupplierForm = $state(false);
  let newSupplierDraft = $state({ name: "" });
  let confirmDeleteSupplierId = $state<string | null>(null);
  let supplierError = $state<string | null>(null);

  function startEditSupplier(s: Supplier): void {
    editingSupplierId = s.id;
    supplierDraft = { ...s };
    supplierError = null;
  }

  function cancelEditSupplier(): void { editingSupplierId = null; supplierError = null; }

  async function saveEditSupplier(): Promise<void> {
    if (!supplierDraft.name.trim()) { supplierError = "Name required"; return; }
    const updated = store.suppliers.map(s =>
      s.id === editingSupplierId ? { ...supplierDraft, name: supplierDraft.name.trim() } : s
    );
    await store.updateSuppliers(updated);
    editingSupplierId = null; supplierError = null;
  }

  async function deleteSupplier(id: string): Promise<void> {
    await store.updateSuppliers(store.suppliers.filter(s => s.id !== id));
    confirmDeleteSupplierId = null;
  }

  async function addSupplier(): Promise<void> {
    if (!newSupplierDraft.name.trim()) { supplierError = "Name required"; return; }
    const newS: Supplier = {
      id: crypto.randomUUID(),
      name: newSupplierDraft.name.trim(),
    };
    await store.updateSuppliers([...store.suppliers, newS]);
    newSupplierDraft = { name: "" };
    showNewSupplierForm = false;
    supplierError = null;
  }
</script>

<div class="page">
  <div class="page-header">
    <h1>Settings</h1>
  </div>

  <div class="sections">

    <!-- Cost categories -->
    <Card>
      <div class="section-header">
        <h2>Cost categories</h2>
        <Button onclick={() => { showNewCostForm = true; costError = null; }}>＋ Add</Button>
      </div>

      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Color</th>
              <th>Emoji</th>
              <th>Name</th>
              <th>Unit</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {#each store.costCategories as cat (cat.id)}
              {#if editingCostId === cat.id}
                <tr class="editing-row">
                  <td><input type="color" bind:value={costDraft.color} class="color-input" /></td>
                  <td><input class="emoji-input" bind:value={costDraft.emoji} maxlength="2" /></td>
                  <td class="name-cell-input"><Input bind:value={costDraft.name} placeholder="Name" /></td>
                  <td class="unit-cell-input"><Input bind:value={costDraftUnit} placeholder="L, kWh…" /></td>
                  <td class="actions">
                    <button class="icon-action ok" onclick={saveEditCost} title="Save">✓</button>
                    <button class="icon-action" onclick={cancelEditCost} title="Cancel">✕</button>
                  </td>
                </tr>
              {:else}
                <tr>
                  <td><span class="color-swatch" style="background:{cat.color}"></span></td>
                  <td class="emoji-cell">{cat.emoji}</td>
                  <td>{cat.name}</td>
                  <td class="unit-cell">{cat.unit ?? "—"}</td>
                  <td class="actions">
                    {#if confirmDeleteCostId === cat.id}
                      <span class="confirm-text">Delete?</span>
                      <button class="icon-action danger" onclick={() => deleteCostCategory(cat.id)}>✓</button>
                      <button class="icon-action" onclick={() => { confirmDeleteCostId = null; }}>✕</button>
                    {:else}
                      <button class="icon-action" onclick={() => startEditCost(cat)} title="Edit">✏</button>
                      <button class="icon-action danger" onclick={() => { confirmDeleteCostId = cat.id; }} title="Delete">🗑</button>
                    {/if}
                  </td>
                </tr>
              {/if}
            {/each}

            {#if showNewCostForm}
              <tr class="editing-row">
                <td><input type="color" bind:value={newCostDraft.color} class="color-input" /></td>
                <td><input class="emoji-input" bind:value={newCostDraft.emoji} maxlength="2" placeholder="💰" /></td>
                <td class="name-cell-input"><Input bind:value={newCostDraft.name} placeholder="Name *" /></td>
                <td class="unit-cell-input"><Input bind:value={newCostDraft.unit} placeholder="L, kWh… (optional)" /></td>
                <td class="actions">
                  <button class="icon-action ok" onclick={addCostCategory} title="Add">✓</button>
                  <button class="icon-action" onclick={() => { showNewCostForm = false; costError = null; }} title="Cancel">✕</button>
                </td>
              </tr>
            {/if}
          </tbody>
        </table>
      </div>
      {#if costError}<div class="error">{costError}</div>{/if}
    </Card>

    <!-- Inventory categories -->
    <Card>
      <div class="section-header">
        <h2>Inventory categories</h2>
        <Button onclick={() => { showNewInvForm = true; invError = null; }}>＋ Add</Button>
      </div>

      <div class="table-wrapper">
        <table>
          <thead>
            <tr><th>Name</th><th></th></tr>
          </thead>
          <tbody>
            {#each store.inventoryCategories as cat (cat.id)}
              {#if editingInvId === cat.id}
                <tr class="editing-row">
                  <td class="name-cell-input wide"><Input bind:value={invDraft.name} placeholder="Name" /></td>
                  <td class="actions">
                    <button class="icon-action ok" onclick={saveEditInv} title="Save">✓</button>
                    <button class="icon-action" onclick={cancelEditInv} title="Cancel">✕</button>
                  </td>
                </tr>
              {:else}
                <tr>
                  <td>{cat.name}</td>
                  <td class="actions">
                    {#if confirmDeleteInvId === cat.id}
                      <span class="confirm-text">Delete?</span>
                      <button class="icon-action danger" onclick={() => deleteInventoryCategory(cat.id)}>✓</button>
                      <button class="icon-action" onclick={() => { confirmDeleteInvId = null; }}>✕</button>
                    {:else}
                      <button class="icon-action" onclick={() => startEditInv(cat)} title="Edit">✏</button>
                      <button class="icon-action danger" onclick={() => { confirmDeleteInvId = cat.id; }} title="Delete">🗑</button>
                    {/if}
                  </td>
                </tr>
              {/if}
            {/each}

            {#if showNewInvForm}
              <tr class="editing-row">
                <td class="name-cell-input wide"><Input bind:value={newInvDraft.name} placeholder="Name *" /></td>
                <td class="actions">
                  <button class="icon-action ok" onclick={addInventoryCategory} title="Add">✓</button>
                  <button class="icon-action" onclick={() => { showNewInvForm = false; invError = null; }} title="Cancel">✕</button>
                </td>
              </tr>
            {/if}
          </tbody>
        </table>
      </div>
      {#if invError}<div class="error">{invError}</div>{/if}
    </Card>

    <!-- Work categories -->
    <Card>
      <div class="section-header">
        <h2>Work categories</h2>
        <Button onclick={() => { showNewWorkForm = true; workError = null; }}>＋ Add</Button>
      </div>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr><th>Emoji</th><th>Name</th><th></th></tr>
          </thead>
          <tbody>
            {#each store.workCategories as cat (cat.id)}
              {#if editingWorkId === cat.id}
                <tr class="editing-row">
                  <td><input class="emoji-input" bind:value={workDraft.emoji} maxlength="2" /></td>
                  <td class="name-cell-input"><Input bind:value={workDraft.name} placeholder="Name" /></td>
                  <td class="actions">
                    <button class="icon-action ok" onclick={saveEditWork} title="Save">✓</button>
                    <button class="icon-action" onclick={cancelEditWork} title="Cancel">✕</button>
                  </td>
                </tr>
              {:else}
                <tr>
                  <td class="emoji-cell">{cat.emoji}</td>
                  <td>{cat.name}</td>
                  <td class="actions">
                    {#if confirmDeleteWorkId === cat.id}
                      <span class="confirm-text">Delete?</span>
                      <button class="icon-action danger" onclick={() => deleteWorkCategory(cat.id)}>✓</button>
                      <button class="icon-action" onclick={() => { confirmDeleteWorkId = null; }}>✕</button>
                    {:else}
                      <button class="icon-action" onclick={() => startEditWork(cat)} title="Edit">✏</button>
                      <button class="icon-action danger" onclick={() => { confirmDeleteWorkId = cat.id; }} title="Delete">🗑</button>
                    {/if}
                  </td>
                </tr>
              {/if}
            {/each}
            {#if showNewWorkForm}
              <tr class="editing-row">
                <td><input class="emoji-input" bind:value={newWorkDraft.emoji} maxlength="2" placeholder="🔧" /></td>
                <td class="name-cell-input"><Input bind:value={newWorkDraft.name} placeholder="Name *" /></td>
                <td class="actions">
                  <button class="icon-action ok" onclick={addWorkCategory} title="Add">✓</button>
                  <button class="icon-action" onclick={() => { showNewWorkForm = false; workError = null; }} title="Cancel">✕</button>
                </td>
              </tr>
            {/if}
          </tbody>
        </table>
      </div>
      {#if workError}<div class="error">{workError}</div>{/if}
    </Card>

    <!-- Suppliers -->
    <Card>
      <div class="section-header">
        <h2>Suppliers</h2>
        <Button onclick={() => { showNewSupplierForm = true; supplierError = null; }}>＋ Add</Button>
      </div>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr><th>Name</th><th></th></tr>
          </thead>
          <tbody>
            {#each store.suppliers as s (s.id)}
              {#if editingSupplierId === s.id}
                <tr class="editing-row">
                  <td class="name-cell-input wide"><Input bind:value={supplierDraft.name} placeholder="Name" /></td>
                  <td class="actions">
                    <button class="icon-action ok" onclick={saveEditSupplier} title="Save">✓</button>
                    <button class="icon-action" onclick={cancelEditSupplier} title="Cancel">✕</button>
                  </td>
                </tr>
              {:else}
                <tr>
                  <td>{s.name}</td>
                  <td class="actions">
                    {#if confirmDeleteSupplierId === s.id}
                      <span class="confirm-text">Delete?</span>
                      <button class="icon-action danger" onclick={() => deleteSupplier(s.id)}>✓</button>
                      <button class="icon-action" onclick={() => { confirmDeleteSupplierId = null; }}>✕</button>
                    {:else}
                      <button class="icon-action" onclick={() => startEditSupplier(s)} title="Edit">✏</button>
                      <button class="icon-action danger" onclick={() => { confirmDeleteSupplierId = s.id; }} title="Delete">🗑</button>
                    {/if}
                  </td>
                </tr>
              {/if}
            {/each}
            {#if showNewSupplierForm}
              <tr class="editing-row">
                <td class="name-cell-input wide"><Input bind:value={newSupplierDraft.name} placeholder="Name *" /></td>
                <td class="actions">
                  <button class="icon-action ok" onclick={addSupplier} title="Add">✓</button>
                  <button class="icon-action" onclick={() => { showNewSupplierForm = false; supplierError = null; }} title="Cancel">✕</button>
                </td>
              </tr>
            {/if}
          </tbody>
        </table>
      </div>
      {#if supplierError}<div class="error">{supplierError}</div>{/if}
    </Card>

  </div>
</div>

<style>
  .page {
    display: flex; flex-direction: column; height: 100%;
    background: var(--bg); font-family: var(--font-sans); overflow-y: auto;
  }
  .page-header {
    padding: var(--space-4) var(--space-4) var(--space-2); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  h1 { margin: 0; font-size: 16px; color: var(--text); font-weight: 600; }
  .sections { padding: var(--space-4); display: flex; flex-direction: column; gap: var(--space-5); }

  .section-header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: var(--space-2);
  }
  h2 { margin: 0; font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }

  .table-wrapper { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; color: var(--text-muted); }
  thead { background: var(--surface-alt); }
  th {
    padding: 5px 10px; color: var(--text-faint); font-size: 10px;
    text-transform: uppercase; letter-spacing: .05em; text-align: left;
    border-bottom: 1px solid var(--border);
  }
  td { padding: 6px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:hover td { background: var(--surface-hover); }
  .editing-row td { background: var(--surface-alt); }

  .color-swatch { display: inline-block; width: 14px; height: 14px; border-radius: 3px; }
  .emoji-cell { font-size: 15px; }
  .unit-cell { color: var(--text-faint); }

  .color-input { width: 36px; height: 24px; border: 1px solid var(--border); border-radius: 3px; padding: 0; cursor: pointer; background: none; }
  .emoji-input {
    width: 36px; background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 3px 4px; border-radius: 3px; font-size: 14px; text-align: center;
  }
  .name-cell-input :global(.ui-input) { width: 160px; }
  .name-cell-input.wide :global(.ui-input) { width: 260px; }
  .unit-cell-input :global(.ui-input) { width: 100px; }

  .actions { display: flex; align-items: center; gap: 4px; white-space: nowrap; }
  .icon-action {
    background: none; border: none; color: var(--text-faint); cursor: pointer; font-size: 12px;
    padding: 2px 5px; border-radius: 3px;
  }
  .icon-action:hover { background: var(--surface-hover); color: var(--text-muted); }
  .icon-action.ok { color: var(--success); }
  .icon-action.ok:hover { background: color-mix(in srgb, var(--success) 18%, var(--surface)); }
  .icon-action.danger { color: var(--danger); }
  .icon-action.danger:hover { background: color-mix(in srgb, var(--danger) 18%, var(--surface)); }
  .confirm-text { font-size: 10px; color: var(--danger); }

  .error { color: var(--danger); font-size: 11px; margin-top: 6px; }
</style>
```

- [ ] **Step 2: Run the full test suite**

Run: `cd packages/editor && npm test -- --run`
Expected: 162/162 passing (no test imports this component directly; this guards against regressions elsewhere).

- [ ] **Step 3: Manually sanity-check in the browser**

Run `npm run dev` in `packages/editor`, open the route for this page, and toggle the theme switcher between light and dark. Confirm: no leftover hardcoded-dark rectangles, search/select/buttons are legible and themed in both modes, and clicking through to any modal still opens correctly.

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/SettingsPage.svelte
git commit -m "feat(editor): migrate SettingsPage.svelte onto Card/Button/Input/tokens"
```

---

### Task 7: CostsPage

**Files:**
- Modify: `packages/editor/src/lib/components/CostsPage.svelte`

Largest and most complex task. Per Architecture rule 1: `cat.color` (pie slice fill, connector line/label colors) is user-configurable category data and is **not modified**. The donut hole's circle `fill` and its "Total" label text colors are chrome (not data) — they switch from hardcoded hex to `var(--surface)`/`var(--text-muted)`/`var(--text)` so the hole blends seamlessly with the `<Card>` it now sits inside. The 10-year bar chart's default bar fill becomes `color-mix(in srgb, var(--accent) 35%, var(--surface))` (a muted accent, replacing the old muted blue-purple); `.bar.highlight` and `.bar-label.current-label` (chrome emphasis, not data) become `var(--accent)`. The two "stat chips" (10-year avg, last complete year) stay native rather than converting to `<StatTile>`, because the second chip embeds a color-coded inline year-over-year delta (`.yoy.up`/`.yoy.down`) that `StatTile`'s plain `value: string|number` prop can't express without expanding that component's API — per the project's standing guidance to avoid expanding an approved component's API surface for a non-essential cosmetic gain. The YoY indicator's up/down colors DO map cleanly onto existing semantic tokens (cost increase = `var(--danger)`, decrease = `var(--success)`) so those convert. The whole chart section is wrapped in a `<Card>` for the first time (previously a flush flat section); the toolbar's search becomes `<Input>`, category/year selects stay native, "+ Add entry" becomes `<Button>`. Table chrome follows the same token treatment as `InventoryPage`'s table.

- [ ] **Step 1: Replace the entire file content**

```svelte
<!-- packages/editor/src/lib/components/CostsPage.svelte -->
<script lang="ts">
  import type { createCostsStore, CostEntry, CategoryBreakdown } from "../costsStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { createHouseStore } from "../houseStore.svelte";
  import CostsEntryModal from "./CostsEntryModal.svelte";
  import CostsCategoryModal from "./CostsCategoryModal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import Card from "./ui/Card.svelte";

  type CostsStore = ReturnType<typeof createCostsStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;
  type HouseStore = ReturnType<typeof createHouseStore>;

  interface Props {
    costsStore: CostsStore;
    settingsStore: SettingsStore;
    floorStore: HouseStore;
    onplaceonmap?: (catId: string) => void;
  }

  let { costsStore, settingsStore, floorStore, onplaceonmap }: Props = $props();

  let modalEntry = $state<CostEntry | "create" | null>(null);
  let chartModalCategoryId = $state<string | null>(null);
  let searchQuery = $state("");
  let categoryFilter = $state("");
  let yearFilter = $state("");

  const categoryMap = $derived(
    new Map(settingsStore.costCategories.map(c => [c.id, c]))
  );
  const supplierMap = $derived(
    new Map(settingsStore.suppliers.map(s => [s.id, s]))
  );

  function categoryName(categoryId: string): string {
    return categoryMap.get(categoryId)?.name ?? "Unknown";
  }

  function categoryEmoji(categoryId: string): string {
    return categoryMap.get(categoryId)?.emoji ?? "?";
  }

  function categoryUnit(categoryId: string): string | null {
    return categoryMap.get(categoryId)?.unit ?? null;
  }

  function roomName(roomId: string | null | undefined): string {
    if (!roomId) return "—";
    for (const floor of floorStore.floors) {
      const room = floor.rooms.find((r: { id: string; label: string }) => r.id === roomId);
      if (room) return room.label || roomId;
    }
    return "—";
  }

  function formatQty(entry: CostEntry): string {
    if (entry.quantity == null) return "—";
    const unit = categoryUnit(entry.categoryId);
    return unit ? `${entry.quantity.toLocaleString()} ${unit}` : String(entry.quantity);
  }

  function formatUnitPrice(entry: CostEntry): string {
    if (entry.unitPrice == null) return "—";
    const unit = categoryUnit(entry.categoryId);
    return unit ? `${entry.unitPrice} €/${unit}` : `${entry.unitPrice} €`;
  }

  const allYears = $derived(
    [...new Set(costsStore.entries.map(e => new Date(e.date).getFullYear()))].sort((a, b) => b - a)
  );

  const filtered = $derived(
    costsStore.entries.filter(e => {
      if (categoryFilter && e.categoryId !== categoryFilter) return false;
      if (yearFilter && new Date(e.date).getFullYear() !== parseInt(yearFilter)) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const name = categoryName(e.categoryId).toLowerCase();
        const sup = (e.supplierId ? (supplierMap.get(e.supplierId)?.name ?? "") : "").toLowerCase();
        const notes = e.notes.toLowerCase();
        if (!name.includes(q) && !sup.includes(q) && !notes.includes(q)) return false;
      }
      return true;
    }).sort((a, b) => b.date.localeCompare(a.date))
  );

  const filteredTotal = $derived(
    filtered.reduce((sum, e) => sum + e.totalAmount, 0)
  );

  const hasEntries = $derived(costsStore.entries.length > 0);

  // --- Chart helpers ---

  interface Slice {
    cat: CategoryBreakdown;
    startDeg: number;
    endDeg: number;
    midDeg: number;
  }

  function polarPoint(cx: number, cy: number, r: number, angleDeg: number) {
    const rad = angleDeg * Math.PI / 180;
    return { x: cx + r * Math.sin(rad), y: cy - r * Math.cos(rad) };
  }

  function donutPath(cx: number, cy: number, outerR: number, innerR: number, startDeg: number, endDeg: number): string {
    const clampedEnd = Math.min(startDeg + 359.99, endDeg);
    const os = polarPoint(cx, cy, outerR, startDeg);
    const oe = polarPoint(cx, cy, outerR, clampedEnd);
    const is = polarPoint(cx, cy, innerR, startDeg);
    const ie = polarPoint(cx, cy, innerR, clampedEnd);
    const large = (clampedEnd - startDeg) > 180 ? 1 : 0;
    return [
      `M ${os.x.toFixed(2)} ${os.y.toFixed(2)}`,
      `A ${outerR} ${outerR} 0 ${large} 1 ${oe.x.toFixed(2)} ${oe.y.toFixed(2)}`,
      `L ${ie.x.toFixed(2)} ${ie.y.toFixed(2)}`,
      `A ${innerR} ${innerR} 0 ${large} 0 ${is.x.toFixed(2)} ${is.y.toFixed(2)}`,
      "Z",
    ].join(" ");
  }

  const PIE_CX = 155;
  const PIE_CY = 110;
  const PIE_OUTER_R = 70;
  const PIE_INNER_R = 28;

  const breakdown = $derived(costsStore.breakdownLastCompleteYear(settingsStore.costCategories));
  const yearlyTotals = $derived(costsStore.totalByYear());
  const lastCompleteYearNum = $derived(costsStore.lastCompleteYear());

  const slices = $derived((() => {
    let angle = 0;
    return breakdown.map(cat => {
      const start = angle;
      const span = (cat.pct / 100) * 360;
      angle += span;
      return { cat, startDeg: start, endDeg: angle, midDeg: start + span / 2 } as Slice;
    });
  })());

  const currentYear = new Date().getFullYear();
  const chartYears = $derived((() => {
    const years: number[] = [];
    const from = currentYear - 9;
    for (let y = from; y <= currentYear; y++) years.push(y);
    return years;
  })());

  const maxBarAmount = $derived(
    Math.max(...chartYears.map(y => yearlyTotals.get(y) ?? 0), 1)
  );

  function barHeight(year: number, maxPx: number): number {
    const amt = yearlyTotals.get(year) ?? 0;
    return Math.round((amt / maxBarAmount) * maxPx);
  }

  function formatK(n: number): string {
    return n >= 1000 ? `${(n / 1000).toFixed(0)}k` : String(Math.round(n));
  }

  const tenYearAvg = $derived((() => {
    const completeYears = chartYears.filter(y => y < currentYear && (yearlyTotals.get(y) ?? 0) > 0);
    if (completeYears.length === 0) return 0;
    const sum = completeYears.reduce((a, y) => a + (yearlyTotals.get(y) ?? 0), 0);
    return sum / completeYears.length;
  })());

  const lastCompleteTotal = $derived(yearlyTotals.get(lastCompleteYearNum) ?? 0);
  const prevYearTotal = $derived(yearlyTotals.get(lastCompleteYearNum - 1) ?? 0);
  const yoyPct = $derived(
    prevYearTotal > 0 ? Math.round(((lastCompleteTotal - prevYearTotal) / prevYearTotal) * 100) : null
  );
</script>

<div class="page">

  <!-- Chart section -->
  {#if !hasEntries}
    <div class="empty-charts">
      <span class="empty-icon">💶</span>
      <p>No entries yet — click ＋ Add entry to get started.</p>
    </div>
  {:else}
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-inner">

          <!-- Pie chart with connector labels -->
          <div class="pie-area">
            <div class="chart-label">
              {lastCompleteYearNum} — breakdown by category
            </div>
            <svg
              viewBox="0 0 310 220"
              width="310"
              height="220"
              style="overflow:visible"
            >
              <!-- Slices -->
              {#each slices as s (s.cat.categoryId)}
                <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
                <path
                  d={donutPath(PIE_CX, PIE_CY, PIE_OUTER_R, PIE_INNER_R, s.startDeg, s.endDeg)}
                  fill={s.cat.color}
                  opacity="0.9"
                  style="cursor:pointer"
                  onclick={() => { chartModalCategoryId = s.cat.categoryId; }}
                />
              {/each}

              <!-- Donut hole -->
              <circle cx={PIE_CX} cy={PIE_CY} r={PIE_INNER_R} fill="var(--surface)" />
              <text x={PIE_CX} y={PIE_CY - 6} text-anchor="middle" fill="var(--text-muted)" font-size="8" font-family="sans-serif">Total</text>
              <text x={PIE_CX} y={PIE_CY + 8} text-anchor="middle" fill="var(--text)" font-size="11" font-family="sans-serif" font-weight="600">
                {breakdown.reduce((a, b) => a + b.totalAmount, 0).toLocaleString(undefined, { maximumFractionDigits: 0 })} €
              </text>

              <!-- Connector lines + labels -->
              {#each slices as s (s.cat.categoryId + "-label")}
                {@const mid = polarPoint(PIE_CX, PIE_CY, PIE_OUTER_R + 4, s.midDeg)}
                {@const elbow = polarPoint(PIE_CX, PIE_CY, PIE_OUTER_R + 18, s.midDeg)}
                {@const isRight = elbow.x >= PIE_CX}
                {@const lineEnd = { x: elbow.x + (isRight ? 28 : -28), y: elbow.y }}
                {@const textX = lineEnd.x + (isRight ? 4 : -4)}
                <line x1={mid.x} y1={mid.y} x2={elbow.x} y2={elbow.y} stroke={s.cat.color} stroke-width="1" opacity="0.7" />
                <line x1={elbow.x} y1={elbow.y} x2={lineEnd.x} y2={lineEnd.y} stroke={s.cat.color} stroke-width="1" opacity="0.7" />
                <circle cx={mid.x} cy={mid.y} r="2" fill={s.cat.color} />
                <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
                <text
                  x={textX}
                  y={elbow.y - 3}
                  text-anchor={isRight ? "start" : "end"}
                  fill={s.cat.color}
                  font-size="9"
                  font-family="sans-serif"
                  font-weight="600"
                  style="cursor:pointer"
                  onclick={() => { chartModalCategoryId = s.cat.categoryId; }}
                >{s.cat.emoji} {s.cat.name}</text>
                <text
                  x={textX}
                  y={elbow.y + 9}
                  text-anchor={isRight ? "start" : "end"}
                  fill="var(--text-faint)"
                  font-size="8"
                  font-family="sans-serif"
                >{s.cat.totalAmount.toLocaleString(undefined, { maximumFractionDigits: 0 })} € · {s.cat.pct.toFixed(0)}%</text>
              {/each}
            </svg>
          </div>

          <div class="chart-divider"></div>

          <!-- 10-year total bar chart -->
          <div class="bar-area">
            <div class="chart-label">Total house costs — last 10 years (€)</div>
            <div class="bar-chart-wrap">
              <div class="y-axis">
                <span>{formatK(maxBarAmount)}</span>
                <span>{formatK(Math.round(maxBarAmount / 2))}</span>
                <span>0</span>
              </div>
              <div class="bars">
                {#each chartYears as y}
                  {@const h = barHeight(y, 100)}
                  {@const isLastComplete = y === lastCompleteYearNum}
                  {@const isCurrent = y === currentYear}
                  {@const hasData = (yearlyTotals.get(y) ?? 0) > 0}
                  <div class="bar-col">
                    <div
                      class="bar"
                      class:highlight={isLastComplete}
                      class:partial={isCurrent}
                      class:empty={!hasData}
                      style="height:{h}px"
                      title="{y}: {(yearlyTotals.get(y) ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })} €"
                    ></div>
                    <span class="bar-label" class:current-label={isCurrent}>{y}</span>
                  </div>
                {/each}
              </div>
            </div>
            <div class="stat-chips">
              <div class="stat-chip">
                <div class="stat-title">10-year avg</div>
                <div class="stat-value">{tenYearAvg.toLocaleString(undefined, { maximumFractionDigits: 0 })} €/yr</div>
              </div>
              <div class="stat-chip">
                <div class="stat-title">Last complete yr</div>
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
  {/if}

  <!-- Toolbar -->
  <div class="toolbar">
    <Input bind:value={searchQuery} placeholder="🔍 Search entries…" />
    <select class="native-input" bind:value={categoryFilter}>
      <option value="">All categories</option>
      {#each settingsStore.costCategories as cat}
        <option value={cat.id}>{cat.emoji} {cat.name}</option>
      {/each}
    </select>
    <select class="native-input" bind:value={yearFilter}>
      <option value="">All years</option>
      {#each allYears as y}
        <option value={String(y)}>{y}</option>
      {/each}
    </select>
    <Button onclick={() => { modalEntry = "create"; }}>＋ Add entry</Button>
  </div>

  <!-- Table -->
  <div class="table-wrapper">
    <table>
      <thead>
        <tr>
          <th></th>
          <th>Category</th>
          <th>Date</th>
          <th>Supplier</th>
          <th class="num-col">Qty</th>
          <th class="num-col">Unit price</th>
          <th class="num-col">Total</th>
          <th>Room</th>
        </tr>
      </thead>
      <tbody>
        {#each filtered as entry (entry.id)}
          <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
          <tr onclick={() => { modalEntry = entry; }}>
            <td class="emoji-cell">{categoryEmoji(entry.categoryId)}</td>
            <td class="name-cell">{categoryName(entry.categoryId)}</td>
            <td>{entry.date}</td>
            <td>{entry.supplierId ? (supplierMap.get(entry.supplierId)?.name ?? "—") : "—"}</td>
            <td class="num-col">{formatQty(entry)}</td>
            <td class="num-col">{formatUnitPrice(entry)}</td>
            <td class="num-col amount-cell">{entry.totalAmount.toLocaleString()} €</td>
            <td>{roomName(entry.roomId)}</td>
          </tr>
        {/each}
        {#if filtered.length === 0}
          <tr>
            <td colspan="8" class="empty">
              {costsStore.entries.length === 0
                ? "No entries yet — click ＋ Add entry to get started."
                : "No entries match your filters."}
            </td>
          </tr>
        {/if}
      </tbody>
    </table>
  </div>

  <div class="footer">
    {filtered.length} entr{filtered.length !== 1 ? "ies" : "y"}
    {#if filteredTotal > 0}
      · total: {filteredTotal.toLocaleString(undefined, { maximumFractionDigits: 0 })} €
    {/if}
  </div>
</div>

{#if modalEntry}
  <CostsEntryModal
    entry={modalEntry === "create" ? null : modalEntry}
    {costsStore}
    {settingsStore}
    {floorStore}
    onclose={() => { modalEntry = null; }}
  />
{/if}

{#if chartModalCategoryId}
  <CostsCategoryModal
    categoryId={chartModalCategoryId}
    {costsStore}
    {settingsStore}
    onclose={() => { chartModalCategoryId = null; }}
    {onplaceonmap}
  />
{/if}

<style>
  .page {
    display: flex; flex-direction: column; height: 100%;
    background: var(--bg); font-family: var(--font-sans);
  }

  .empty-charts {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 32px; gap: 10px; color: var(--text-faint); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .empty-icon { font-size: 36px; }
  .empty-charts p { margin: 0; font-size: 13px; }

  .chart-card-wrap { padding: var(--space-4) var(--space-4) 0; flex-shrink: 0; }
  .chart-inner {
    display: flex; gap: 24px; align-items: flex-start;
  }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }
  .pie-area { flex-shrink: 0; }
  .chart-divider { width: 1px; background: var(--border); align-self: stretch; flex-shrink: 0; margin: 0 8px; }

  .bar-area { flex: 1; min-width: 0; }
  .bar-chart-wrap { display: flex; align-items: flex-end; gap: 4px; height: 120px; }
  .y-axis {
    display: flex; flex-direction: column; justify-content: space-between;
    align-items: flex-end; height: 100px; padding-bottom: 16px;
    font-size: 8px; color: var(--text-faint); flex-shrink: 0; padding-right: 4px;
  }
  .bars { display: flex; align-items: flex-end; gap: 4px; flex: 1; height: 100%; padding-bottom: 16px; border-bottom: 1px solid var(--border); border-left: 1px solid var(--border); }
  .bar-col { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; flex: 1; height: 100%; gap: 2px; }
  .bar { width: 100%; border-radius: 2px 2px 0 0; background: color-mix(in srgb, var(--accent) 35%, var(--surface)); min-height: 2px; transition: height .2s; }
  .bar.highlight { background: var(--accent); }
  .bar.partial { background: var(--surface-alt); outline: 1px dashed var(--accent); opacity: .8; }
  .bar.empty { background: transparent; }
  .bar-label { font-size: 7px; color: var(--text-faint); white-space: nowrap; }
  .bar-label.current-label { color: var(--accent); }

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

  .toolbar {
    display: flex; align-items: center; gap: var(--space-2); padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .toolbar :global(.ui-input) { flex: 1; }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px;
    font-family: var(--font-sans); box-sizing: border-box; cursor: pointer;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }

  .table-wrapper { flex: 1; overflow-y: auto; }
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
  .emoji-cell { font-size: 15px; width: 28px; text-align: center; }
  .name-cell { color: var(--text); }
  .amount-cell { color: var(--text); }
  .empty { text-align: center; color: var(--text-faint); padding: 32px; }

  .footer {
    padding: 6px 12px; font-size: 11px; color: var(--text-faint);
    border-top: 1px solid var(--border); flex-shrink: 0;
  }
</style>
```

- [ ] **Step 2: Run the full test suite**

Run: `cd packages/editor && npm test -- --run`
Expected: 162/162 passing (no test imports this component directly; this guards against regressions elsewhere).

- [ ] **Step 3: Manually sanity-check in the browser**

Run `npm run dev` in `packages/editor`, open the route for this page, and toggle the theme switcher between light and dark. Confirm: no leftover hardcoded-dark rectangles, search/select/buttons are legible and themed in both modes, and clicking through to any modal still opens correctly.

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/CostsPage.svelte
git commit -m "feat(editor): migrate CostsPage.svelte onto Card/Button/Input/tokens"
```

---

## Final Step: Holistic Review

After all 7 tasks are complete and individually committed:

- [ ] **Dispatch a final code-reviewer subagent** to review the entire diff against the parent commit (the Phase 4 worktree's branch point). It should check:
  - No hardcoded hex colors remain in any of the 7 files **except** the explicitly-preserved data/status colors documented in the Architecture section above (`warrantyChip`, `statusColor`, `cat.color`, `store.getColor`).
  - No `Props` interface on any of the 7 page components changed (same prop names/types/optionality as before).
  - No parent/consumer file (`App.svelte` or wherever these pages are mounted) needed changes — confirm by grepping for each page component's name outside its own file.
  - `npm test -- --run` passes 162/162.
  - `svelte-check` shows no new errors beyond the pre-existing unrelated ones already present on `main`.
- [ ] Fix any issues the reviewer raises, re-review, repeat until approved.
- [ ] Use **superpowers:finishing-a-development-branch** to present the 4 standard options (merge locally / push+PR / keep as-is / discard) and complete the branch per the user's choice.

## Spec coverage checklist (self-review)

- [x] `InventoryPage.svelte` — Task 4
- [x] `ChoresPage.svelte` — Task 5
- [x] `ChoreListPage.svelte` — Task 3
- [x] `CostsPage.svelte` — Task 7
- [x] `WorksPage.svelte` — Task 2
- [x] `SettingsPage.svelte` — Task 6
- [x] `ConsumablesPage.svelte` — Task 1
- [x] "migrated onto Card/StatTile/Button/tokens" — Card used in Tasks 1(n/a, stub has no card-worthy content),5,6,7; Button used in Tasks 1(n/a),2,4,5,6,7; StatTile considered and explicitly *not* used in Task 7 with documented rationale (no other page has a stat-tile-shaped UI element); tokens used in all 7.
- [x] "existing tables/charts keep their current data logic, only visual styling changes" — confirmed no `$derived`, store method, or business-logic function signature changes in any task; only `<script>` imports (new UI component imports) were added, all existing logic reproduced verbatim.
- [x] No placeholders, TBDs, or "similar to Task N" shortcuts — every task embeds the complete literal file content.
