<script lang="ts">
  import type { createWorksStore, Work } from "../worksStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import WorkModal from "./WorkModal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import SortableTable from "./ui/SortableTable.svelte";
  import type { Column } from "./ui/SortableTable.types";

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
