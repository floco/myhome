<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createWorksStore, Work } from "../worksStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import WorkModal from "./WorkModal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import SortableTable from "./ui/SortableTable.svelte";
  import type { Column } from "./ui/SortableTable.types";
  import Card from "./ui/Card.svelte";
  import WorksTimeline from "./WorksTimeline.svelte";

  type WorksStore = ReturnType<typeof createWorksStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    store: WorksStore;
    settingsStore: SettingsStore;
    onplaceonmap?: (workId: string) => void;
    selectedItemId?: string | null;
    onclearselection?: () => void;
  }

  let { store, settingsStore, onplaceonmap, selectedItemId = null, onclearselection }: Props = $props();

  let modalWork = $state<Work | "create" | null>(null);

  $effect(() => {
    if (selectedItemId) {
      const found = store.works.find((w) => w.id === selectedItemId);
      if (found) {
        modalWork = found;
        onclearselection?.();
      }
    }
  });

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

  const plannedCount = $derived(store.works.filter((w) => w.status === "planned").length);
  const inProgressCount = $derived(store.works.filter((w) => w.status === "in_progress").length);
  const doneCount = $derived(store.works.filter((w) => w.status === "done").length);
  const allTimeCost = $derived(store.works.reduce((sum, w) => sum + (w.totalCost ?? 0), 0));

  function handleTimelineClick(id: string): void {
    const found = store.works.find((w) => w.id === id);
    if (found) modalWork = found;
  }

  function statusLabel(status: Work["status"]): string {
    if (status === "in_progress") return $_("works.status.inProgress");
    if (status === "done") return $_("works.status.done");
    return $_("works.status.planned");
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

  {#if store.works.length === 0}
    <div class="empty-charts">
      <span class="empty-icon">🔧</span>
      <p>{$_('works.page.emptyCharts')}</p>
    </div>
  {:else}
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
  {/if}

  <div class="table-card-wrap">
    <Card style="display:flex; flex-direction:column; padding:0; overflow:hidden; flex:1; min-height:0;">
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
        {#if work.placement}<span class="pin-indicator" title={$_('works.page.pinned')}>📍</span>{/if}
      {/snippet}

      <SortableTable
        columns={[
          { key: "emoji", label: "", sortable: false, cellClass: "emoji-cell", cell: emojiCell },
          { key: "title", label: $_('works.page.title'), sortValue: (w) => w.title, cellClass: "name-cell", cell: titleCell },
          { key: "category", label: $_('costs.page.category'), sortValue: (w) => categoryMap.get(w.categoryId ?? "")?.name ?? null, cell: categoryCell },
          { key: "date", label: $_('costs.page.date'), sortValue: (w) => (w.date ? new Date(w.date) : null), cell: dateCell },
          { key: "supplier", label: $_('costs.page.supplier'), sortValue: (w) => supplierMap.get(w.supplierId ?? "")?.name ?? null, cell: supplierCell },
          { key: "cost", label: $_('inventory.page.cost'), sortValue: (w) => w.totalCost, cell: costCell },
          { key: "status", label: $_('works.page.status'), sortValue: (w) => w.status, cell: statusCell },
        ] as Column<Work>[]}
        rows={filteredWorks}
        rowKey={(work) => work.id}
        rowClick={(work) => { modalWork = work; }}
        emptyMessage={store.works.length === 0 ? $_('works.page.emptyNoWorks') : $_('works.page.emptyNoMatch')}
      />
    </div>

    <div class="footer">{$_('works.page.footer', { values: { n: filteredWorks.length, total: fmt(totalCost) } })}</div>
    </Card>
  </div>
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
  .filter-sel { cursor: pointer; }

  .table-wrapper { flex: 1; overflow-y: auto; }
  :global(.emoji-cell) { font-size: 16px; width: 32px; text-align: center; }
  :global(.name-cell) { color: var(--text); font-weight: 600; }
  .desc { font-size: 11px; color: var(--text-faint); font-weight: 400; margin-left: 6px; }
  .status-chip { padding: 2px 7px; border-radius: var(--radius-sm); font-size: 10px; font-weight: 500; }
  .pin-indicator { font-size: 11px; margin-left: 4px; }

  .footer { padding: var(--space-2) var(--space-4); border-top: 1px solid var(--border); font-size: 11px; color: var(--text-faint); flex-shrink: 0; }
</style>
