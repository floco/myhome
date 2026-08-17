<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createWorksStore, Work } from "../worksStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { createContactsStore } from "../contactsStore.svelte";
  import WorkModal from "./WorkModal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import SortableTable from "./ui/SortableTable.svelte";
  import type { Column } from "./ui/SortableTable.types";
  import Card from "./ui/Card.svelte";
  import StatTile from "./ui/StatTile.svelte";
  import WorksTimeline from "./WorksTimeline.svelte";
  import Modal from "./ui/Modal.svelte";
  import FilterButton from "./ui/FilterButton.svelte";

  type WorksStore = ReturnType<typeof createWorksStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;
  type ContactsStore = ReturnType<typeof createContactsStore>;

  interface Props {
    store: WorksStore;
    settingsStore: SettingsStore;
    contactsStore: ContactsStore;
    onplaceonmap?: (workId: string) => void;
    selectedItemId?: string | null;
    onclearselection?: () => void;
  }

  let { store, settingsStore, contactsStore, onplaceonmap, selectedItemId = null, onclearselection }: Props = $props();

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
  let filterModalOpen = $state(false);
  const filtersActive = $derived(statusFilter !== "" || categoryFilter !== "");

  const categoryMap = $derived(
    new Map(settingsStore.workCategories.map(c => [c.id, c]))
  );
  const supplierMap = $derived(
    new Map(contactsStore.contacts.map(c => [c.id, c]))
  );

  const filteredWorks = $derived(store.works.filter(w => {
    if (statusFilter && w.status !== statusFilter) return false;
    if (categoryFilter && w.categoryId !== categoryFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (!w.title.toLowerCase().includes(q) && !w.description.toLowerCase().includes(q)) return false;
    }
    return true;
  }).sort((a, b) => {
    // Default order (before the user picks a column to sort by): work
    // still to be done outranks work that's done, and within each group
    // the most recent date comes first.
    const aNotDone = a.status === "done" ? 0 : 1;
    const bNotDone = b.status === "done" ? 0 : 1;
    if (aNotDone !== bNotDone) return bNotDone - aNotDone;
    const aTime = a.date ? new Date(a.date).getTime() : 0;
    const bTime = b.date ? new Date(b.date).getTime() : 0;
    return bTime - aTime;
  }));

  const totalCost = $derived(
    filteredWorks.reduce((sum, w) => sum + (w.totalCost ?? 0), 0)
  );

  const allTimeCost = $derived(store.works.reduce((sum, w) => sum + (w.totalCost ?? 0), 0));

  const yearsSpan = $derived.by(() => {
    if (store.works.length === 0) return 0;
    const times = store.works.map((w) => new Date(w.date).getTime());
    const spanMs = Math.max(...times) - Math.min(...times);
    return Math.floor(spanMs / (1000 * 60 * 60 * 24 * 365.25));
  });

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
      <Card style="flex:1; min-width:0;">
        <div class="chart-label">{$_('works.page.houseTimeline')}</div>
        <WorksTimeline works={store.works} onworkclick={handleTimelineClick} />
      </Card>
      <div class="stat-tiles">
        <StatTile label={$_('works.page.yearsSpan')} value={yearsSpan} />
        <StatTile label={$_('works.page.totalCost')} value={`${fmt(allTimeCost)} €`} />
      </div>
    </div>
  {/if}

  <div class="table-card-wrap">
    <Card style="display:flex; flex-direction:column; padding:0; overflow:hidden; flex:1; min-height:0;">
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

    <div class="table-wrapper">
      {#snippet emojiCell(work: Work)}
        {categoryMap.get(work.categoryId ?? "")?.emoji ?? "🔧"}
      {/snippet}
      {#snippet titleCell(work: Work)}
        <div class="title-desc">
          {work.title}
          {#if work.description}<span class="desc">{work.description}</span>{/if}
        </div>
      {/snippet}
      {#snippet categoryCell(work: Work)}
        {categoryMap.get(work.categoryId ?? "")?.name ?? "—"}
      {/snippet}
      {#snippet dateCell(work: Work)}
        {work.date}
      {/snippet}
      {#snippet supplierCell(work: Work)}
        {supplierMap.get(work.contactId ?? "")?.name ?? "—"}
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
          { key: "category", label: $_('costs.page.category'), sortValue: (w) => categoryMap.get(w.categoryId ?? "")?.name ?? null, cell: categoryCell, hideBelow: "mobile" },
          { key: "date", label: $_('costs.page.date'), sortValue: (w) => (w.date ? new Date(w.date) : null), cell: dateCell, hideBelow: "tablet" },
          { key: "supplier", label: $_('costs.page.supplier'), sortValue: (w) => supplierMap.get(w.contactId ?? "")?.name ?? null, cell: supplierCell, hideBelow: "tablet" },
          { key: "cost", label: $_('inventory.page.cost'), sortValue: (w) => w.totalCost, cell: costCell, hideBelow: "mobile" },
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
    {contactsStore}
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
  .title-desc {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .desc { font-size: 11px; color: var(--text-faint); font-weight: 400; margin-left: 6px; }
  .status-chip { padding: 2px 7px; border-radius: var(--radius-sm); font-size: 10px; font-weight: 500; }
  .pin-indicator { font-size: 11px; margin-left: 4px; }

  .footer { padding: var(--space-2) var(--space-4); border-top: 1px solid var(--border); font-size: 11px; color: var(--text-faint); flex-shrink: 0; }
</style>
