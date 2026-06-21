<!-- packages/editor/src/lib/components/WorksPage.svelte -->
<script lang="ts">
  import type { createWorksStore, Work } from "../worksStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import WorkModal from "./WorkModal.svelte";

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
    <input class="search" placeholder="🔍 Search…" bind:value={searchQuery} />
    <select class="filter-sel" bind:value={statusFilter}>
      <option value="">All statuses</option>
      <option value="planned">Planned</option>
      <option value="in_progress">In progress</option>
      <option value="done">Done</option>
    </select>
    <select class="filter-sel" bind:value={categoryFilter}>
      <option value="">All categories</option>
      {#each settingsStore.workCategories as cat}
        <option value={cat.id}>{cat.emoji} {cat.name}</option>
      {/each}
    </select>
    <button class="add-btn" onclick={() => { modalWork = "create"; }}>＋ Add work</button>
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
  .page { display: flex; flex-direction: column; height: 100%; background: #141428; font-family: sans-serif; }

  .toolbar {
    display: flex; gap: 8px; padding: 10px 16px;
    border-bottom: 1px solid #2a2a4a; flex-shrink: 0; align-items: center;
  }
  .search {
    flex: 1; background: #111128; border: 1px solid #2a2a4a; color: #ccc;
    padding: 5px 10px; border-radius: 4px; font-size: 12px;
  }
  .filter-sel {
    background: #111128; border: 1px solid #2a2a4a; color: #aaa;
    padding: 5px 8px; border-radius: 4px; font-size: 11px; cursor: pointer;
  }
  .add-btn {
    background: #3344aa; color: #ccf; border: none;
    padding: 5px 14px; border-radius: 4px; font-size: 12px; cursor: pointer; white-space: nowrap;
  }
  .add-btn:hover { background: #4455bb; }

  .list { flex: 1; overflow-y: auto; padding: 12px 16px; display: flex; flex-direction: column; gap: 8px; }
  .empty { color: #445; font-size: 13px; text-align: center; padding: 40px 0; }

  .card {
    background: #111128; border: 1px solid #2a2a4a; border-left-width: 3px;
    border-radius: 6px; padding: 10px 14px; cursor: pointer;
  }
  .card:hover { background: #161638; }
  .card-top { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
  .cat-emoji { font-size: 16px; flex-shrink: 0; }
  .card-title { font-size: 13px; color: #eee; font-weight: 600; flex: 1; }
  .status-chip { padding: 2px 7px; border-radius: 3px; font-size: 10px; font-weight: 500; flex-shrink: 0; }
  .card-meta { display: flex; gap: 12px; font-size: 11px; color: #556; flex-wrap: wrap; }
  .pin-indicator { font-size: 11px; }
  .card-desc { font-size: 11px; color: #445; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  .footer { padding: 8px 16px; border-top: 1px solid #2a2a4a; font-size: 11px; color: #445; flex-shrink: 0; }
</style>
